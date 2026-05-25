from __future__ import annotations

import logging

from shared.db.client import connect
from shared.db.llm_analysis_repo import LLMAnalysisRepository
from shared.models.news import RawNewsItem
from shared.queue import RabbitMQQueue

from llm_analyzer.analyzer import LLMAnalyzer

logger = logging.getLogger(__name__)


class LLMAnalyzerWorker:
    def __init__(
        self,
        analyzer: LLMAnalyzer,
        blob,
        queue: RabbitMQQueue,
        database_url: str,
        outbound_queue: RabbitMQQueue | None = None,
    ) -> None:
        self._analyzer = analyzer
        self._blob = blob
        self._queue = queue
        self._database_url = database_url
        self._outbound_queue = outbound_queue

    async def run(self) -> None:
        logger.info("llm_analyzer.worker.start")
        async for message, payload in self._queue.consume():
            blob_key = payload.get("blob_key", "")
            try:
                data = await self._blob.get(blob_key)
                if data is None:
                    logger.warning("llm_analyzer.worker.blob_missing key=%s", blob_key)
                    await message.ack()
                    continue

                item = RawNewsItem.model_validate_json(data)
                analysis = await self._analyzer.analyze(item, blob_key)
                if analysis is None:
                    await message.ack()  # no content to analyze — discard permanently
                    continue

                async with connect(self._database_url) as conn:
                    analysis_id = await LLMAnalysisRepository(conn).insert(analysis)

                if self._outbound_queue and analysis.tickers:
                    await self._outbound_queue.put({
                        "llm_analysis_id": analysis_id,
                        "tickers": analysis.tickers,
                        "event_timestamp": analysis.event_timestamp.isoformat()
                        if analysis.event_timestamp else None,
                    })

                await message.ack()
                logger.info(
                    "llm_analyzer.worker.done key=%s tickers=%s sentiment=%s",
                    blob_key,
                    analysis.tickers,
                    analysis.sentiment,
                )
            except Exception as exc:
                logger.exception("llm_analyzer.worker.error key=%s error=%s", blob_key, exc)
                await message.nack(requeue=True)
