from __future__ import annotations

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = ""
    model_dir: str = "./models"
    model_version: str = "0.1.0"

    prediction_horizons: list[str] = ["1h", "4h", "1d"]
    test_split: float = 0.2
    min_samples: int = 100

    log_level: str = "INFO"

    @field_validator("prediction_horizons", mode="before")
    @classmethod
    def _split_csv(cls, v):
        if isinstance(v, str):
            return [x.strip() for x in v.split(",") if x.strip()]
        return v
