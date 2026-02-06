"""
TradingAgent — autonomous trading unit with full lifecycle management.

Each agent owns:
  • A BaseStrategy instance
  • An AgentConfig (symbols, risk, interval)
  • An AgentState (P&L, trades, metrics)
  • An asyncio task that ticks at config.scan_interval_seconds
"""

from __future__ import annotations

import asyncio
import enum
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from app.agents.agent_config import AgentConfig
from app.agents.agent_state import AgentState, AgentTradeRecord
from app.agents.base_strategy import BaseStrategy
from app.brokers.base import BrokerInterface, OrderRequest
from app.risk.kill_switch import is_kill_switch_active
from app.risk.limits import check_daily_loss_limit
from app.storage.state import get_session_state
from app.strategy.signal_schema import Signal

logger = logging.getLogger(__name__)


class AgentStatus(str, enum.Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"


class TradingAgent:
    """Autonomous trading agent with lifecycle management."""

    def __init__(
        self,
        agent_id: str,
        name: str,
        strategy: BaseStrategy,
        config: AgentConfig,
    ) -> None:
        self.id = agent_id
        self.name = name
        self.strategy = strategy
        self.config = config
        self.state = AgentState(agent_id=agent_id)
        self.status = AgentStatus.IDLE
        self._task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()
        self._pause_event = asyncio.Event()
        self._pause_event.set()  # not paused initially
        self.created_at = datetime.now(timezone.utc).isoformat()

    # ── Lifecycle ──────────────────────────────────────────────

    async def start(self, broker: BrokerInterface) -> None:
        """Start the agent's tick loop."""
        if self.status == AgentStatus.RUNNING:
            logger.warning("[%s] Already running.", self.id)
            return
        self._stop_event.clear()
        self._pause_event.set()
        self.status = AgentStatus.RUNNING
        self._task = asyncio.create_task(self._run_loop(broker), name=f"agent-{self.id}")
        logger.info("[%s] Started (strategy=%s, symbols=%s).", self.id, self.strategy.name, self.config.symbols)

    async def stop(self) -> None:
        """Stop the agent gracefully."""
        self._stop_event.set()
        self._pause_event.set()  # unblock if paused
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self.status = AgentStatus.STOPPED
        logger.info("[%s] Stopped.", self.id)

    async def pause(self) -> None:
        """Pause the agent (blocks tick loop)."""
        self._pause_event.clear()
        self.status = AgentStatus.PAUSED
        logger.info("[%s] Paused.", self.id)

    async def resume(self) -> None:
        """Resume a paused agent."""
        self._pause_event.set()
        self.status = AgentStatus.RUNNING
        logger.info("[%s] Resumed.", self.id)

    # ── Main loop ─────────────────────────────────────────────

    async def _run_loop(self, broker: BrokerInterface) -> None:
        """Background tick loop."""
        try:
            while not self._stop_event.is_set():
                await self._pause_event.wait()
                if self._stop_event.is_set():
                    break
                try:
                    await self.tick(broker)
                except Exception as exc:
                    self.state.record_error(str(exc))
                    logger.error("[%s] Tick error: %s", self.id, exc, exc_info=True)
                await asyncio.sleep(self.config.scan_interval_seconds)
        except asyncio.CancelledError:
            pass
        finally:
            if self.status != AgentStatus.STOPPED:
                self.status = AgentStatus.STOPPED

    async def tick(self, broker: BrokerInterface) -> List[Signal]:
        """Single execution cycle: generate signals → risk check → place orders."""
        self.state.last_tick_at = datetime.now(timezone.utc).isoformat()

        # Kill switch check
        if is_kill_switch_active():
            logger.warning("[%s] Kill switch active — skipping tick.", self.id)
            return []

        # Global daily loss check
        session = get_session_state()
        dl_check = check_daily_loss_limit(session.daily_pnl)
        if not dl_check.passed:
            logger.warning("[%s] Global daily loss limit hit — skipping.", self.id)
            return []

        # Per-agent risk budget check
        if self.state.daily_pnl <= -abs(self.config.risk_budget):
            logger.warning("[%s] Agent risk budget exhausted ($%.2f).", self.id, self.state.daily_pnl)
            return []

        # Generate signals
        params = self.strategy.get_effective_params(self.config.params)
        signals = await self.strategy.generate_signals(self.config.symbols, broker, params)

        # Filter by min confidence and non-neutral
        actionable = [
            s for s in signals
            if s.direction != "neutral" and s.confidence >= self.config.min_confidence
        ]

        # Check position limits
        if self.state.open_position_count >= self.config.max_positions:
            logger.info("[%s] Max positions reached (%d) — no new entries.", self.id, self.config.max_positions)
            return signals

        for sig in actionable:
            if self.state.open_position_count >= self.config.max_positions:
                break
            await self._execute_signal(sig, broker)

        return signals

    async def _execute_signal(self, sig: Signal, broker: BrokerInterface) -> None:
        """Convert a signal into an order and submit it."""
        side = "buy" if sig.direction == "long" else "sell"
        client_oid = f"sbf_{self.id}_{uuid4().hex[:8]}"

        # Simple position sizing based on risk budget
        risk_per_share = abs(sig.stop_level - (sig.metadata.get("current_price", 0) or 0)) if sig.stop_level else 1.0
        risk_per_share = max(risk_per_share, 0.01)
        qty = max(1, int(self.config.max_risk_per_trade / risk_per_share))

        order = OrderRequest(
            symbol=sig.symbol, side=side, qty=qty,
            order_type="market", client_order_id=client_oid,
        )
        try:
            result = await broker.place_order(order)
            trade = AgentTradeRecord(
                symbol=sig.symbol, side=side, qty=qty,
                entry_price=result.avg_fill_price or 0.0,
                order_id=result.order_id, client_order_id=client_oid,
                stop_loss=sig.stop_level, target=sig.target_level,
            )
            self.state.record_trade(trade)
            logger.info("[%s] Order placed: %s %d %s (oid=%s)", self.id, side, qty, sig.symbol, result.order_id)
        except Exception as exc:
            self.state.record_error(f"Order failed for {sig.symbol}: {exc}")
            logger.error("[%s] Order failed: %s", self.id, exc)

