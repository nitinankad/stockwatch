from __future__ import annotations

import json
import logging

import psycopg

from shared.models.feature_vector import FeatureVector

logger = logging.getLogger(__name__)


class FeatureVectorRepository:
    def __init__(self, conn: psycopg.AsyncConnection) -> None:
        self._conn = conn

    async def insert(self, fv: FeatureVector) -> int:
        cursor = await self._conn.execute(
            """
            INSERT INTO feature_vectors
                (ticker, snapshot_timestamp, prediction_horizon, features, predicted_at)
            VALUES (%s, %s, %s, %s, NOW())
            RETURNING id
            """,
            (fv.ticker, fv.snapshot_timestamp, fv.prediction_horizon, json.dumps(fv.features)),
        )
        row = await cursor.fetchone()
        row_id = row["id"]
        await self._conn.commit()
        logger.info("feature_vector.insert id=%s ticker=%s", row_id, fv.ticker)
        return row_id

    async def get_by_id(self, fv_id: int) -> FeatureVector | None:
        cursor = await self._conn.execute(
            """
            SELECT id, ticker, snapshot_timestamp, prediction_horizon, features,
                   actual_pct_change, predicted_at, created_at
            FROM feature_vectors WHERE id = %s
            """,
            (fv_id,),
        )
        row = await cursor.fetchone()
        return FeatureVector(**row) if row else None

    async def get_labeled(self, horizon: str) -> list[FeatureVector]:
        """Returns feature vectors that have been reconciled (have actual_pct_change)."""
        cursor = await self._conn.execute(
            """
            SELECT id, ticker, snapshot_timestamp, prediction_horizon, features,
                   actual_pct_change, predicted_at, created_at
            FROM feature_vectors
            WHERE prediction_horizon = %s AND actual_pct_change IS NOT NULL
            ORDER BY predicted_at
            """,
            (horizon,),
        )
        rows = await cursor.fetchall()
        return [FeatureVector(**row) for row in rows]

    async def insert_with_actual(self, fv: FeatureVector) -> int:
        """Insert a feature vector with actual_pct_change already known (used by backfill)."""
        cursor = await self._conn.execute(
            """
            INSERT INTO feature_vectors
                (ticker, snapshot_timestamp, prediction_horizon, features,
                 actual_pct_change, predicted_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                fv.ticker,
                fv.snapshot_timestamp,
                fv.prediction_horizon,
                json.dumps(fv.features),
                fv.actual_pct_change,
                fv.snapshot_timestamp,
            ),
        )
        row = await cursor.fetchone()
        row_id = row["id"]
        await self._conn.commit()
        return row_id

    async def get_unreconciled(self) -> list[FeatureVector]:
        cursor = await self._conn.execute(
            """
            SELECT id, ticker, snapshot_timestamp, prediction_horizon, features,
                   actual_pct_change, predicted_at, created_at
            FROM feature_vectors
            WHERE actual_pct_change IS NULL
            ORDER BY predicted_at
            """
        )
        rows = await cursor.fetchall()
        return [FeatureVector(**row) for row in rows]

    async def update_actual_pct_change(self, fv_id: int, actual: float) -> None:
        await self._conn.execute(
            "UPDATE feature_vectors SET actual_pct_change = %s WHERE id = %s",
            (actual, fv_id),
        )
        await self._conn.commit()
