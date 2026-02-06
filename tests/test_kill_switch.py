"""Unit tests for app.risk.kill_switch — emergency halt mechanism."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.brokers.base import BrokerInterface, Position, OrderResult
from app.risk.kill_switch import (
    emergency_stop,
    get_kill_switch_info,
    is_kill_switch_active,
    reset_kill_switch,
)


# ── Fixtures ──────────────────────────────────────────────────

def _make_mock_broker(positions=None, cancel_raises=False, close_raises=False):
    """Create a mock broker with configurable behaviour."""
    broker = AsyncMock(spec=BrokerInterface)
    broker.get_positions.return_value = positions or []
    broker.cancel_all_orders.return_value = None
    if cancel_raises:
        broker.cancel_all_orders.side_effect = Exception("cancel failed")
    if close_raises:
        broker.close_position.side_effect = Exception("close failed")
    else:
        broker.close_position.return_value = OrderResult(
            order_id="mock-123", status="filled"
        )
    return broker


@pytest.fixture(autouse=True)
def _reset_switch():
    """Ensure kill switch is reset before and after every test."""
    reset_kill_switch()
    yield
    reset_kill_switch()


# ── is_kill_switch_active / reset ─────────────────────────────

def test_initially_inactive():
    assert is_kill_switch_active() is False


def test_get_info_initial():
    info = get_kill_switch_info()
    assert info["active"] is False
    assert info["reason"] == ""
    assert info["timestamp"] == ""


def test_reset_clears_flag():
    # Manually set the flag via module internals
    import app.risk.kill_switch as ks
    ks._kill_switch_active = True
    ks._kill_switch_reason = "test"
    ks._kill_switch_timestamp = "2025-01-01T00:00:00Z"
    assert is_kill_switch_active() is True

    reset_kill_switch()
    assert is_kill_switch_active() is False
    info = get_kill_switch_info()
    assert info["reason"] == ""


# ── emergency_stop ────────────────────────────────────────────

@pytest.mark.asyncio
@patch("app.risk.kill_switch.log_event")
async def test_emergency_stop_no_positions(mock_log):
    broker = _make_mock_broker(positions=[])
    summary = await emergency_stop(broker, reason="Unit test")

    assert is_kill_switch_active() is True
    assert summary["orders_cancelled"] is True
    assert summary["positions_closed"] == []
    assert summary["errors"] == []
    assert summary["reason"] == "Unit test"

    # Verify audit log was called
    mock_log.assert_called_once()
    call_args = mock_log.call_args
    assert call_args[0][0] == "kill_switch"
    assert call_args[1]["level"] == "critical"


@pytest.mark.asyncio
@patch("app.risk.kill_switch.log_event")
async def test_emergency_stop_with_positions(mock_log):
    positions = [
        Position(symbol="AAPL", qty=10, side="long"),
        Position(symbol="TSLA", qty=5, side="long"),
    ]
    broker = _make_mock_broker(positions=positions)
    summary = await emergency_stop(broker, reason="P&L breach")

    assert is_kill_switch_active() is True
    assert summary["orders_cancelled"] is True
    assert len(summary["positions_closed"]) == 2
    assert summary["positions_closed"][0]["symbol"] == "AAPL"
    assert summary["positions_closed"][1]["symbol"] == "TSLA"

    broker.cancel_all_orders.assert_awaited_once()
    assert broker.close_position.await_count == 2


@pytest.mark.asyncio
@patch("app.risk.kill_switch.log_event")
async def test_emergency_stop_cancel_failure(mock_log):
    broker = _make_mock_broker(cancel_raises=True)
    summary = await emergency_stop(broker, reason="error test")

    assert is_kill_switch_active() is True
    assert summary["orders_cancelled"] is False
    assert len(summary["errors"]) >= 1
    assert "cancel" in summary["errors"][0].lower()


@pytest.mark.asyncio
@patch("app.risk.kill_switch.log_event")
async def test_emergency_stop_close_failure(mock_log):
    positions = [Position(symbol="AAPL", qty=10, side="long")]
    broker = _make_mock_broker(positions=positions, close_raises=True)
    summary = await emergency_stop(broker, reason="close err")

    assert is_kill_switch_active() is True
    assert len(summary["errors"]) >= 1
    assert "close" in summary["errors"][0].lower() or "AAPL" in summary["errors"][0]


@pytest.mark.asyncio
@patch("app.risk.kill_switch.log_event")
async def test_get_info_after_trigger(mock_log):
    broker = _make_mock_broker()
    await emergency_stop(broker, reason="info check")

    info = get_kill_switch_info()
    assert info["active"] is True
    assert info["reason"] == "info check"
    assert info["timestamp"] != ""

