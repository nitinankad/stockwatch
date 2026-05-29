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
import json
import logging
import signal
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd
import psycopg
from dotenv import load_dotenv

from backfill.config import Settings
from backfill.service import (
    HORIZON_MINUTES,
    _horizon_bars,
    _min_lookback,
)
from feature_eng.indicators import FEATURE_COLUMNS, SENTIMENT_FEATURE_NAMES, bar_size_minutes, compute_features_df
from fundamentals.loader import FundamentalsCache, FUNDAMENTAL_FEATURE_NAMES
from shared.db.client import connect

_EDGAR_DIR = Path(__file__).resolve().parents[1] / "data" / "edgar"

load_dotenv()

# ── Graceful shutdown ────────────────────────────────────────────────────────
_shutdown = threading.Event()

def _install_signal_handlers() -> None:
    def _handle(signum, frame):
        if not _shutdown.is_set():
            print("\nShutdown requested — draining current batches…", flush=True)
            _shutdown.set()
    signal.signal(signal.SIGINT, _handle)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _handle)
# ────────────────────────────────────────────────────────────────────────────

logger = logging.getLogger(__name__)

_EPOCH      = datetime(2000, 1, 1, tzinfo=timezone.utc)
_BATCH_SIZE = 10_000  # rows per executemany call

_INSERT_FV_SQL = """
    INSERT INTO feature_vectors
        (ticker, snapshot_timestamp, prediction_horizon, features,
         actual_pct_change, predicted_at)
    VALUES (%s, %s, %s, %s, %s, %s)
    ON CONFLICT (ticker, snapshot_timestamp, prediction_horizon) DO NOTHING
"""

_SELECT_BARS_SQL = """
    SELECT open, high, low, close, volume, timestamp
    FROM ohlcv
    WHERE ticker = %s AND timeframe = %s
    ORDER BY timestamp
"""


def _flush(conn: psycopg.Connection, batch: list[tuple]) -> int:
    with conn.pipeline():
        with conn.cursor() as cur:
            cur.executemany(_INSERT_FV_SQL, batch)
    conn.commit()
    return len(batch)


def _compute_and_insert_sync(
    ticker: str,
    raw_rows: list[dict],
    new_horizons: list[str],
    bar_minutes: int,
    min_lookback: int,
    max_horizon_bars: int,
    sample_interval: int,
    database_url: str,
    fundamentals: FundamentalsCache | None = None,
) -> int:
    """CPU-bound compute + sync DB write — runs in a thread via asyncio.to_thread."""
    if len(raw_rows) < min_lookback + max_horizon_bars + 1:
        logger.warning(
            "skip ticker=%s reason=insufficient_bars n=%d need=%d",
            ticker, len(raw_rows), min_lookback + max_horizon_bars + 1,
        )
        return 0

    # Build DataFrame directly from raw dicts (no OHLCVBar round-trip).
    df         = pd.DataFrame(raw_rows)
    feat_df    = compute_features_df(df, bar_minutes=bar_minutes)
    for col in FEATURE_COLUMNS:
        if col not in feat_df.columns:
            feat_df[col] = 0.0
    feat_matrix = feat_df[FEATURE_COLUMNS].to_numpy(dtype=np.float32)

    # Precompute before the loop to avoid per-iteration overhead.
    valid_mask = ~np.isnan(feat_matrix).any(axis=1)
    close_arr  = df["close"].to_numpy(dtype=np.float64)
    timestamps = df["timestamp"].tolist()
    h_bars_map = {h: _horizon_bars(h, bar_minutes) for h in new_horizons}

    # Forward-walking EDGAR pointer: O(n_snapshots + n_filings) vs O(n_snapshots * n_filings).
    # Snapshots are chronologically ordered so the pointer only ever moves forward.
    edgar_lookup = fundamentals.make_pointer(ticker) if fundamentals else None

    batch: list[tuple] = []
    inserted = 0

    with psycopg.connect(database_url) as conn:
        for i in range(min_lookback, len(raw_rows) - max_horizon_bars, sample_interval):
            if _shutdown.is_set():
                logger.info("ticker=%s stopping early on shutdown signal", ticker)
                break
            if not valid_mask[i]:
                continue
            entry_price = close_arr[i]
            if entry_price == 0:
                continue

            snapshot_ts   = timestamps[i]
            features_dict = dict(zip(FEATURE_COLUMNS, feat_matrix[i].tolist()))
            # Drop placeholder zeros — absent keys become NaN in XGBoost.
            for k in FUNDAMENTAL_FEATURE_NAMES:
                features_dict.pop(k, None)
            for k in SENTIMENT_FEATURE_NAMES:
                features_dict.pop(k, None)
            if edgar_lookup:
                edgar = edgar_lookup(snapshot_ts)
                if edgar:
                    features_dict.update(edgar)
            features_json = json.dumps(features_dict)

            for horizon, h_bars in h_bars_map.items():
                exit_price = close_arr[i + h_bars]
                if exit_price == 0:
                    continue
                actual_pct = (exit_price - entry_price) / entry_price * 100
                batch.append((
                    ticker,
                    snapshot_ts,
                    horizon,
                    features_json,
                    actual_pct,
                    snapshot_ts,
                ))
                if len(batch) >= _BATCH_SIZE:
                    inserted += _flush(conn, batch)
                    batch.clear()

        if batch:
            inserted += _flush(conn, batch)

    logger.info("ticker=%s inserted=%d", ticker, inserted)
    return inserted


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
    fundamentals: FundamentalsCache | None = None,
) -> int:
    bar_minutes      = bar_size_minutes(timeframe)
    min_lookback     = _min_lookback(bar_minutes)
    max_horizon_bars = max(_horizon_bars(h, bar_minutes) for h in new_horizons)

    # ── Async phase: read raw rows (no OHLCVBar allocation) ──────────────
    async with connect(database_url) as conn:
        cur      = await conn.execute(_SELECT_BARS_SQL, (ticker, timeframe))
        raw_rows = await cur.fetchall()

    if not raw_rows:
        logger.warning("skip ticker=%s reason=no_bars_in_db timeframe=%s", ticker, timeframe)
        return 0

    logger.info("ticker=%s bars=%d generating horizons=%s", ticker, len(raw_rows), new_horizons)

    # ── Thread phase: CPU compute + sync psycopg write ───────────────────
    # asyncio.to_thread releases the event loop during pandas ops and DB writes,
    # allowing other tickers' async I/O to proceed in parallel.
    return await asyncio.to_thread(
        _compute_and_insert_sync,
        ticker, raw_rows, new_horizons, bar_minutes,
        min_lookback, max_horizon_bars, sample_interval, database_url,
        fundamentals,
    )


async def main(
    new_horizons: list[str],
    tickers: list[str] | None,
    timeframe: str,
    sample_interval: int,
    database_url: str,
    max_workers: int = 4,
    fundamentals: FundamentalsCache | None = None,
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
            return await _process_ticker(ticker, new_horizons, timeframe, sample_interval, database_url, fundamentals)

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
        default=25,
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

    _install_signal_handlers()
    print("\nBackfilling new horizons from existing ohlcv data (no Alpaca calls).")
    print("Press Ctrl+C to stop gracefully — current batches will be flushed first.\n")

    fundamentals = None
    if _EDGAR_DIR.exists():
        fundamentals = FundamentalsCache(_EDGAR_DIR)
        print(f"EDGAR fundamentals loaded for: {', '.join(fundamentals.tickers) or 'none'}\n")
    else:
        print(f"No EDGAR data found at {_EDGAR_DIR} — fundamental features will be absent (NaN in model).\n")

    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    try:
        asyncio.run(main(
            new_horizons, tickers, timeframe,
            settings.sample_interval_minutes, settings.database_url,
            max_workers=args.workers,
            fundamentals=fundamentals,
        ))
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        if _shutdown.is_set():
            print("\nStopped early. Re-run anytime — ON CONFLICT DO NOTHING skips already-inserted rows.")
