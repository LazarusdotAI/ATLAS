"""
Chat Intent Handlers — detect user intent and gather structured data.

Each handler calls the appropriate strategy module, formats the results
as a context dict, and returns it for injection into the LLM prompt so the
LLM can generate a natural-language response.

Supported intents:
  forecast, trade_plan, technical_analysis, consensus, screen,
  sentiment, account, education, backtest, workflow, trade_execute
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from app.brokers.base import BrokerInterface

logger = logging.getLogger(__name__)

# ── Timeframe mapping ─────────────────────────────────────────

_TF_ALIASES: Dict[str, str] = {
    "1m": "1Min", "1min": "1Min", "1-min": "1Min", "1 min": "1Min",
    "5m": "5Min", "5min": "5Min", "5-min": "5Min", "5 min": "5Min",
    "15m": "15Min", "15min": "15Min", "15-min": "15Min", "15 min": "15Min",
    "1h": "1Hour", "1hr": "1Hour", "1hour": "1Hour", "1 hour": "1Hour",
    "1d": "1Day", "1day": "1Day", "daily": "1Day", "1 day": "1Day",
}


def _extract_symbol(text: str) -> Optional[str]:
    """Extract a stock ticker from natural language.

    Looks for $SYMBOL, explicit ticker mentions, or standalone 1-5 letter
    uppercase words that look like tickers.
    """
    # $AAPL style
    m = re.search(r'\$([A-Za-z]{1,5})\b', text)
    if m:
        return m.group(1).upper()
    # "for AAPL", "on TSLA", "of NVDA", "about SPY"
    m = re.search(r'(?:for|on|of|about|analyze|predict|forecast)\s+([A-Z]{1,5})\b', text)
    if m:
        return m.group(1).upper()
    # Standalone uppercase 1-5 letter word (heuristic — pick the last one)
    tickers = re.findall(r'\b([A-Z]{1,5})\b', text)
    # Filter out common English words
    _STOP = {
        "I", "A", "AN", "THE", "AND", "OR", "FOR", "TO", "IN", "ON", "AT",
        "MY", "ME", "OF", "IS", "IT", "IF", "UP", "DO", "BE", "BY", "NO",
        "SO", "WE", "HE", "AS", "ALL", "CAN", "HAS", "RSI", "MACD", "VWAP",
        "ATR", "EMA", "SMA", "BUY", "SELL", "SET", "GET", "NOT", "YOU",
        "WHAT", "SHOW", "FIND", "GIVE", "TELL", "HOW", "WHY", "WHEN",
        "WITH", "FROM", "THAT", "THIS", "YOUR", "THEY", "THEM", "WILL",
        "HAVE", "JUST", "THEN", "LIKE", "MAKE", "TAKE", "STOP", "EACH",
        "DAY", "NEW", "NOW", "OLD", "ANY", "MIN", "MAX", "TOP", "LOW",
    }
    filtered = [t for t in tickers if t not in _STOP and len(t) >= 2]
    if filtered:
        return filtered[-1]
    return None


def _extract_timeframe(text: str) -> str:
    """Extract a timeframe string from user text. Default '5Min'."""
    lower = text.lower()
    for alias, tf in _TF_ALIASES.items():
        if alias in lower:
            return tf
    return "5Min"


# ── Intent classifier (keyword / pattern) ────────────────────

INTENT_PATTERNS: List[Tuple[str, List[str]]] = [
    ("backtest", [
        r"\bback\s?test", r"\bhistorical\s+test", r"\bsimulat",
    ]),
    ("consensus", [
        r"\ball\s+(your\s+)?models", r"\bmulti[\-\s]?signal", r"\bconsensus",
        r"\bwhat do.*(models|signals)\s+say", r"\baggregate",
        r"\bcombine.*signals",
    ]),
    ("screen", [
        r"\bscreen", r"\bscan\b", r"\bfind\s+me\b", r"\blook\s+for\b",
        r"\bbullish\s+setups?\b", r"\bmomentum\s+plays?\b",
        r"\bscalp\s+setups?\b", r"\bdiscover\b",
    ]),
    ("trade_plan", [
        r"\btrade\s+plan", r"\btrade\s+setup", r"\bentry\s+and\s+exit",
        r"\bgive\s+me\s+a\s+plan", r"\bposition\s+siz", r"\bplan\s+for\b",
    ]),
    ("forecast", [
        r"\bpredict", r"\bforecast", r"\btrajectory", r"\bprice\s+prediction",
        r"\bwhere\s+is.*going", r"\bprojection", r"\boutlook\b",
    ]),
    ("technical_analysis", [
        r"\brsi\b", r"\bmacd\b", r"\bvwap\b", r"\bbollinger",
        r"\btechnical\s+analysis", r"\bindicators?\b", r"\bshow\s+me\b.*chart",
        r"\batr\b", r"\bema\b", r"\bsma\b",
    ]),
    ("sentiment", [
        r"\bsentiment", r"\bnews\b.*(?:analy|about)", r"\bheadline",
        r"\bwhat.*mood", r"\bbullish\s+or\s+bearish",
        r"\bhow.*(?:feel|feeling).*about",
    ]),
    ("account", [
        r"\baccount\b", r"\bequity\b", r"\bbuying\s+power",
        r"\bp[&/]?l\b", r"\bpositions?\b", r"\bbalance\b",
        r"\bportfolio\b", r"\bwhat.*(?:own|holding|have)\b",
        r"\borders?\b", r"\bopen\s+orders?\b",
    ]),
    ("education", [
        r"\bexplain\b", r"\bwhat\s+is\b", r"\bteach\b", r"\bhow\s+does\b",
        r"\bdefine\b", r"\bdefinition\b", r"\btutorial\b",
    ]),
]


def detect_intent(message: str) -> str:
    """Classify user message into an intent category.

    Returns one of: forecast, trade_plan, technical_analysis, consensus,
    screen, sentiment, account, education, backtest, workflow, trade_execute,
    or 'general' as fallback.
    """
    lower = message.lower()

    # Check for workflow (multiple intents chained)
    intents_found: List[str] = []
    for intent, patterns in INTENT_PATTERNS:
        for pat in patterns:
            if re.search(pat, lower):
                intents_found.append(intent)
                break
    if len(intents_found) >= 2:
        return "workflow"
    if intents_found:
        return intents_found[0]

    # Trade execution (buy/sell with qty — existing path)
    if re.search(r'\b(buy|sell)\b.*\b\d+\b', lower) or re.search(r'\b\d+\b.*\b(buy|sell)\b', lower):
        return "trade_execute"

    return "general"


# ── Handler functions ────────────────────────────────────────
# Each returns (context_data: dict, error: Optional[str]).
# context_data is injected into the LLM prompt as structured info.


async def handle_forecast(
    message: str, broker: BrokerInterface,
) -> Tuple[Dict[str, Any], Optional[str]]:
    """Run technical + optional FinGPT forecast for a symbol."""
    symbol = _extract_symbol(message)
    if not symbol:
        return {}, "I need a ticker symbol to generate a forecast. Try: 'Predict AAPL 5min'"

    tf = _extract_timeframe(message)

    from app.strategy.forecaster import generate_forecast_signal
    try:
        signal = await generate_forecast_signal(broker, symbol, timeframe=tf)
        data = {
            "intent": "forecast",
            "symbol": symbol,
            "timeframe": tf,
            "direction": signal.direction,
            "confidence": signal.confidence,
            "stop_level": signal.stop_level,
            "target_level": signal.target_level,
            "horizon": signal.horizon,
            "rationale": signal.rationale,
            "metadata": signal.metadata,
        }
        return data, None
    except Exception as exc:
        logger.error("Forecast failed for %s: %s", symbol, exc, exc_info=True)
        return {}, f"Forecast error for {symbol}: {exc}"


async def handle_trade_plan(
    message: str, broker: BrokerInterface,
) -> Tuple[Dict[str, Any], Optional[str]]:
    """Generate a complete trade plan: entry, stop, target, sizing, conviction."""
    symbol = _extract_symbol(message)
    if not symbol:
        return {}, "I need a ticker symbol for a trade plan. Try: 'Trade plan for TSLA'"

    tf = _extract_timeframe(message)

    from app.strategy.forecaster import generate_forecast_signal
    try:
        signal = await generate_forecast_signal(broker, symbol, timeframe=tf)

        # Get account info for position sizing
        account = await broker.get_account()
        equity = account.equity

        # Position sizing: risk 1% of equity per trade, using stop distance
        risk_budget = equity * 0.01  # 1% risk
        current_price = signal.metadata.get("current_price", 0)
        stop = signal.stop_level
        target = signal.target_level

        if current_price and stop:
            risk_per_share = abs(current_price - stop)
            if risk_per_share > 0:
                shares = max(1, int(risk_budget / risk_per_share))
            else:
                shares = 1
            total_risk = shares * risk_per_share
            rr_ratio = abs(target - current_price) / risk_per_share if target and risk_per_share > 0 else 0
        else:
            shares = 1
            total_risk = 0
            rr_ratio = 0

        data = {
            "intent": "trade_plan",
            "symbol": symbol,
            "timeframe": tf,
            "direction": signal.direction,
            "confidence": signal.confidence,
            "current_price": current_price,
            "entry_price": current_price,
            "stop_loss": stop,
            "target_price": target,
            "position_size_shares": shares,
            "risk_per_share": abs(current_price - stop) if current_price and stop else None,
            "total_risk_dollars": round(total_risk, 2),
            "risk_reward_ratio": round(rr_ratio, 2),
            "equity": equity,
            "risk_pct_of_equity": round((total_risk / equity) * 100, 2) if equity > 0 else 0,
            "rationale": signal.rationale,
            "indicators": {
                "rsi": signal.metadata.get("rsi"),
                "macd_histogram": signal.metadata.get("macd_histogram"),
                "atr": signal.metadata.get("atr"),
                "volume_surge": signal.metadata.get("volume_surge"),
                "trend_slope": signal.metadata.get("trend_slope"),
            },
        }
        return data, None
    except Exception as exc:
        logger.error("Trade plan failed for %s: %s", symbol, exc, exc_info=True)
        return {}, f"Trade plan error for {symbol}: {exc}"


async def handle_technical_analysis(
    message: str, broker: BrokerInterface,
) -> Tuple[Dict[str, Any], Optional[str]]:
    """Compute and return individual technical indicators for a symbol."""
    symbol = _extract_symbol(message)
    if not symbol:
        return {}, "I need a ticker symbol for technical analysis. Try: 'RSI and MACD for SPY'"

    tf = _extract_timeframe(message)

    from app.strategy.forecaster import (
        generate_forecast_signal,
        compute_rsi, compute_macd, compute_atr,
        compute_bollinger_bands, compute_vwap, compute_volume_surge,
        compute_trend_slope,
    )
    try:
        # Use the full forecaster to get all indicators at once
        signal = await generate_forecast_signal(broker, symbol, timeframe=tf)
        meta = signal.metadata

        data = {
            "intent": "technical_analysis",
            "symbol": symbol,
            "timeframe": tf,
            "current_price": meta.get("current_price"),
            "indicators": {
                "rsi": meta.get("rsi"),
                "macd_histogram": meta.get("macd_histogram"),
                "atr": meta.get("atr"),
                "trend_slope": meta.get("trend_slope"),
                "volume_surge": meta.get("volume_surge"),
                "volatility_annual": meta.get("volatility_annual"),
                "bollinger": meta.get("bollinger"),
            },
            "direction": signal.direction,
            "confidence": signal.confidence,
            "rationale": signal.rationale,
        }
        return data, None
    except Exception as exc:
        logger.error("Technical analysis failed for %s: %s", symbol, exc, exc_info=True)
        return {}, f"Technical analysis error for {symbol}: {exc}"


async def handle_consensus(
    message: str, broker: BrokerInterface,
) -> Tuple[Dict[str, Any], Optional[str]]:
    """Run all signal modules and aggregate via meta-controller."""
    symbol = _extract_symbol(message)
    if not symbol:
        return {}, "I need a ticker symbol for consensus analysis. Try: 'What do your models say about NVDA?'"

    from app.strategy.forecaster import generate_forecast_signal
    from app.strategy.sentiment import generate_blended_sentiment_signal
    from app.strategy.rl_policy import generate_rl_signal
    from app.strategy.trading_agents_adapter import generate_trading_agents_signal
    from app.strategy.meta_controller import _weighted_vote, DEFAULT_SOURCE_WEIGHTS

    signals = []
    errors = []

    # Run all modules concurrently
    tasks = {
        "forecaster": generate_forecast_signal(broker, symbol),
        "sentiment": generate_blended_sentiment_signal(
            f"Latest market analysis for {symbol}", symbol
        ),
        "rl_policy": generate_rl_signal(broker, symbol),
        "trading_agents": generate_trading_agents_signal(symbol),
    }

    results = await asyncio.gather(
        *tasks.values(), return_exceptions=True
    )
    source_names = list(tasks.keys())

    for name, result in zip(source_names, results):
        if isinstance(result, Exception):
            errors.append(f"{name}: {result}")
            logger.warning("Consensus module %s failed: %s", name, result)
        else:
            signals.append(result)

    # Aggregate
    direction, confidence, agreeing = _weighted_vote(signals, DEFAULT_SOURCE_WEIGHTS)

    signal_summaries = []
    for s in signals:
        signal_summaries.append({
            "source": s.source,
            "direction": s.direction,
            "confidence": s.confidence,
            "rationale": s.rationale[:2],  # top 2 reasons
        })

    data = {
        "intent": "consensus",
        "symbol": symbol,
        "consensus_direction": direction,
        "consensus_confidence": confidence,
        "agreeing_count": len(agreeing),
        "total_signals": len(signals),
        "signal_details": signal_summaries,
        "errors": errors,
    }
    return data, None


async def handle_screen(
    message: str, broker: BrokerInterface,
) -> Tuple[Dict[str, Any], Optional[str]]:
    """Screen the market for setups matching the user's criteria."""
    from app.strategy.screener import screen_market, batch_analyze, PRESETS

    lower = message.lower()

    # Detect preset from message
    preset = "scalp_long"  # default
    if "short" in lower or "bearish" in lower:
        preset = "scalp_short"
    elif "momentum" in lower:
        preset = "momentum"

    # Extract price constraints from message
    filters = None
    price_match = re.search(r'under\s+\$?(\d+)', lower)
    if price_match:
        max_price = int(price_match.group(1))
        base = dict(PRESETS.get(preset, {}))
        base["Price"] = f"Under ${max_price}"
        filters = base

    try:
        tickers = screen_market(filters=filters, preset=preset, limit=20)
        if not tickers:
            return {"intent": "screen", "preset": preset, "tickers": [], "signals": []}, None

        # Analyze top results
        signals = await batch_analyze(broker, tickers[:10], timeframe="5Min")
        signal_data = []
        for s in signals[:10]:
            signal_data.append({
                "symbol": s.symbol,
                "direction": s.direction,
                "confidence": s.confidence,
                "stop_level": s.stop_level,
                "target_level": s.target_level,
                "rationale": s.rationale[:2],
            })

        data = {
            "intent": "screen",
            "preset": preset,
            "total_screened": len(tickers),
            "tickers": tickers[:20],
            "top_signals": signal_data,
        }
        return data, None
    except Exception as exc:
        logger.error("Screener failed: %s", exc, exc_info=True)
        return {}, f"Screener error: {exc}"


async def handle_sentiment(
    message: str, broker: BrokerInterface,
) -> Tuple[Dict[str, Any], Optional[str]]:
    """Run blended sentiment analysis on user-provided text or a symbol."""
    from app.strategy.sentiment import generate_blended_sentiment_signal

    symbol = _extract_symbol(message) or "MARKET"

    # Use the user's message as the text to analyze
    # Strip common prefixes so we analyze the actual content
    text = re.sub(
        r'^(?:sentiment|analyze|what.*?(?:mood|sentiment)|news)\s*(?:for|on|about|of)?\s*',
        '', message, flags=re.IGNORECASE,
    ).strip()
    if len(text) < 5:
        text = f"Current market conditions for {symbol}"

    try:
        signal = await generate_blended_sentiment_signal(text, symbol)
        data = {
            "intent": "sentiment",
            "symbol": symbol,
            "analyzed_text": text[:200],
            "direction": signal.direction,
            "confidence": signal.confidence,
            "rationale": signal.rationale,
            "metadata": signal.metadata,
        }
        return data, None
    except Exception as exc:
        logger.error("Sentiment failed: %s", exc, exc_info=True)
        return {}, f"Sentiment analysis error: {exc}"


async def handle_account(
    message: str, broker: BrokerInterface,
) -> Tuple[Dict[str, Any], Optional[str]]:
    """Fetch account info, positions, and/or orders."""
    lower = message.lower()
    data: Dict[str, Any] = {"intent": "account"}

    try:
        # Always include account summary
        account = await broker.get_account()
        data["equity"] = account.equity
        data["buying_power"] = account.buying_power
        data["cash"] = account.cash
        data["daily_pnl"] = account.daily_pnl
        data["account_type"] = account.account_type

        # Include positions if asked or by default
        if any(w in lower for w in ("position", "holding", "own", "portfolio", "all")):
            positions = await broker.get_positions()
            data["positions"] = [
                {
                    "symbol": p.symbol, "qty": p.qty, "side": p.side,
                    "entry_price": p.entry_price, "current_price": p.current_price,
                    "unrealised_pnl": p.unrealised_pnl,
                }
                for p in positions
            ]

        # Include orders if asked
        if any(w in lower for w in ("order", "recent order", "open order")):
            orders = await broker.get_orders(status="open", limit=10)
            data["open_orders"] = orders if isinstance(orders, list) else []

        return data, None
    except Exception as exc:
        logger.error("Account query failed: %s", exc, exc_info=True)
        return {}, f"Account query error: {exc}"


async def handle_education(
    message: str, broker: BrokerInterface,
) -> Tuple[Dict[str, Any], Optional[str]]:
    """Return context for educational/coaching questions.

    The LLM handles the actual explanation — we just provide system context
    about our risk controls and available tools.
    """
    data = {
        "intent": "education",
        "available_tools": [
            "Technical forecaster (RSI, MACD, ATR, Bollinger, VWAP, trend slope)",
            "Sentiment analysis (ProsusAI/finbert + finbert-tone blended)",
            "RL policy (PPO/A2C/DQN via Stable-Baselines3)",
            "TradingAgents (multi-agent LLM framework)",
            "Market screener (finviz-based with scalp/momentum presets)",
            "Meta-controller (weighted consensus from all models)",
        ],
        "risk_controls": [
            "Daily loss limit: -$100 hard stop",
            "Position size: max 5% of equity per trade",
            "Symbol allowlist enforcement",
            "Market hours restriction (NYSE 09:30-16:00 ET)",
            "Kill switch for emergency stop",
            "Human approval gate before every trade execution",
        ],
    }
    return data, None


async def handle_backtest(
    message: str, broker: BrokerInterface,
) -> Tuple[Dict[str, Any], Optional[str]]:
    """Run a backtest on requested symbols using the technical strategy.

    Parses symbols, days, and timeframe from the message, then calls the
    backtesting engine and returns structured results.
    """
    from app.strategy.backtester import run_backtest

    # Extract symbols — multiple tickers or default to SPY
    symbols = _extract_backtest_symbols(message)
    if not symbols:
        symbols = ["SPY"]

    # Extract days (default 30)
    days_match = re.search(r'(\d+)\s*(?:day|days|d)\b', message, re.IGNORECASE)
    days = int(days_match.group(1)) if days_match else 30
    days = max(5, min(365, days))  # clamp

    # Extract timeframe
    tf = _extract_timeframe(message) or "5Min"

    try:
        result = await run_backtest(
            broker=broker,
            symbols=symbols,
            days=days,
            timeframe=tf,
            min_confidence=0.55,
        )
        data = {
            "intent": "backtest",
            "available": True,
            **result.to_dict(),
        }
        return data, None
    except Exception as exc:
        logger.error("Backtest failed: %s", exc, exc_info=True)
        return {
            "intent": "backtest",
            "available": False,
            "error": str(exc),
        }, f"Backtest error: {exc}"


def _extract_backtest_symbols(text: str) -> List[str]:
    """Extract multiple ticker symbols from a backtest request."""
    # Look for $TICKER patterns
    dollar_tickers = re.findall(r'\$([A-Za-z]{1,5})\b', text)
    if dollar_tickers:
        return [t.upper() for t in dollar_tickers]

    # Look for comma-separated tickers: "AAPL, MSFT, TSLA"
    csv_match = re.search(r'\b([A-Z]{1,5}(?:\s*,\s*[A-Z]{1,5})+)\b', text)
    if csv_match:
        return [t.strip() for t in csv_match.group(1).split(",")]

    # "for AAPL" / "on SPY" style (single)
    m = re.search(r'(?:for|on|of|about)\s+([A-Z]{1,5})\b', text)
    if m:
        return [m.group(1)]

    # "most liquid stocks" or generic — use default list
    if re.search(r'(?:liquid|top|popular|major)\s+(?:stock|ticker|symbol)', text, re.IGNORECASE):
        return ["SPY", "QQQ", "AAPL", "MSFT", "TSLA", "NVDA", "AMD", "AMZN", "GOOG", "META"]

    # "earnings" keyword → default earnings-relevant tickers
    if re.search(r'earning', text, re.IGNORECASE):
        return ["SPY", "QQQ", "AAPL", "MSFT", "TSLA", "NVDA", "AMD", "AMZN", "GOOG", "META"]

    # Fallback: find any uppercase words that look like tickers
    tickers = re.findall(r'\b([A-Z]{2,5})\b', text)
    # Filter out common words
    noise = {"THE", "AND", "FOR", "WITH", "FROM", "THAT", "THIS", "HELP",
             "COME", "BASED", "AFTER", "RIGHT", "DAY", "MIN", "MOST"}
    return [t for t in tickers if t not in noise][:10]


async def handle_workflow(
    message: str, broker: BrokerInterface,
) -> Tuple[Dict[str, Any], Optional[str]]:
    """Execute a chained multi-step workflow.

    Detects multiple intents in the message and runs them sequentially,
    combining results into a single structured response.
    """
    lower = message.lower()
    results: List[Dict[str, Any]] = []
    errors: List[str] = []

    # Determine which steps to run
    steps: List[Tuple[str, Any]] = []
    for intent, patterns in INTENT_PATTERNS:
        for pat in patterns:
            if re.search(pat, lower):
                handler = _HANDLER_MAP.get(intent)
                if handler:
                    steps.append((intent, handler))
                break

    if not steps:
        return {}, "I couldn't determine the workflow steps. Please be more specific."

    # Execute steps sequentially (order matters for chaining)
    for step_name, handler in steps:
        try:
            data, err = await handler(message, broker)
            if err:
                errors.append(f"Step '{step_name}': {err}")
            elif data:
                results.append(data)
        except Exception as exc:
            errors.append(f"Step '{step_name}' failed: {exc}")

    workflow_data = {
        "intent": "workflow",
        "steps_executed": [s[0] for s in steps],
        "step_results": results,
        "errors": errors,
    }
    return workflow_data, None


# ── Handler dispatch map ─────────────────────────────────────

_HANDLER_MAP: Dict[str, Any] = {
    "forecast": handle_forecast,
    "trade_plan": handle_trade_plan,
    "technical_analysis": handle_technical_analysis,
    "consensus": handle_consensus,
    "screen": handle_screen,
    "sentiment": handle_sentiment,
    "account": handle_account,
    "education": handle_education,
    "backtest": handle_backtest,
    "workflow": handle_workflow,
}


async def route_intent(
    intent: str, message: str, broker: BrokerInterface,
) -> Tuple[Dict[str, Any], Optional[str]]:
    """Route a detected intent to the appropriate handler.

    Returns (context_data, error_message).
    """
    handler = _HANDLER_MAP.get(intent)
    if handler is None:
        return {}, None  # No special handler — pure LLM response
    return await handler(message, broker)