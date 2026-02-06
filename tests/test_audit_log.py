"""Unit tests for app.storage.audit_log — structured JSONL logging."""

import json
import pytest
from pathlib import Path
from unittest.mock import patch

from app.storage.audit_log import (
    log_event,
    log_order_draft,
    log_order_approved,
    log_order_rejected,
    log_order_submitted,
    log_risk_violation,
    log_error,
    log_slippage,
    log_fill_quality,
    log_prompt,
    log_tool_call,
)


@pytest.fixture
def tmp_audit_log(tmp_path):
    """Patch audit log to write to a temp file."""
    log_file = tmp_path / "test_audit.jsonl"
    with patch("app.storage.audit_log.get_app_settings") as mock_settings:
        mock_settings.return_value.audit_log_path = str(log_file)
        yield log_file


def _read_events(log_file: Path) -> list[dict]:
    """Read all JSONL events from file."""
    if not log_file.exists():
        return []
    return [json.loads(line) for line in log_file.read_text().strip().split("\n") if line.strip()]


# ── log_event ─────────────────────────────────────────────────

def test_log_event_creates_file(tmp_audit_log):
    log_event("test_event", {"key": "value"})
    events = _read_events(tmp_audit_log)
    assert len(events) == 1
    assert events[0]["event"] == "test_event"
    assert events[0]["key"] == "value"
    assert "timestamp" in events[0]


def test_log_event_appends(tmp_audit_log):
    log_event("first", {"n": 1})
    log_event("second", {"n": 2})
    events = _read_events(tmp_audit_log)
    assert len(events) == 2
    assert events[0]["event"] == "first"
    assert events[1]["event"] == "second"


def test_log_event_level(tmp_audit_log):
    log_event("warn_event", {"msg": "caution"}, level="warning")
    events = _read_events(tmp_audit_log)
    assert events[0]["level"] == "warning"


# ── Helper functions ──────────────────────────────────────────

def test_log_order_draft(tmp_audit_log):
    log_order_draft({"symbol": "AAPL", "side": "buy", "qty": 10})
    events = _read_events(tmp_audit_log)
    assert events[0]["event"] == "order_draft"
    assert events[0]["order"]["symbol"] == "AAPL"


def test_log_order_approved(tmp_audit_log):
    log_order_approved({"symbol": "TSLA"}, "User approved")
    events = _read_events(tmp_audit_log)
    assert events[0]["event"] == "order_approved"
    assert events[0]["reason"] == "User approved"


def test_log_order_rejected(tmp_audit_log):
    log_order_rejected({"symbol": "GME"}, "Risk check failed")
    events = _read_events(tmp_audit_log)
    assert events[0]["event"] == "order_rejected"
    assert events[0]["level"] == "warning"


def test_log_order_submitted(tmp_audit_log):
    log_order_submitted({"symbol": "SPY"}, {"order_id": "abc-123"})
    events = _read_events(tmp_audit_log)
    assert events[0]["event"] == "order_submitted"


def test_log_risk_violation(tmp_audit_log):
    log_risk_violation(["over limit"], {"symbol": "NVDA"})
    events = _read_events(tmp_audit_log)
    assert events[0]["event"] == "risk_violation"
    assert events[0]["violations"] == ["over limit"]


def test_log_error(tmp_audit_log):
    log_error("Connection timeout", {"endpoint": "/orders"})
    events = _read_events(tmp_audit_log)
    assert events[0]["event"] == "error"
    assert events[0]["level"] == "error"


# ── New logging functions ─────────────────────────────────────

def test_log_slippage(tmp_audit_log):
    log_slippage("AAPL", "buy", 175.0, 175.50, 10, order_id="ord-1")
    events = _read_events(tmp_audit_log)
    assert events[0]["event"] == "slippage"
    assert events[0]["slippage"] == 0.5
    assert events[0]["total_slippage_cost"] == 5.0


def test_log_slippage_sell(tmp_audit_log):
    log_slippage("TSLA", "sell", 250.0, 249.50, 5)
    events = _read_events(tmp_audit_log)
    assert events[0]["slippage"] == 0.5  # positive = unfavorable


def test_log_slippage_high_triggers_warning(tmp_audit_log):
    log_slippage("AAPL", "buy", 100.0, 102.0, 10)  # 2% slippage
    events = _read_events(tmp_audit_log)
    assert events[0]["level"] == "warning"


def test_log_fill_quality(tmp_audit_log):
    log_fill_quality("ord-1", "AAPL", 10, 10, "filled", latency_ms=45.2)
    events = _read_events(tmp_audit_log)
    assert events[0]["event"] == "fill_quality"
    assert events[0]["fill_ratio"] == 1.0
    assert events[0]["partial"] is False
    assert events[0]["rejected"] is False


def test_log_fill_quality_partial(tmp_audit_log):
    log_fill_quality("ord-2", "TSLA", 10, 6, "partially_filled")
    events = _read_events(tmp_audit_log)
    assert events[0]["partial"] is True
    assert events[0]["fill_ratio"] == 0.6


def test_log_fill_quality_rejected(tmp_audit_log):
    log_fill_quality("ord-3", "SPY", 5, 0, "rejected")
    events = _read_events(tmp_audit_log)
    assert events[0]["rejected"] is True


def test_log_prompt(tmp_audit_log):
    log_prompt("Buy AAPL", "You are a trading bot", "I'll buy AAPL", "openai", "gpt-4o")
    events = _read_events(tmp_audit_log)
    assert events[0]["event"] == "llm_prompt"
    assert events[0]["provider"] == "openai"


def test_log_tool_call(tmp_audit_log):
    log_tool_call("get_account_info", {}, "equity=25000")
    events = _read_events(tmp_audit_log)
    assert events[0]["event"] == "tool_call"
    assert events[0]["tool"] == "get_account_info"

