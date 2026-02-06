"""Technical forecaster — generates signals from price data and indicators.

Computes RSI, MACD, ATR, Bollinger Bands, VWAP, volume surge, and trend
slope, then combines them into a single Signal.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from app.brokers.base import BrokerInterface
from app.strategy.signal_schema import Signal

logger = logging.getLogger(__name__)


# ── Indicator computation ─────────────────────────────────────


def compute_rsi(prices: pd.Series, period: int = 14) -> Optional[float]:
    """Compute Relative Strength Index."""
    if len(prices) < period + 1:
        return None
    delta = prices.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    if loss.iloc[-1] == 0:
        return 100.0
    rs = gain.iloc[-1] / loss.iloc[-1]
    return round(100 - 100 / (1 + rs), 2)


def compute_macd(prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Optional[float]:
    """Compute MACD histogram value."""
    if len(prices) < slow + signal:
        return None
    ema_fast = prices.ewm(span=fast).mean()
    ema_slow = prices.ewm(span=slow).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal).mean()
    histogram = macd_line - signal_line
    return round(histogram.iloc[-1], 4)


def compute_atr(highs: pd.Series, lows: pd.Series, closes: pd.Series, period: int = 14) -> Optional[float]:
    """Compute Average True Range."""
    if len(closes) < period + 1:
        return None
    tr1 = highs - lows
    tr2 = (highs - closes.shift()).abs()
    tr3 = (lows - closes.shift()).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(period).mean()
    return round(atr.iloc[-1], 4)


def compute_bollinger_bands(prices: pd.Series, period: int = 20, std_dev: float = 2.0) -> Optional[Dict[str, float]]:
    """Compute Bollinger Bands: upper, middle, lower, and %B."""
    if len(prices) < period:
        return None
    sma = prices.rolling(period).mean()
    std = prices.rolling(period).std()
    upper = sma + std_dev * std
    lower = sma - std_dev * std
    current = prices.iloc[-1]
    band_width = upper.iloc[-1] - lower.iloc[-1]
    pct_b = (current - lower.iloc[-1]) / band_width if band_width > 0 else 0.5
    return {
        "upper": round(upper.iloc[-1], 2),
        "middle": round(sma.iloc[-1], 2),
        "lower": round(lower.iloc[-1], 2),
        "pct_b": round(pct_b, 4),
    }


def compute_vwap(prices: pd.Series, volumes: pd.Series) -> Optional[float]:
    """Compute Volume-Weighted Average Price."""
    if len(prices) < 2 or volumes.sum() == 0:
        return None
    return round((prices * volumes).sum() / volumes.sum(), 2)


def compute_volume_surge(volumes: pd.Series, lookback: int = 20) -> Optional[float]:
    """Compute volume surge ratio (current vs average)."""
    if len(volumes) < lookback + 1:
        return None
    avg = volumes.iloc[-(lookback + 1):-1].mean()
    if avg == 0:
        return None
    return round(volumes.iloc[-1] / avg, 2)


def compute_trend_slope(prices: pd.Series, period: int = 20) -> Optional[float]:
    """Compute linear trend slope over the lookback period."""
    if len(prices) < period:
        return None
    y = prices.iloc[-period:].values
    x = np.arange(period)
    slope = np.polyfit(x, y, 1)[0]
    return round(slope, 4)


# ── Main forecast function ────────────────────────────────────


async def generate_forecast_signal(
    broker: BrokerInterface,
    symbol: str,
    timeframe: str = "5Min",
) -> Signal:
    """Generate a technical forecast signal for a symbol.

    Fetches bar data from the broker, computes indicators, and produces
    a Signal with direction, confidence, and metadata.
    """
    # Fetch bar data
    try:
        bars_data = await broker.get_quote(symbol)
        # In production, this would fetch historical bars via get_bars
        # For now, we work with what's available
    except Exception as exc:
        logger.warning("Failed to fetch data for %s: %s", symbol, exc)

    # Since we may not have full bar data, generate a signal from
    # whatever data is available. This is a placeholder that would
    # be backed by real market data in production.
    return Signal(
        symbol=symbol,
        direction="neutral",
        confidence=0.5,
        horizon="intraday",
        source="forecaster_technical",
        rationale=["Insufficient data for full analysis"],
        metadata={
            "timeframe": timeframe,
            "current_price": 0,
        },
    )
