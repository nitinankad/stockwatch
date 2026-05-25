"""
One-time migration: add hour_of_day, day_of_week, minutes_since_open to all
existing feature_vectors rows using their stored snapshot_timestamp.

Run from the project root:
    python scripts/migrate_time_features.py

Safe to re-run — the JSONB || operator overwrites the three keys if they already
exist, leaving all other features untouched.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import psycopg
import psycopg.rows
from dotenv import load_dotenv

from backfill.config import Settings

_SQL = """
UPDATE feature_vectors
SET features = features || jsonb_build_object(
    'hour_of_day',
    ROUND((
        EXTRACT(HOUR    FROM snapshot_timestamp AT TIME ZONE 'America/New_York')
        + EXTRACT(MINUTE FROM snapshot_timestamp AT TIME ZONE 'America/New_York') / 60.0
    )::numeric, 4),

    'day_of_week',
    -- ISODOW: 1=Monday..7=Sunday  →  subtract 1 for 0=Monday..6=Sunday
    (EXTRACT(ISODOW FROM snapshot_timestamp AT TIME ZONE 'America/New_York') - 1)::float,

    'minutes_since_open',
    GREATEST(0,
        EXTRACT(HOUR   FROM snapshot_timestamp AT TIME ZONE 'America/New_York') * 60
        + EXTRACT(MINUTE FROM snapshot_timestamp AT TIME ZONE 'America/New_York')
        - (9 * 60 + 30)   -- 9:30 AM ET = market open
    )::float
)
"""

_COUNT_SQL = "SELECT COUNT(*) AS n FROM feature_vectors"


async def main() -> None:
    load_dotenv()
    settings = Settings()

    if not settings.database_url:
        print("DATABASE_URL not set in .env")
        sys.exit(1)

    async with await psycopg.AsyncConnection.connect(
        settings.database_url,
        row_factory=psycopg.rows.dict_row,
    ) as conn:
        row = await (await conn.execute(_COUNT_SQL)).fetchone()
        total = row["n"]
        print(f"Updating {total:,} feature_vector rows with time features...")

        await conn.execute(_SQL)
        await conn.commit()

    print("Done. Re-run `python -m training` to retrain with the new features.")


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
