"""
Start all services in a single process.

    python run.py

Long-running services (ingestion, llm_analyzer, feature_eng, prediction) run
continuously. Scheduled jobs (training) are managed by APScheduler inside the
same event loop — no cron setup required.

Schedule:
  - Training: weekly on Monday at 18:00 America/New_York
"""
from __future__ import annotations

import asyncio
import logging
import sys

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv

from ingestion.__main__ import _build_feature_eng, _build_llm_analyzer, _build_news_service, _build_ohlcv_service
from ingestion.config import Settings as IngestionSettings
from ingestion.feature_eng.config import Settings as FeatEngSettings
from ingestion.llm_analyzer.config import Settings as LLMSettings
from backend.prediction.__main__ import build_worker as build_prediction
from backend.prediction.config import Settings as PredictionSettings
from shared.logging import configure
from training.config import Settings as TrainingSettings
from training.trainer import Trainer

logger = logging.getLogger(__name__)

_TZ = "America/New_York"


def _build_scheduler(train: TrainingSettings) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()

    if train.database_url:
        trainer = Trainer(
            database_url=train.database_url,
            model_dir=train.model_dir,
            model_version=train.model_version,
            horizons=train.prediction_horizons,
            test_split=train.test_split,
            min_samples=train.min_samples,
        )
        scheduler.add_job(
            trainer.run,
            CronTrigger(day_of_week="mon", hour=18, minute=0, timezone=_TZ),
            id="training",
            max_instances=1,
            coalesce=True,
        )
        logger.info("run: training scheduled weekly on Monday at 18:00 %s", _TZ)
    else:
        logger.warning("run: training skipped — missing DATABASE_URL")

    return scheduler


async def main() -> None:
    load_dotenv()

    ing   = IngestionSettings()
    llm   = LLMSettings()
    feat  = FeatEngSettings()
    pred  = PredictionSettings()
    train = TrainingSettings()

    configure(ing.log_level)

    # ── Long-running services ──────────────────────────────────────────────────
    coros = []
    for label, builder in [
        ("news ingestion", lambda: _build_news_service(ing)),
        ("ohlcv polling",  lambda: _build_ohlcv_service(ing)),
        ("llm analyzer",   lambda: _build_llm_analyzer(llm)),
        ("feature eng",    lambda: _build_feature_eng(feat)),
        ("prediction",     lambda: build_prediction(pred)),
    ]:
        try:
            coros.append(builder().run())
            logger.info("run: %s enabled", label)
        except RuntimeError as exc:
            logger.warning("run: %s skipped — %s", label, exc)

    if not coros:
        logger.error("run: no services started — check your .env")
        return

    # ── Scheduled jobs (training) ──────────────────────────────────────────────
    scheduler = _build_scheduler(train)
    scheduler.start()

    try:
        await asyncio.gather(*coros)
    finally:
        scheduler.shutdown(wait=False)


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
