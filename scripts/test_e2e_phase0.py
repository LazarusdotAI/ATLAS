#!/usr/bin/env python3
"""
Phase 0 End-to-End Test
========================
Validates the full pipeline:
  1. Connect to Alpaca MCP server
  2. Fetch a quote for a symbol
  3. Read account info
  4. Draft an order
  5. Run risk checks
  6. Show approval prompt
  7. Log the decision

Usage:
  python -m scripts.test_e2e_phase0 [SYMBOL]
  (default symbol: AAPL)
"""

from __future__ import annotations

import asyncio
import logging
import sys

from rich.console import Console
from rich.logging import RichHandler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(rich_tracebacks=True)],
)
logger = logging.getLogger(__name__)
console = Console()


async def run_e2e_test(symbol: str = "AAPL") -> None:
    from app.mcp_client import AlpacaMCPClient
    from app.tools.alpaca_tools import (
        get_account, get_quote, get_latest_trade, get_bars,
        get_clock, get_orders, draft_order, OrderPayload,
    )
    from app.risk.limits import run_all_checks
    from app.risk.approvals import ApprovalContext, request_approval
    from app.storage.state import get_session_state
    from app.storage.audit_log import (
        log_order_draft, log_order_approved, log_order_rejected,
        log_risk_violation,
    )

    client = AlpacaMCPClient()

    async with client.connect():
        console.rule("[bold green]Phase 0 — End-to-End Test[/bold green]")

        # 1. Market clock
        console.print("\n[bold]1. Market Clock[/bold]")
        clock = await get_clock(client)
        console.print(clock)

        # 2. Account info
        console.print("\n[bold]2. Account Info[/bold]")
        account = await get_account(client)
        console.print(account)

        state = get_session_state()
        state.update_from_account(account if isinstance(account, dict) else {})
        console.print(
            f"   Equity: ${state.equity:,.2f}  |  "
            f"Buying Power: ${state.buying_power:,.2f}  |  "
            f"Daily P&L: ${state.daily_pnl:,.2f}"
        )

        # 3. Quote
        console.print(f"\n[bold]3. Latest Quote for {symbol}[/bold]")
        quote = await get_quote(client, symbol)
        console.print(quote)

        # 4. Latest trade
        console.print(f"\n[bold]4. Latest Trade for {symbol}[/bold]")
        trade = await get_latest_trade(client, symbol)
        console.print(trade)

        # 5. Draft an order
        console.print(f"\n[bold]5. Drafting Order[/bold]")
        order = draft_order(
            symbol=symbol,
            side="buy",
            qty=1,
            order_type="market",
            time_in_force="day",
        )
        console.print(f"   Draft: {order}")
        log_order_draft(order.to_dict())

        # 6. Risk checks
        console.print(f"\n[bold]6. Risk Checks[/bold]")
        # Estimate cost (use a rough price from quote or 0)
        est_price = 200.0  # placeholder — in real use, parse from quote
        est_cost = est_price * (order.qty or 1)

        risk_result = run_all_checks(
            symbol=order.symbol,
            order_notional=est_cost,
            equity=state.equity,
            current_pnl=state.daily_pnl,
            open_order_count=state.open_order_count,
        )

        if risk_result.passed:
            console.print("   [green]✅ All risk checks passed[/green]")
        else:
            console.print("   [red]❌ Risk violations:[/red]")
            for v in risk_result.violations:
                console.print(f"      • {v}")
            log_risk_violation(risk_result.violations, {"symbol": symbol})

        # 7. Approval gate
        console.print(f"\n[bold]7. Approval Gate[/bold]")
        ctx = ApprovalContext(
            order=order,
            account_type="paper",
            equity=state.equity,
            buying_power=state.buying_power,
            current_pnl=state.daily_pnl,
            estimated_cost=est_cost,
            risk_violations=risk_result.violations,
        )

        result = await request_approval(ctx, mode="cli")

        if result.approved:
            console.print("[bold green]✅ Order APPROVED[/bold green]")
            log_order_approved(order.to_dict(), result.reason)
            console.print(
                "[yellow]ℹ️  In production, this would now submit the order. "
                "Skipping for Phase 0 test.[/yellow]"
            )
        else:
            console.print(f"[bold red]❌ Order REJECTED: {result.reason}[/bold red]")
            log_order_rejected(order.to_dict(), result.reason)

        console.rule("[bold green]Test Complete[/bold green]")


def main() -> None:
    symbol = sys.argv[1] if len(sys.argv) > 1 else "AAPL"
    asyncio.run(run_e2e_test(symbol))


if __name__ == "__main__":
    main()

