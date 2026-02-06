"""
Centralised configuration loaded from environment / .env file.
Uses pydantic-settings for validation and type coercion.
"""

from __future__ import annotations

from pathlib import Path
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


class AlpacaSettings(BaseSettings):
    """Alpaca broker connection."""

    model_config = SettingsConfigDict(env_file=_ENV_FILE, extra="ignore")

    api_key: str = Field("", alias="ALPACA_API_KEY")
    secret_key: str = Field("", alias="ALPACA_SECRET_KEY")
    base_url: str = Field(
        "https://paper-api.alpaca.markets", alias="ALPACA_BASE_URL"
    )
    data_url: str = Field(
        "https://data.alpaca.markets", alias="ALPACA_DATA_URL"
    )
    mcp_server_cmd: str = Field(
        "uvx alpaca-mcp-server", alias="ALPACA_MCP_SERVER_CMD"
    )
    mcp_transport: str = Field("stdio", alias="ALPACA_MCP_TRANSPORT")


class LLMSettings(BaseSettings):
    """LLM provider configuration."""

    model_config = SettingsConfigDict(env_file=_ENV_FILE, extra="ignore")

    provider: str = Field("openai", alias="LLM_PROVIDER")
    model: str = Field("gpt-4o", alias="LLM_MODEL")
    api_key: str = Field("", alias="LLM_API_KEY")
    base_url: str = Field(
        "http://localhost:11434", alias="LLM_BASE_URL"
    )


class RiskSettings(BaseSettings):
    """Hard risk limits — enforced globally."""

    model_config = SettingsConfigDict(env_file=_ENV_FILE, extra="ignore")

    daily_loss_limit: float = Field(-100.0, alias="DAILY_LOSS_LIMIT")
    max_position_size_pct: float = Field(5.0, alias="MAX_POSITION_SIZE_PCT")
    max_open_orders: int = Field(10, alias="MAX_OPEN_ORDERS")
    symbol_allowlist: List[str] = Field(
        default_factory=lambda: [
            "AAPL", "MSFT", "TSLA", "SPY", "QQQ",
            "NVDA", "AMD", "AMZN", "GOOG", "META",
        ],
        alias="SYMBOL_ALLOWLIST",
    )


class SecuritySettings(BaseSettings):
    """API security configuration."""

    model_config = SettingsConfigDict(env_file=_ENV_FILE, extra="ignore")

    api_key: str = Field("", alias="API_KEY")
    api_key_header: str = Field("X-API-Key", alias="API_KEY_HEADER")
    auth_enabled: bool = Field(True, alias="AUTH_ENABLED")


class AutonomousSettings(BaseSettings):
    """Autonomous trading mode configuration."""

    model_config = SettingsConfigDict(env_file=_ENV_FILE, extra="ignore")

    enabled: bool = Field(False, alias="AUTONOMOUS_MODE_ENABLED")
    confirm: str = Field("", alias="AUTONOMOUS_MODE_CONFIRM")
    scan_interval_seconds: float = Field(300.0, alias="AUTONOMOUS_SCAN_INTERVAL_SECONDS")
    max_positions: int = Field(3, alias="AUTONOMOUS_MAX_POSITIONS")
    risk_budget: float = Field(-50.0, alias="AUTONOMOUS_RISK_BUDGET")
    symbols: List[str] = Field(
        default_factory=lambda: ["SPY", "QQQ"],
        alias="AUTONOMOUS_SYMBOLS",
    )
    strategy: str = Field("technical", alias="AUTONOMOUS_STRATEGY")
    min_confidence: float = Field(0.65, alias="AUTONOMOUS_MIN_CONFIDENCE")


class AppSettings(BaseSettings):
    """Top-level app settings."""

    model_config = SettingsConfigDict(env_file=_ENV_FILE, extra="ignore")

    log_level: str = Field("INFO", alias="LOG_LEVEL")
    audit_log_path: str = Field("logs/audit.jsonl", alias="AUDIT_LOG_PATH")
    trading_mode: str = Field("paper", alias="TRADING_MODE")  # "paper" or "live"
    market_hours_only: bool = Field(False, alias="MARKET_HOURS_ONLY")
    live_mode_confirm: str = Field("", alias="LIVE_MODE_CONFIRM")  # Must be "I_UNDERSTAND_LIVE_TRADING" to enable live


# ── Singleton accessors ──────────────────────────────────────
_alpaca: AlpacaSettings | None = None
_llm: LLMSettings | None = None
_risk: RiskSettings | None = None
_app: AppSettings | None = None
_security: SecuritySettings | None = None
_autonomous: AutonomousSettings | None = None


def get_alpaca_settings() -> AlpacaSettings:
    global _alpaca
    if _alpaca is None:
        _alpaca = AlpacaSettings()
    return _alpaca


def get_llm_settings() -> LLMSettings:
    global _llm
    if _llm is None:
        _llm = LLMSettings()
    return _llm


def get_risk_settings() -> RiskSettings:
    global _risk
    if _risk is None:
        _risk = RiskSettings()
    return _risk


def get_app_settings() -> AppSettings:
    global _app
    if _app is None:
        _app = AppSettings()
    return _app


def get_security_settings() -> SecuritySettings:
    global _security
    if _security is None:
        _security = SecuritySettings()
    return _security



def validate_trading_mode() -> None:
    """Safety gate: refuse to start in live mode without explicit confirmation.

    Set ``TRADING_MODE=live`` **and** ``LIVE_MODE_CONFIRM=I_UNDERSTAND_LIVE_TRADING``
    to trade with real money.  If the confirm flag is missing, the app falls
    back to paper mode and logs a warning.
    """
    app = get_app_settings()
    if app.trading_mode.lower() == "live":
        if app.live_mode_confirm != "I_UNDERSTAND_LIVE_TRADING":
            import logging
            logging.getLogger(__name__).warning(
                "TRADING_MODE=live but LIVE_MODE_CONFIRM is missing/wrong. "
                "Falling back to PAPER mode for safety."
            )
            app.trading_mode = "paper"


def is_paper_mode() -> bool:
    """Return True if the app is in paper-trading mode."""
    return get_app_settings().trading_mode.lower() != "live"


def get_autonomous_settings() -> AutonomousSettings:
    global _autonomous
    if _autonomous is None:
        _autonomous = AutonomousSettings()
    return _autonomous


def validate_autonomous_mode() -> bool:
    """Safety gate: refuse to enable autonomous mode without explicit confirmation.

    Set ``AUTONOMOUS_MODE_ENABLED=true`` **and**
    ``AUTONOMOUS_MODE_CONFIRM=I_UNDERSTAND_AUTONOMOUS_TRADING`` to enable.
    Returns True if autonomous mode is properly enabled, False otherwise.
    """
    auto = get_autonomous_settings()
    if auto.enabled:
        if auto.confirm != "I_UNDERSTAND_AUTONOMOUS_TRADING":
            import logging
            logging.getLogger(__name__).warning(
                "AUTONOMOUS_MODE_ENABLED=true but AUTONOMOUS_MODE_CONFIRM is "
                "missing/wrong. Autonomous mode DISABLED for safety."
            )
            auto.enabled = False
            return False
        return True
    return False


def is_autonomous_enabled() -> bool:
    """Return True if autonomous trading is properly enabled."""
    auto = get_autonomous_settings()
    return auto.enabled and auto.confirm == "I_UNDERSTAND_AUTONOMOUS_TRADING"
