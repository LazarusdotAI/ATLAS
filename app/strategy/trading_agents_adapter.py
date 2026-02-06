"""TradingAgents adapter — multi-agent LLM framework signal generation."""

from __future__ import annotations

import logging

from app.strategy.signal_schema import Signal

logger = logging.getLogger(__name__)


async def generate_trading_agents_signal(symbol: str) -> Signal:
    """Generate a signal from the TradingAgents multi-agent framework.

    Falls back to neutral if the framework is unavailable.
    """
    try:
        # TradingAgents integration would go here
        raise ImportError("TradingAgents framework not configured")
    except (ImportError, Exception) as exc:
        logger.info("TradingAgents unavailable: %s. Returning neutral.", exc)
        return Signal(
            symbol=symbol,
            direction="neutral",
            confidence=0.0,
            horizon="intraday",
            source="trading_agents",
            rationale=["TradingAgents framework not available"],
            metadata={"error": str(exc)},
        )
