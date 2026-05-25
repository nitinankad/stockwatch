from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class OHLCVBar(BaseModel):
    ticker: str
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    timestamp: datetime
    timeframe: str = "1Min"
