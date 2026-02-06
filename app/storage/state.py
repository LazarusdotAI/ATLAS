"""Session state — in-memory state for the current trading session.

Tracks daily P&L, equity snapshots, and trade history.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class SessionState:
    """Mutable in-memory session state."""

    session_date: str = field(default_factory=lambda: date.today().isoformat())
    daily_pnl: float = 0.0
    equity: float = 0.0
    buying_power: float = 0.0
    cash: float = 0.0
    last_equity: float = 0.0
    equity_snapshots: List[Dict[str, Any]] = field(default_factory=list)
    trade_count: int = 0

    def update_from_account(self, data: Dict[str, Any]) -> None:
        """Update session state from raw account data."""
        self.equity = float(data.get("equity", self.equity))
        self.buying_power = float(data.get("buying_power", self.buying_power))
        self.cash = float(data.get("cash", self.cash))
        last_eq = float(data.get("last_equity", self.equity))
        if last_eq > 0:
            self.daily_pnl = self.equity - last_eq
            self.last_equity = last_eq

    def reset_daily(self) -> None:
        """Reset daily counters for a new trading session."""
        self.daily_pnl = 0.0
        self.session_date = date.today().isoformat()
        self.equity_snapshots.clear()
        self.trade_count = 0


# ── Singleton ─────────────────────────────────────────────────

_session_state: Optional[SessionState] = None


def get_session_state() -> SessionState:
    """Return the global session state singleton."""
    global _session_state
    if _session_state is None:
        _session_state = SessionState()
    return _session_state
