from __future__ import annotations

import asyncio
import json
import logging

import pandas as pd
import psycopg

from feature_eng.indicators import bar_size_minutes, compute_ohlcv_features
from shared.alpaca import AlpacaClient
from shared.models.ohlcv import OHLCVBar

logger = logging.getLogger(__name__)

# Minutes per horizon (timeframe-independent).
# Trading-day minutes: 1d=390, 1w=5×390=1950, 2w=10×390=3900, 1m≈21×390=8190
HORIZON_MINUTES: dict[str, int] = {
    "1h":  60,
    "4h":  240,
    "1d":  390,
    "1w":  1_950,
    "2w":  3_900,
    "1m":  8_190,
}

_MACD_MIN_BARS = 35
_BATCH_SIZE    = 500   # rows per executemany call

_INSERT_OHLCV_SQL = """
    INSERT INTO ohlcv (ticker, open, high, low, close, volume, timestamp, timeframe)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (ticker, timestamp, timeframe) DO NOTHING
"""

_INSERT_FV_SQL = """
    INSERT INTO feature_vectors
        (ticker, snapshot_timestamp, prediction_horizon, features,
         actual_pct_change, predicted_at)
    VALUES (%s, %s, %s, %s, %s, %s)
    ON CONFLICT (ticker, snapshot_timestamp, prediction_horizon) DO NOTHING
"""

_ZERO_SENTIMENT: dict[str, float] = {
    "sentiment_avg_1h":    0.0,
    "sentiment_count_1h":  0.0,
    "sentiment_deviation": 0.0,
    "sentiment_momentum":  0.0,
    "has_breaking_event":  0.0,
}


def _horizon_bars(horizon: str, bar_minutes: int) -> int:
    return HORIZON_MINUTES.get(horizon, 60) // bar_minutes


def _min_lookback(bar_minutes: int) -> int:
    """Lookback in bars: enough for 5 trading days (price_change_5d) and MACD minimum."""
    return max(_MACD_MIN_BARS, 1_950 // bar_minutes)


class BackfillService:
    def __init__(
        self,
        alpaca: AlpacaClient,
        database_url: str,
        symbols: list[str],
        timeframe: str = "1Min",
        sample_interval: int = 15,
        prediction_horizons: list[str] | None = None,
        max_workers: int = 4,
    ) -> None:
        self._alpaca        = alpaca
        self._database_url  = database_url
        self._symbols       = symbols
        self._timeframe     = timeframe
        self._bar_minutes   = bar_size_minutes(timeframe)
        self._sample_interval = sample_interval
        self._horizons      = prediction_horizons or ["1h", "4h", "1d"]
        self._max_workers   = max_workers

    # ------------------------------------------------------------------
    # Public entry point (runs in the main async event loop)
    # ------------------------------------------------------------------

    async def run(self, start, end) -> None:
        logger.info(
            "backfill.start symbols=%s start=%s end=%s timeframe=%s workers=%d",
            self._symbols, start, end, self._timeframe, self._max_workers,
        )

        # ── Main thread: one Alpaca API call for all tickers ───────────
        bars_by_ticker = await self._alpaca.get_bars(
            self._symbols, start=start, end=end, timeframe=self._timeframe
        )

        valid = {
            ticker: sorted(bars, key=lambda b: b.timestamp)
            for ticker, bars in bars_by_ticker.items()
            if bars
        }
        for ticker in set(self._symbols) - set(valid):
            logger.warning("backfill.skip ticker=%s reason=no_bars", ticker)

        # ── Threads: OHLCV write + feature computation + FV inserts ────
        # asyncio.to_thread runs each ticker's CPU-bound + DB work in a
        # real OS thread, leaving the event loop free.  The semaphore
        # caps concurrent DB connections to self._max_workers.
        sem = asyncio.Semaphore(self._max_workers)

        async def bounded(ticker: str, bars: list[OHLCVBar]) -> int:
            async with sem:
                return await asyncio.to_thread(
                    self._compute_and_insert, ticker, bars
                )

        results = await asyncio.gather(
            *[bounded(t, b) for t, b in valid.items()]
        )
        total = sum(results)
        logger.info("backfill.done total_vectors=%d", total)

    # ------------------------------------------------------------------
    # Per-ticker worker — runs in a thread, uses sync psycopg
    # ------------------------------------------------------------------

    def _compute_and_insert(self, ticker: str, bars: list[OHLCVBar]) -> int:
        """
        Compute features for every sampled snapshot and batch-insert into
        feature_vectors.  Runs in a thread — uses psycopg sync connection
        so the event loop is never blocked.
        """
        min_lookback     = _min_lookback(self._bar_minutes)
        max_horizon_bars = max(_horizon_bars(h, self._bar_minutes) for h in self._horizons)

        if len(bars) < min_lookback + max_horizon_bars + 1:
            logger.warning(
                "backfill.skip ticker=%s reason=insufficient_bars n=%d need=%d",
                ticker, len(bars), min_lookback + max_horizon_bars + 1,
            )
            return 0

        df       = pd.DataFrame([b.model_dump() for b in bars])
        batch: list[tuple] = []
        inserted = 0

        with psycopg.connect(self._database_url) as conn:
            # ── OHLCV batch write ──────────────────────────────────────
            ohlcv_rows = [
                (b.ticker, b.open, b.high, b.low, b.close, b.volume, b.timestamp, b.timeframe)
                for b in bars
            ]
            for chunk_start in range(0, len(ohlcv_rows), _BATCH_SIZE):
                chunk = ohlcv_rows[chunk_start : chunk_start + _BATCH_SIZE]
                with conn.cursor() as cur:
                    cur.executemany(_INSERT_OHLCV_SQL, chunk)
                conn.commit()
            logger.info("backfill.ohlcv_written ticker=%s bars=%d", ticker, len(bars))

            # ── Feature vectors ────────────────────────────────────────
            for i in range(min_lookback, len(bars) - max_horizon_bars, self._sample_interval):
                window       = df.iloc[i - min_lookback : i + 1]
                snapshot_bar = bars[i]
                features     = {
                    **compute_ohlcv_features(window, bar_minutes=self._bar_minutes),
                    **_ZERO_SENTIMENT,
                }
                features_json = json.dumps(features)

                for horizon in self._horizons:
                    h_bars      = _horizon_bars(horizon, self._bar_minutes)
                    exit_bar    = bars[i + h_bars]
                    entry_price = float(snapshot_bar.close)
                    exit_price  = float(exit_bar.close)
                    if entry_price == 0:
                        continue

                    actual_pct = (exit_price - entry_price) / entry_price * 100
                    batch.append((
                        ticker,
                        snapshot_bar.timestamp,
                        horizon,
                        features_json,
                        actual_pct,
                        snapshot_bar.timestamp,   # predicted_at
                    ))

                    if len(batch) >= _BATCH_SIZE:
                        inserted += _flush(conn, batch)
                        batch.clear()

            if batch:
                inserted += _flush(conn, batch)

        logger.info("backfill.vectors_inserted ticker=%s count=%d", ticker, inserted)
        return inserted


def _flush(conn: psycopg.Connection, batch: list[tuple]) -> int:
    """Execute a batch insert and return the number of rows written."""
    with conn.cursor() as cur:
        cur.executemany(_INSERT_FV_SQL, batch)
        n = max(cur.rowcount, 0)
    conn.commit()
    return n
