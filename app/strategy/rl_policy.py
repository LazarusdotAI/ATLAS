"""RL policy — Stable-Baselines3 reinforcement learning signal generation."""

from __future__ import annotations

import logging
from typing import Any, Dict

from app.brokers.base import BrokerInterface
from app.strategy.signal_schema import Signal

logger = logging.getLogger(__name__)


async def generate_rl_signal(broker: BrokerInterface, symbol: str) -> Signal:
    """Generate a signal from the RL policy model.

    Falls back to neutral if the model is unavailable.
    """
    try:
        from stable_baselines3 import PPO
        # In production, load a trained model checkpoint
        # model = PPO.load("checkpoints/rl_policy.zip")
        raise ImportError("No trained RL model checkpoint available")
    except (ImportError, Exception) as exc:
        logger.info("RL policy unavailable: %s. Returning neutral.", exc)
        return Signal(
            symbol=symbol,
            direction="neutral",
            confidence=0.0,
            horizon="intraday",
            source="rl_policy",
            rationale=["RL model not loaded"],
            metadata={"error": str(exc)},
        )
