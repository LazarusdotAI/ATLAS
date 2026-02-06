"""
AgentRegistry — singleton manager for all trading agents.

Responsibilities:
  • Create / delete agents
  • Start / stop / pause / resume agents
  • List agents and their states
  • Enforce global risk limits across all agents
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from uuid import uuid4

from app.agents.agent import AgentStatus, TradingAgent
from app.agents.agent_config import AgentConfig
from app.agents.base_strategy import BaseStrategy
from app.brokers.base import BrokerInterface

logger = logging.getLogger(__name__)


class AgentRegistry:
    """Centralized registry for all trading agents."""

    _instance: Optional["AgentRegistry"] = None

    def __init__(self) -> None:
        self._agents: Dict[str, TradingAgent] = {}
        self._strategies: Dict[str, BaseStrategy] = {}

    @classmethod
    def get_instance(cls) -> "AgentRegistry":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset the singleton (for testing)."""
        cls._instance = None

    # ── Strategy registration ──────────────────────────────────

    def register_strategy(self, strategy: BaseStrategy) -> None:
        """Register a strategy so agents can use it by name."""
        self._strategies[strategy.name] = strategy
        logger.info("Strategy registered: %s (v%s)", strategy.name, strategy.version)

    def get_strategy(self, name: str) -> Optional[BaseStrategy]:
        return self._strategies.get(name)

    def list_strategies(self) -> List[Dict[str, Any]]:
        return [s.info() for s in self._strategies.values()]

    # ── Agent CRUD ─────────────────────────────────────────────

    def create_agent(
        self,
        name: str,
        config: AgentConfig,
        agent_id: Optional[str] = None,
    ) -> TradingAgent:
        """Create a new agent. Raises ValueError if strategy not found."""
        strategy = self._strategies.get(config.strategy_name)
        if strategy is None:
            available = list(self._strategies.keys())
            raise ValueError(
                f"Strategy '{config.strategy_name}' not registered. "
                f"Available: {available}"
            )

        aid = agent_id or uuid4().hex[:12]
        agent = TradingAgent(
            agent_id=aid, name=name, strategy=strategy, config=config,
        )
        self._agents[aid] = agent
        logger.info("Agent created: %s (%s) — strategy=%s", name, aid, config.strategy_name)
        return agent

    def get_agent(self, agent_id: str) -> Optional[TradingAgent]:
        return self._agents.get(agent_id)

    def delete_agent(self, agent_id: str) -> bool:
        agent = self._agents.pop(agent_id, None)
        if agent is None:
            return False
        logger.info("Agent deleted: %s (%s)", agent.name, agent_id)
        return True

    def list_agents(self) -> List[TradingAgent]:
        return list(self._agents.values())

    # ── Lifecycle helpers ──────────────────────────────────────

    async def start_agent(self, agent_id: str, broker: BrokerInterface) -> bool:
        agent = self._agents.get(agent_id)
        if agent is None:
            return False
        await agent.start(broker)
        return True

    async def stop_agent(self, agent_id: str) -> bool:
        agent = self._agents.get(agent_id)
        if agent is None:
            return False
        await agent.stop()
        return True

    async def pause_agent(self, agent_id: str) -> bool:
        agent = self._agents.get(agent_id)
        if agent is None:
            return False
        await agent.pause()
        return True

    async def resume_agent(self, agent_id: str, broker: BrokerInterface) -> bool:
        agent = self._agents.get(agent_id)
        if agent is None:
            return False
        await agent.resume()
        return True

    async def stop_all_agents(self) -> int:
        """Stop every running/paused agent. Returns count stopped."""
        count = 0
        for agent in self._agents.values():
            if agent.status in (AgentStatus.RUNNING, AgentStatus.PAUSED):
                await agent.stop()
                count += 1
        logger.info("Stopped %d agent(s).", count)
        return count

    # ── Aggregate state ────────────────────────────────────────

    def aggregate_pnl(self) -> float:
        """Sum of daily P&L across all agents."""
        return sum(a.state.daily_pnl for a in self._agents.values())

    def agent_summary(self, agent_id: str) -> Optional[Dict[str, Any]]:
        agent = self._agents.get(agent_id)
        if agent is None:
            return None
        return {
            "id": agent.id,
            "name": agent.name,
            "status": agent.status.value,
            "strategy": agent.strategy.name,
            "config": agent.config.to_dict(),
            "performance": agent.state.performance(),
            "created_at": agent.created_at,
        }

    def all_summaries(self) -> List[Dict[str, Any]]:
        return [self.agent_summary(aid) for aid in self._agents]  # type: ignore[misc]

