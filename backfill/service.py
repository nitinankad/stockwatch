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

# Minutes per horizon (timeframe-independent)
HORIZON_MINUTES: dict[str, int] = {"1h": 60, "4h": 240, "1d": 390}

# MACD(12,26,9) needs 35 bars minimum
_MACD_MIN_BARS = 35


def _bars_per_minute(timeframe: str) -> int:
    """Inverse of bar size: how many bars fit in one minute."""
    return {"1Min": 1, "5Min": 5}.get(timeframe, 1)


def _horizon_bars(horizon: str, bar_minutes: int) -> int:
    return HORIZON_MINUTES.get(horizon, 60) // bar_minutes


def _min_lookback(bar_minutes: int) -> int:
    """120-minute lookback expressed as bar count, floored at MACD minimum."""
    return max(_MACD_MIN_BARS, 120 // bar_minutes)

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
        timeframe: str = "1Min",
        sample_interval: int = 15,
        prediction_horizons: list[str] | None = None,
    ) -> None:
        self._alpaca = alpaca
        self._database_url = database_url
        self._symbols = symbols
        self._timeframe = timeframe
        self._bar_minutes = _bars_per_minute(timeframe)
        self._sample_interval = sample_interval
        self._horizons = prediction_horizons or ["1h", "4h", "1d"]

    async def run(self, start, end) -> None:
        logger.info(
            "backfill.start symbols=%s start=%s end=%s timeframe=%s",
            self._symbols, start, end, self._timeframe,
        )
        bars_by_ticker = await self._alpaca.get_bars(
            self._symbols, start=start, end=end, timeframe=self._timeframe
        )

        for ticker, bars in bars_by_ticker.items():
            if not bars:
                logger.warning("backfill.skip ticker=%s reason=no_bars", ticker)
                continue
            await self._process_ticker(ticker, bars)

        logger.info("backfill.done")

    async def _process_ticker(self, ticker: str, bars: list[OHLCVBar]) -> None:
        bars.sort(key=lambda b: b.timestamp)
        min_lookback = _min_lookback(self._bar_minutes)
        max_horizon_bars = max(_horizon_bars(h, self._bar_minutes) for h in self._horizons)

        # Write all bars to ohlcv table first
        async with connect(self._database_url) as conn:
            await OHLCVRepository(conn).upsert_bars(bars)
        logger.info("backfill.ohlcv_written ticker=%s bars=%d", ticker, len(bars))

        df = pd.DataFrame([b.model_dump() for b in bars])
        inserted = 0

        # Sample every N bars, leaving enough room for lookback and future horizon
        for i in range(min_lookback, len(bars) - max_horizon_bars, self._sample_interval):
            window = df.iloc[i - min_lookback : i + 1]
            snapshot_bar = bars[i]

            ohlcv_features = compute_ohlcv_features(window)
            features = {**ohlcv_features, **_ZERO_SENTIMENT}

            async with connect(self._database_url) as conn:
                fv_repo = FeatureVectorRepository(conn)
                for horizon in self._horizons:
                    horizon_bars = _horizon_bars(horizon, self._bar_minutes)
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
