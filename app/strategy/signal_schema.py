"""Signal schema — unified Pydantic model for all trading signals.

Every strategy module produces Signal objects conforming to this schema.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator


class Signal(BaseModel):
    """A single trading signal produced by any strategy module."""

    symbol: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    direction: Literal["long", "short", "neutral"]
    confidence: float = Field(ge=0.0, le=1.0)
    stop_level: Optional[float] = None
    target_level: Optional[float] = None
    horizon: Literal["intraday", "next_bar", "next_day"]
    source: str
    rationale: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("symbol", mode="before")
    @classmethod
    def _uppercase_symbol(cls, v: str) -> str:
        return v.strip().upper()

    @field_validator("confidence", mode="after")
    @classmethod
    def _round_confidence(cls, v: float) -> float:
        return round(v, 4)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a plain dict."""
        return self.model_dump()

    def __str__(self) -> str:
        return (
            f"Signal({self.symbol} {self.direction.upper()} "
            f"{self.confidence:.0%} [{self.source}])"
        )
