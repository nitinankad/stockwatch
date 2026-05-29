from __future__ import annotations

import asyncio
import sys

from dotenv import load_dotenv

from .config import Settings
from .worker import PredictionWorker
from shared.logging import configure
from shared.queue import RabbitMQQueue


def build_worker(settings: Settings) -> PredictionWorker:
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is required for prediction")
    if not settings.rabbitmq_url:
        raise RuntimeError("RABBITMQ_URL is required for prediction")

    return PredictionWorker(
        queue=RabbitMQQueue(settings.rabbitmq_url, settings.inbound_queue_name),
        database_url=settings.database_url,
        model_dir=settings.model_dir,
        model_version=settings.model_version,
        s3_bucket=settings.s3_bucket,
        s3_prefix=settings.s3_prefix,
        s3_endpoint_url=settings.s3_endpoint_url,
        s3_region=settings.s3_region,
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
