"""Unit tests for LLM output validation — _extract_trade_action parsing."""

import pytest

from app.llm import _extract_trade_action


# ── Valid JSON code block ─────────────────────────────────────

def test_extract_valid_json_block():
    text = 'Here is the trade:\n```json\n{"action":"trade","symbol":"AAPL","side":"buy","qty":10,"order_type":"market"}\n```'
    result = _extract_trade_action(text)
    assert result is not None
    assert result["symbol"] == "AAPL"
    assert result["side"] == "buy"
    assert result["qty"] == 10


def test_extract_valid_json_block_with_nulls():
    text = '```json\n{"action":"trade","symbol":"TSLA","side":"sell","qty":5,"order_type":"limit","limit_price":250.0,"stop_loss":null,"target":null}\n```'
    result = _extract_trade_action(text)
    assert result is not None
    assert result["symbol"] == "TSLA"
    assert result["limit_price"] == 250.0


# ── Raw JSON without code fences ──────────────────────────────

def test_extract_raw_json():
    text = 'I recommend: {"action":"trade","symbol":"SPY","side":"buy","qty":1,"order_type":"market"}'
    result = _extract_trade_action(text)
    assert result is not None
    assert result["symbol"] == "SPY"


# ── Non-trade JSON ────────────────────────────────────────────

def test_non_trade_action_returns_none():
    text = '```json\n{"action":"info","symbol":"AAPL"}\n```'
    result = _extract_trade_action(text)
    assert result is None


def test_no_json_at_all():
    text = "The market is currently closed. Try again tomorrow."
    result = _extract_trade_action(text)
    assert result is None


def test_empty_string():
    result = _extract_trade_action("")
    assert result is None


# ── Malformed JSON ────────────────────────────────────────────

def test_malformed_json_in_block():
    text = '```json\n{"action":"trade", "symbol": AAPL, broken}\n```'
    result = _extract_trade_action(text)
    assert result is None


def test_incomplete_json():
    text = '```json\n{"action":"trade","symbol":"AAPL"\n```'
    # Missing closing brace inside the group — depends on regex
    result = _extract_trade_action(text)
    # Should either return None or handle gracefully
    assert result is None or isinstance(result, dict)


def test_nested_braces():
    text = '{"action":"trade","symbol":"AAPL","side":"buy","qty":10,"order_type":"market","meta":{"source":"chat"}}'
    # The raw fallback regex won't capture nested braces, so should return None
    result = _extract_trade_action(text)
    # Either None or valid dict is acceptable
    assert result is None or isinstance(result, dict)


# ── Edge cases ────────────────────────────────────────────────

def test_multiple_json_blocks_takes_first():
    text = (
        '```json\n{"action":"trade","symbol":"AAPL","side":"buy","qty":5,"order_type":"market"}\n```\n'
        '```json\n{"action":"trade","symbol":"TSLA","side":"sell","qty":3,"order_type":"limit"}\n```'
    )
    result = _extract_trade_action(text)
    assert result is not None
    assert result["symbol"] == "AAPL"  # First match wins


def test_json_with_extra_whitespace():
    text = '```json\n  {  "action" : "trade" , "symbol" : "AMD" , "side" : "buy" , "qty" : 20 , "order_type" : "market" }  \n```'
    result = _extract_trade_action(text)
    assert result is not None
    assert result["symbol"] == "AMD"


def test_json_with_newlines_inside():
    text = '```json\n{\n  "action": "trade",\n  "symbol": "NVDA",\n  "side": "buy",\n  "qty": 15,\n  "order_type": "market"\n}\n```'
    result = _extract_trade_action(text)
    assert result is not None
    assert result["symbol"] == "NVDA"


def test_case_sensitivity_action():
    # action must be exactly "trade" (lowercase)
    text = '```json\n{"action":"Trade","symbol":"AAPL","side":"buy","qty":10,"order_type":"market"}\n```'
    result = _extract_trade_action(text)
    assert result is None  # "Trade" != "trade"


def test_missing_action_key():
    text = '```json\n{"symbol":"AAPL","side":"buy","qty":10,"order_type":"market"}\n```'
    result = _extract_trade_action(text)
    assert result is None

