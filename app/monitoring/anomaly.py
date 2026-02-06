"""Anomaly detector — runtime anomaly monitoring.

Monitors for:
  • Slippage > 2%
  • P&L swings > $50 in 60 seconds
  • API error rate > 5 in 60 seconds
"""

from __future__ import annotations

import logging
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class AnomalyDetector:
    """Lightweight anomaly detector for runtime monitoring."""

    anomaly_count: int = 0
    _slippage_events: deque = field(default_factory=lambda: deque(maxlen=100))
    _pnl_events: deque = field(default_factory=lambda: deque(maxlen=100))
    _error_events: deque = field(default_factory=lambda: deque(maxlen=100))

    def record_slippage(self, pct: float) -> bool:
        """Record slippage event. Returns True if anomalous (>2%)."""
        self._slippage_events.append((time.time(), pct))
        if abs(pct) > 2.0:
            self.anomaly_count += 1
            logger.warning("ANOMALY: Slippage %.2f%% exceeds 2%% threshold", pct)
            return True
        return False

    def record_pnl_change(self, delta: float) -> bool:
        """Record P&L change. Returns True if anomalous (>$50 in 60s)."""
        now = time.time()
        self._pnl_events.append((now, delta))
        # Sum recent P&L changes in the last 60 seconds
        recent_sum = sum(d for t, d in self._pnl_events if now - t <= 60)
        if abs(recent_sum) > 50:
            self.anomaly_count += 1
            logger.warning("ANOMALY: P&L swing $%.2f in 60s exceeds $50 threshold", recent_sum)
            return True
        return False

    def record_error(self) -> bool:
        """Record API error. Returns True if anomalous (>5 in 60s)."""
        now = time.time()
        self._error_events.append(now)
        recent = sum(1 for t in self._error_events if now - t <= 60)
        if recent > 5:
            self.anomaly_count += 1
            logger.warning("ANOMALY: %d API errors in 60s exceeds threshold of 5", recent)
            return True
        return False


# ── Singleton ─────────────────────────────────────────────────

_detector: Optional[AnomalyDetector] = None


def get_anomaly_detector() -> AnomalyDetector:
    """Return the global anomaly detector singleton."""
    global _detector
    if _detector is None:
        _detector = AnomalyDetector()
    return _detector
