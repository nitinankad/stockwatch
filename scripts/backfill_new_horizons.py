"""
Generate feature vectors for new prediction horizons using existing OHLCV data
already in the database — no Alpaca API calls, no re-downloading anything.

Run from the project root:
    python scripts/backfill_new_horizons.py

Override which horizons to generate:
    python scripts/backfill_new_horizons.py --horizons 1w,2w,1m

Override which tickers to process:
    python scripts/backfill_new_horizons.py --tickers AAPL,MSFT,NVDA

Override concurrency (default: 4 tickers in parallel):
    python scripts/backfill_new_horizons.py --workers 8

The script is safe to re-run: feature_vectors has a unique constraint on
(ticker, snapshot_timestamp, prediction_horizon) so duplicates are silently
skipped via ON CONFLICT DO NOTHING.
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
from dotenv import load_dotenv

from backfill.config import Settings
from backfill.service import (
    HORIZON_MINUTES,
    _ZERO_SENTIMENT,
    _horizon_bars,
    _min_lookback,
)
from feature_eng.indicators import bar_size_minutes, compute_ohlcv_features
from shared.db.client import connect
from shared.db.feature_vector_repo import FeatureVectorRepository
from shared.db.ohlcv_repo import OHLCVRepository
from shared.models.feature_vector import FeatureVector

load_dotenv()

logger = logging.getLogger(__name__)

_EPOCH      = datetime(2000, 1, 1, tzinfo=timezone.utc)
_BATCH_SIZE = 500   # rows per executemany call


async def _distinct_tickers(database_url: str) -> list[str]:
    async with connect(database_url) as conn:
        cursor = await conn.execute("SELECT DISTINCT ticker FROM ohlcv ORDER BY ticker")
        rows = await cursor.fetchall()
    return [r["ticker"] for r in rows]


async def _process_ticker(
    ticker: str,
    new_horizons: list[str],
    timeframe: str,
    sample_interval: int,
    database_url: str,
) -> int:
    """Each ticker gets its own connection so tickers can run concurrently."""
    bar_minutes      = bar_size_minutes(timeframe)
    min_lookback     = _min_lookback(bar_minutes)
    max_horizon_bars = max(_horizon_bars(h, bar_minutes) for h in new_horizons)

    async with connect(database_url) as conn:
        bars = await OHLCVRepository(conn).get_bars(ticker, since=_EPOCH, timeframe=timeframe)
        if not bars:
            logger.warning("skip ticker=%s reason=no_bars_in_db timeframe=%s", ticker, timeframe)
            return 0

        logger.info("ticker=%s bars=%d generating horizons=%s", ticker, len(bars), new_horizons)

        df      = pd.DataFrame([b.model_dump() for b in bars])
        fv_repo = FeatureVectorRepository(conn)
        batch: list[FeatureVector] = []
        inserted = 0

        for i in range(min_lookback, len(bars) - max_horizon_bars, sample_interval):
            window       = df.iloc[i - min_lookback : i + 1]
            snapshot_bar = bars[i]
            features     = {**compute_ohlcv_features(window, bar_minutes=bar_minutes), **_ZERO_SENTIMENT}

            for horizon in new_horizons:
                h_bars      = _horizon_bars(horizon, bar_minutes)
                exit_bar    = bars[i + h_bars]
                entry_price = float(snapshot_bar.close)
                exit_price  = float(exit_bar.close)
                if entry_price == 0:
                    continue

                batch.append(FeatureVector(
                    ticker=ticker,
                    snapshot_timestamp=snapshot_bar.timestamp,
                    prediction_horizon=horizon,
                    features=features,
                    actual_pct_change=(exit_price - entry_price) / entry_price * 100,
                ))

                if len(batch) >= _BATCH_SIZE:
                    inserted += await fv_repo.batch_insert_with_actual(batch)
                    batch.clear()

        if batch:
            inserted += await fv_repo.batch_insert_with_actual(batch)

    logger.info("ticker=%s inserted=%d", ticker, inserted)
    return inserted


async def main(
    new_horizons: list[str],
    tickers: list[str] | None,
    timeframe: str,
    sample_interval: int,
    database_url: str,
    max_workers: int = 4,
) -> None:
    unknown = [h for h in new_horizons if h not in HORIZON_MINUTES]
    if unknown:
        print(f"ERROR: unknown horizon(s): {unknown}. Valid: {list(HORIZON_MINUTES)}")
        sys.exit(1)

    all_tickers = await _distinct_tickers(database_url)
    if not all_tickers:
        print("No tickers found in the ohlcv table. Run `python -m backfill` first.")
        sys.exit(1)

    targets = [t for t in all_tickers if t in tickers] if tickers else all_tickers
    if not targets:
        print(f"None of the requested tickers {tickers} found in ohlcv table.")
        print(f"Available: {all_tickers}")
        sys.exit(1)

    print(f"Tickers     : {', '.join(targets)}")
    print(f"New horizons: {', '.join(new_horizons)}")
    print(f"Timeframe   : {timeframe}  |  Sample every {sample_interval} bars")
    print(f"Concurrency : {max_workers} tickers in parallel  |  Batch size: {_BATCH_SIZE}")
    print()

    sem = asyncio.Semaphore(max_workers)

    async def bounded(ticker: str) -> int:
        async with sem:
            return await _process_ticker(ticker, new_horizons, timeframe, sample_interval, database_url)

    results = await asyncio.gather(*[bounded(t) for t in targets])
    total = sum(results)

    print(f"\nDone. Inserted {total:,} new feature vectors.")
    print("Now run: python -m training")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate feature vectors for new horizons from existing DB bars."
    )
    parser.add_argument(
        "--horizons",
        default="1h,4h,1d,1w,2w,1m",
        help="Comma-separated horizons to generate (default: all)",
    )
    parser.add_argument(
        "--tickers",
        default=None,
        help="Comma-separated tickers to process (default: all tickers in ohlcv table)",
    )
    parser.add_argument(
        "--timeframe",
        default=None,
        help="Bar timeframe to read from DB (default: from OHLCV_TIMEFRAME env or 1Min)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Number of tickers to process concurrently (default: 4)",
    )
    args = parser.parse_args()

    settings = Settings()

    if not settings.database_url:
        print("ERROR: DATABASE_URL not set in .env")
        sys.exit(1)

    new_horizons = [h.strip() for h in args.horizons.split(",") if h.strip()]
    tickers      = [t.strip().upper() for t in args.tickers.split(",") if t.strip()] if args.tickers else None
    timeframe    = args.timeframe or settings.ohlcv_timeframe or "1Min"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s %(message)s",
        datefmt="%H:%M:%S",
    )

    print("\nBackfilling new horizons from existing ohlcv data (no Alpaca calls).\n")

    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    asyncio.run(main(
        new_horizons, tickers, timeframe,
        settings.sample_interval_minutes, settings.database_url,
        max_workers=args.workers,
    ))
