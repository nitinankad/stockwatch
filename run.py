"""
Start all services in a single process.

    python run.py

Long-running services (ingestion, llm_analyzer, feature_eng, prediction) run
continuously. Scheduled jobs (reconciliation, training) are managed by
APScheduler inside the same event loop — no cron setup required.

Schedule:
  - Reconciliation: daily at 17:00 America/New_York
  - Training:       weekly on Monday at 18:00 America/New_York
"""
from __future__ import annotations

import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv

from backfill.config import Settings as BackfillSettings
from feature_eng.__main__ import build_worker as build_feature_eng
from feature_eng.config import Settings as FeatEngSettings
from ingestion.__main__ import build_news_service, build_ohlcv_service
from ingestion.config import Settings as IngestionSettings
from llm_analyzer.__main__ import build_worker as build_llm_analyzer
from llm_analyzer.config import Settings as LLMSettings
from prediction.__main__ import build_worker as build_prediction
from prediction.config import Settings as PredictionSettings
from reconciliation.config import Settings as ReconSettings
from reconciliation.service import ReconciliationService
from shared.alpaca import AlpacaClient
from shared.logging import configure
from training.config import Settings as TrainingSettings
from training.trainer import Trainer

logger = logging.getLogger(__name__)

_TZ = "America/New_York"


def _build_scheduler(recon: ReconSettings, train: TrainingSettings) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()

    if recon.database_url and recon.alpaca_api_key and recon.alpaca_api_secret:
        svc = ReconciliationService(
            alpaca=AlpacaClient(recon.alpaca_api_key, recon.alpaca_api_secret),
            database_url=recon.database_url,
        )
        scheduler.add_job(
            svc.run,
            CronTrigger(hour=17, minute=0, timezone=_TZ),
            id="reconciliation",
            max_instances=1,
            coalesce=True,
        )
        logger.info("run: reconciliation scheduled daily at 17:00 %s", _TZ)
    else:
        logger.warning("run: reconciliation skipped — missing ALPACA_API_KEY or DATABASE_URL")

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
    recon = ReconSettings()
    train = TrainingSettings()

    configure(ing.log_level)

    # ── Long-running services ──────────────────────────────────────────────────
    coros = []
    for label, builder in [
        ("news ingestion", lambda: build_news_service(ing)),
        ("ohlcv polling",  lambda: build_ohlcv_service(ing)),
        ("llm analyzer",   lambda: build_llm_analyzer(llm)),
        ("feature eng",    lambda: build_feature_eng(feat)),
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

    # ── Scheduled jobs (reconciliation + training) ─────────────────────────────
    scheduler = _build_scheduler(recon, train)
    scheduler.start()

    try:
        await asyncio.gather(*coros)
    finally:
        scheduler.shutdown(wait=False)


if __name__ == "__main__":
    asyncio.run(main())
