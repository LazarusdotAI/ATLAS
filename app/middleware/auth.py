"""API key authentication middleware."""

from __future__ import annotations

import logging

from fastapi import HTTPException, Request

from app.settings import get_security_settings

logger = logging.getLogger(__name__)


async def require_api_key(request: Request) -> None:
    """FastAPI dependency that validates the API key header.

    Skips authentication if AUTH_ENABLED is false or no API_KEY is set.
    WebSocket and health endpoints are excluded.
    """
    # Skip auth for health checks and WebSocket upgrades
    if request.url.path in ("/health", "/health/detailed", "/ws"):
        return

    cfg = get_security_settings()
    if not cfg.auth_enabled or not cfg.api_key:
        return

    provided = request.headers.get(cfg.api_key_header, "")
    if provided != cfg.api_key:
        logger.warning("Unauthorized API access from %s to %s", request.client.host if request.client else "unknown", request.url.path)
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
