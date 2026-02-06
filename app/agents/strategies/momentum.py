"""Momentum strategy — price momentum + volume surge signals."""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from app.agents.base_strategy import BaseStrategy
from app.brokers.base import BrokerInterface
from app.strategy.signal_schema import Signal

logger = logging.getLogger(__name__)


class MomentumStrategy(BaseStrategy):
    """Strategy based on price momentum and volume surge detection."""

    name = "momentum"
    description = "Momentum strategy with volume surge confirmation"
    version = "1.0.0"
    default_params = {
        "lookback_period": 20,
        "volume_surge_threshold": 1.5,
        "momentum_threshold": 0.02,
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
                    source="momentum",
                    rationale=["Momentum analysis pending market data"],
                ))
            except Exception as exc:
                logger.warning("Momentum signal failed for %s: %s", symbol, exc)
        return signals

    def validate_params(self, params: Dict[str, Any]) -> bool:
        return True
