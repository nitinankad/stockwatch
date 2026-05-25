from __future__ import annotations

from datetime import datetime, timedelta, timezone

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _default_start() -> str:
    return (datetime.now(timezone.utc) - timedelta(days=180)).strftime("%Y-%m-%d")


def _default_end() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = ""
    alpaca_api_key: str = ""
    alpaca_api_secret: str = ""

    backfill_symbols: list[str] = []
    backfill_start: str = ""   # YYYY-MM-DD, defaults to 180 days ago
    backfill_end: str = ""     # YYYY-MM-DD, defaults to today

    # Bar timeframe — must match what ingestion wrote ("1Min" or "5Min")
    ohlcv_timeframe: str = "1Min"

    # How often to sample a feature vector from the bar stream (every N bars)
    sample_interval_minutes: int = 15

    prediction_horizons: list[str] = ["1h", "4h", "1d"]

    log_level: str = "INFO"

    @field_validator("backfill_symbols", "prediction_horizons", mode="before")
    @classmethod
    def _split_csv(cls, v):
        if isinstance(v, str):
            return [x.strip() for x in v.split(",") if x.strip()]
        return v

    def start_dt(self) -> datetime:
        s = self.backfill_start or _default_start()
        return datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=timezone.utc)

    def end_dt(self) -> datetime:
        e = self.backfill_end or _default_end()
        return datetime.strptime(e, "%Y-%m-%d").replace(tzinfo=timezone.utc)
