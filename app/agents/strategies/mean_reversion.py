"""Mean reversion strategy — Bollinger band oscillation signals."""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from app.agents.base_strategy import BaseStrategy
from app.brokers.base import BrokerInterface
from app.strategy.signal_schema import Signal

logger = logging.getLogger(__name__)


class MeanReversionStrategy(BaseStrategy):
    """Strategy based on Bollinger Band mean reversion."""

    name = "mean_reversion"
    description = "Mean reversion using Bollinger Bands and RSI divergence"
    version = "1.0.0"
    default_params = {
        "bb_period": 20,
        "bb_std_dev": 2.0,
        "rsi_oversold": 30,
        "rsi_overbought": 70,
    }

    async def generate_signals(
        self,
        symbols: List[str],
        broker: BrokerInterface,
        params: Dict[str, Any],
    ) -> List[Signal]:
        signals = []
        for symbol in symbols:
            try:
                signals.append(Signal(
                    symbol=symbol,
                    direction="neutral",
                    confidence=0.5,
                    horizon="intraday",
                    source="mean_reversion",
                    rationale=["Mean reversion analysis pending market data"],
                ))
            except Exception as exc:
                logger.warning("Mean reversion signal failed for %s: %s", symbol, exc)
        return signals

    def validate_params(self, params: Dict[str, Any]) -> bool:
        return True
