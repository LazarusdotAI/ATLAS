"""Market screener — finviz-based stock screening with presets."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.brokers.base import BrokerInterface
from app.strategy.signal_schema import Signal

logger = logging.getLogger(__name__)

# ── Screening presets ─────────────────────────────────────────

PRESETS: Dict[str, Dict[str, str]] = {
    "scalp_long": {
        "Market Cap.": "+Small (over $300mln)",
        "Average Volume": "Over 1M",
        "Relative Volume": "Over 1.5",
        "Change": "Up",
        "Current Volume": "Over 500K",
    },
    "scalp_short": {
        "Market Cap.": "+Small (over $300mln)",
        "Average Volume": "Over 1M",
        "Relative Volume": "Over 1.5",
        "Change": "Down",
        "Current Volume": "Over 500K",
    },
    "momentum": {
        "Market Cap.": "+Mid (over $2bln)",
        "Average Volume": "Over 500K",
        "20-Day Simple Moving Average": "Price above SMA20",
        "50-Day Simple Moving Average": "Price above SMA50",
        "Change": "Up 3%",
    },
}


def screen_market(
    filters: Optional[Dict[str, str]] = None,
    preset: Optional[str] = "scalp_long",
    limit: int = 50,
) -> List[str]:
    """Screen the market and return a list of ticker symbols.

    Uses finviz screener when available, otherwise returns an empty list.
    """
    try:
        from finvizfinance.screener.overview import Overview

        screener = Overview()
        effective_filters = filters or PRESETS.get(preset or "scalp_long", {})
        screener.set_filter(filters_dict=effective_filters)
        df = screener.screener_view()
        if df is not None and not df.empty:
            return df["Ticker"].tolist()[:limit]
    except ImportError:
        logger.info("finvizfinance not installed — screener unavailable.")
    except Exception as exc:
        logger.warning("Screener error: %s", exc)

    return []


async def batch_analyze(
    broker: BrokerInterface,
    tickers: List[str],
    timeframe: str = "5Min",
) -> List[Signal]:
    """Run technical analysis on a batch of tickers."""
    from app.strategy.forecaster import generate_forecast_signal

    signals = []
    for ticker in tickers:
        try:
            sig = await generate_forecast_signal(broker, ticker, timeframe=timeframe)
            signals.append(sig)
        except Exception as exc:
            logger.warning("Analysis failed for %s: %s", ticker, exc)
    return signals
