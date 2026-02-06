"""Meta-controller — weighted signal consensus from multiple models.

Combines signals from: sentiment, technical forecaster, RL policy,
and TradingAgents into a single direction + confidence score.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from app.strategy.signal_schema import Signal

logger = logging.getLogger(__name__)

# ── Default source weights ────────────────────────────────────

DEFAULT_SOURCE_WEIGHTS: Dict[str, float] = {
    "sentiment": 0.25,
    "forecaster_technical": 0.45,
    "rl_policy": 0.10,
    "trading_agents": 0.40,
}

_DEFAULT_UNKNOWN_WEIGHT = 0.2


def _weighted_vote(
    signals: List[Signal],
    weights: Dict[str, float],
) -> Tuple[str, float, List[Signal]]:
    """Weighted voting across signals.

    Returns (direction, confidence, agreeing_signals).

    Direction is 'long', 'short', or 'neutral'.
    Confidence is the proportion of weighted votes for the winning direction.
    """
    if not signals:
        return "neutral", 0.0, []

    # Filter out neutral signals for voting
    non_neutral = [s for s in signals if s.direction != "neutral"]
    if not non_neutral:
        return "neutral", 0.0, []

    # Accumulate weighted scores per direction
    long_score = 0.0
    short_score = 0.0

    for sig in non_neutral:
        w = weights.get(sig.source, _DEFAULT_UNKNOWN_WEIGHT)
        weighted = sig.confidence * w
        if sig.direction == "long":
            long_score += weighted
        elif sig.direction == "short":
            short_score += weighted

    total = long_score + short_score
    if total == 0:
        return "neutral", 0.0, []

    if long_score >= short_score:
        direction = "long"
        confidence = long_score / total
        agreeing = [s for s in non_neutral if s.direction == "long"]
    else:
        direction = "short"
        confidence = short_score / total
        agreeing = [s for s in non_neutral if s.direction == "short"]

    return direction, round(confidence, 4), agreeing


def _average_levels(signals: List[Signal]) -> Tuple[Optional[float], Optional[float]]:
    """Average stop_level and target_level across signals that have them."""
    stops = [s.stop_level for s in signals if s.stop_level is not None]
    targets = [s.target_level for s in signals if s.target_level is not None]

    avg_stop = sum(stops) / len(stops) if stops else None
    avg_target = sum(targets) / len(targets) if targets else None

    return avg_stop, avg_target
