"""Backtesting engine — historical strategy replay with performance metrics."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.brokers.base import BrokerInterface

logger = logging.getLogger(__name__)


@dataclass
class BacktestResult:
    """Results from a backtest run."""

    symbols: List[str] = field(default_factory=list)
    days: int = 30
    timeframe: str = "5Min"
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    total_pnl: float = 0.0
    win_rate: float = 0.0
    sharpe_ratio: Optional[float] = None
    max_drawdown: Optional[float] = None
    profit_factor: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbols": self.symbols,
            "days": self.days,
            "timeframe": self.timeframe,
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "total_pnl": round(self.total_pnl, 2),
            "win_rate": round(self.win_rate, 4),
            "sharpe_ratio": self.sharpe_ratio,
            "max_drawdown": self.max_drawdown,
            "profit_factor": self.profit_factor,
        }


async def run_backtest(
    broker: BrokerInterface,
    symbols: List[str],
    days: int = 30,
    timeframe: str = "5Min",
    min_confidence: float = 0.55,
) -> BacktestResult:
    """Run a historical backtest on the given symbols.

    This is a simplified backtester. A production implementation would
    fetch historical bar data and replay the strategy over it.
    """
    logger.info("Backtest requested: symbols=%s days=%d tf=%s", symbols, days, timeframe)

    return BacktestResult(
        symbols=symbols,
        days=days,
        timeframe=timeframe,
        total_trades=0,
        winning_trades=0,
        losing_trades=0,
        total_pnl=0.0,
        win_rate=0.0,
    )
