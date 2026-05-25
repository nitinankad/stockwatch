from __future__ import annotations

import asyncio
import sys

from dotenv import load_dotenv

from shared.logging import configure
from training.config import Settings
from training.trainer import Trainer


def main() -> None:
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    load_dotenv()
    settings = Settings()
    configure(settings.log_level)

    if not settings.database_url:
        raise SystemExit("DATABASE_URL is required")

    trainer = Trainer(
        database_url=settings.database_url,
        model_dir=settings.model_dir,
        model_version=settings.model_version,
        horizons=settings.prediction_horizons,
        test_split=settings.test_split,
        min_samples=settings.min_samples,
        s3_bucket=settings.s3_bucket,
        s3_prefix=settings.s3_prefix,
        s3_endpoint_url=settings.s3_endpoint_url,
        s3_region=settings.s3_region,
    )
    asyncio.run(trainer.run())


if __name__ == "__main__":
    main()
