from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from ingestion.sources.base import NewsSource
from ingestion.storage.blob.base import BlobStorage
from shared.models.news import RawNewsItem

logger = logging.getLogger(__name__)


class NewsIngestionService:
    def __init__(
        self,
        sources: list[NewsSource],
        blob: BlobStorage,
        poll_interval_seconds: int = 300,
        llm_analyzer=None,
        feature_engine=None,
        database_url: str = "",
    ) -> None:
        self._sources = sources
        self._blob = blob
        self._poll_interval = poll_interval_seconds
        self._llm_analyzer = llm_analyzer
        self._feature_engine = feature_engine
        self._database_url = database_url

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
            stats["new"] += 1
            await self._analyze_and_engineer(item, key)
        logger.info("news_ingestion.source.done source=%s stats=%s", source.name, stats)
        return stats

    async def _analyze_and_engineer(self, item: RawNewsItem, blob_key: str) -> None:
        if not self._llm_analyzer or not self._database_url:
            return

        try:
            analysis = await self._llm_analyzer.analyze(item, blob_key)
        except Exception as exc:
            logger.exception("news_ingestion.llm.error key=%s error=%s", blob_key, exc)
            return

        if analysis is None:
            return

        from shared.db.client import connect
        from shared.db.llm_analysis_repo import LLMAnalysisRepository

        async with connect(self._database_url) as conn:
            analysis_id = await LLMAnalysisRepository(conn).insert(analysis)

        if analysis_id is None:
            return  # duplicate

        logger.info(
            "news_ingestion.llm.done key=%s tickers=%s sentiment=%s",
            blob_key, analysis.tickers, analysis.sentiment,
        )

        if self._feature_engine and analysis.tickers:
            ts = analysis.event_timestamp or datetime.now(timezone.utc)
            try:
                await self._feature_engine.process(analysis.tickers, ts)
            except Exception as exc:
                logger.exception(
                    "news_ingestion.feature_eng.error tickers=%s error=%s",
                    analysis.tickers, exc,
                )


def _blob_key(item: RawNewsItem) -> str:
    date = (item.published_at or datetime.now(timezone.utc)).strftime("%Y-%m-%d")
    return f"news/{item.source}/{date}/{item.url_hash}.json"
