"""Unit tests for app.risk.limits — risk-check enforcement."""

import pytest
from unittest.mock import patch

from app.risk.limits import (
    RiskCheckResult,
    check_daily_loss_limit,
    check_symbol_allowed,
    check_position_size,
    check_open_orders,
    run_all_checks,
)


# ── RiskCheckResult ────────────────────────────────────────────

def test_result_pass():
    r = RiskCheckResult(passed=True)
    assert bool(r) is True
    assert r.violations == []


def test_result_add_violation():
    r = RiskCheckResult(passed=True)
    r.add_violation("boom")
    assert r.passed is False
    assert "boom" in r.violations


# ── Daily loss limit ───────────────────────────────────────────

@patch("app.risk.limits.get_risk_settings")
def test_pnl_within_limit(mock_settings):
    mock_settings.return_value.daily_loss_limit = -100.0
    r = check_daily_loss_limit(-50.0)
    assert r.passed is True


@patch("app.risk.limits.get_risk_settings")
def test_pnl_at_limit(mock_settings):
    mock_settings.return_value.daily_loss_limit = -100.0
    r = check_daily_loss_limit(-100.0)
    assert r.passed is False


@patch("app.risk.limits.get_risk_settings")
def test_pnl_over_limit(mock_settings):
    mock_settings.return_value.daily_loss_limit = -100.0
    r = check_daily_loss_limit(-150.0)
    assert r.passed is False


@patch("app.risk.limits.get_risk_settings")
def test_pnl_positive(mock_settings):
    mock_settings.return_value.daily_loss_limit = -100.0
    r = check_daily_loss_limit(200.0)
    assert r.passed is True


# ── Symbol allowlist ───────────────────────────────────────────

@patch("app.risk.limits.get_risk_settings")
def test_symbol_in_list(mock_settings):
    mock_settings.return_value.symbol_allowlist = ["AAPL", "TSLA"]
    r = check_symbol_allowed("AAPL")
    assert r.passed is True


@patch("app.risk.limits.get_risk_settings")
def test_symbol_not_in_list(mock_settings):
    mock_settings.return_value.symbol_allowlist = ["AAPL", "TSLA"]
    r = check_symbol_allowed("GME")
    assert r.passed is False


@patch("app.risk.limits.get_risk_settings")
def test_symbol_empty_allowlist(mock_settings):
    mock_settings.return_value.symbol_allowlist = []
    r = check_symbol_allowed("ANY")
    assert r.passed is True


@patch("app.risk.limits.get_risk_settings")
def test_symbol_case_insensitive(mock_settings):
    mock_settings.return_value.symbol_allowlist = ["AAPL"]
    r = check_symbol_allowed("aapl")
    assert r.passed is True


# ── Position size ──────────────────────────────────────────────

@patch("app.risk.limits.get_risk_settings")
def test_position_within_limit(mock_settings):
    mock_settings.return_value.max_position_size_pct = 5.0
    r = check_position_size(order_notional=400, equity=10000)
    assert r.passed is True  # 4%


@patch("app.risk.limits.get_risk_settings")
def test_position_over_limit(mock_settings):
    mock_settings.return_value.max_position_size_pct = 5.0
    r = check_position_size(order_notional=600, equity=10000)
    assert r.passed is False  # 6%


@patch("app.risk.limits.get_risk_settings")
def test_position_zero_equity(mock_settings):
    mock_settings.return_value.max_position_size_pct = 5.0
    r = check_position_size(order_notional=100, equity=0)
    assert r.passed is False


# ── Open orders ────────────────────────────────────────────────

@patch("app.risk.limits.get_risk_settings")
def test_orders_within_limit(mock_settings):
    mock_settings.return_value.max_open_orders = 10
    r = check_open_orders(5)
    assert r.passed is True


@patch("app.risk.limits.get_risk_settings")
def test_orders_at_limit(mock_settings):
    mock_settings.return_value.max_open_orders = 10
    r = check_open_orders(10)
    assert r.passed is False


# ── Combined run_all_checks ────────────────────────────────────

@patch("app.risk.limits.get_risk_settings")
def test_all_checks_pass(mock_settings):
    s = mock_settings.return_value
    s.daily_loss_limit = -100.0
    s.symbol_allowlist = ["AAPL"]
    s.max_position_size_pct = 10.0
    s.max_open_orders = 10
    r = run_all_checks("AAPL", 500, 10000, -20.0, 2)
    assert r.passed is True
    assert r.violations == []


@patch("app.risk.limits.get_risk_settings")
def test_all_checks_multiple_failures(mock_settings):
    s = mock_settings.return_value
    s.daily_loss_limit = -100.0
    s.symbol_allowlist = ["AAPL"]
    s.max_position_size_pct = 5.0
    s.max_open_orders = 3
    r = run_all_checks("GME", 600, 10000, -120.0, 5)
    assert r.passed is False
    assert len(r.violations) >= 3  # pnl + symbol + orders (+ maybe size)

