from __future__ import annotations

import logging
from datetime import datetime

import psycopg

from ingestion.models.ohlcv import OHLCVBar

logger = logging.getLogger(__name__)


class OHLCVRepository:
    def __init__(self, conn: psycopg.AsyncConnection) -> None:
        self._conn = conn

    async def upsert_bars(self, bars: list[OHLCVBar]) -> int:
        if not bars:
            return 0
        await self._conn.executemany(
            """
            INSERT INTO ohlcv (ticker, open, high, low, close, volume, timestamp, timeframe)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (ticker, timestamp, timeframe) DO NOTHING
            """,
            [
                (b.ticker, b.open, b.high, b.low, b.close, b.volume, b.timestamp, b.timeframe)
                for b in bars
            ],
        )
        logger.info("ohlcv.upsert count=%s", len(bars))
        return len(bars)

    async def get_latest_timestamp(self, ticker: str) -> datetime | None:
        cursor = await self._conn.execute(
            "SELECT MAX(timestamp) AS ts FROM ohlcv WHERE ticker = %s",
            (ticker,),
        )
        row = await cursor.fetchone()
        return row["ts"] if row else None
