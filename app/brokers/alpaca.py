"""Alpaca broker implementation using the MCP client."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.brokers.base import (
    AccountInfo,
    BrokerInterface,
    OrderRequest,
    OrderResult,
    Position,
)
from app.mcp_client import AlpacaMCPClient

logger = logging.getLogger(__name__)


class AlpacaBroker(BrokerInterface):
    """Alpaca broker via MCP server."""

    def __init__(self) -> None:
        self._client = AlpacaMCPClient()
        self._ctx: Any = None

    async def connect(self) -> None:
        self._ctx = self._client.connect()
        await self._ctx.__aenter__()
        logger.info("AlpacaBroker connected via MCP.")

    async def disconnect(self) -> None:
        if self._ctx:
            await self._ctx.__aexit__(None, None, None)
            self._ctx = None
        logger.info("AlpacaBroker disconnected.")

    async def get_account(self) -> AccountInfo:
        data = await self._client.call_tool("get_account_info")
        if isinstance(data, dict):
            return AccountInfo(
                equity=float(data.get("equity", 0)),
                buying_power=float(data.get("buying_power", 0)),
                cash=float(data.get("cash", 0)),
                daily_pnl=float(data.get("equity", 0)) - float(data.get("last_equity", data.get("equity", 0))),
                account_type=data.get("account_type", "paper"),
                broker="alpaca",
                raw=data,
            )
        return AccountInfo(broker="alpaca")

    async def get_positions(self) -> List[Position]:
        data = await self._client.call_tool("get_positions")
        if not isinstance(data, list):
            return []
        return [
            Position(
                symbol=p.get("symbol", ""),
                qty=float(p.get("qty", 0)),
                side=p.get("side", "long"),
                entry_price=float(p.get("avg_entry_price", 0)),
                current_price=float(p.get("current_price", 0)),
                market_value=float(p.get("market_value", 0)),
                unrealised_pnl=float(p.get("unrealized_pl", 0)),
            )
            for p in data
        ]

    async def get_orders(self, status: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
        args: Dict[str, Any] = {"limit": limit}
        if status:
            args["status"] = status
        data = await self._client.call_tool("get_orders", args)
        return data if isinstance(data, list) else []

    async def get_clock(self) -> Dict[str, Any]:
        data = await self._client.call_tool("get_clock")
        return data if isinstance(data, dict) else {}

    async def get_quote(self, symbol: str) -> Dict[str, Any]:
        data = await self._client.call_tool("get_latest_quote", {"symbol": symbol})
        return data if isinstance(data, dict) else {}

    async def place_order(self, order: OrderRequest) -> OrderResult:
        args: Dict[str, Any] = {
            "symbol": order.symbol,
            "side": order.side,
            "qty": str(order.qty),
            "type": order.order_type,
            "time_in_force": order.time_in_force,
        }
        if order.limit_price is not None:
            args["limit_price"] = str(order.limit_price)
        if order.client_order_id:
            args["client_order_id"] = order.client_order_id
        if order.notional is not None:
            args["notional"] = str(order.notional)

        data = await self._client.call_tool("place_order", args)
        if isinstance(data, dict):
            return OrderResult(
                order_id=data.get("id", ""),
                symbol=data.get("symbol", order.symbol),
                side=data.get("side", order.side),
                qty=float(data.get("qty", order.qty)),
                filled_qty=float(data.get("filled_qty", 0)),
                avg_fill_price=float(data.get("filled_avg_price", 0)) if data.get("filled_avg_price") else None,
                status=data.get("status", ""),
            )
        return OrderResult(order_id="", status="unknown")

    async def close_position(self, symbol: str, qty: Optional[float] = None) -> OrderResult:
        args: Dict[str, Any] = {"symbol": symbol}
        if qty is not None:
            args["qty"] = str(qty)
        data = await self._client.call_tool("close_position", args)
        if isinstance(data, dict):
            return OrderResult(
                order_id=data.get("id", ""),
                symbol=symbol,
                status=data.get("status", "closed"),
                avg_fill_price=float(data.get("filled_avg_price", 0)) if data.get("filled_avg_price") else None,
            )
        return OrderResult(symbol=symbol, status="closed")

    async def cancel_all_orders(self) -> None:
        await self._client.call_tool("cancel_all_orders")

    async def close_all_positions(self) -> None:
        await self._client.call_tool("close_all_positions")
