"""Alpaca tool types — shared data models for order payloads."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class OrderPayload:
    """Payload for an Alpaca order."""

    symbol: str = ""
    side: str = "buy"
    qty: Optional[float] = None
    order_type: str = "market"
    time_in_force: str = "day"
    limit_price: Optional[float] = None
    notional: Optional[float] = None
