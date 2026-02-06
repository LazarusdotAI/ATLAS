"""
LLM Wrapper — unified interface for language models with intelligent routing.

Supports:
  • OpenAI  (GPT-4o, etc.)
  • Anthropic (Claude)
  • Ollama  (local models)

The wrapper detects the user's intent, gathers relevant data from the
appropriate strategy modules, injects that data into the LLM context,
and lets the LLM generate a natural-language response.

Capabilities:
  1. Predictive forecasting (technical + FinGPT)
  2. Complete trade plan generation (entry, stop, target, sizing)
  3. Technical analysis on demand (RSI, MACD, VWAP, ATR, Bollinger)
  4. Multi-signal consensus (sentiment + forecast + RL + TradingAgents)
  5. Market screening & discovery
  6. News & sentiment interpretation (FinBERT blended)
  7. Account & position queries
  8. Backtesting (historical strategy replay with performance metrics)
  9. Educational & coaching responses
  10. Workflow automation (chained multi-step requests)
  11. Trade execution (with human approval gate)
  12. Autonomous trading mode (AI-driven loop with safety controls)

Usage:
    reply, actions = await process_chat_message("Predict AAPL 5min", [], broker)
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from app.brokers.base import BrokerInterface, OrderRequest
from app.chat_handlers import detect_intent, route_intent, _extract_symbol
from app.risk.kill_switch import is_kill_switch_active
from app.risk.limits import run_all_checks
from app.settings import get_llm_settings
from app.storage.audit_log import log_event, log_prompt

logger = logging.getLogger(__name__)


# ── System prompt ──────────────────────────────────────────────

SYSTEM_PROMPT = """\
You are StockBotFree, an AI trading co-pilot operating in MANUAL mode.
The user is an active scalper. You have access to powerful analysis modules.

## Your Capabilities
1. **Predictive Forecasting** — Technical indicators (RSI, MACD, ATR, Bollinger, \
VWAP, trend slope, volume surge) and optional FinGPT LLM-based forecasting.
2. **Trade Plans** — Complete plans with entry, stop-loss, target, position sizing, \
risk/reward ratio, and conviction level.
3. **Technical Analysis** — Individual indicator values with interpretation.
4. **Multi-Signal Consensus** — Aggregate views from sentiment, technical forecaster, \
RL policy, and TradingAgents frameworks.
5. **Market Screening** — Scan for bullish/bearish/momentum setups using finviz.
6. **Sentiment Analysis** — FinBERT + FinBERT-Tone blended NLP analysis.
7. **Account Queries** — Equity, buying power, P&L, positions, open orders.
8. **Backtesting** — Historical strategy replay with performance metrics (P&L, win \
rate, Sharpe ratio, max drawdown, profit factor).
9. **Education** — Explain trading concepts, indicators, and risk management.
10. **Trade Execution** — Parse and propose trades (always requiring user confirmation).
11. **Autonomous Mode** — AI-driven trading loop (when enabled by the user).

## Hard Rules
• Daily loss limit: **-$100 net P&L**. Refuse new trades if breached.
• **NEVER** execute a trade without explicit user instruction and confirmation.
• Always include data source, confidence level, and risk context in responses.
• Use plain English. Be concise but complete.

## Response Guidelines
When analysis data is provided in [ANALYSIS DATA], use it to craft your response:
- Present numbers clearly (prices to 2 decimal places, percentages to 1 decimal)
- Explain what the data means in practical terms
- Always mention the confidence level and any caveats
- For trade plans, structure as: Direction → Entry → Stop → Target → Size → Risk

When the user gives a trade command, include a JSON block:
```json
{"action":"trade","symbol":"...","side":"buy|sell","qty":...,"order_type":"market|limit",\
"limit_price":null,"stop_loss":null,"target":null}
```
"""


# ── Provider-agnostic chat ─────────────────────────────────────

async def _call_openai(messages: List[Dict[str, str]], model: str, api_key: str) -> str:
    """Call OpenAI chat completions."""
    import openai
    client = openai.AsyncOpenAI(api_key=api_key)
    resp = await client.chat.completions.create(model=model, messages=messages)
    return resp.choices[0].message.content or ""


async def _call_anthropic(messages: List[Dict[str, str]], model: str, api_key: str) -> str:
    """Call Anthropic messages API."""
    import anthropic
    client = anthropic.AsyncAnthropic(api_key=api_key)
    # Anthropic expects system separate from messages
    system = ""
    user_msgs = []
    for m in messages:
        if m["role"] == "system":
            system = m["content"]
        else:
            user_msgs.append(m)
    resp = await client.messages.create(
        model=model, max_tokens=1024, system=system, messages=user_msgs,
    )
    return resp.content[0].text if resp.content else ""


async def _call_ollama(messages: List[Dict[str, str]], model: str, base_url: str) -> str:
    """Call local Ollama instance."""
    import httpx
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            f"{base_url}/api/chat",
            json={"model": model, "messages": messages, "stream": False},
        )
        resp.raise_for_status()
        return resp.json().get("message", {}).get("content", "")


async def _llm_chat(messages: List[Dict[str, str]]) -> str:
    """Route to the configured LLM provider."""
    cfg = get_llm_settings()
    provider = cfg.provider.lower()
    if provider == "openai":
        return await _call_openai(messages, cfg.model, cfg.api_key)
    elif provider == "anthropic":
        return await _call_anthropic(messages, cfg.model, cfg.api_key)
    elif provider in ("ollama", "local"):
        return await _call_ollama(messages, cfg.model, cfg.base_url)
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")


# ── Parse trade action from LLM reply ─────────────────────────

def _extract_trade_action(text: str) -> Optional[Dict[str, Any]]:
    """Try to extract a JSON trade action from the LLM response."""
    # Look for ```json ... ``` blocks
    match = re.search(r'```json\s*(\{.*?\})\s*```', text, re.DOTALL)
    if match:
        try:
            obj = json.loads(match.group(1))
            if obj.get("action") == "trade":
                return obj
        except json.JSONDecodeError:
            pass
    # Fallback: look for raw JSON object with "action":"trade"
    match = re.search(r'\{[^{}]*"action"\s*:\s*"trade"[^{}]*\}', text)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    return None



# ── Build data-enriched prompt ────────────────────────────────

def _build_data_prompt(intent: str, data: Dict[str, Any]) -> str:
    """Format gathered data as a structured context block for the LLM."""
    if not data:
        return ""

    lines = [f"\n[ANALYSIS DATA — intent: {intent}]"]
    for key, val in data.items():
        if key == "intent":
            continue
        if isinstance(val, dict):
            lines.append(f"  {key}:")
            for k2, v2 in val.items():
                lines.append(f"    {k2}: {v2}")
        elif isinstance(val, list):
            lines.append(f"  {key}:")
            for item in val[:15]:  # cap list output
                if isinstance(item, dict):
                    summary = ", ".join(f"{k}={v}" for k, v in item.items())
                    lines.append(f"    - {summary}")
                else:
                    lines.append(f"    - {item}")
        else:
            lines.append(f"  {key}: {val}")
    lines.append("[END ANALYSIS DATA]")
    return "\n".join(lines)


# ── Main entry point ───────────────────────────────────────────

async def process_chat_message(
    message: str,
    context: List[Dict[str, str]],
    broker: BrokerInterface,
) -> Tuple[str, List[Dict[str, Any]]]:
    """Process a user chat message and return (reply, actions).

    Flow:
      1. Detect intent from user message
      2. Route to handler → gather structured data
      3. Inject data into LLM context
      4. LLM generates natural-language response
      5. Extract trade actions if present

    Parameters
    ----------
    message : str
        The user's natural-language input.
    context : list[dict]
        Previous conversation messages [{"role": "...", "content": "..."}].
    broker : BrokerInterface
        Connected broker for account/order operations.

    Returns
    -------
    (reply, actions) where reply is the text response and actions is a
    list of dicts describing any trades or lookups performed.
    """
    actions: List[Dict[str, Any]] = []

    # ── 1. Detect intent ─────────────────────────────────────
    intent = detect_intent(message)
    logger.info("Chat intent detected: %s (message: %.80s…)", intent, message)

    # ── 2. Gather data from handler ──────────────────────────
    data_context = {}
    handler_error = None
    if intent not in ("trade_execute", "general"):
        try:
            data_context, handler_error = await route_intent(intent, message, broker)
        except Exception as exc:
            logger.error("Handler error for intent=%s: %s", intent, exc, exc_info=True)
            handler_error = str(exc)

    # ── 3. Build LLM message history with data injection ─────
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(context[-20:])  # keep last 20 for context window

    # Build user message with data context
    user_content = message
    if handler_error:
        user_content += f"\n\n[HANDLER ERROR: {handler_error}]"
    elif data_context:
        user_content += _build_data_prompt(intent, data_context)

    messages.append({"role": "user", "content": user_content})

    # ── 4. Call LLM ──────────────────────────────────────────
    cfg = get_llm_settings()
    try:
        reply = await _llm_chat(messages)
        log_prompt(
            user_message=message,
            system_prompt=SYSTEM_PROMPT,
            llm_response=reply,
            provider=cfg.provider,
            model=cfg.model,
        )
    except Exception as exc:
        logger.error("LLM call failed: %s", exc, exc_info=True)
        return f"LLM error: {exc}", []

    # Record intent in actions for the frontend
    actions.append({"action": "intent_detected", "intent": intent})

    # ── 5. Check for trade action in the reply ───────────────
    trade = _extract_trade_action(reply)
    if trade is None:
        return reply, actions

    # ── 6. Validate & propose trade ──────────────────────────
    if is_kill_switch_active():
        return "🚨 Kill switch is active — no trades allowed.", [
            {"action": "blocked", "reason": "kill_switch"}
        ]

    symbol = str(trade.get("symbol", "")).upper()
    side = str(trade.get("side", "")).lower()
    qty = float(trade.get("qty", 0))
    order_type = str(trade.get("order_type", "market")).lower()
    limit_price = trade.get("limit_price")

    if not symbol or side not in ("buy", "sell") or qty <= 0:
        return f"Could not parse valid trade from: {trade}", []

    # Fetch account for risk check
    account = await broker.get_account()
    current_price_est = qty * 100  # rough estimate; real price from quote
    try:
        quote = await broker.get_quote(symbol)
        if isinstance(quote, dict):
            ask = float(quote.get("ask_price", quote.get("ap", 0)) or 0)
            if ask > 0:
                current_price_est = qty * ask
    except Exception as exc:
        logger.warning("Quote fetch failed for %s, using estimate: %s", symbol, exc)

    risk = run_all_checks(
        symbol=symbol,
        order_notional=current_price_est,
        equity=account.equity,
        current_pnl=account.daily_pnl,
        open_order_count=0,
    )
    if not risk.passed:
        actions.append({"action": "risk_rejected", "violations": risk.violations})
        return f"⚠️ Trade rejected by risk checks: {'; '.join(risk.violations)}", actions

    # Build order
    order = OrderRequest(
        symbol=symbol,
        side=side,
        qty=qty,
        order_type=order_type,
        limit_price=float(limit_price) if limit_price else None,
    )

    # Confirmation prompt (don't auto-execute — return for user approval)
    actions.append({
        "action": "trade_proposed",
        "order": order.to_dict(),
        "stop_loss": trade.get("stop_loss"),
        "target": trade.get("target"),
        "status": "awaiting_approval",
    })
    log_event("chat_trade_proposed", {"order": order.to_dict()})

    confirm_msg = (
        f"📋 **Trade Proposed:**\n"
        f"- {side.upper()} {int(qty)} {symbol} @ {order_type.upper()}"
        f"{f' ${limit_price}' if limit_price else ''}\n"
        f"- Stop: {trade.get('stop_loss', 'N/A')}  |  Target: {trade.get('target', 'N/A')}\n\n"
        f"Reply **CONFIRM** to execute or **CANCEL** to abort."
    )
    return confirm_msg, actions


# ── Autonomous decision function ──────────────────────────────

AUTONOMOUS_SYSTEM_PROMPT = """\
You are StockBotFree operating in AUTONOMOUS trading mode.
You receive market data and technical signals and must decide whether to trade.

Respond ONLY with a valid JSON object. No commentary, no markdown, just JSON.

Decision schema:
{
  "action": "buy" | "sell" | "hold",
  "symbol": "TICKER",
  "confidence": 0.0-1.0,
  "rationale": "Brief reason",
  "stop_loss": null or price,
  "target": null or price
}

Rules:
• "hold" if signals are mixed, weak, or uncertain (confidence < 0.6)
• Always set stop_loss and target for buy/sell actions
• Be conservative — capital preservation is paramount
• Only trade when multiple signals agree with high confidence
"""


async def autonomous_decision(
    market_data: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """Ask the LLM for a structured autonomous trading decision.

    Parameters
    ----------
    market_data : dict
        Pre-gathered signal data, indicator values, and market context.

    Returns
    -------
    dict with keys: action, symbol, confidence, rationale, stop_loss, target
    or None if the LLM response can't be parsed.
    """
    messages = [
        {"role": "system", "content": AUTONOMOUS_SYSTEM_PROMPT},
        {"role": "user", "content": json.dumps(market_data, default=str)},
    ]

    try:
        raw = await _llm_chat(messages)
        log_prompt(
            user_message=json.dumps(market_data, default=str)[:500],
            system_prompt=AUTONOMOUS_SYSTEM_PROMPT[:200],
            llm_response=raw,
            provider=get_llm_settings().provider,
            model=get_llm_settings().model,
        )
    except Exception as exc:
        logger.error("Autonomous LLM call failed: %s", exc)
        return None

    # Parse JSON from response
    try:
        # Strip markdown fencing if present
        clean = re.sub(r'```json\s*', '', raw)
        clean = re.sub(r'```\s*', '', clean).strip()
        decision = json.loads(clean)
        if isinstance(decision, dict) and "action" in decision:
            return decision
    except json.JSONDecodeError:
        pass

    # Fallback: extract JSON object
    match = re.search(r'\{[^{}]*"action"[^{}]*\}', raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    logger.warning("Could not parse autonomous decision from LLM: %.200s", raw)
    return None

