from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from dotenv import load_dotenv

from ingestion.feature_eng.config import Settings
from ingestion.feature_eng.worker import FeatureEngWorker
from ingestion.fundamentals.loader import FundamentalsCache
from shared.logging import configure
from shared.queue import RabbitMQQueue

_EDGAR_DIR = Path(__file__).parent.parent.parent / "data" / "edgar"


def build_worker(settings: Settings) -> FeatureEngWorker:
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
    settings = Settings()
    configure(settings.log_level)
    asyncio.run(build_worker(settings).run())


if __name__ == "__main__":
    main()
