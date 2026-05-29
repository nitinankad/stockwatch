from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import pandas as pd

from shared.db.client import connect
from shared.db.feature_vector_repo import FeatureVectorRepository
from shared.db.llm_analysis_repo import LLMAnalysisRepository
from shared.db.ohlcv_repo import OHLCVRepository
from shared.models.feature_vector import FeatureVector
from shared.models.llm_analysis import LLMAnalysis

from ingestion.feature_eng.indicators import bar_size_minutes, compute_ohlcv_features
from ingestion.fundamentals.loader import FundamentalsCache

logger = logging.getLogger(__name__)

_SENTIMENT_SCORE = {"bullish": 1.0, "neutral": 0.0, "bearish": -1.0}


class FeatureEngine:
    def __init__(
        self,
        database_url: str,
        ohlcv_timeframe: str = "1Min",
        prediction_horizons: list[str] | None = None,
        fundamentals: FundamentalsCache | None = None,
    ) -> None:
        self._database_url = database_url
        self._bar_minutes = bar_size_minutes(ohlcv_timeframe)
        self._timeframe = ohlcv_timeframe
        self._horizons = prediction_horizons or ["1h", "4h", "1d"]
        self._fundamentals = fundamentals

    async def process(self, tickers: list[str], event_timestamp: datetime) -> None:
        now = event_timestamp
        since_ohlcv = now - timedelta(days=365)
        since_sentiment = now - timedelta(hours=1)
        since_sentiment_prev = now - timedelta(hours=2)

        async with connect(self._database_url) as conn:
            ohlcv_repo = OHLCVRepository(conn)
            llm_repo = LLMAnalysisRepository(conn)
            fv_repo = FeatureVectorRepository(conn)

            for ticker in tickers:
                bars = await ohlcv_repo.get_bars(ticker, since=since_ohlcv, timeframe=self._timeframe)
                if not bars:
                    logger.info("feature_eng.skip ticker=%s reason=no_ohlcv", ticker)
                    continue

                recent_analyses = await llm_repo.get_since(ticker, since=since_sentiment_prev)
                ohlcv_features = compute_ohlcv_features(
                    pd.DataFrame([b.model_dump() for b in bars]),
                    bar_minutes=self._bar_minutes,
                )
                sentiment_features = _compute_sentiment(
                    recent_analyses, since_sentiment, since_sentiment_prev, now
                )
                features = {**ohlcv_features, **sentiment_features}
                if self._fundamentals:
                    features.update(self._fundamentals.get_as_of(ticker, now))

                for horizon in self._horizons:
                    fv = FeatureVector(
                        ticker=ticker,
                        snapshot_timestamp=now,
                        prediction_horizon=horizon,
                        features=features,
                    )
                    fv_id = await fv_repo.insert(fv)
                    if fv_id is None:
                        logger.debug("feature_eng.duplicate ticker=%s horizon=%s", ticker, horizon)
                        continue
                    logger.info("feature_eng.done ticker=%s horizon=%s fv_id=%s", ticker, horizon, fv_id)


def _compute_sentiment(
    analyses: list[LLMAnalysis],
    since_1h: datetime,
    since_2h: datetime,
    now: datetime,
) -> dict[str, float]:
    def score(a: LLMAnalysis) -> float:
        return _SENTIMENT_SCORE.get(a.sentiment, 0.0)

    recent = [a for a in analyses if a.created_at and a.created_at >= since_1h]
    prev = [a for a in analyses if a.created_at and since_2h <= a.created_at < since_1h]
    breaking_cutoff = now - timedelta(minutes=15)
    has_breaking = any(a.created_at and a.created_at >= breaking_cutoff for a in recent)

    scores_recent = [score(a) for a in recent]
    scores_prev = [score(a) for a in prev]

    avg = sum(scores_recent) / len(scores_recent) if scores_recent else 0.0
    count = float(len(scores_recent))

    if len(scores_recent) > 1:
        mean = sum(scores_recent) / len(scores_recent)
        variance = sum((s - mean) ** 2 for s in scores_recent) / len(scores_recent)
        deviation = variance ** 0.5
    else:
        deviation = 0.0

    prev_avg = sum(scores_prev) / len(scores_prev) if scores_prev else 0.0
    momentum = avg - prev_avg

    return {
        "sentiment_avg_1h": round(avg, 4),
        "sentiment_count_1h": count,
        "sentiment_deviation": round(deviation, 4),
        "sentiment_momentum": round(momentum, 4),
        "has_breaking_event": float(has_breaking),
    }
