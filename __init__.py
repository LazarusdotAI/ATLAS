"""
Multi-Agent Trading Framework for StockBotFree.

Exports:
    BaseStrategy      — ABC that all strategies implement
    AgentConfig       — Per-agent configuration
    AgentState        — Per-agent P&L, trades, metrics
    TradingAgent      — Autonomous trading agent with lifecycle
    AgentRegistry     — Singleton manager for all agents
    AgentStatus       — Agent lifecycle states
"""

from app.agents.base_strategy import BaseStrategy
from app.agents.agent_config import AgentConfig
from app.agents.agent_state import AgentState
from app.agents.agent import TradingAgent, AgentStatus
from app.agents.registry import AgentRegistry

__all__ = [
    "BaseStrategy",
    "AgentConfig",
    "AgentState",
    "TradingAgent",
    "AgentStatus",
    "AgentRegistry",
]

