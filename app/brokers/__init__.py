"""Broker abstraction layer.

Provides a unified interface to different brokers. Currently supports
Alpaca via MCP.
"""

from __future__ import annotations

from app.brokers.base import BrokerInterface


async def get_broker() -> BrokerInterface:
    """Create and connect the default broker (Alpaca via MCP)."""
    from app.brokers.alpaca import AlpacaBroker

    broker = AlpacaBroker()
    await broker.connect()
    return broker
