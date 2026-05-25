from __future__ import annotations

import asyncio

from dotenv import load_dotenv

from feature_eng.config import Settings
from feature_eng.worker import FeatureEngWorker
from shared.logging import configure
from shared.queue import RabbitMQQueue


def build_worker(settings: Settings) -> FeatureEngWorker:
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is required for feature_eng")
    if not settings.rabbitmq_url:
        raise RuntimeError("RABBITMQ_URL is required for feature_eng")

    return FeatureEngWorker(
        inbound=RabbitMQQueue(settings.rabbitmq_url, settings.inbound_queue_name),
        outbound=RabbitMQQueue(settings.rabbitmq_url, settings.outbound_queue_name),
        database_url=settings.database_url,
        ohlcv_lookback_minutes=settings.ohlcv_lookback_minutes,
        ohlcv_timeframe=settings.ohlcv_timeframe,
        prediction_horizons=settings.prediction_horizons,
    )


def main() -> None:
    load_dotenv()
    settings = Settings()
    configure(settings.log_level)
    asyncio.run(build_worker(settings).run())


if __name__ == "__main__":
    main()
