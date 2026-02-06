"""
FastAPI application — REST + WebSocket endpoints for StockBotFree.

Endpoints:
  GET  /health          — liveness probe
  GET  /account         — current account snapshot
  GET  /positions       — open positions
  GET  /orders          — order history
  GET  /clock           — market open/close status
  POST /chat            — natural-language trade chat
  POST /screen          — run mass market screener
  POST /kill-switch     — emergency stop
  GET  /kill-switch     — kill switch status
  WS   /ws              — real-time event stream

Run:
    uvicorn app.api:app --reload --port 8000
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

from fastapi import Body, Depends, FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.brokers import get_broker
from app.brokers.base import BrokerInterface
from app.middleware.auth import require_api_key
from app.risk.kill_switch import (
    emergency_stop,
    get_kill_switch_info,
    is_kill_switch_active,
)
from app.storage.state import get_session_state

logger = logging.getLogger(__name__)

# ── Shared broker singleton ────────────────────────────────────
_broker: Optional[BrokerInterface] = None


async def _get_broker() -> BrokerInterface:
    global _broker
    if _broker is None:
        try:
            _broker = await get_broker()
        except Exception as exc:
            logger.error("Broker connection failed: %s", exc)
            raise HTTPException(
                status_code=503,
                detail=f"Broker unavailable: {exc}",
            )
    return _broker


@asynccontextmanager
async def lifespan(application: FastAPI):
    """Startup: connect broker. Shutdown: disconnect."""
    global _broker
    try:
        _broker = await get_broker()
        logger.info("Broker connected on startup.")
    except Exception as exc:
        logger.warning("Broker connection failed on startup: %s — running without broker.", exc)
        _broker = None
    yield
    if _broker is not None:
        try:
            await _broker.disconnect()
        except Exception:
            pass
        _broker = None
        logger.info("Broker disconnected on shutdown.")


# ── Rate limiter ──────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="StockBotFree API",
    version="0.1.0",
    lifespan=lifespan,
    dependencies=[Depends(require_api_key)],
)

app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def _rate_limit_handler(request: Request, exc: RateLimitExceeded):
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded. Try again later."},
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request / Response models ──────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    context: Optional[List[Dict[str, str]]] = None


class ChatResponse(BaseModel):
    reply: str
    actions: List[Dict[str, Any]] = []
    intent: Optional[str] = None


class ScreenRequest(BaseModel):
    preset: Optional[str] = "scalp_long"
    filters: Optional[Dict[str, str]] = None
    limit: int = 50
    analyze: bool = True
    timeframe: str = "5Min"


class KillSwitchRequest(BaseModel):
    reason: str = "Manual trigger via API"


# ── Health ─────────────────────────────────────────────────────

@app.get("/health")
async def health():
    """Liveness probe — basic status."""
    return {"status": "ok", "kill_switch": is_kill_switch_active()}


@app.get("/health/detailed")
async def health_detailed():
    """Detailed health check with dependency status."""
    deps = {}

    # Broker connectivity
    try:
        broker = await _get_broker()
        await broker.get_clock()
        deps["broker"] = {"status": "ok"}
    except Exception as e:
        deps["broker"] = {"status": "error", "detail": str(e)[:200]}

    # Audit log writable
    try:
        from app.storage.audit_log import _get_log_path
        path = _get_log_path()
        deps["audit_log"] = {"status": "ok", "path": str(path)}
    except Exception as e:
        deps["audit_log"] = {"status": "error", "detail": str(e)[:200]}

    # Anomaly detector
    from app.monitoring.anomaly import get_anomaly_detector
    detector = get_anomaly_detector()
    deps["anomaly_detector"] = {
        "status": "ok",
        "anomaly_count": detector.anomaly_count,
    }

    overall = "ok" if all(d["status"] == "ok" for d in deps.values()) else "degraded"
    return {
        "status": overall,
        "kill_switch": is_kill_switch_active(),
        "dependencies": deps,
    }


# ── Account ────────────────────────────────────────────────────

@app.get("/account")
async def account():
    """Return current account snapshot: equity, buying power, cash, daily P&L."""
    broker = await _get_broker()
    info = await broker.get_account()
    state = get_session_state()
    state.update_from_account(info.raw)
    return {
        "equity": info.equity,
        "buying_power": info.buying_power,
        "cash": info.cash,
        "daily_pnl": info.daily_pnl,
        "account_type": info.account_type,
        "broker": info.broker,
    }


# ── Positions ──────────────────────────────────────────────────

@app.get("/positions")
async def positions():
    """List all open positions with current price and unrealised P&L."""
    broker = await _get_broker()
    pos_list = await broker.get_positions()
    return [
        {
            "symbol": p.symbol,
            "qty": p.qty,
            "side": p.side,
            "entry_price": p.entry_price,
            "current_price": p.current_price,
            "market_value": p.market_value,
            "unrealised_pnl": p.unrealised_pnl,
        }
        for p in pos_list
    ]


# ── Orders ─────────────────────────────────────────────────────

@app.get("/orders")
async def orders(status: Optional[str] = None, limit: Optional[int] = 20):
    """Fetch recent orders. Optionally filter by status (open, closed, all)."""
    broker = await _get_broker()
    return await broker.get_orders(status=status, limit=limit)


# ── Clock ──────────────────────────────────────────────────────

@app.get("/clock")
async def clock():
    """Return market clock status: is_open, next_open, next_close."""
    broker = await _get_broker()
    return await broker.get_clock()



# ── Chat ───────────────────────────────────────────────────────

@app.post("/chat", response_model=ChatResponse)
@limiter.limit("10/minute")
async def chat(request: Request, req: ChatRequest = Body(...)):
    """Process a natural-language message.

    Delegates to the LLM wrapper (app.llm) when available.
    Falls back to echo mode until the LLM is wired up.
    """
    try:
        from app.llm import process_chat_message
        reply, actions = await process_chat_message(
            req.message, req.context or [], await _get_broker(),
        )
        # Extract intent from actions if present
        intent = None
        for a in actions:
            if a.get("action") == "intent_detected":
                intent = a.get("intent")
                break
        return ChatResponse(reply=reply, actions=actions, intent=intent)
    except (ImportError, AttributeError):
        # LLM wrapper not yet implemented — echo back
        return ChatResponse(
            reply=f"[echo] {req.message}  (LLM not connected yet)",
            actions=[],
        )
    except Exception as exc:
        logger.error("Chat endpoint error: %s", exc, exc_info=True)
        return ChatResponse(
            reply=f"⚠️ Server error: {exc}",
            actions=[],
        )


# ── Screener ───────────────────────────────────────────────────

@app.post("/screen")
@limiter.limit("5/minute")
async def screen(request: Request, req: ScreenRequest = Body(...)):
    """Run mass market screener and optionally analyze results."""
    from app.strategy.screener import screen_market, batch_analyze

    tickers = screen_market(
        filters=req.filters, preset=req.preset, limit=req.limit,
    )
    if not tickers:
        return {"tickers": [], "signals": []}

    if req.analyze:
        broker = await _get_broker()
        signals = await batch_analyze(broker, tickers, timeframe=req.timeframe)
        return {
            "tickers": tickers,
            "signals": [s.to_dict() for s in signals],
        }
    return {"tickers": tickers, "signals": []}


# ── Kill switch ────────────────────────────────────────────────

@app.get("/kill-switch")
async def kill_switch_status():
    """Check current kill switch state (active/inactive, reason, timestamp)."""
    return get_kill_switch_info()


@app.post("/kill-switch")
@limiter.limit("5/minute")
async def trigger_kill_switch(request: Request, req: KillSwitchRequest = Body(...)):
    """Trigger emergency stop: cancel all orders, close all positions, block new trades."""
    broker = await _get_broker()
    summary = await emergency_stop(broker, reason=req.reason)
    return summary


# ── Autonomous trading ────────────────────────────────────────


class AutonomousStartRequest(BaseModel):
    """Optional overrides when starting autonomous mode."""
    symbols: Optional[List[str]] = None
    strategy: Optional[str] = None
    scan_interval_seconds: Optional[float] = None


@app.get("/autonomous/status")
async def autonomous_status():
    """Get current autonomous trading status."""
    from app.agents.autonomous_trader import AutonomousTrader
    trader = AutonomousTrader.get_instance()
    return trader.status()


@app.post("/autonomous/start")
@limiter.limit("3/minute")
async def autonomous_start(request: Request, req: AutonomousStartRequest = Body(AutonomousStartRequest())):
    """Start autonomous trading. Requires AUTONOMOUS_MODE_ENABLED=true in .env."""
    from app.agents.autonomous_trader import AutonomousTrader
    from app.settings import get_autonomous_settings

    # Apply optional overrides
    if req.symbols or req.strategy or req.scan_interval_seconds:
        auto_cfg = get_autonomous_settings()
        if req.symbols:
            auto_cfg.symbols = req.symbols
        if req.strategy:
            auto_cfg.strategy = req.strategy
        if req.scan_interval_seconds:
            auto_cfg.scan_interval_seconds = req.scan_interval_seconds

    broker = await _get_broker()
    trader = AutonomousTrader.get_instance()
    trader_result = await trader.start(broker)
    if "error" in trader_result:
        raise HTTPException(status_code=400, detail=trader_result["error"])
    return trader_result


@app.post("/autonomous/stop")
@limiter.limit("5/minute")
async def autonomous_stop(request: Request):
    """Stop autonomous trading."""
    from app.agents.autonomous_trader import AutonomousTrader
    trader = AutonomousTrader.get_instance()
    result = await trader.stop()
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


# ── WebSocket (real-time events) ───────────────────────────────

_ws_clients: List[WebSocket] = []


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    """Real-time WebSocket stream. Send 'ping' for pong, 'account' for snapshot."""
    await ws.accept()
    _ws_clients.append(ws)
    try:
        while True:
            data = await ws.receive_text()
            # Heartbeat or command handling
            if data == "ping":
                await ws.send_json({"type": "pong"})
            elif data == "account":
                broker = await _get_broker()
                info = await broker.get_account()
                await ws.send_json({
                    "type": "account",
                    "equity": info.equity,
                    "daily_pnl": info.daily_pnl,
                    "buying_power": info.buying_power,
                })
    except WebSocketDisconnect:
        _ws_clients.remove(ws)


async def broadcast(event: Dict[str, Any]) -> None:
    """Broadcast an event to all connected WebSocket clients."""
    for ws in list(_ws_clients):
        try:
            await ws.send_json(event)
        except Exception:
            _ws_clients.remove(ws)

