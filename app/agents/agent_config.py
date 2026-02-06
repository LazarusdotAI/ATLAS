"""
AgentConfig — per-agent configuration dataclass.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class AgentConfig:
    """Configuration for a single trading agent."""

    # Strategy identifier (must match a registered strategy name)
    strategy_name: str = "technical"

    # Symbols this agent watches
    symbols: List[str] = field(default_factory=lambda: ["SPY"])

    # Risk budget — optional per-agent soft limit (dollars)
    risk_budget: float = 30.0

    # Max $ risk per single trade
    max_risk_per_trade: float = 50.0

    # How often the agent ticks (seconds)
    scan_interval_seconds: float = 60.0

    # Strategy-specific parameter overrides
    params: Dict[str, Any] = field(default_factory=dict)

    # Whether this agent is enabled at creation
    enabled: bool = True

    # Optional human-readable description
    description: str = ""

    # Minimum confidence threshold to act on a signal
    min_confidence: float = 0.6

    # Max concurrent positions this agent can hold
    max_positions: int = 3

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to dict."""
        return {
            "strategy_name": self.strategy_name,
            "symbols": self.symbols,
            "risk_budget": self.risk_budget,
            "max_risk_per_trade": self.max_risk_per_trade,
            "scan_interval_seconds": self.scan_interval_seconds,
            "params": self.params,
            "enabled": self.enabled,
            "description": self.description,
            "min_confidence": self.min_confidence,
            "max_positions": self.max_positions,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentConfig":
        """Create from dict (API payloads)."""
        return cls(
            strategy_name=data.get("strategy_name", "technical"),
            symbols=data.get("symbols", ["SPY"]),
            risk_budget=float(data.get("risk_budget", 30.0)),
            max_risk_per_trade=float(data.get("max_risk_per_trade", 50.0)),
            scan_interval_seconds=float(data.get("scan_interval_seconds", 60.0)),
            params=data.get("params", {}),
            enabled=data.get("enabled", True),
            description=data.get("description", ""),
            min_confidence=float(data.get("min_confidence", 0.6)),
            max_positions=int(data.get("max_positions", 3)),
        )

