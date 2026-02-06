"""Risk limits — pre-trade check enforcement.

Checks:
  • Daily loss limit (hard stop at -$100 default)
  • Symbol allowlist
  • Position size (max % of equity)
  • Max open orders
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List

from app.settings import get_risk_settings

logger = logging.getLogger(__name__)


@dataclass
class RiskCheckResult:
    """Outcome of one or more risk checks."""

    passed: bool = True
    violations: List[str] = field(default_factory=list)

    def add_violation(self, message: str) -> None:
        """Record a violation and mark the result as failed."""
        self.violations.append(message)
        self.passed = False

    def __bool__(self) -> bool:
        return self.passed


# ── Individual checks ─────────────────────────────────────────


def check_daily_loss_limit(current_pnl: float) -> RiskCheckResult:
    """Fail if current P&L has hit or exceeded the daily loss limit."""
    result = RiskCheckResult()
    cfg = get_risk_settings()
    if current_pnl <= cfg.daily_loss_limit:
        result.add_violation(
            f"Daily loss limit breached: P&L ${current_pnl:.2f} <= limit ${cfg.daily_loss_limit:.2f}"
        )
    return result


def check_symbol_allowed(symbol: str) -> RiskCheckResult:
    """Fail if symbol is not in the allowlist (empty list = allow all)."""
    result = RiskCheckResult()
    cfg = get_risk_settings()
    if not cfg.symbol_allowlist:
        return result  # empty list means allow all
    if symbol.upper() not in [s.upper() for s in cfg.symbol_allowlist]:
        result.add_violation(
            f"Symbol '{symbol}' not in allowlist: {cfg.symbol_allowlist}"
        )
    return result


def check_position_size(order_notional: float, equity: float) -> RiskCheckResult:
    """Fail if the order would exceed the max position size as % of equity."""
    result = RiskCheckResult()
    cfg = get_risk_settings()
    if equity <= 0:
        result.add_violation("Equity is zero or negative — cannot validate position size.")
        return result
    pct = (order_notional / equity) * 100
    if pct > cfg.max_position_size_pct:
        result.add_violation(
            f"Position size {pct:.1f}% exceeds max {cfg.max_position_size_pct}% of equity"
        )
    return result


def check_open_orders(count: int) -> RiskCheckResult:
    """Fail if the number of open orders meets or exceeds the limit."""
    result = RiskCheckResult()
    cfg = get_risk_settings()
    if count >= cfg.max_open_orders:
        result.add_violation(
            f"Open order count {count} >= max {cfg.max_open_orders}"
        )
    return result


# ── Aggregate check ───────────────────────────────────────────


def run_all_checks(
    symbol: str,
    order_notional: float,
    equity: float,
    current_pnl: float,
    open_order_count: int,
) -> RiskCheckResult:
    """Run all pre-trade risk checks and return combined result."""
    combined = RiskCheckResult()

    for check in [
        check_daily_loss_limit(current_pnl),
        check_symbol_allowed(symbol),
        check_position_size(order_notional, equity),
        check_open_orders(open_order_count),
    ]:
        if not check.passed:
            for v in check.violations:
                combined.add_violation(v)

    return combined
