"""
AutonomousTrader — singleton autonomous trading loop.

Wraps the existing TradingAgent infrastructure with:
  • Toggle on/off via settings (AUTONOMOUS_MODE_ENABLED)
  • Position management (stop-loss, take-profit monitoring)
  • Kill switch integration
  • Full audit logging of every decision
  • Heartbeat / watchdog for liveness detection
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.agents.agent import AgentStatus, TradingAgent
from app.agents.agent_config import AgentConfig
from app.agents.agent_state import AgentState, AgentTradeRecord
from app.brokers.base import BrokerInterface, Position
from app.risk.kill_switch import emergency_stop, is_kill_switch_active
from app.settings import (
    get_autonomous_settings,
    get_risk_settings,
    is_autonomous_enabled,
)
from app.storage.audit_log import log_event
from app.storage.state import get_session_state
from app.strategy.signal_schema import Signal

logger = logging.getLogger(__name__)


class AutonomousTrader:
    """Singleton autonomous trading loop with position management."""

    _instance: Optional["AutonomousTrader"] = None

    def __init__(self) -> None:
        self._agent: Optional[TradingAgent] = None
        self._task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()
        self._running = False
        self._started_at: Optional[str] = None
        self._last_heartbeat: Optional[str] = None
        self._tick_count = 0
        self._position_check_count = 0

    @classmethod
    def get_instance(cls) -> "AutonomousTrader":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset singleton (for testing)."""
        cls._instance = None

    # ── Properties ──────────────────────────────────────────────

    @property
    def is_running(self) -> bool:
        return self._running and self._task is not None and not self._task.done()

    @property
    def agent(self) -> Optional[TradingAgent]:
        return self._agent

    def status(self) -> Dict[str, Any]:
        """Return full status snapshot."""
        auto_cfg = get_autonomous_settings()
        result: Dict[str, Any] = {
            "running": self.is_running,
            "enabled": is_autonomous_enabled(),
            "started_at": self._started_at,
            "last_heartbeat": self._last_heartbeat,
            "tick_count": self._tick_count,
            "position_checks": self._position_check_count,
            "config": {
                "scan_interval_seconds": auto_cfg.scan_interval_seconds,
                "max_positions": auto_cfg.max_positions,
                "risk_budget": auto_cfg.risk_budget,
                "symbols": auto_cfg.symbols,
                "strategy": auto_cfg.strategy,
                "min_confidence": auto_cfg.min_confidence,
            },
        }
        if self._agent:
            result["agent_id"] = self._agent.id
            result["agent_status"] = self._agent.status.value
            result["performance"] = self._agent.state.performance()
            result["open_trades"] = [
                t.to_dict() for t in self._agent.state.open_trades
            ]
        return result

    # ── Start / Stop ────────────────────────────────────────────

    async def start(self, broker: BrokerInterface) -> Dict[str, Any]:
        """Start autonomous trading. Returns status dict."""
        if self.is_running:
            return {"error": "Autonomous trader is already running."}

        if not is_autonomous_enabled():
            return {
                "error": (
                    "Autonomous mode is not enabled. Set "
                    "AUTONOMOUS_MODE_ENABLED=true and "
                    "AUTONOMOUS_MODE_CONFIRM=I_UNDERSTAND_AUTONOMOUS_TRADING "
                    "in .env"
                )
            }

        if is_kill_switch_active():
            return {"error": "Kill switch is active. Cannot start autonomous trading."}

        # Build agent from autonomous settings
        auto_cfg = get_autonomous_settings()
        config = AgentConfig(
            strategy_name=auto_cfg.strategy,
            symbols=auto_cfg.symbols,
            risk_budget=abs(auto_cfg.risk_budget),
            max_risk_per_trade=abs(auto_cfg.risk_budget) / auto_cfg.max_positions,
            scan_interval_seconds=auto_cfg.scan_interval_seconds,
            min_confidence=auto_cfg.min_confidence,
            max_positions=auto_cfg.max_positions,
            description="Autonomous trading agent",
        )

        # Resolve strategy
        from app.agents.registry import AgentRegistry
        registry = AgentRegistry.get_instance()
        strategy = registry.get_strategy(auto_cfg.strategy)
        if strategy is None:
            # Try to register default strategies
            await self._register_default_strategies(registry)
            strategy = registry.get_strategy(auto_cfg.strategy)
            if strategy is None:
                return {
                    "error": f"Strategy '{auto_cfg.strategy}' not registered. "
                    f"Available: {[s['name'] for s in registry.list_strategies()]}"
                }

        self._agent = TradingAgent(
            agent_id="autonomous_main",
            name="Autonomous Trader",
            strategy=strategy,
            config=config,
        )

        self._stop_event.clear()
        self._running = True
        self._started_at = datetime.now(timezone.utc).isoformat()
        self._tick_count = 0
        self._position_check_count = 0

        log_event("autonomous_start", {
            "symbols": auto_cfg.symbols,
            "strategy": auto_cfg.strategy,
            "risk_budget": auto_cfg.risk_budget,
            "scan_interval": auto_cfg.scan_interval_seconds,
            "max_positions": auto_cfg.max_positions,
        })

        self._task = asyncio.create_task(
            self._run_loop(broker), name="autonomous-trader"
        )

        logger.info(
            "AUTONOMOUS TRADER STARTED: symbols=%s strategy=%s interval=%ds",
            auto_cfg.symbols, auto_cfg.strategy, auto_cfg.scan_interval_seconds,
        )
        return self.status()

    async def stop(self) -> Dict[str, Any]:
        """Stop autonomous trading gracefully."""
        if not self.is_running:
            return {"error": "Autonomous trader is not running."}

        self._stop_event.set()
        self._running = False

        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        log_event("autonomous_stop", {
            "tick_count": self._tick_count,
            "position_checks": self._position_check_count,
            "performance": self._agent.state.performance() if self._agent else {},
        })

        logger.info("AUTONOMOUS TRADER STOPPED after %d ticks.", self._tick_count)
        return self.status()

    # ── Main loop ──────────────────────────────────────────────

    async def _run_loop(self, broker: BrokerInterface) -> None:
        """Background autonomous trading loop."""
        auto_cfg = get_autonomous_settings()
        try:
            while not self._stop_event.is_set():
                self._last_heartbeat = datetime.now(timezone.utc).isoformat()
                self._tick_count += 1

                try:
                    # 1. Check kill switch
                    if is_kill_switch_active():
                        logger.warning("Kill switch active — autonomous trader pausing.")
                        await asyncio.sleep(30)
                        continue

                    # 2. Check daily loss limit
                    session = get_session_state()
                    risk_cfg = get_risk_settings()
                    if session.daily_pnl <= risk_cfg.daily_loss_limit:
                        logger.warning(
                            "Daily loss limit hit ($%.2f <= $%.2f) — autonomous trader stopped.",
                            session.daily_pnl, risk_cfg.daily_loss_limit,
                        )
                        log_event("autonomous_daily_limit", {
                            "daily_pnl": session.daily_pnl,
                            "limit": risk_cfg.daily_loss_limit,
                        })
                        break

                    # 3. Check market hours
                    try:
                        clock = await broker.get_clock()
                        if not clock.get("is_open", False):
                            logger.info("Market closed — autonomous trader waiting.")
                            await asyncio.sleep(60)
                            continue
                    except Exception as exc:
                        logger.warning("Clock check failed: %s", exc)

                    # 4. Manage existing positions (stop-loss / take-profit)
                    await self._manage_positions(broker)

                    # 5. Generate new signals via agent tick
                    if self._agent:
                        signals = await self._agent.tick(broker)
                        if signals:
                            log_event("autonomous_signals", {
                                "tick": self._tick_count,
                                "signal_count": len(signals),
                                "signals": [
                                    {"symbol": s.symbol, "direction": s.direction,
                                     "confidence": s.confidence}
                                    for s in signals[:10]
                                ],
                            })

                except Exception as exc:
                    logger.error("Autonomous tick error: %s", exc, exc_info=True)
                    log_event("autonomous_error", {
                        "tick": self._tick_count, "error": str(exc),
                    }, level="error")

                await asyncio.sleep(auto_cfg.scan_interval_seconds)

        except asyncio.CancelledError:
            pass
        finally:
            self._running = False
            logger.info("Autonomous trading loop exited.")

    # ── Position management ────────────────────────────────────

    async def _manage_positions(self, broker: BrokerInterface) -> None:
        """Monitor open trades and close at stop-loss or take-profit."""
        if not self._agent:
            return

        open_trades = self._agent.state.open_trades
        if not open_trades:
            return

        self._position_check_count += 1

        # Fetch current positions from broker
        try:
            positions = await broker.get_positions()
        except Exception as exc:
            logger.warning("Failed to fetch positions: %s", exc)
            return

        pos_map: Dict[str, Position] = {p.symbol: p for p in positions}

        for trade in open_trades:
            pos = pos_map.get(trade.symbol)
            if pos is None:
                # Position was closed externally — mark it
                self._agent.state.close_trade(
                    trade.order_id, trade.entry_price, status="closed"
                )
                log_event("autonomous_position_closed_external", {
                    "symbol": trade.symbol, "order_id": trade.order_id,
                })
                continue

            current_price = pos.current_price
            if current_price <= 0:
                continue

            # Check stop-loss
            if trade.stop_loss is not None:
                hit_stop = False
                if trade.side == "buy" and current_price <= trade.stop_loss:
                    hit_stop = True
                elif trade.side == "sell" and current_price >= trade.stop_loss:
                    hit_stop = True

                if hit_stop:
                    logger.warning(
                        "STOP-LOSS HIT: %s @ $%.2f (stop=$%.2f)",
                        trade.symbol, current_price, trade.stop_loss,
                    )
                    await self._close_trade(broker, trade, current_price, "stopped_out")
                    continue

            # Check take-profit
            if trade.target is not None:
                hit_target = False
                if trade.side == "buy" and current_price >= trade.target:
                    hit_target = True
                elif trade.side == "sell" and current_price <= trade.target:
                    hit_target = True

                if hit_target:
                    logger.info(
                        "TARGET HIT: %s @ $%.2f (target=$%.2f)",
                        trade.symbol, current_price, trade.target,
                    )
                    await self._close_trade(broker, trade, current_price, "target_hit")
                    continue

    async def _close_trade(
        self,
        broker: BrokerInterface,
        trade: AgentTradeRecord,
        exit_price: float,
        status: str,
    ) -> None:
        """Close a trade via the broker and update agent state."""
        try:
            result = await broker.close_position(trade.symbol, qty=trade.qty)
            actual_exit = result.avg_fill_price or exit_price
            pnl = self._agent.state.close_trade(trade.order_id, actual_exit, status)

            log_event("autonomous_trade_closed", {
                "symbol": trade.symbol,
                "side": trade.side,
                "qty": trade.qty,
                "entry_price": trade.entry_price,
                "exit_price": actual_exit,
                "pnl": pnl,
                "status": status,
            })
            logger.info(
                "Closed %s %s: entry=$%.2f exit=$%.2f P&L=$%.2f (%s)",
                trade.symbol, trade.side, trade.entry_price,
                actual_exit, pnl or 0.0, status,
            )
        except Exception as exc:
            logger.error("Failed to close position %s: %s", trade.symbol, exc)
            log_event("autonomous_close_error", {
                "symbol": trade.symbol, "error": str(exc),
            }, level="error")

    # ── Strategy registration helper ───────────────────────────

    async def _register_default_strategies(self, registry) -> None:
        """Register built-in strategies if none are registered."""
        try:
            from app.agents.strategies.technical import TechnicalForecasterStrategy
            if not registry.get_strategy("technical"):
                registry.register_strategy(TechnicalForecasterStrategy())
        except ImportError:
            pass
        try:
            from app.agents.strategies.momentum import MomentumStrategy
            if not registry.get_strategy("momentum"):
                registry.register_strategy(MomentumStrategy())
        except (ImportError, Exception):
            pass
        try:
            from app.agents.strategies.mean_reversion import MeanReversionStrategy
            if not registry.get_strategy("mean_reversion"):
                registry.register_strategy(MeanReversionStrategy())
        except (ImportError, Exception):
            pass

