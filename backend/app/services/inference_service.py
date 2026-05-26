from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import psycopg
import xgboost as xgb

from feature_eng.indicators import FEATURE_COLUMNS, bar_size_minutes, compute_ohlcv_features
from shared.db.ohlcv_repo import OHLCVRepository

import pandas as pd

logger = logging.getLogger(__name__)

_SENTIMENT_ZERO = {
    "sentiment_avg_1h":    0.0,
    "sentiment_count_1h":  0.0,
    "sentiment_deviation": 0.0,
    "sentiment_momentum":  0.0,
    "has_breaking_event":  0.0,
}

_ALL_HORIZONS = ["1h", "4h", "1d", "1w", "2w", "1m"]


def load_models(model_dir: str | Path) -> dict[str, xgb.Booster]:
    """Load all available XGBoost models from model_dir at startup."""
    model_dir = Path(model_dir)
    models: dict[str, xgb.Booster] = {}
    for horizon in _ALL_HORIZONS:
        path = model_dir / f"xgb_{horizon}.json"
        if path.exists():
            m = xgb.Booster()
            m.load_model(str(path))
            models[horizon] = m
            logger.info("inference.model_loaded horizon=%s", horizon)
    if not models:
        logger.warning("inference.no_models_found dir=%s", model_dir)
    return models


class InferenceService:
    def __init__(self, models: dict[str, xgb.Booster], timeframe: str = "1Min") -> None:
        self._models = models
        self._timeframe = timeframe
        self._bar_minutes = bar_size_minutes(timeframe)

    async def predict(
        self,
        ticker: str,
        conn: psycopg.AsyncConnection,
        horizons: list[str] | None = None,
    ) -> list[dict]:
        """
        Fetch the last 8 trading days of OHLCV bars for `ticker`, compute
        features, and return one prediction dict per requested horizon.
        """
        since = datetime.now(timezone.utc) - timedelta(days=365)
        bars = await OHLCVRepository(conn).get_bars(
            ticker, since=since, timeframe=self._timeframe
        )
        if len(bars) < 35:
            logger.warning(
                "inference.insufficient_bars ticker=%s n=%d timeframe=%s",
                ticker, len(bars), self._timeframe,
            )
            return 0, []

        df = pd.DataFrame([{
            "open":      float(b.open),
            "high":      float(b.high),
            "low":       float(b.low),
            "close":     float(b.close),
            "volume":    float(b.volume),
            "timestamp": b.timestamp,
        } for b in bars])

        features = {
            **compute_ohlcv_features(df, bar_minutes=self._bar_minutes),
            **_SENTIMENT_ZERO,
        }

        x = np.array(
            [[features.get(col, 0.0) for col in FEATURE_COLUMNS]],
            dtype=np.float32,
        )
        dmatrix = xgb.DMatrix(x, feature_names=FEATURE_COLUMNS)

        targets = horizons or list(self._models.keys())
        results = []
        for horizon in _ALL_HORIZONS:           # preserve canonical order
            if horizon not in targets:
                continue
            model = self._models.get(horizon)
            if model is None:
                continue
            prob = float(model.predict(dmatrix)[0])
            results.append({
                "horizon":    horizon,
                "probability": round(prob, 4),
                "direction":  "bullish" if prob >= 0.5 else "bearish",
                "conviction": round(abs(prob - 0.5), 4),
            })

        logger.info(
            "inference.predicted ticker=%s bars=%d horizons=%s",
            ticker, len(bars), [r["horizon"] for r in results],
        )
        return len(bars), results
