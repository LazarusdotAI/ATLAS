"""Human approval gate — require confirmation before trade execution.

Supports multiple approval modes:
  • cli — interactive terminal prompt via Rich console
  • auto_approve — bypass for testing / autonomous mode
  • auto_reject — block all trades
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from rich.console import Console
from rich.table import Table

logger = logging.getLogger(__name__)
console = Console()


@dataclass
class ApprovalContext:
    """All information needed to approve or reject a trade."""

    order: Any  # OrderPayload
    account_type: str = "paper"
    equity: float = 0.0
    buying_power: float = 0.0
    current_pnl: float = 0.0
    estimated_cost: float = 0.0
    max_loss: float = 0.0
    stop_level: Optional[float] = None
    position_pct_of_equity: float = 0.0
    risk_violations: List[str] = field(default_factory=list)
    signal_sources: List[str] = field(default_factory=list)


@dataclass
class ApprovalResult:
    """Outcome of an approval request."""

    approved: bool = False
    reason: str = ""


def format_approval_summary(ctx: ApprovalContext) -> Table:
    """Build a Rich Table summarising the trade for approval."""
    table = Table(title="Trade Approval", show_header=True, header_style="bold cyan")
    table.add_column("Field", style="dim")
    table.add_column("Value")

    order = ctx.order
    table.add_row("Symbol", str(getattr(order, "symbol", "?")))
    table.add_row("Side", str(getattr(order, "side", "?")))

    qty = getattr(order, "qty", None)
    notional = getattr(order, "notional", None)
    if qty:
        table.add_row("Quantity", str(qty))
    if notional:
        table.add_row("Notional", f"${notional:,.2f}")

    table.add_row("Order Type", str(getattr(order, "order_type", "market")))
    limit_price = getattr(order, "limit_price", None)
    if limit_price:
        table.add_row("Limit Price", f"${limit_price:,.2f}")

    table.add_row("Account", ctx.account_type.upper())
    table.add_row("Equity", f"${ctx.equity:,.2f}")
    table.add_row("Current P&L", f"${ctx.current_pnl:+,.2f}")
    table.add_row("Est. Cost", f"${ctx.estimated_cost:,.2f}")
    table.add_row("Position % of Equity", f"{ctx.position_pct_of_equity:.1f}%")

    if ctx.stop_level is not None:
        table.add_row("Stop Level", f"${ctx.stop_level:,.2f}")
    if ctx.max_loss:
        table.add_row("Max Loss", f"${ctx.max_loss:,.2f}")

    if ctx.risk_violations:
        table.add_row("Risk Violations", "; ".join(ctx.risk_violations))
    if ctx.signal_sources:
        table.add_row("Signal Sources", ", ".join(ctx.signal_sources))

    return table


def request_approval_cli(ctx: ApprovalContext) -> ApprovalResult:
    """Request approval via interactive CLI prompt."""
    table = format_approval_summary(ctx)
    console.print(table)

    try:
        answer = console.input("\n[bold]Approve this trade? (yes/no): [/bold]").strip().lower()
        if answer in ("yes", "y"):
            return ApprovalResult(approved=True, reason="User approved via CLI")
        return ApprovalResult(approved=False, reason="User rejected via CLI")
    except EOFError:
        return ApprovalResult(approved=False, reason="Cancelled (EOF)")
    except KeyboardInterrupt:
        return ApprovalResult(approved=False, reason="Cancelled (KeyboardInterrupt)")


async def request_approval(ctx: ApprovalContext, mode: str = "cli") -> ApprovalResult:
    """Request trade approval in the specified mode.

    Modes:
      cli — interactive terminal prompt
      auto_approve — always approve (for testing)
      auto_reject — always reject
    """
    if mode == "auto_reject":
        return ApprovalResult(approved=False, reason="Auto-reject mode")
    if mode == "auto_approve":
        return ApprovalResult(approved=True, reason="Auto-approved")
    if mode == "cli":
        return request_approval_cli(ctx)
    raise ValueError(f"Unknown approval mode: {mode!r}")
