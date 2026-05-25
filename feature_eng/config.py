from __future__ import annotations

from pydantic import field_validator
from pydantic_settings import SettingsConfigDict

from shared.settings import CsvAwareSettings


class Settings(CsvAwareSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = ""
    rabbitmq_url: str = "amqp://guest:guest@localhost/"

    # Queue names
    inbound_queue_name: str = "llm_analyzed"
    outbound_queue_name: str = "feature_ready"

    # Bar timeframe — must match what ingestion writes ("1Min" or "5Min")
    ohlcv_timeframe: str = "1Min"

    # How many minutes of OHLCV history to load for indicators
    ohlcv_lookback_minutes: int = 120

    # Prediction horizons to generate feature vectors for
    prediction_horizons: list[str] = ["1h", "4h", "1d"]

    log_level: str = "INFO"

    @field_validator("prediction_horizons", mode="before")
    @classmethod
    def _split_csv(cls, v):
        if isinstance(v, str):
            return [x.strip() for x in v.split(",") if x.strip()]
        return v
