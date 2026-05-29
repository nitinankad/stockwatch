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

    # Blob storage — must match ingestion config so both services read/write the same store
    blob_backend: str = "local"
    s3_bucket: str = "stockwatch-news-dev"
    s3_endpoint_url: str | None = None
    s3_region: str = "us-east-1"
    local_blob_root: str = "./blob_store"

    # LLM
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"

    # Worker
    queue_name: str = "raw_news"
    outbound_queue_name: str = "llm_analyzed"

    log_level: str = "INFO"
