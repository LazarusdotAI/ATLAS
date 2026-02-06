"""
MCP Client — manages a session to the Alpaca MCP server.

Responsibilities:
  • Start / stop the MCP server process (stdio transport).
  • Discover available tools.
  • Invoke tools by name with JSON arguments.
  • Return structured results to callers.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import shlex
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Dict, List, Optional

from mcp import ClientSession, types
from mcp.client.stdio import StdioServerParameters, stdio_client

from app.settings import get_alpaca_settings

logger = logging.getLogger(__name__)


# Default allowlist — only include safe, read-and-trade tools.
# Exclude account-management, funding, and destructive operations.
DEFAULT_TOOL_ALLOWLIST: set[str] = {
    # Read-only / informational
    "get_account_info",
    "get_positions",
    "get_position",
    "get_orders",
    "get_order",
    "get_clock",
    "get_calendar",
    "get_assets",
    "get_asset",
    "get_bars",
    "get_latest_bar",
    "get_latest_trade",
    "get_latest_quote",
    "get_snapshot",
    "get_trades",
    "get_quotes",
    # Trading
    "place_order",
    "cancel_order",
    "cancel_all_orders",
    "close_position",
    "close_all_positions",
}


class AlpacaMCPClient:
    """Async wrapper around an MCP session to the Alpaca MCP server."""

    def __init__(self, tool_allowlist: Optional[set[str]] = None) -> None:
        self._session: Optional[ClientSession] = None
        self._tools: List[types.Tool] = []
        self._tool_names: set[str] = set()
        self._allowlist: set[str] = tool_allowlist if tool_allowlist is not None else DEFAULT_TOOL_ALLOWLIST

    # ── Connection lifecycle ──────────────────────────────────

    @asynccontextmanager
    async def connect(self) -> AsyncGenerator["AlpacaMCPClient", None]:
        """Context manager that starts the MCP server and yields a ready client."""
        cfg = get_alpaca_settings()

        # Build env with Alpaca keys
        env = {
            **os.environ,
            "ALPACA_API_KEY": cfg.api_key,
            "ALPACA_SECRET_KEY": cfg.secret_key,
        }

        # Parse the server command
        parts = shlex.split(cfg.mcp_server_cmd)
        command = parts[0]
        args = parts[1:] + ["serve"]

        server_params = StdioServerParameters(
            command=command,
            args=args,
            env=env,
        )

        logger.info("Starting Alpaca MCP server: %s %s", command, " ".join(args))

        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                self._session = session

                # Discover tools
                tool_result = await session.list_tools()
                self._tools = tool_result.tools
                self._tool_names = {t.name for t in self._tools}
                logger.info(
                    "Connected. %d tools available: %s",
                    len(self._tools),
                    sorted(self._tool_names),
                )

                yield self

        self._session = None
        self._tools = []
        self._tool_names = set()
        logger.info("MCP session closed.")

    # ── Tool discovery ────────────────────────────────────────

    @property
    def tools(self) -> List[types.Tool]:
        return list(self._tools)

    @property
    def tool_names(self) -> set[str]:
        return set(self._tool_names)

    def has_tool(self, name: str) -> bool:
        return name in self._tool_names

    # ── Tool invocation ───────────────────────────────────────

    async def call_tool(
        self, name: str, arguments: Optional[Dict[str, Any]] = None
    ) -> Any:
        """Call an MCP tool by name and return parsed result.

        Raises ValueError if the tool is not in the allowlist or not available.
        """
        if self._session is None:
            raise RuntimeError("Not connected. Use `async with client.connect():`")
        if self._allowlist and name not in self._allowlist:
            raise ValueError(
                f"Tool '{name}' is not in the allowlist. "
                f"Allowed: {sorted(self._allowlist)}"
            )
        if name not in self._tool_names:
            raise ValueError(
                f"Tool '{name}' not found. Available: {sorted(self._tool_names)}"
            )

        logger.debug("Calling tool %s(%s)", name, arguments or {})
        result = await self._session.call_tool(name, arguments or {})

        # Extract text content from result
        texts: list[str] = []
        for content in result.content:
            if isinstance(content, types.TextContent):
                texts.append(content.text)

        combined = "\n".join(texts)

        # Try to parse as JSON
        try:
            return json.loads(combined)
        except (json.JSONDecodeError, ValueError):
            return combined

    # ── Convenience: raw session access ───────────────────────

    @property
    def session(self) -> ClientSession:
        if self._session is None:
            raise RuntimeError("Not connected.")
        return self._session

