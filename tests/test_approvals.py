"""Unit tests for app.risk.approvals — human approval gate."""

import pytest
from unittest.mock import patch, MagicMock

from app.risk.approvals import (
    ApprovalContext,
    ApprovalResult,
    format_approval_summary,
    request_approval,
    request_approval_cli,
)
from app.tools.alpaca_tools import OrderPayload


# ── Fixtures ──────────────────────────────────────────────────

def _make_context(**overrides) -> ApprovalContext:
    """Create a default ApprovalContext for testing."""
    order = OrderPayload(
        symbol="AAPL",
        side="buy",
        qty=10,
        order_type="market",
        time_in_force="day",
    )
    defaults = dict(
        order=order,
        account_type="paper",
        equity=25000.0,
        buying_power=50000.0,
        current_pnl=-20.0,
        estimated_cost=1750.0,
        max_loss=100.0,
        stop_level=170.0,
        position_pct_of_equity=7.0,
        risk_violations=[],
        signal_sources=["chat"],
    )
    defaults.update(overrides)
    return ApprovalContext(**defaults)


# ── ApprovalResult ────────────────────────────────────────────

def test_approval_result_approved():
    r = ApprovalResult(approved=True, reason="User approved")
    assert r.approved is True
    assert r.reason == "User approved"


def test_approval_result_rejected():
    r = ApprovalResult(approved=False, reason="Auto-reject mode")
    assert r.approved is False


# ── format_approval_summary ───────────────────────────────────

def test_format_approval_summary_returns_table():
    ctx = _make_context()
    result = format_approval_summary(ctx)
    # Should return a Rich Table object
    assert result is not None
    assert hasattr(result, "columns")  # Rich Table has columns


def test_format_with_risk_violations():
    ctx = _make_context(risk_violations=["Over daily loss limit"])
    result = format_approval_summary(ctx)
    assert result is not None


def test_format_with_limit_order():
    order = OrderPayload(
        symbol="TSLA", side="sell", qty=5,
        order_type="limit", limit_price=250.0,
    )
    ctx = _make_context(order=order)
    result = format_approval_summary(ctx)
    assert result is not None


def test_format_with_notional_order():
    order = OrderPayload(symbol="SPY", side="buy", notional=500.0)
    ctx = _make_context(order=order)
    result = format_approval_summary(ctx)
    assert result is not None


# ── request_approval_cli ──────────────────────────────────────

@patch("app.risk.approvals.console")
def test_cli_approved(mock_console):
    mock_console.input.return_value = "yes"
    ctx = _make_context()
    result = request_approval_cli(ctx)
    assert result.approved is True
    assert "approved" in result.reason.lower()


@patch("app.risk.approvals.console")
def test_cli_rejected(mock_console):
    mock_console.input.return_value = "no"
    ctx = _make_context()
    result = request_approval_cli(ctx)
    assert result.approved is False


@patch("app.risk.approvals.console")
def test_cli_y_shorthand(mock_console):
    mock_console.input.return_value = "y"
    ctx = _make_context()
    result = request_approval_cli(ctx)
    assert result.approved is True


@patch("app.risk.approvals.console")
def test_cli_eof_cancels(mock_console):
    mock_console.input.side_effect = EOFError()
    ctx = _make_context()
    result = request_approval_cli(ctx)
    assert result.approved is False
    assert "cancel" in result.reason.lower() or "eof" in result.reason.lower()


@patch("app.risk.approvals.console")
def test_cli_keyboard_interrupt_cancels(mock_console):
    mock_console.input.side_effect = KeyboardInterrupt()
    ctx = _make_context()
    result = request_approval_cli(ctx)
    assert result.approved is False


# ── request_approval (async modes) ───────────────────────────

@pytest.mark.asyncio
async def test_auto_reject_mode():
    ctx = _make_context()
    result = await request_approval(ctx, mode="auto_reject")
    assert result.approved is False
    assert "auto-reject" in result.reason.lower()


@pytest.mark.asyncio
async def test_auto_approve_mode():
    ctx = _make_context()
    result = await request_approval(ctx, mode="auto_approve")
    assert result.approved is True
    assert "auto-approved" in result.reason.lower()


@pytest.mark.asyncio
async def test_unknown_mode_raises():
    ctx = _make_context()
    with pytest.raises(ValueError, match="Unknown approval mode"):
        await request_approval(ctx, mode="web_ui")


@pytest.mark.asyncio
@patch("app.risk.approvals.console")
async def test_cli_mode_via_request_approval(mock_console):
    mock_console.input.return_value = "yes"
    ctx = _make_context()
    result = await request_approval(ctx, mode="cli")
    assert result.approved is True

