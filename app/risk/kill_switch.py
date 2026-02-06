"""Kill switch — emergency halt mechanism.

When triggered:
  1. Cancel all open orders
  2. Close all open positions at market
  3. Block all new trades until manually reset
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

from app.brokers.base import BrokerInterface
from app.storage.audit_log import log_event

logger = logging.getLogger(__name__)

# ── Module-level state ────────────────────────────────────────
_kill_switch_active: bool = False
_kill_switch_reason: str = ""
_kill_switch_timestamp: str = ""


def is_kill_switch_active() -> bool:
    """Return True if the kill switch is currently engaged."""
    return _kill_switch_active


def get_kill_switch_info() -> Dict[str, Any]:
    """Return current kill switch state."""
    return {
        "active": _kill_switch_active,
        "reason": _kill_switch_reason,
        "timestamp": _kill_switch_timestamp,
    }


def reset_kill_switch() -> None:
    """Reset the kill switch to allow trading again."""
    global _kill_switch_active, _kill_switch_reason, _kill_switch_timestamp
    _kill_switch_active = False
    _kill_switch_reason = ""
    _kill_switch_timestamp = ""
    logger.info("Kill switch reset.")


async def emergency_stop(broker: BrokerInterface, reason: str = "Manual trigger") -> Dict[str, Any]:
    """Trigger emergency stop: cancel all orders, close all positions.

    Returns a summary dict with results of the operation.
    """
    global _kill_switch_active, _kill_switch_reason, _kill_switch_timestamp

    _kill_switch_active = True
    _kill_switch_reason = reason
    _kill_switch_timestamp = datetime.now(timezone.utc).isoformat()

    summary: Dict[str, Any] = {
        "reason": reason,
        "timestamp": _kill_switch_timestamp,
        "orders_cancelled": False,
        "positions_closed": [],
        "errors": [],
    }

    # 1. Cancel all open orders
    try:
        await broker.cancel_all_orders()
        summary["orders_cancelled"] = True
    except Exception as exc:
        error_msg = f"Cancel all orders failed: {exc}"
        summary["errors"].append(error_msg)
        logger.error(error_msg)

    # 2. Close all positions
    try:
        positions = await broker.get_positions()
        for pos in positions:
            try:
                await broker.close_position(pos.symbol, qty=pos.qty)
                summary["positions_closed"].append({
                    "symbol": pos.symbol,
                    "qty": pos.qty,
                    "side": pos.side,
                })
            except Exception as exc:
                error_msg = f"Close position {pos.symbol} failed: {exc}"
                summary["errors"].append(error_msg)
                logger.error(error_msg)
    except Exception as exc:
        error_msg = f"Get positions failed: {exc}"
        summary["errors"].append(error_msg)
        logger.error(error_msg)

    # 3. Audit log
    log_event("kill_switch", {
        "reason": reason,
        "orders_cancelled": summary["orders_cancelled"],
        "positions_closed_count": len(summary["positions_closed"]),
        "error_count": len(summary["errors"]),
    }, level="critical")

    logger.critical("KILL SWITCH ACTIVATED: %s", reason)
    return summary
