from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

from ingestion.config import Settings
from ingestion.utils.logging import configure

logger = logging.getLogger(__name__)

_EDGAR_DIR = Path(__file__).parent.parent / "data" / "edgar"


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


def _build_news_service(settings: Settings):
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

    llm_analyzer = None
    if settings.deepseek_api_key and settings.database_url:
        from ingestion.llm_analyzer.analyzer import LLMAnalyzer
        llm_analyzer = LLMAnalyzer(
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
            model=settings.deepseek_model,
        )

    feature_engine = None
    if settings.database_url:
        from ingestion.feature_eng.engine import FeatureEngine
        from ingestion.fundamentals.loader import FundamentalsCache
        fundamentals = FundamentalsCache(_EDGAR_DIR) if _EDGAR_DIR.exists() else None
        feature_engine = FeatureEngine(
            database_url=settings.database_url,
            ohlcv_timeframe=settings.ohlcv_timeframe,
            prediction_horizons=settings.prediction_horizons,
            fundamentals=fundamentals,
        )

    return NewsIngestionService(
        sources,
        _build_blob(settings),
        settings.news_poll_interval_seconds,
        llm_analyzer=llm_analyzer,
        feature_engine=feature_engine,
        database_url=settings.database_url,
    )


def _build_ohlcv_service(settings: Settings):
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

    settings = Settings()
    configure(settings.log_level)

    coros = []
    for label, builder in [
        ("news ingestion", lambda: _build_news_service(settings)),
        ("ohlcv polling",  lambda: _build_ohlcv_service(settings)),
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
