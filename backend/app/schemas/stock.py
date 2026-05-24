from pydantic import BaseModel, Field


class StockResponse(BaseModel):
    ticker: str = Field(examples=["NVDA"])
    company: str = Field(examples=["NVIDIA Corporation"])
    industry: str = Field(examples=["Semiconductors"])
    market_cap: int | None = Field(default=None, examples=[2_180_000_000_000])


class StockListResponse(BaseModel):
    count: int
    results: list[StockResponse]
