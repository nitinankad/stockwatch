from __future__ import annotations

import logging

import pandas as pd

from feature_eng.indicators import FEATURE_COLUMNS, compute_ohlcv_features
from shared.alpaca import AlpacaClient
from shared.db.client import connect
from shared.db.feature_vector_repo import FeatureVectorRepository
from shared.db.ohlcv_repo import OHLCVRepository
from shared.models.feature_vector import FeatureVector
from shared.models.ohlcv import OHLCVBar

logger = logging.getLogger(__name__)

# 1-min bars per horizon
HORIZON_BARS: dict[str, int] = {"1h": 60, "4h": 240, "1d": 390}

# Minimum lookback bars needed for indicators (MACD needs 35, we use 120 for stability)
MIN_LOOKBACK = 120

_ZERO_SENTIMENT: dict[str, float] = {
    "sentiment_avg_1h": 0.0,
    "sentiment_count_1h": 0.0,
    "sentiment_deviation": 0.0,
    "sentiment_momentum": 0.0,
    "has_breaking_event": 0.0,
}


class BackfillService:
    def __init__(
        self,
        alpaca: AlpacaClient,
        database_url: str,
        symbols: list[str],
        sample_interval: int = 15,
        prediction_horizons: list[str] | None = None,
    ) -> None:
        self._alpaca = alpaca
        self._database_url = database_url
        self._symbols = symbols
        self._sample_interval = sample_interval
        self._horizons = prediction_horizons or ["1h", "4h", "1d"]

    async def run(self, start, end) -> None:
        logger.info(
            "backfill.start symbols=%s start=%s end=%s", self._symbols, start, end
        )
        bars_by_ticker = await self._alpaca.get_bars(self._symbols, start=start, end=end)

        for ticker, bars in bars_by_ticker.items():
            if not bars:
                logger.warning("backfill.skip ticker=%s reason=no_bars", ticker)
                continue
            await self._process_ticker(ticker, bars)

        logger.info("backfill.done")

    async def _process_ticker(self, ticker: str, bars: list[OHLCVBar]) -> None:
        bars.sort(key=lambda b: b.timestamp)
        max_horizon_bars = max(HORIZON_BARS.get(h, 60) for h in self._horizons)

        # Write all bars to ohlcv table first
        async with connect(self._database_url) as conn:
            await OHLCVRepository(conn).upsert_bars(bars)
        logger.info("backfill.ohlcv_written ticker=%s bars=%d", ticker, len(bars))

        df = pd.DataFrame([b.model_dump() for b in bars])
        inserted = 0

        # Sample every N bars, leaving enough room for lookback and future horizon
        for i in range(MIN_LOOKBACK, len(bars) - max_horizon_bars, self._sample_interval):
            window = df.iloc[i - MIN_LOOKBACK : i + 1]
            snapshot_bar = bars[i]

            ohlcv_features = compute_ohlcv_features(window)
            features = {**ohlcv_features, **_ZERO_SENTIMENT}

            async with connect(self._database_url) as conn:
                fv_repo = FeatureVectorRepository(conn)
                for horizon in self._horizons:
                    horizon_bars = HORIZON_BARS.get(horizon, 60)
                    exit_bar = bars[i + horizon_bars]
                    entry_price = float(snapshot_bar.close)
                    exit_price = float(exit_bar.close)

                    if entry_price == 0:
                        continue

                    actual_pct = (exit_price - entry_price) / entry_price * 100
                    fv = FeatureVector(
                        ticker=ticker,
                        snapshot_timestamp=snapshot_bar.timestamp,
                        prediction_horizon=horizon,
                        features=features,
                        actual_pct_change=actual_pct,
                    )
                    await fv_repo.insert_with_actual(fv)
                    inserted += 1

        logger.info("backfill.vectors_inserted ticker=%s count=%d", ticker, inserted)
