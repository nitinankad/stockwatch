from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel


class FeatureVector(BaseModel):
    id: int | None = None
    ticker: str
    snapshot_timestamp: datetime
    prediction_horizon: str  # '1h', '4h', '1d', etc.
    features: dict[str, Any]
    actual_pct_change: Decimal | None = None
    predicted_at: datetime | None = None
    created_at: datetime | None = None
