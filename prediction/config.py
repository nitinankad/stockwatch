from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = ""
    rabbitmq_url: str = "amqp://guest:guest@localhost/"

    inbound_queue_name: str = "feature_ready"

    # Directory containing XGBoost model files named xgb_{horizon}.json
    model_dir: str = "./models"
    model_version: str = "0.1.0"

    log_level: str = "INFO"
