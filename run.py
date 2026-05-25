"""
Start all services in a single process.

    python run.py

Each service that can't start due to missing config is skipped with a warning.
"""
from __future__ import annotations

import asyncio
import logging

from dotenv import load_dotenv

from ingestion.__main__ import build_news_service, build_ohlcv_service
from ingestion.config import Settings as IngestionSettings
from llm_analyzer.__main__ import build_worker
from llm_analyzer.config import Settings as LLMSettings
from shared.logging import configure

logger = logging.getLogger(__name__)


async def main() -> None:
    load_dotenv()

    ing = IngestionSettings()
    llm = LLMSettings()
    configure(ing.log_level)

    coros = []

    try:
        coros.append(build_news_service(ing).run())
        logger.info("run: news ingestion enabled")
    except RuntimeError as exc:
        logger.warning("run: news ingestion skipped — %s", exc)

    try:
        coros.append(build_ohlcv_service(ing).run())
        logger.info("run: ohlcv polling enabled")
    except RuntimeError as exc:
        logger.warning("run: ohlcv polling skipped — %s", exc)

    try:
        coros.append(build_worker(llm).run())
        logger.info("run: llm analyzer enabled")
    except RuntimeError as exc:
        logger.warning("run: llm analyzer skipped — %s", exc)

    if not coros:
        logger.error("run: no services started — check your .env")
        return

    await asyncio.gather(*coros)


if __name__ == "__main__":
    asyncio.run(main())
