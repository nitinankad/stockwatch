from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from ingestion.sources.base import NewsSource
from ingestion.storage.blob.base import BlobStorage
from shared.queue import RabbitMQQueue
from shared.models.news import RawNewsItem

logger = logging.getLogger(__name__)


class NewsIngestionService:
    def __init__(
        self,
        sources: list[NewsSource],
        blob: BlobStorage,
        poll_interval_seconds: int = 300,
        queue: RabbitMQQueue | None = None,
    ) -> None:
        self._sources = sources
        self._blob = blob
        self._poll_interval = poll_interval_seconds
        self._queue = queue

    async def run(self) -> None:
        logger.info("news_ingestion.start sources=%s", [s.name for s in self._sources])
        while True:
            await self._poll()
            logger.info("news_ingestion.sleeping seconds=%s", self._poll_interval)
            await asyncio.sleep(self._poll_interval)

    async def _poll(self) -> None:
        results = await asyncio.gather(
            *[self._ingest_source(source) for source in self._sources],
            return_exceptions=True,
        )
        for source, result in zip(self._sources, results):
            if isinstance(result, Exception):
                logger.exception(
                    "news_ingestion.source.error source=%s",
                    source.name,
                    exc_info=result,
                )

    async def _ingest_source(self, source: NewsSource) -> dict[str, int]:
        stats = {"seen": 0, "new": 0, "duplicate": 0}
        async for item in source.fetch():
            stats["seen"] += 1
            key = _blob_key(item)
            if await self._blob.exists(key):
                stats["duplicate"] += 1
                continue
            await self._blob.put(
                key=key,
                data=item.model_dump_json().encode(),
                metadata={"source": source.name, "url_hash": item.url_hash},
            )
            if self._queue:
                await self._queue.put({"blob_key": key})
            stats["new"] += 1
        logger.info("news_ingestion.source.done source=%s stats=%s", source.name, stats)
        return stats


def _blob_key(item: RawNewsItem) -> str:
    date = (item.published_at or datetime.now(timezone.utc)).strftime("%Y-%m-%d")
    return f"news/{item.source}/{date}/{item.url_hash}.json"
