from __future__ import annotations

import json
import logging

from openai import AsyncOpenAI

from shared.models.llm_analysis import LLMAnalysis
from shared.models.news import RawNewsItem

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are a financial news analyst. Given a news headline, extract:
1. Stock tickers mentioned or strongly implied (NYSE/NASDAQ only, high confidence only)
2. Overall market sentiment toward those stocks

Return JSON only — no markdown, no other text.

Example:
{"tickers": ["AAPL", "MSFT"], "sentiment": "bullish"}

Sentiment must be exactly "bullish", "bearish", or "neutral".
Return [] for tickers if none are identifiable with confidence."""


class LLMAnalyzer:
    def __init__(self, api_key: str, base_url: str, model: str) -> None:
        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self._model = model

    async def analyze(self, item: RawNewsItem, blob_key: str) -> LLMAnalysis | None:
        """
        Returns None if the article has no analyzable content (caller should ack + discard).
        Raises on transient errors (caller should nack + requeue).
        """
        if not item.title:
            logger.info("llm_analyzer.analyze.skip key=%s reason=no_title", blob_key)
            return None

        prompt = f"Headline: {item.title}\nSource: {item.source}"
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0,
            max_tokens=128,
            response_format={"type": "json_object"},
        )
        data = json.loads(response.choices[0].message.content or "{}")

        tickers = [t.upper().strip() for t in data.get("tickers", []) if t]
        sentiment = data.get("sentiment", "neutral").lower()
        if sentiment not in ("bullish", "bearish", "neutral"):
            sentiment = "neutral"

        return LLMAnalysis(
            tickers=tickers,
            sentiment=sentiment,
            raw_object_key=blob_key,
            event_timestamp=item.published_at,
        )
