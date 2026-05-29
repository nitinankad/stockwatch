from __future__ import annotations

import json
import logging
import math
from typing import AsyncIterator

import numpy as np
import psycopg

from ingestion.feature_eng.indicators import SENTIMENT_FEATURE_NAMES
from ingestion.fundamentals.loader import FUNDAMENTAL_FEATURE_NAMES
from shared.models.feature_vector import FeatureVector

# Keys absent from a feature JSON blob mean "data was never computed for this row"
# and should surface as NaN in XGBoost (which has native missing-value handling),
# not as 0.0 (which looks like a real value to the model).
_NAN_DEFAULT_COLS = frozenset(FUNDAMENTAL_FEATURE_NAMES) | frozenset(SENTIMENT_FEATURE_NAMES)

logger = logging.getLogger(__name__)


def _get_feature(features: dict, col: str) -> float:
    """Return the feature value, defaulting to NaN for sentiment and fundamental
    columns (absent key = data was never computed → XGBoost missing-value handling)
    and 0.0 for all other columns (absent key = zero is the correct neutral value)."""
    if col in features:
        return features[col]
    return math.nan if col in _NAN_DEFAULT_COLS else 0.0


class FeatureVectorRepository:
    def __init__(self, conn: psycopg.AsyncConnection) -> None:
        self._conn = conn

    async def insert(self, fv: FeatureVector) -> int | None:
        """Returns the new row id, or None if this (ticker, snapshot, horizon) already exists."""
        cursor = await self._conn.execute(
            """
            INSERT INTO feature_vectors
                (ticker, snapshot_timestamp, prediction_horizon, features, predicted_at)
            VALUES (%s, %s, %s, %s, NOW())
            ON CONFLICT (ticker, snapshot_timestamp, prediction_horizon) DO NOTHING
            RETURNING id
            """,
            (fv.ticker, fv.snapshot_timestamp, fv.prediction_horizon, json.dumps(fv.features)),
        )
        row = await cursor.fetchone()
        await self._conn.commit()
        if row is None:
            logger.debug("feature_vector.duplicate ticker=%s snapshot=%s horizon=%s",
                         fv.ticker, fv.snapshot_timestamp, fv.prediction_horizon)
            return None
        logger.info("feature_vector.insert id=%s ticker=%s", row["id"], fv.ticker)
        return row["id"]

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

    async def iter_labeled_xy(
        self,
        horizon: str,
        feature_columns: list[str],
        batch_size: int = 10_000,
    ) -> AsyncIterator[tuple[np.ndarray, np.ndarray]]:
        """Stream labeled rows as (X, y) numpy batches without materialising FeatureVector objects.

        Each yielded X has shape (batch, len(feature_columns)) float32.
        Each yielded y has shape (batch,) float32 — actual_pct_change values.
        SPY rows are excluded (SPY is a benchmark, not a tradeable signal).
        """
        async with self._conn.cursor() as cur:
            await cur.execute(
                """
                SELECT features, actual_pct_change
                FROM feature_vectors
                WHERE prediction_horizon = %s AND actual_pct_change IS NOT NULL
                  AND ticker != 'SPY'
                ORDER BY predicted_at
                """,
                (horizon,),
            )
            while True:
                rows = await cur.fetchmany(batch_size)
                if not rows:
                    break
                X = np.array(
                    [[_get_feature(row["features"], col) for col in feature_columns] for row in rows],
                    dtype=np.float32,
                )
                y = np.array([float(row["actual_pct_change"]) for row in rows], dtype=np.float32)
                yield X, y

    async def iter_alpha_xy(
        self,
        horizon: str,
        feature_columns: list[str],
        batch_size: int = 10_000,
    ) -> AsyncIterator[tuple[np.ndarray, np.ndarray]]:
        """Stream market-relative (X, y) batches where y = stock_return - SPY_return.

        Rows with no matching SPY snapshot fall back to raw stock return via COALESCE.
        SPY rows are excluded from training.
        """
        async with self._conn.cursor() as cur:
            await cur.execute(
                """
                SELECT fv.features,
                       fv.actual_pct_change
                           - COALESCE(spy.actual_pct_change, 0) AS alpha,
                       fv.predicted_at
                FROM feature_vectors fv
                LEFT JOIN LATERAL (
                    SELECT actual_pct_change
                    FROM feature_vectors spy
                    WHERE spy.ticker            = 'SPY'
                      AND spy.prediction_horizon = fv.prediction_horizon
                      AND spy.actual_pct_change IS NOT NULL
                      AND spy.snapshot_timestamp
                              BETWEEN fv.snapshot_timestamp - INTERVAL '10 minutes'
                                  AND fv.snapshot_timestamp + INTERVAL '10 minutes'
                    ORDER BY ABS(EXTRACT(EPOCH FROM
                                    (spy.snapshot_timestamp - fv.snapshot_timestamp)))
                    LIMIT 1
                ) spy ON true
                WHERE fv.prediction_horizon  = %s
                  AND fv.actual_pct_change   IS NOT NULL
                  AND fv.ticker             != 'SPY'
                ORDER BY fv.predicted_at
                """,
                (horizon,),
            )
            while True:
                rows = await cur.fetchmany(batch_size)
                if not rows:
                    break
                X = np.array(
                    [[_get_feature(row["features"], col) for col in feature_columns] for row in rows],
                    dtype=np.float32,
                )
                y = np.array([float(row["alpha"]) for row in rows], dtype=np.float32)
                yield X, y

    async def insert_with_actual(self, fv: FeatureVector) -> int | None:
        """Insert a feature vector with actual_pct_change already known (used by backfill).
        Returns None if the row already exists — safe to re-run backfill."""
        cursor = await self._conn.execute(
            """
            INSERT INTO feature_vectors
                (ticker, snapshot_timestamp, prediction_horizon, features,
                 actual_pct_change, predicted_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (ticker, snapshot_timestamp, prediction_horizon) DO NOTHING
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
        await self._conn.commit()
        return row["id"] if row else None

    async def batch_insert_with_actual(self, fvs: list[FeatureVector]) -> int:
        """Batch-insert feature vectors using executemany (pipeline mode).
        Returns the number of rows written; duplicates are silently skipped."""
        if not fvs:
            return 0
        rows = [
            (
                fv.ticker,
                fv.snapshot_timestamp,
                fv.prediction_horizon,
                json.dumps(fv.features),
                fv.actual_pct_change,
                fv.snapshot_timestamp,
            )
            for fv in fvs
        ]
        async with self._conn.cursor() as cur:
            await cur.executemany(
                """
                INSERT INTO feature_vectors
                    (ticker, snapshot_timestamp, prediction_horizon, features,
                     actual_pct_change, predicted_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (ticker, snapshot_timestamp, prediction_horizon) DO NOTHING
                """,
                rows,
            )
            inserted = cur.rowcount if cur.rowcount >= 0 else len(fvs)
        await self._conn.commit()
        return inserted

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
