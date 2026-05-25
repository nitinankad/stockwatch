from __future__ import annotations

import argparse
import asyncio
import sys

from dotenv import load_dotenv

from ingestion.config import Settings
from ingestion.utils.logging import configure


def _build_blob(settings: Settings):
    if settings.blob_backend == "local":
        from ingestion.storage.blob.local import LocalFilesystemBlob
        return LocalFilesystemBlob(settings.local_blob_root)
    from ingestion.storage.blob.s3 import S3Blob
    return S3Blob(
        bucket=settings.s3_bucket,
        region=settings.s3_region,
        endpoint_url=settings.s3_endpoint_url,
    )


def build_news_service(settings: Settings):
    from ingestion.services.news_ingestion import NewsIngestionService
    from ingestion.sources.alpaca_news import AlpacaNewsSource
    from ingestion.sources.finnhub import FinnhubSource
    from ingestion.sources.reddit import RedditSource
    from ingestion.sources.rss import RSSSource

    sources = []

    if settings.rss_feeds:
        sources.append(RSSSource(settings.rss_feeds, timeout=settings.request_timeout_seconds))

    if settings.alpaca_api_key and settings.alpaca_api_secret:
        sources.append(
            AlpacaNewsSource(
                settings.alpaca_api_key,
                settings.alpaca_api_secret,
                timeout=settings.request_timeout_seconds,
            )
        )

    if settings.reddit_subreddits:
        sources.append(RedditSource(settings.reddit_subreddits, timeout=settings.request_timeout_seconds))

    if settings.finnhub_api_key and settings.finnhub_symbols:
        sources.append(FinnhubSource(settings.finnhub_api_key, settings.finnhub_symbols))

    if not sources:
        raise RuntimeError("No news sources configured — set RSS_FEEDS, ALPACA_API_KEY, etc.")

    queue = None
    if settings.rabbitmq_url:
        from shared.queue import RabbitMQQueue
        queue = RabbitMQQueue(settings.rabbitmq_url, "raw_news")

    return NewsIngestionService(
        sources,
        _build_blob(settings),
        settings.news_poll_interval_seconds,
        queue=queue,
    )


def build_ohlcv_service(settings: Settings):
    from ingestion.services.ohlcv_polling import OHLCVPollingService
    from ingestion.sources.alpaca_ohlcv import AlpacaOHLCVSource

    if not settings.alpaca_api_key or not settings.alpaca_api_secret:
        raise RuntimeError("ALPACA_API_KEY and ALPACA_API_SECRET are required for ohlcv")
    if not settings.ohlcv_symbols:
        raise RuntimeError("OHLCV_SYMBOLS is required for ohlcv")
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is required for ohlcv")

    source = AlpacaOHLCVSource(
        settings.alpaca_api_key,
        settings.alpaca_api_secret,
        timeframe=settings.ohlcv_timeframe,
    )
    return OHLCVPollingService(
        source,
        settings.database_url,
        settings.ohlcv_symbols,
        settings.ohlcv_poll_interval_seconds,
    )


def main() -> None:
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    load_dotenv()

    parser = argparse.ArgumentParser(prog="python -m ingestion")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("news", help="Start the news ingestion loop")
    subparsers.add_parser("ohlcv", help="Start the OHLCV polling loop")
    args = parser.parse_args()

    settings = Settings()
    configure(settings.log_level)

    if args.command == "news":
        asyncio.run(build_news_service(settings).run())
    elif args.command == "ohlcv":
        asyncio.run(build_ohlcv_service(settings).run())


if __name__ == "__main__":
    main()
