from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class StockResponse(BaseModel):
    ticker: str = Field(examples=["NVDA"])
    company: str = Field(examples=["NVIDIA Corporation"])
    industry: str = Field(examples=["Semiconductors"])
    market_cap: int | None = Field(default=None, examples=[2_180_000_000_000])


class StockListResponse(BaseModel):
    count: int
    results: list[StockResponse]


class HorizonPrediction(BaseModel):
    horizon: str = Field(examples=["1h"])
    predicted_pct_change: Decimal
    direction: str = Field(examples=["bullish"])
    actual_pct_change: Decimal | None = None
    error: Decimal | None = None
    predicted_at: datetime
    resolved_at: datetime | None = None
    snapshot_timestamp: datetime


class PredictionsResponse(BaseModel):
    ticker: str
    predictions: list[HorizonPrediction]


class SignalHorizon(BaseModel):
    horizon: str = Field(examples=["1h"])
    probability: float = Field(description="P(stock outperforms SPY)", examples=[0.62])
    direction: str = Field(examples=["bullish"])
    conviction: float = Field(description="|probability - 0.5|", examples=[0.12])


class SignalResponse(BaseModel):
    ticker: str
    computed_at: datetime
    bar_count: int
    signals: list[SignalHorizon]
