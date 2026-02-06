"""Structured JSONL audit log.

Every significant event (orders, risk violations, LLM prompts, errors)
is appended as a single JSON line to the audit log file.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from app.settings import get_app_settings

logger = logging.getLogger(__name__)


def _get_log_path() -> Path:
    """Return the audit log file path (creating parent dirs if needed)."""
    cfg = get_app_settings()
    path = Path(cfg.audit_log_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _write_event(record: Dict[str, Any]) -> None:
    """Append a single JSON line to the audit log."""
    path = _get_log_path()
    try:
        with path.open("a") as f:
            f.write(json.dumps(record, default=str) + "\n")
    except Exception as exc:
        logger.error("Failed to write audit log: %s", exc)


# ── Core logging function ─────────────────────────────────────


def log_event(event_type: str, data: Dict[str, Any], level: str = "info") -> None:
    """Log a generic event to the audit trail."""
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": event_type,
        "level": level,
        **data,
    }
    _write_event(record)


# ── Convenience helpers ───────────────────────────────────────


def log_order_draft(order: Dict[str, Any]) -> None:
    """Log a proposed order before approval."""
    log_event("order_draft", {"order": order})


def log_order_approved(order: Dict[str, Any], reason: str) -> None:
    """Log an approved order."""
    log_event("order_approved", {"order": order, "reason": reason})


def log_order_rejected(order: Dict[str, Any], reason: str) -> None:
    """Log a rejected order."""
    log_event("order_rejected", {"order": order, "reason": reason}, level="warning")


def log_order_submitted(order: Dict[str, Any], result: Dict[str, Any]) -> None:
    """Log a submitted (executed) order."""
    log_event("order_submitted", {"order": order, "result": result})


def log_risk_violation(violations: list, context: Dict[str, Any]) -> None:
    """Log a risk-check violation."""
    log_event("risk_violation", {"violations": violations, **context}, level="warning")


def log_error(message: str, context: Optional[Dict[str, Any]] = None) -> None:
    """Log an error event."""
    log_event("error", {"message": message, **(context or {})}, level="error")


def log_slippage(
    symbol: str,
    side: str,
    expected_price: float,
    actual_price: float,
    qty: float,
    order_id: Optional[str] = None,
) -> None:
    """Log execution slippage.

    Slippage is always expressed as a positive number for unfavorable fills.
    """
    if side == "buy":
        slippage = actual_price - expected_price
    else:
        slippage = expected_price - actual_price

    total_cost = abs(slippage) * qty
    slippage_pct = abs(slippage) / expected_price * 100 if expected_price > 0 else 0
    level = "warning" if slippage_pct >= 1.0 else "info"

    log_event("slippage", {
        "symbol": symbol,
        "side": side,
        "expected_price": expected_price,
        "actual_price": actual_price,
        "slippage": abs(slippage),
        "slippage_pct": round(slippage_pct, 4),
        "total_slippage_cost": round(total_cost, 2),
        "qty": qty,
        "order_id": order_id,
    }, level=level)


def log_fill_quality(
    order_id: str,
    symbol: str,
    qty_requested: float,
    qty_filled: float,
    status: str,
    latency_ms: Optional[float] = None,
) -> None:
    """Log order fill quality metrics."""
    fill_ratio = qty_filled / qty_requested if qty_requested > 0 else 0
    partial = 0 < qty_filled < qty_requested
    rejected = qty_filled == 0 and status in ("rejected", "cancelled")

    log_event("fill_quality", {
        "order_id": order_id,
        "symbol": symbol,
        "qty_requested": qty_requested,
        "qty_filled": qty_filled,
        "fill_ratio": round(fill_ratio, 4),
        "partial": partial,
        "rejected": rejected,
        "status": status,
        "latency_ms": latency_ms,
    })


def log_prompt(
    user_message: str,
    system_prompt: str,
    llm_response: str,
    provider: str,
    model: str,
) -> None:
    """Log an LLM prompt/response pair for audit trail."""
    log_event("llm_prompt", {
        "user_message": user_message[:500],
        "system_prompt_length": len(system_prompt),
        "llm_response": llm_response[:500],
        "provider": provider,
        "model": model,
    })


def log_tool_call(tool_name: str, arguments: Dict[str, Any], result: Any) -> None:
    """Log an MCP tool invocation."""
    log_event("tool_call", {
        "tool": tool_name,
        "arguments": arguments,
        "result": str(result)[:500],
    })
