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

    # Directory to cache model files locally
    model_dir: str = "./models"
    model_version: str = "0.1.0"

    # S3 — if set, models are downloaded from S3 when not found locally
    s3_bucket: str = ""
    s3_prefix: str = "models"
    s3_endpoint_url: str | None = None
    s3_region: str = "us-east-1"

    log_level: str = "INFO"
