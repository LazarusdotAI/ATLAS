"""Integration tests for full pipeline: chat → LLM → risk check → approval.

Uses mock broker and patched LLM to test the complete flow without
real API calls.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.brokers.base import (
    AccountInfo, BrokerInterface, OrderRequest, OrderResult, Position,
)
from app.llm import process_chat_message, _extract_trade_action
from app.risk.kill_switch import reset_kill_switch


# ── Fixtures ──────────────────────────────────────────────────

def _mock_broker(equity=25000.0, daily_pnl=-20.0):
    broker = AsyncMock(spec=BrokerInterface)
    broker.get_account.return_value = AccountInfo(
        equity=equity, buying_power=50000.0, cash=25000.0,
        daily_pnl=daily_pnl, account_type="paper", broker="mock",
    )
    broker.get_quote.return_value = {"ask_price": "175.00", "bid_price": "174.95"}
    broker.place_order.return_value = OrderResult(
        order_id="test-001", symbol="AAPL", side="buy",
        qty=10, filled_qty=10, avg_fill_price=175.00, status="filled",
    )
    return broker


@pytest.fixture(autouse=True)
def _reset():
    reset_kill_switch()
    yield
    reset_kill_switch()


# ── Full pipeline: chat message → trade proposal ─────────────

MOCK_LLM_TRADE_RESPONSE = """
I'll execute that trade for you.
```json
{"action":"trade","symbol":"AAPL","side":"buy","qty":10,"order_type":"market","limit_price":null,"stop_loss":170.0,"target":180.0}
```
"""

MOCK_LLM_PLAIN_RESPONSE = "The market is currently open. SPY is trading at $450."


@pytest.mark.asyncio
@patch("app.llm._llm_chat")
@patch("app.risk.limits.get_risk_settings")
async def test_trade_proposal_flow(mock_risk_settings, mock_llm):
    """Chat message with trade intent → risk check → proposal."""
    mock_llm.return_value = MOCK_LLM_TRADE_RESPONSE
    s = mock_risk_settings.return_value
    s.daily_loss_limit = -100.0
    s.symbol_allowlist = ["AAPL", "TSLA", "SPY"]
    s.max_position_size_pct = 10.0
    s.max_open_orders = 10

    broker = _mock_broker()
    reply, actions = await process_chat_message("Buy 10 AAPL at market", [], broker)

    assert "trade" in reply.lower() or "AAPL" in reply
    assert len(actions) >= 1
    # First action is always intent_detected, trade_proposed follows
    trade_actions = [a for a in actions if a["action"] == "trade_proposed"]
    assert len(trade_actions) == 1
    assert trade_actions[0]["order"]["symbol"] == "AAPL"
    assert trade_actions[0]["status"] == "awaiting_approval"


@pytest.mark.asyncio
@patch("app.llm._llm_chat")
async def test_plain_message_no_actions(mock_llm):
    """Non-trade message → plain response, no actions."""
    mock_llm.return_value = MOCK_LLM_PLAIN_RESPONSE

    broker = _mock_broker()
    reply, actions = await process_chat_message("What's the market doing?", [], broker)

    assert reply == MOCK_LLM_PLAIN_RESPONSE
    # Only intent_detected action expected (no trade actions)
    trade_actions = [a for a in actions if a["action"] != "intent_detected"]
    assert trade_actions == []


@pytest.mark.asyncio
@patch("app.llm._llm_chat")
@patch("app.risk.limits.get_risk_settings")
async def test_risk_rejection_blocks_trade(mock_risk_settings, mock_llm):
    """Trade blocked when daily loss limit hit."""
    mock_llm.return_value = MOCK_LLM_TRADE_RESPONSE
    s = mock_risk_settings.return_value
    s.daily_loss_limit = -100.0
    s.symbol_allowlist = ["AAPL"]
    s.max_position_size_pct = 10.0
    s.max_open_orders = 10

    broker = _mock_broker(daily_pnl=-120.0)  # Over the limit
    reply, actions = await process_chat_message("Buy 10 AAPL", [], broker)

    assert "rejected" in reply.lower() or "risk" in reply.lower()
    assert any(a.get("action") == "risk_rejected" for a in actions)


@pytest.mark.asyncio
@patch("app.llm._llm_chat")
async def test_kill_switch_blocks_trade(mock_llm):
    """Trade blocked when kill switch is active."""
    mock_llm.return_value = MOCK_LLM_TRADE_RESPONSE

    # Activate kill switch
    import app.risk.kill_switch as ks
    ks._kill_switch_active = True

    broker = _mock_broker()
    reply, actions = await process_chat_message("Buy 10 AAPL", [], broker)

    assert "kill switch" in reply.lower()
    assert any(a.get("reason") == "kill_switch" for a in actions)


@pytest.mark.asyncio
@patch("app.llm._llm_chat")
@patch("app.risk.limits.get_risk_settings")
async def test_symbol_not_allowed_rejection(mock_risk_settings, mock_llm):
    """Trade blocked when symbol not in allowlist."""
    mock_llm.return_value = MOCK_LLM_TRADE_RESPONSE.replace("AAPL", "GME")
    s = mock_risk_settings.return_value
    s.daily_loss_limit = -100.0
    s.symbol_allowlist = ["AAPL", "TSLA"]
    s.max_position_size_pct = 10.0
    s.max_open_orders = 10

    broker = _mock_broker()
    reply, actions = await process_chat_message("Buy 10 GME", [], broker)

    assert "rejected" in reply.lower() or "risk" in reply.lower()


@pytest.mark.asyncio
@patch("app.llm._llm_chat")
async def test_llm_error_returns_message(mock_llm):
    """LLM call failure → error message, no crash."""
    mock_llm.side_effect = Exception("API timeout")

    broker = _mock_broker()
    reply, actions = await process_chat_message("Buy AAPL", [], broker)

    assert "error" in reply.lower()
    assert actions == []

