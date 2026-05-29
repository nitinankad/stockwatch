"""
Start all services in a single process.

    python run.py

Runs news ingestion and OHLCV polling continuously.
"""
from __future__ import annotations

import asyncio
import logging
import sys

from dotenv import load_dotenv

from ingestion.__main__ import _build_news_service, _build_ohlcv_service
from ingestion.config import Settings as IngestionSettings
from shared.logging import configure

logger = logging.getLogger(__name__)


async def main() -> None:
    load_dotenv()

    ing = IngestionSettings()
    configure(ing.log_level)

    coros = []
    for label, builder in [
        ("news ingestion", lambda: _build_news_service(ing)),
        ("ohlcv polling",  lambda: _build_ohlcv_service(ing)),
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
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
