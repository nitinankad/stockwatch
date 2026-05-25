from __future__ import annotations

import asyncio

from dotenv import load_dotenv

from shared.logging import configure
from training.config import Settings
from training.trainer import Trainer


def main() -> None:
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
    )
    asyncio.run(trainer.run())


if __name__ == "__main__":
    main()
