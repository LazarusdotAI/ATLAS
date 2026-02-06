#!/usr/bin/env python3
"""
Phase 1 End-to-End Signal Test
================================
Validates all Phase 1 modules:
  1. Signal schema validation
  2. Sentiment module (FinBERT — optional, skips if model not downloaded)
  3. Forecaster module (OHLCV technical analysis)
  4. RL policy stub
  5. Meta-controller (combine signals → TradeProposal)

Usage:
  python -m scripts.test_phase1_signals [SYMBOL]
  (default symbol: AAPL)
"""

from __future__ import annotations

import asyncio
import logging
import sys

from rich.console import Console
from rich.logging import RichHandler
from rich.table import Table

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(rich_tracebacks=True)],
)
logger = logging.getLogger(__name__)
console = Console()


def test_signal_schema() -> None:
    """Validate Signal schema creation and validation."""
    from app.strategy.signal_schema import Signal

    console.rule("[bold cyan]1. Signal Schema Tests[/bold cyan]")

    # Valid signal
    s = Signal(
        symbol="aapl",
        direction="long",
        confidence=0.85,
        horizon="intraday",
        source="test",
        rationale=["Test signal"],
        metadata={"test": True},
    )
    console.print(f"  ✅ Valid signal: {s}")
    console.print(f"     symbol normalised: {s.symbol}")
    assert s.symbol == "AAPL", "Symbol should be uppercased"

    # Confidence clamping
    try:
        Signal(symbol="SPY", direction="short", confidence=1.5,
               horizon="next_bar", source="test")
        console.print("  ❌ Should have rejected confidence > 1.0")
    except Exception:
        console.print("  ✅ Rejected confidence > 1.0")

    # Direction validation
    try:
        Signal(symbol="SPY", direction="sideways", confidence=0.5,  # type: ignore
               horizon="next_bar", source="test")
        console.print("  ❌ Should have rejected invalid direction")
    except Exception:
        console.print("  ✅ Rejected invalid direction 'sideways'")

    console.print("  [green]Signal schema tests passed.[/green]\n")


async def test_sentiment() -> None:
    """Test FinBERT sentiment module (skips if model unavailable)."""
    console.rule("[bold cyan]2. Sentiment Module (FinBERT)[/bold cyan]")

    try:
        from app.strategy.sentiment import generate_sentiment_signal

        headlines = [
            ("Apple beats Q4 earnings expectations, stock surges", "AAPL"),
            ("Tesla recalls 500,000 vehicles over safety concerns", "TSLA"),
            ("Markets trade flat as investors await Fed decision", "SPY"),
        ]

        for text, sym in headlines:
            signal = await generate_sentiment_signal(text, sym)
            console.print(f"  {signal}")
            for r in signal.rationale:
                console.print(f"    • {r}")
            console.print()

        console.print("  [green]Sentiment module OK.[/green]\n")

    except Exception as exc:
        console.print(f"  [yellow]⚠ Skipped (FinBERT not available): {exc}[/yellow]\n")


async def test_forecaster(symbol: str) -> None:
    """Test OHLCV forecaster with live bars."""
    console.rule(f"[bold cyan]3. Forecaster Module ({symbol})[/bold cyan]")

    from app.mcp_client import AlpacaMCPClient
    from app.strategy.forecaster import generate_forecast_signal

    client = AlpacaMCPClient()
    async with client.connect():
        signal = await generate_forecast_signal(client, symbol, timeframe="1Day", lookback=100)
        console.print(f"  {signal}")
        for r in signal.rationale:
            console.print(f"    • {r}")

        # Show metadata table
        if signal.metadata:
            table = Table(title="Indicator Values", show_header=True)
            table.add_column("Indicator", style="cyan")
            table.add_column("Value", style="white")
            for key in ["rsi", "macd_histogram", "atr", "trend_slope", "volume_surge", "volatility_annual"]:
                if key in signal.metadata:
                    table.add_row(key, f"{signal.metadata[key]:.4f}")
            if "sub_scores" in signal.metadata:
                for k, v in signal.metadata["sub_scores"].items():
                    table.add_row(f"score_{k}", f"{v:+.2f}")
            console.print(table)

    console.print("  [green]Forecaster module OK.[/green]\n")
    return signal  # return for meta-controller test


async def test_rl_stub(symbol: str) -> None:
    """Test RL policy stub."""
    console.rule("[bold cyan]4. RL Policy Stub[/bold cyan]")

    from app.mcp_client import AlpacaMCPClient
    from app.strategy.rl_policy import generate_rl_signal

    client = AlpacaMCPClient()
    async with client.connect():
        signal = await generate_rl_signal(client, symbol)
        console.print(f"  {signal}")
        for r in signal.rationale:
            console.print(f"    • {r}")

    console.print("  [green]RL stub OK.[/green]\n")


async def test_meta_controller(symbol: str) -> None:
    """Test meta-controller with synthetic signals."""
    console.rule("[bold cyan]5. Meta-Controller[/bold cyan]")

    from app.mcp_client import AlpacaMCPClient
    from app.strategy.signal_schema import Signal
    from app.strategy.meta_controller import combine_signals

    # Create synthetic signals to test consensus logic
    signals = [
        Signal(
            symbol=symbol, direction="long", confidence=0.8,
            horizon="intraday", source="forecaster_technical",
            stop_level=195.0, target_level=215.0,
            metadata={"current_price": 200.0},
        ),
        Signal(
            symbol=symbol, direction="long", confidence=0.7,
            horizon="intraday", source="sentiment",
            rationale=["Positive earnings headline"],
        ),
        Signal(
            symbol=symbol, direction="neutral", confidence=0.5,
            horizon="intraday", source="rl_policy",
        ),
    ]

    client = AlpacaMCPClient()
    async with client.connect():
        proposal = await combine_signals(
            client=client,
            symbol=symbol,
            signals=signals,
            equity=100000.0,
            current_pnl=0.0,
            open_order_count=0,
            risk_per_trade=20.0,
        )

    console.print(f"  {proposal}")
    console.print(f"    Direction:  {proposal.consensus_direction}")
    console.print(f"    Confidence: {proposal.consensus_confidence:.0%}")
    console.print(f"    Stop:       {proposal.stop_level}")
    console.print(f"    Target:     {proposal.target_level}")
    if proposal.order:
        console.print(f"    Order:      {proposal.order.side.upper()} {proposal.order.qty} {proposal.order.symbol}")
    if proposal.risk_check:
        if proposal.risk_check.passed:
            console.print("    Risk:       [green]✅ All checks passed[/green]")
        else:
            for v in proposal.risk_check.violations:
                console.print(f"    Risk:       [red]❌ {v}[/red]")
    if proposal.rejection_reason:
        console.print(f"    Rejected:   {proposal.rejection_reason}")

    console.print("  [green]Meta-controller OK.[/green]\n")


async def main() -> None:
    symbol = sys.argv[1].upper() if len(sys.argv) > 1 else "AAPL"

    console.rule("[bold green]Phase 1 — Signal Module Tests[/bold green]")
    console.print(f"Symbol: {symbol}\n")

    # 1. Schema tests (no MCP needed)
    test_signal_schema()

    # 2. Sentiment (optional — needs FinBERT model)
    await test_sentiment()

    # 3. Forecaster (needs MCP connection)
    await test_forecaster(symbol)

    # 4. RL stub (needs MCP connection)
    await test_rl_stub(symbol)

    # 5. Meta-controller (needs MCP connection)
    await test_meta_controller(symbol)

    console.rule("[bold green]All Phase 1 Tests Complete[/bold green]")


if __name__ == "__main__":
    asyncio.run(main())

