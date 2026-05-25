"""
Start all services in a single process.

    python run.py

Each service that can't start due to missing config is skipped with a warning.
"""
from __future__ import annotations

import asyncio
import logging

from dotenv import load_dotenv

from feature_eng.__main__ import build_worker as build_feature_eng
from feature_eng.config import Settings as FeatEngSettings
from ingestion.__main__ import build_news_service, build_ohlcv_service
from ingestion.config import Settings as IngestionSettings
from llm_analyzer.__main__ import build_worker as build_llm_analyzer
from llm_analyzer.config import Settings as LLMSettings
from prediction.__main__ import build_worker as build_prediction
from prediction.config import Settings as PredictionSettings
from shared.logging import configure

logger = logging.getLogger(__name__)


async def main() -> None:
    load_dotenv()

    ing = IngestionSettings()
    llm = LLMSettings()
    feat = FeatEngSettings()
    pred = PredictionSettings()

    configure(ing.log_level)

    coros = []

    for label, builder, settings in [
        ("news ingestion",    lambda: build_news_service(ing),    ing),
        ("ohlcv polling",     lambda: build_ohlcv_service(ing),   ing),
        ("llm analyzer",      lambda: build_llm_analyzer(llm),    llm),
        ("feature eng",       lambda: build_feature_eng(feat),    feat),
        ("prediction",        lambda: build_prediction(pred),     pred),
    ]:
        try:
            coros.append(builder().run())
            logger.info("run: %s enabled", label)
        except RuntimeError as exc:
            logger.warning("run: %s skipped — %s", label, exc)

    if not coros:
        logger.error("run: no services started — check your .env")
        return

    await asyncio.gather(*coros)


if __name__ == "__main__":
    asyncio.run(main())
