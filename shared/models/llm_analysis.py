from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class LLMAnalysis(BaseModel):
    id: int | None = None
    tickers: list[str]
    sentiment: str  # 'bullish' | 'bearish' | 'neutral'
    raw_object_key: str
    event_timestamp: datetime | None = None
    created_at: datetime | None = None
