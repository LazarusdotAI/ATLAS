"""Technical forecaster strategy — built-in strategy for technical analysis."""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from app.agents.base_strategy import BaseStrategy
from app.brokers.base import BrokerInterface
from app.strategy.signal_schema import Signal

logger = logging.getLogger(__name__)


class TechnicalForecasterStrategy(BaseStrategy):
    """Strategy that uses RSI, MACD, ATR, Bollinger, VWAP for signals."""

    name = "technical"
    description = "Technical indicator-based forecaster (RSI, MACD, ATR, Bollinger, VWAP)"
    version = "1.0.0"
    default_params = {
        "rsi_period": 14,
        "macd_fast": 12,
        "macd_slow": 26,
        "atr_period": 14,
        "bb_period": 20,
    }

    async def generate_signals(
        self,
        symbols: List[str],
        broker: BrokerInterface,
        params: Dict[str, Any],
    ) -> List[Signal]:
        from app.strategy.forecaster import generate_forecast_signal

        signals = []
        for symbol in symbols:
            try:
                sig = await generate_forecast_signal(broker, symbol)
                signals.append(sig)
            except Exception as exc:
                logger.warning("Technical signal failed for %s: %s", symbol, exc)
        return signals

    def validate_params(self, params: Dict[str, Any]) -> bool:
        return True
