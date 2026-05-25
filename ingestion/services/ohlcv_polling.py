from __future__ import annotations

import asyncio
import logging

from ingestion.models.ohlcv import OHLCVBar
from ingestion.sources.base import OHLCVSource
from ingestion.storage.db.client import connect
from ingestion.storage.db.ohlcv_repo import OHLCVRepository

logger = logging.getLogger(__name__)


class OHLCVPollingService:
    def __init__(
        self,
        source: OHLCVSource,
        database_url: str,
        symbols: list[str],
        poll_interval_seconds: int = 60,
    ) -> None:
        self._source = source
        self._database_url = database_url
        self._symbols = symbols
        self._poll_interval = poll_interval_seconds

    async def run(self) -> None:
        logger.info("ohlcv_polling.start symbols=%s", self._symbols)
        while True:
            await self._poll()
            await asyncio.sleep(self._poll_interval)

    async def _poll(self) -> None:
        bars: list[OHLCVBar] = []
        async for bar in self._source.poll(self._symbols):
            bars.append(bar)

        if not bars:
            logger.info("ohlcv_polling.no_bars")
            return

        async with connect(self._database_url) as conn:
            repo = OHLCVRepository(conn)
            count = await repo.upsert_bars(bars)
            logger.info(
                "ohlcv_polling.done upserted=%s received=%s",
                count,
                len(bars),
            )
