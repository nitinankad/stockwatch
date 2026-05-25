from __future__ import annotations

from typing import Any

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    database_url: str = ""

    # Messaging
    rabbitmq_url: str = ""  # set to enable queue publishing after blob writes

    # Blob storage
    blob_backend: str = "s3"  # "s3" | "local"
    s3_bucket: str = "stockwatch-news-dev"
    s3_endpoint_url: str | None = None  # set to http://localhost:4566 for LocalStack
    s3_region: str = "us-east-1"
    local_blob_root: str = "./blob_store"

    # News sources
    rss_feeds: list[str] = [
        "https://finance.yahoo.com/news/rssindex",
        "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",
        "https://www.cnbc.com/id/100003114/device/rss/rss.html",
    ]
    alpaca_api_key: str | None = None
    alpaca_api_secret: str | None = None
    reddit_subreddits: list[str] = ["stocks", "investing", "wallstreetbets"]
    finnhub_api_key: str | None = None
    finnhub_symbols: list[str] = []

    # OHLCV polling
    ohlcv_symbols: list[str] = []
    ohlcv_poll_interval_seconds: int = 60

    # News ingestion
    news_poll_interval_seconds: int = 300
    request_timeout_seconds: int = 25

    log_level: str = "INFO"

    @field_validator("rss_feeds", "reddit_subreddits", "finnhub_symbols", "ohlcv_symbols", mode="before")
    @classmethod
    def _split_csv(cls, v: Any) -> Any:
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]
        return v
