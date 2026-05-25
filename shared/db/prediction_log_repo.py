from __future__ import annotations

import logging

import psycopg

from shared.models.prediction_log import PredictionLog

logger = logging.getLogger(__name__)


class PredictionLogRepository:
    def __init__(self, conn: psycopg.AsyncConnection) -> None:
        self._conn = conn

    async def insert(self, log: PredictionLog) -> int:
        cursor = await self._conn.execute(
            """
            INSERT INTO prediction_logs (
                feature_vector_id, ticker, model_version,
                predicted_pct_change, derived_direction, predicted_at
            )
            VALUES (%s, %s, %s, %s, %s, NOW())
            RETURNING id
            """,
            (
                log.feature_vector_id,
                log.ticker,
                log.model_version,
                log.predicted_pct_change,
                log.derived_direction,
            ),
        )
        row = await cursor.fetchone()
        row_id = row["id"]
        await self._conn.commit()
        logger.info("prediction_log.insert id=%s ticker=%s", row_id, log.ticker)
        return row_id

    async def get_unresolved(self) -> list[PredictionLog]:
        cursor = await self._conn.execute(
            """
            SELECT id, feature_vector_id, ticker, model_version,
                   predicted_pct_change, derived_direction,
                   actual_pct_change, error, predicted_at, resolved_at
            FROM prediction_logs
            WHERE resolved_at IS NULL
            ORDER BY predicted_at
            """
        )
        rows = await cursor.fetchall()
        return [PredictionLog(**row) for row in rows]

    async def resolve(self, log_id: int, actual: float, error: float) -> None:
        await self._conn.execute(
            """
            UPDATE prediction_logs
            SET actual_pct_change = %s, error = %s, resolved_at = NOW()
            WHERE id = %s
            """,
            (actual, error, log_id),
        )
        await self._conn.commit()
