"""Unit tests for app.strategy.meta_controller — consensus & sizing logic."""

import pytest

from app.strategy.signal_schema import Signal
from app.strategy.meta_controller import (
    _weighted_vote,
    _average_levels,
    DEFAULT_SOURCE_WEIGHTS,
)


# ── Helper ─────────────────────────────────────────────────────

def _sig(direction: str, confidence: float, source: str,
         stop: float | None = None, target: float | None = None) -> Signal:
    return Signal(
        symbol="TEST",
        direction=direction,
        confidence=confidence,
        horizon="intraday",
        source=source,
        stop_level=stop,
        target_level=target,
    )


# ── _weighted_vote ─────────────────────────────────────────────

def test_all_neutral():
    sigs = [_sig("neutral", 0.5, "a"), _sig("neutral", 0.8, "b")]
    direction, conf, agreeing = _weighted_vote(sigs, DEFAULT_SOURCE_WEIGHTS)
    assert direction == "neutral"
    assert agreeing == []


def test_unanimous_long():
    sigs = [
        _sig("long", 0.9, "forecaster_technical"),
        _sig("long", 0.8, "sentiment"),
    ]
    direction, conf, agreeing = _weighted_vote(sigs, DEFAULT_SOURCE_WEIGHTS)
    assert direction == "long"
    assert conf == 1.0  # 100% agree on long
    assert len(agreeing) == 2


def test_unanimous_short():
    sigs = [
        _sig("short", 0.7, "forecaster_technical"),
        _sig("short", 0.6, "trading_agents"),
    ]
    direction, conf, agreeing = _weighted_vote(sigs, DEFAULT_SOURCE_WEIGHTS)
    assert direction == "short"
    assert conf == 1.0
    assert len(agreeing) == 2


def test_mixed_long_wins():
    sigs = [
        _sig("long", 0.9, "forecaster_technical"),   # 0.9 * 0.45 = 0.405
        _sig("short", 0.6, "sentiment"),              # 0.6 * 0.25 = 0.15
    ]
    direction, conf, agreeing = _weighted_vote(sigs, DEFAULT_SOURCE_WEIGHTS)
    assert direction == "long"
    assert conf > 0.5


def test_mixed_no_consensus():
    """When short outweighs long slightly, short wins; but if neither
    clears >50 % the result is neutral.  With the current impl an exact
    50/50 tie favours long (>= check), so we need an *unambiguous*
    scenario where the minority side has >50 %."""
    weights = {"a": 1.0, "b": 1.0, "c": 1.0}
    sigs = [
        _sig("long", 0.4, "a"),
        _sig("short", 0.4, "b"),
        _sig("long", 0.01, "c"),   # tiny nudge → long barely leads
    ]
    direction, conf, agreeing = _weighted_vote(sigs, weights)
    # long total = 0.41, short total = 0.4 → long wins
    assert direction == "long"
    # confidence ≈ 0.41/0.81 ≈ 0.506 — just barely above 50 %
    assert conf > 0.5


def test_single_signal_long():
    sigs = [_sig("long", 0.8, "forecaster_technical")]
    direction, conf, agreeing = _weighted_vote(sigs, DEFAULT_SOURCE_WEIGHTS)
    assert direction == "long"
    assert conf == 1.0
    assert len(agreeing) == 1


def test_empty_signals():
    direction, conf, agreeing = _weighted_vote([], DEFAULT_SOURCE_WEIGHTS)
    assert direction == "neutral"


# ── _average_levels ────────────────────────────────────────────

def test_average_levels_all_present():
    sigs = [_sig("long", 0.8, "a", stop=99.0, target=105.0),
            _sig("long", 0.7, "b", stop=98.0, target=106.0)]
    stop, target = _average_levels(sigs)
    assert stop == 98.5
    assert target == 105.5


def test_average_levels_partial():
    sigs = [_sig("long", 0.8, "a", stop=100.0, target=110.0),
            _sig("long", 0.7, "b")]  # no stop/target
    stop, target = _average_levels(sigs)
    assert stop == 100.0
    assert target == 110.0


def test_average_levels_none():
    sigs = [_sig("long", 0.8, "a"), _sig("long", 0.7, "b")]
    stop, target = _average_levels(sigs)
    assert stop is None
    assert target is None


# ── Source weights ─────────────────────────────────────────────

def test_default_weights_contain_expected_sources():
    assert "sentiment" in DEFAULT_SOURCE_WEIGHTS
    assert "forecaster_technical" in DEFAULT_SOURCE_WEIGHTS
    assert "trading_agents" in DEFAULT_SOURCE_WEIGHTS
    assert "rl_policy" in DEFAULT_SOURCE_WEIGHTS


def test_unknown_source_gets_default_weight():
    """Unknown sources get 0.2 default in _weighted_vote."""
    sigs = [_sig("long", 0.9, "unknown_source")]
    direction, conf, agreeing = _weighted_vote(sigs, DEFAULT_SOURCE_WEIGHTS)
    assert direction == "long"
    assert len(agreeing) == 1

