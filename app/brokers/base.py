"""Broker base classes — abstract interface and shared data models.

All broker implementations must subclass BrokerInterface and implement
every abstract method.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class AccountInfo:
    """Snapshot of the trading account."""

    equity: float = 0.0
    buying_power: float = 0.0
    cash: float = 0.0
    daily_pnl: float = 0.0
    account_type: str = "paper"
    broker: str = ""
    raw: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Position:
    """A single open position."""

    symbol: str = ""
    qty: float = 0.0
    side: str = "long"
    entry_price: float = 0.0
    current_price: float = 0.0
    market_value: float = 0.0
    unrealised_pnl: float = 0.0


@dataclass
class OrderRequest:
    """Parameters for placing a new order."""

    symbol: str = ""
    side: str = "buy"
    qty: float = 0.0
    order_type: str = "market"
    limit_price: Optional[float] = None
    client_order_id: Optional[str] = None
    time_in_force: str = "day"
    notional: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "symbol": self.symbol,
            "side": self.side,
            "qty": self.qty,
            "order_type": self.order_type,
            "time_in_force": self.time_in_force,
        }
        if self.limit_price is not None:
            d["limit_price"] = self.limit_price
        if self.client_order_id:
            d["client_order_id"] = self.client_order_id
        if self.notional is not None:
            d["notional"] = self.notional
        return d


@dataclass
class OrderResult:
    """Result returned after placing/closing an order."""

    order_id: str = ""
    symbol: str = ""
    side: str = ""
    qty: float = 0.0
    filled_qty: float = 0.0
    avg_fill_price: Optional[float] = None
    status: str = ""


class BrokerInterface(ABC):
    """Abstract broker interface.

    All broker adapters must implement these methods.
    """

    @abstractmethod
    async def connect(self) -> None:
        ...

    @abstractmethod
    async def disconnect(self) -> None:
        ...

    @abstractmethod
    async def get_account(self) -> AccountInfo:
        ...

    @abstractmethod
    async def get_positions(self) -> List[Position]:
        ...

    @abstractmethod
    async def get_orders(self, status: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
        ...

    @abstractmethod
    async def get_clock(self) -> Dict[str, Any]:
        ...

    @abstractmethod
    async def get_quote(self, symbol: str) -> Dict[str, Any]:
        ...

    @abstractmethod
    async def place_order(self, order: OrderRequest) -> OrderResult:
        ...

    @abstractmethod
    async def close_position(self, symbol: str, qty: Optional[float] = None) -> OrderResult:
        ...

    @abstractmethod
    async def cancel_all_orders(self) -> None:
        ...

    @abstractmethod
    async def close_all_positions(self) -> None:
        ...
