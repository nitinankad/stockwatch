from __future__ import annotations

import numpy as np
import pandas as pd

# Canonical feature order — must match between feature_eng (writes) and prediction (reads).
FEATURE_COLUMNS = [
    "rsi_14",
    "macd_signal",
    "bb_position",
    "vwap_deviation",
    "volume_ratio",
    "price_change_5",
    "price_change_20",
    "sentiment_avg_1h",
    "sentiment_count_1h",
    "sentiment_deviation",
    "sentiment_momentum",
    "has_breaking_event",
]


def compute_ohlcv_features(bars: pd.DataFrame) -> dict[str, float]:
    """
    bars: DataFrame with columns [open, high, low, close, volume],
    sorted ascending by timestamp. Returns the OHLCV-derived features.
    """
    close = bars["close"].astype(float)
    high = bars["high"].astype(float)
    low = bars["low"].astype(float)
    volume = bars["volume"].astype(float)

    return {
        "rsi_14": _rsi(close, 14),
        "macd_signal": _macd_signal(close),
        "bb_position": _bb_position(close, 20),
        "vwap_deviation": _vwap_deviation(high, low, close, volume),
        "volume_ratio": _volume_ratio(volume, 20),
        "price_change_5": _pct_change(close, 5),
        "price_change_20": _pct_change(close, 20),
    }


def _rsi(close: pd.Series, period: int) -> float:
    if len(close) < period + 1:
        return 50.0
    delta = close.diff().dropna()
    gain = delta.clip(lower=0).ewm(alpha=1 / period, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / period, adjust=False).mean()
    l = loss.iloc[-1]
    rs = gain.iloc[-1] / l if l != 0 else float("inf")
    return round(100 - (100 / (1 + rs)), 4)


def _macd_signal(close: pd.Series) -> float:
    if len(close) < 35:
        return 0.0
    macd = close.ewm(span=12, adjust=False).mean() - close.ewm(span=26, adjust=False).mean()
    return round(float(macd.ewm(span=9, adjust=False).mean().iloc[-1]), 4)


def _bb_position(close: pd.Series, period: int) -> float:
    if len(close) < period:
        return 0.5
    sma = close.rolling(period).mean().iloc[-1]
    std = close.rolling(period).std().iloc[-1]
    if std == 0:
        return 0.5
    upper = sma + 2 * std
    lower = sma - 2 * std
    pos = (float(close.iloc[-1]) - lower) / (upper - lower)
    return round(float(np.clip(pos, 0.0, 1.0)), 4)


def _vwap_deviation(
    high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series
) -> float:
    typical = (high + low + close) / 3
    vwap = (typical * volume).cumsum() / volume.cumsum()
    v = float(vwap.iloc[-1])
    if v == 0:
        return 0.0
    return round((float(close.iloc[-1]) - v) / v, 4)


def _volume_ratio(volume: pd.Series, period: int) -> float:
    if len(volume) < period:
        return 1.0
    avg = volume.rolling(period).mean().iloc[-1]
    if avg == 0:
        return 1.0
    return round(float(volume.iloc[-1] / avg), 4)


def _pct_change(close: pd.Series, n: int) -> float:
    if len(close) <= n:
        return 0.0
    base = float(close.iloc[-(n + 1)])
    if base == 0:
        return 0.0
    return round((float(close.iloc[-1]) - base) / base * 100, 4)
