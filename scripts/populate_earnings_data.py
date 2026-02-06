#!/usr/bin/env python3
"""
Populate Earnings Playbook — pre-compute historical earnings metrics.

Connects to Alpaca via the broker interface, fetches daily bars around
each stock's last 10 earnings events, computes per-event and aggregate
metrics, and writes everything to data/earnings_playbook.json.

Usage:
    python -m scripts.populate_earnings_data          # all 20 symbols
    python -m scripts.populate_earnings_data AAPL NVDA # specific symbols
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from datetime import date
from pathlib import Path

# Ensure project root is on sys.path
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from app.brokers.alpaca_broker import AlpacaBroker
from app.data.earnings_calendar import TARGET_SYMBOLS, get_earnings_dates
from app.agents.strategies.earnings_playbook import (
    _fetch_bars_around_date,
    _compute_single_event_metrics,
    calculate_earnings_metrics,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("populate_earnings")

OUTPUT_PATH = _ROOT / "data" / "earnings_playbook.json"


async def populate(symbols: list[str]) -> dict:
    """Fetch and compute earnings metrics for each symbol."""
    broker = AlpacaBroker()
    await broker.connect()

    playbook: dict = {}
    today = date.today().isoformat()

    for i, sym in enumerate(symbols, 1):
        logger.info("[%d/%d] Processing %s ...", i, len(symbols), sym)
        dates = get_earnings_dates(sym, limit=10, before=today)
        if not dates:
            logger.warning("  No earnings dates for %s — skipping", sym)
            continue

        events = []
        for earn_date, timing in dates:
            df = await _fetch_bars_around_date(broker, sym, earn_date)
            if df is None:
                logger.warning("  No data for %s around %s", sym, earn_date)
                continue
            metrics = _compute_single_event_metrics(df, earn_date, timing)
            if metrics:
                events.append(metrics)
                logger.info("  ✓ %s %s: move=%.2f%%, gap=%.2f%%, pattern=%s",
                            earn_date, timing, metrics["move_pct"],
                            metrics["gap_pct"], metrics["pattern"])

        aggregate = calculate_earnings_metrics(sym, events)
        playbook[sym] = {"symbol": sym, "events": events, "aggregate": aggregate}

        if aggregate:
            logger.info("  AGGREGATE: bias=%s, avg_move=%.1f%%, win_rate=%.0f%%, "
                        "dominant=%s, vol_surge=%.1fx",
                        aggregate.get("directional_bias"),
                        aggregate.get("avg_abs_move_pct", 0),
                        aggregate.get("win_rate", 0) * 100,
                        aggregate.get("dominant_pattern"),
                        aggregate.get("avg_volume_surge", 0))
        else:
            logger.warning("  No events computed for %s", sym)

    await broker.disconnect()
    return playbook


def main():
    symbols = sys.argv[1:] if len(sys.argv) > 1 else TARGET_SYMBOLS
    # Validate symbols
    symbols = [s.upper() for s in symbols]
    invalid = [s for s in symbols if s not in TARGET_SYMBOLS]
    if invalid:
        logger.warning("Unknown symbols (no calendar data): %s", invalid)
        symbols = [s for s in symbols if s in TARGET_SYMBOLS]

    if not symbols:
        logger.error("No valid symbols to process.")
        sys.exit(1)

    logger.info("Processing %d symbols: %s", len(symbols), symbols)

    playbook = asyncio.run(populate(symbols))

    # Merge with existing file if it exists
    if OUTPUT_PATH.exists():
        try:
            with open(OUTPUT_PATH, "r") as f:
                existing = json.load(f)
            existing.update(playbook)
            playbook = existing
        except (json.JSONDecodeError, OSError):
            pass

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(playbook, f, indent=2, default=str)

    logger.info("Wrote %d symbols to %s", len(playbook), OUTPUT_PATH)

    # Summary table
    print("\n" + "=" * 80)
    print(f"{'Symbol':<8} {'Events':>6} {'AvgMove':>8} {'Bias':<8} "
          f"{'WinRate':>8} {'Pattern':<15} {'VolSurge':>9}")
    print("-" * 80)
    for sym, data in sorted(playbook.items()):
        agg = data.get("aggregate", {})
        if not agg:
            print(f"{sym:<8} {'N/A':>6}")
            continue
        print(f"{sym:<8} {agg.get('num_events', 0):>6} "
              f"{agg.get('avg_abs_move_pct', 0):>7.1f}% "
              f"{agg.get('directional_bias', '?'):<8} "
              f"{agg.get('win_rate', 0)*100:>7.0f}% "
              f"{agg.get('dominant_pattern', '?'):<15} "
              f"{agg.get('avg_volume_surge', 0):>8.1f}x")
    print("=" * 80)


if __name__ == "__main__":
    main()

