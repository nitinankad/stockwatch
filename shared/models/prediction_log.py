from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class PredictionLog(BaseModel):
    id: int | None = None
    feature_vector_id: int
    ticker: str
    model_version: str
    predicted_pct_change: Decimal
    derived_direction: str  # 'bullish' | 'bearish'
    actual_pct_change: Decimal | None = None
    error: Decimal | None = None  # predicted minus actual
    predicted_at: datetime | None = None
    resolved_at: datetime | None = None
