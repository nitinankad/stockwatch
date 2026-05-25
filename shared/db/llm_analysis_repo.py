from __future__ import annotations

import logging
from datetime import datetime

import psycopg

from shared.models.llm_analysis import LLMAnalysis

logger = logging.getLogger(__name__)


class LLMAnalysisRepository:
    def __init__(self, conn: psycopg.AsyncConnection) -> None:
        self._conn = conn

    async def insert(self, analysis: LLMAnalysis) -> int | None:
        """Returns the new row id, or None if the article was already processed."""
        cursor = await self._conn.execute(
            """
            INSERT INTO llm_analysis (tickers, sentiment, raw_object_key, event_timestamp)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (raw_object_key) DO NOTHING
            RETURNING id
            """,
            (
                analysis.tickers,
                analysis.sentiment,
                analysis.raw_object_key,
                analysis.event_timestamp,
            ),
        )
        row = await cursor.fetchone()
        await self._conn.commit()
        if row is None:
            logger.debug("llm_analysis.duplicate key=%s", analysis.raw_object_key)
            return None
        logger.info("llm_analysis.insert id=%s tickers=%s", row["id"], analysis.tickers)
        return row["id"]

    async def get_since(self, ticker: str, since: datetime) -> list[LLMAnalysis]:
        cursor = await self._conn.execute(
            """
            SELECT id, tickers, sentiment, raw_object_key, event_timestamp, created_at
            FROM llm_analysis
            WHERE %s = ANY(tickers) AND created_at >= %s
            ORDER BY created_at DESC
            """,
            (ticker, since),
        )
        rows = await cursor.fetchall()
        return [LLMAnalysis(**row) for row in rows]

    async def get_recent(self, ticker: str, limit: int = 100) -> list[LLMAnalysis]:
        cursor = await self._conn.execute(
            """
            SELECT id, tickers, sentiment, raw_object_key, event_timestamp, created_at
            FROM llm_analysis
            WHERE %s = ANY(tickers)
            ORDER BY created_at DESC
            LIMIT %s
            """,
            (ticker, limit),
        )
        rows = await cursor.fetchall()
        return [LLMAnalysis(**row) for row in rows]
