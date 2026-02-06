"""
BaseStrategy — Abstract base class for all trading strategies.

Every strategy must implement:
  • generate_signals(symbols, broker, params) → List[Signal]
  • validate_params(params) → bool
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List

from app.brokers.base import BrokerInterface
from app.strategy.signal_schema import Signal


class BaseStrategy(ABC):
    """Abstract base class for trading strategies."""

    name: str = "base"
    description: str = "Base strategy — do not use directly."
    version: str = "0.1.0"
    default_params: Dict[str, Any] = {}

    @abstractmethod
    async def generate_signals(
        self,
        symbols: List[str],
        broker: BrokerInterface,
        params: Dict[str, Any],
    ) -> List[Signal]:
        """Generate trading signals for the given symbols.

        Parameters
        ----------
        symbols : list[str]
            Tickers to analyse.
        broker : BrokerInterface
            Connected broker for market data access.
        params : dict
            Strategy-specific parameters (merged with default_params).

        Returns
        -------
        list[Signal]
            Zero or more signals (may be empty if no actionable setup).
        """
        ...

    @abstractmethod
    def validate_params(self, params: Dict[str, Any]) -> bool:
        """Return True if *params* are valid for this strategy."""
        ...

    def get_effective_params(self, overrides: Dict[str, Any]) -> Dict[str, Any]:
        """Merge default_params with user overrides."""
        merged = {**self.default_params}
        merged.update(overrides)
        return merged

    def info(self) -> Dict[str, Any]:
        """Return strategy metadata as a serialisable dict."""
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "default_params": self.default_params,
        }

