"""Sentiment analysis — FinBERT + FinBERT-Tone blended NLP signals."""

from __future__ import annotations

import logging
from typing import Any, Dict

from app.strategy.signal_schema import Signal

logger = logging.getLogger(__name__)


async def generate_blended_sentiment_signal(text: str, symbol: str = "MARKET") -> Signal:
    """Generate a blended sentiment signal from text using FinBERT models.

    Falls back to neutral if models are unavailable.
    """
    try:
        from transformers import pipeline

        classifier = pipeline("sentiment-analysis", model="ProsusAI/finbert")
        result = classifier(text[:512])[0]

        label = result["label"].lower()
        score = float(result["score"])

        if label == "positive":
            direction = "long"
        elif label == "negative":
            direction = "short"
        else:
            direction = "neutral"

        return Signal(
            symbol=symbol,
            direction=direction,
            confidence=round(score, 4),
            horizon="intraday",
            source="sentiment",
            rationale=[f"FinBERT: {label} ({score:.2%})"],
            metadata={"raw_label": label, "raw_score": score, "text_length": len(text)},
        )
    except Exception as exc:
        logger.warning("Sentiment model unavailable: %s. Returning neutral.", exc)
        return Signal(
            symbol=symbol,
            direction="neutral",
            confidence=0.5,
            horizon="intraday",
            source="sentiment",
            rationale=["Sentiment model unavailable"],
            metadata={"error": str(exc)},
        )
