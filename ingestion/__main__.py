from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

from ingestion.config import Settings as IngestionSettings
from ingestion.feature_eng.config import Settings as FeatureEngSettings
from ingestion.llm_analyzer.config import Settings as LLMSettings
from ingestion.utils.logging import configure

logger = logging.getLogger(__name__)

_EDGAR_DIR = Path(__file__).parent.parent / "data" / "edgar"


def _build_blob(settings: IngestionSettings):
    if settings.blob_backend == "local":
        from ingestion.storage.blob.local import LocalFilesystemBlob
        return LocalFilesystemBlob(settings.local_blob_root)
    from ingestion.storage.blob.s3 import S3Blob
    return S3Blob(
        bucket=settings.s3_bucket,
        region=settings.s3_region,
        endpoint_url=settings.s3_endpoint_url,
    )


def _build_news_service(settings: IngestionSettings):
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


def _build_ohlcv_service(settings: IngestionSettings):
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


def _build_llm_analyzer(settings: LLMSettings):
    from ingestion.llm_analyzer.analyzer import LLMAnalyzer
    from ingestion.llm_analyzer.worker import LLMAnalyzerWorker
    from shared.queue import RabbitMQQueue

    if not settings.deepseek_api_key:
        raise RuntimeError("DEEPSEEK_API_KEY is required for llm_analyzer")
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is required for llm_analyzer")
    if not settings.rabbitmq_url:
        raise RuntimeError("RABBITMQ_URL is required for llm_analyzer")

    blob_backend = settings.blob_backend
    if blob_backend == "local":
        from ingestion.storage.blob.local import LocalFilesystemBlob
        blob = LocalFilesystemBlob(settings.local_blob_root)
    else:
        from ingestion.storage.blob.s3 import S3Blob
        blob = S3Blob(
            bucket=settings.s3_bucket,
            region=settings.s3_region,
            endpoint_url=settings.s3_endpoint_url,
        )

    return LLMAnalyzerWorker(
        analyzer=LLMAnalyzer(
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
            model=settings.deepseek_model,
        ),
        blob=blob,
        queue=RabbitMQQueue(settings.rabbitmq_url, settings.queue_name),
        database_url=settings.database_url,
        outbound_queue=RabbitMQQueue(settings.rabbitmq_url, settings.outbound_queue_name),
    )


def _build_feature_eng(settings: FeatureEngSettings):
    from ingestion.feature_eng.worker import FeatureEngWorker
    from ingestion.fundamentals.loader import FundamentalsCache
    from shared.queue import RabbitMQQueue

    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is required for feature_eng")
    if not settings.rabbitmq_url:
        raise RuntimeError("RABBITMQ_URL is required for feature_eng")

    fundamentals = FundamentalsCache(_EDGAR_DIR) if _EDGAR_DIR.exists() else None

    return FeatureEngWorker(
        inbound=RabbitMQQueue(settings.rabbitmq_url, settings.inbound_queue_name),
        outbound=RabbitMQQueue(settings.rabbitmq_url, settings.outbound_queue_name),
        database_url=settings.database_url,
        ohlcv_lookback_minutes=settings.ohlcv_lookback_minutes,
        ohlcv_timeframe=settings.ohlcv_timeframe,
        prediction_horizons=settings.prediction_horizons,
        fundamentals=fundamentals,
    )


def main() -> None:
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    load_dotenv()

    ing  = IngestionSettings()
    llm  = LLMSettings()
    feat = FeatureEngSettings()

    configure(ing.log_level)

    coros = []
    for label, builder in [
        ("news ingestion", lambda: _build_news_service(ing)),
        ("ohlcv polling",  lambda: _build_ohlcv_service(ing)),
        ("llm analyzer",   lambda: _build_llm_analyzer(llm)),
        ("feature eng",    lambda: _build_feature_eng(feat)),
    ]:
        try:
            coros.append(builder().run())
            logger.info("ingestion: %s enabled", label)
        except RuntimeError as exc:
            logger.warning("ingestion: %s skipped — %s", label, exc)

    if not coros:
        logger.error("ingestion: no services started — check your .env")
        return

    asyncio.run(asyncio.gather(*coros))


if __name__ == "__main__":
    main()
