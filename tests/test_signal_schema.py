"""Unit tests for app.strategy.signal_schema.Signal."""

import pytest
from pydantic import ValidationError

from app.strategy.signal_schema import Signal


# ── Construction & defaults ────────────────────────────────────

def test_signal_minimal():
    s = Signal(
        symbol="aapl", direction="long", confidence=0.75,
        horizon="intraday", source="test",
    )
    assert s.symbol == "AAPL"  # uppercased
    assert s.direction == "long"
    assert s.confidence == 0.75
    assert s.stop_level is None
    assert s.target_level is None
    assert s.rationale == []
    assert s.metadata == {}
    assert s.timestamp  # auto-filled


def test_signal_full_fields():
    s = Signal(
        symbol="TSLA", direction="short", confidence=0.90,
        horizon="next_bar", source="forecaster_technical",
        stop_level=250.0, target_level=220.0,
        rationale=["RSI overbought"], metadata={"rsi": 82},
    )
    assert s.stop_level == 250.0
    assert s.target_level == 220.0
    assert len(s.rationale) == 1
    assert s.metadata["rsi"] == 82


# ── Validation ─────────────────────────────────────────────────

def test_confidence_bounds_low():
    with pytest.raises(ValidationError):
        Signal(symbol="X", direction="long", confidence=-0.1,
               horizon="intraday", source="t")


def test_confidence_bounds_high():
    with pytest.raises(ValidationError):
        Signal(symbol="X", direction="long", confidence=1.1,
               horizon="intraday", source="t")


def test_confidence_edge_zero():
    s = Signal(symbol="X", direction="neutral", confidence=0.0,
               horizon="intraday", source="t")
    assert s.confidence == 0.0


def test_confidence_edge_one():
    s = Signal(symbol="X", direction="long", confidence=1.0,
               horizon="intraday", source="t")
    assert s.confidence == 1.0


def test_confidence_rounding():
    s = Signal(symbol="X", direction="long", confidence=0.123456,
               horizon="intraday", source="t")
    assert s.confidence == 0.1235


def test_invalid_direction():
    with pytest.raises(ValidationError):
        Signal(symbol="X", direction="up", confidence=0.5,
               horizon="intraday", source="t")


def test_invalid_horizon():
    with pytest.raises(ValidationError):
        Signal(symbol="X", direction="long", confidence=0.5,
               horizon="weekly", source="t")


def test_symbol_whitespace():
    s = Signal(symbol="  msft  ", direction="long", confidence=0.5,
               horizon="intraday", source="t")
    assert s.symbol == "MSFT"


# ── Serialization ──────────────────────────────────────────────

def test_to_dict():
    s = Signal(
        symbol="SPY", direction="long", confidence=0.80,
        horizon="next_day", source="test",
    )
    d = s.to_dict()
    assert isinstance(d, dict)
    assert d["symbol"] == "SPY"
    assert d["direction"] == "long"
    assert d["confidence"] == 0.80
    assert "timestamp" in d


def test_str_repr():
    s = Signal(
        symbol="QQQ", direction="short", confidence=0.60,
        horizon="intraday", source="sentiment",
    )
    text = str(s)
    assert "SHORT" in text
    assert "QQQ" in text
    assert "60%" in text

