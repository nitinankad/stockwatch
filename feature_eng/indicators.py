from __future__ import annotations

from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

_ET = ZoneInfo("America/New_York")

# Canonical feature order — must match between feature_eng (writes) and prediction (reads).
FEATURE_COLUMNS = [
    "rsi_14",
    "macd_signal",
    "bb_position",
    "vwap_deviation",
    "volume_ratio",
    "price_change_5",
    "price_change_20",
    "price_change_1d",
    "price_change_5d",
    "sentiment_avg_1h",
    "sentiment_count_1h",
    "sentiment_deviation",
    "sentiment_momentum",
    "has_breaking_event",
    "hour_of_day",
    "day_of_week",
    "minutes_since_open",
]

# 1 trading day = 390 minutes; 5 trading days = 1950 minutes
_TRADING_DAY_MINUTES = 390
_TRADING_WEEK_MINUTES = 1_950


def bar_size_minutes(timeframe: str) -> int:
    """Width of a single bar in minutes for common Alpaca timeframes."""
    return {"1Min": 1, "5Min": 5, "15Min": 15, "1Hour": 60}.get(timeframe, 1)


def compute_ohlcv_features(bars: pd.DataFrame, bar_minutes: int = 1) -> dict[str, float]:
    """
    bars: DataFrame with columns [open, high, low, close, volume, timestamp],
    sorted ascending by timestamp. Returns the OHLCV-derived features.

    bar_minutes: width of each bar in minutes (1 for 1Min bars, 5 for 5Min bars).
    Multi-day features return 0.0 gracefully when bars is too short.
    """
    close = bars["close"].astype(float)
    high = bars["high"].astype(float)
    low = bars["low"].astype(float)
    volume = bars["volume"].astype(float)
    last_ts = bars["timestamp"].iloc[-1]

    bars_per_day  = _TRADING_DAY_MINUTES  // bar_minutes   # e.g. 390 for 1Min, 78 for 5Min
    bars_per_week = _TRADING_WEEK_MINUTES // bar_minutes   # e.g. 1950 for 1Min, 390 for 5Min

    return {
        "rsi_14":          _rsi(close, 14),
        "macd_signal":     _macd_signal(close),
        "bb_position":     _bb_position(close, 20),
        "vwap_deviation":  _vwap_deviation(high, low, close, volume),
        "volume_ratio":    _volume_ratio(volume, 20),
        "price_change_5":  _pct_change(close, 5),
        "price_change_20": _pct_change(close, 20),
        "price_change_1d": _pct_change(close, bars_per_day),
        "price_change_5d": _pct_change(close, bars_per_week),
        **_time_features(last_ts),
    }


def _time_features(timestamp) -> dict[str, float]:
    ts = timestamp
    if hasattr(ts, "to_pydatetime"):
        ts = ts.to_pydatetime()
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=ZoneInfo("UTC"))
    ts_et = ts.astimezone(_ET)
    hour_of_day = ts_et.hour + ts_et.minute / 60.0
    day_of_week = float(ts_et.weekday())  # 0=Monday, 4=Friday
    minutes_since_open = max(0.0, (ts_et.hour - 9) * 60 + ts_et.minute - 30)
    return {
        "hour_of_day":        round(hour_of_day, 4),
        "day_of_week":        day_of_week,
        "minutes_since_open": float(minutes_since_open),
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
