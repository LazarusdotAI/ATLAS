"""
AgentState — per-agent P&L, trade log, positions, and performance metrics.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class AgentTradeRecord:
    """Record of a single trade executed by an agent."""

    symbol: str
    side: str            # "buy" | "sell"
    qty: float
    entry_price: float
    order_id: str
    client_order_id: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    stop_loss: Optional[float] = None
    target: Optional[float] = None
    exit_price: Optional[float] = None
    exit_timestamp: Optional[str] = None
    pnl: Optional[float] = None
    status: str = "open"  # "open" | "closed" | "stopped_out" | "target_hit"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol, "side": self.side, "qty": self.qty,
            "entry_price": self.entry_price, "order_id": self.order_id,
            "client_order_id": self.client_order_id, "timestamp": self.timestamp,
            "stop_loss": self.stop_loss, "target": self.target,
            "exit_price": self.exit_price, "exit_timestamp": self.exit_timestamp,
            "pnl": self.pnl, "status": self.status,
        }


@dataclass
class AgentState:
    """Mutable state for a single trading agent."""

    agent_id: str = ""
    session_date: str = field(default_factory=lambda: date.today().isoformat())
    trades: List[AgentTradeRecord] = field(default_factory=list)
    daily_pnl: float = 0.0
    total_pnl: float = 0.0
    win_count: int = 0
    loss_count: int = 0
    total_trades: int = 0
    open_position_count: int = 0
    last_tick_at: Optional[str] = None
    error_count: int = 0
    last_error: Optional[str] = None

    def record_trade(self, trade: AgentTradeRecord) -> None:
        """Record a new trade."""
        self.trades.append(trade)
        self.total_trades += 1
        self.open_position_count += 1
        logger.info(
            "[Agent %s] Trade: %s %s %s @ %.2f (order %s)",
            self.agent_id, trade.side, trade.qty, trade.symbol,
            trade.entry_price, trade.order_id,
        )

    def close_trade(self, order_id: str, exit_price: float, status: str = "closed") -> Optional[float]:
        """Close a trade and compute P&L. Returns the P&L or None."""
        for t in self.trades:
            if t.order_id == order_id and t.status == "open":
                t.exit_price = exit_price
                t.exit_timestamp = datetime.now(timezone.utc).isoformat()
                t.status = status
                if t.side == "buy":
                    t.pnl = (exit_price - t.entry_price) * t.qty
                else:
                    t.pnl = (t.entry_price - exit_price) * t.qty
                self.daily_pnl += t.pnl
                self.total_pnl += t.pnl
                if t.pnl >= 0:
                    self.win_count += 1
                else:
                    self.loss_count += 1
                self.open_position_count = max(0, self.open_position_count - 1)
                logger.info(
                    "[Agent %s] Closed %s: P&L $%.2f (total $%.2f)",
                    self.agent_id, t.symbol, t.pnl, self.daily_pnl,
                )
                return t.pnl
        return None

    def record_error(self, error: str) -> None:
        self.error_count += 1
        self.last_error = error

    @property
    def win_rate(self) -> float:
        closed = self.win_count + self.loss_count
        return self.win_count / closed if closed > 0 else 0.0

    @property
    def open_trades(self) -> List[AgentTradeRecord]:
        return [t for t in self.trades if t.status == "open"]

    def performance(self) -> Dict[str, Any]:
        """Return performance metrics as a dict."""
        return {
            "agent_id": self.agent_id,
            "daily_pnl": round(self.daily_pnl, 2),
            "total_pnl": round(self.total_pnl, 2),
            "total_trades": self.total_trades,
            "win_count": self.win_count,
            "loss_count": self.loss_count,
            "win_rate": round(self.win_rate, 4),
            "open_positions": self.open_position_count,
            "error_count": self.error_count,
            "last_tick_at": self.last_tick_at,
        }

    def reset_daily(self) -> None:
        """Reset daily counters (call at start of new session)."""
        self.daily_pnl = 0.0
        self.session_date = date.today().isoformat()
        self.trades = [t for t in self.trades if t.status == "open"]

