"""
Quick smoke-test for the trained XGBoost models.

Run from the project root:
    python scripts/test_xgb.py

Loads models/xgb_{1h,4h,1d}.json and runs several labelled scenarios through
each model, printing a results table.  No database or live data required.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Allow imports from project root
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Windows: Python's stdout defaults to cp1252 which can't encode ▲/▼.
# Reconfigure the encoder to UTF-8, then re-enable VT processing so ANSI
# colour codes still work (reconfigure() can reset the console mode).
if sys.platform == "win32":
    import ctypes
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    _k32 = ctypes.windll.kernel32
    _h   = _k32.GetStdHandle(-11)           # STD_OUTPUT_HANDLE
    _m   = ctypes.c_ulong()
    _k32.GetConsoleMode(_h, ctypes.byref(_m))
    _k32.SetConsoleMode(_h, _m.value | 0x0004)  # ENABLE_VIRTUAL_TERMINAL_PROCESSING

import numpy as np
import xgboost as xgb

from feature_eng.indicators import FEATURE_COLUMNS

# ---------------------------------------------------------------------------
# Default time contexts — merged into each scenario.
# Sentiment features are zeroed because the current models were trained on
# backfill data (zero sentiment).  Set them to non-zero once live data
# has been collected and the models retrained.
# ---------------------------------------------------------------------------

# Typical mid-morning session: 10:30 AM ET, Tuesday
_MID_MORNING = {
    "hour_of_day":        10.5,
    "day_of_week":         1.0,   # Tuesday
    "minutes_since_open": 60.0,
}

# Market open: 9:35 AM ET, Wednesday
_OPEN = {
    "hour_of_day":         9.58,
    "day_of_week":         2.0,   # Wednesday
    "minutes_since_open":  5.0,
}

# Lunch lull: 12:30 PM ET, Thursday
_LUNCH = {
    "hour_of_day":        12.5,
    "day_of_week":         3.0,   # Thursday
    "minutes_since_open": 180.0,
}

# End of day: 3:30 PM ET, Friday
_END_OF_DAY = {
    "hour_of_day":        15.5,
    "day_of_week":         4.0,   # Friday
    "minutes_since_open": 360.0,
}

# Monday open: often sets tone for the week
_MONDAY_OPEN = {
    "hour_of_day":         9.75,
    "day_of_week":         0.0,   # Monday
    "minutes_since_open": 15.0,
}

_ZERO_SENTIMENT = {
    "sentiment_avg_1h":    0.0,
    "sentiment_count_1h":  0.0,
    "sentiment_deviation": 0.0,
    "sentiment_momentum":  0.0,
    "has_breaking_event":  0.0,
}

# Trend-regime contexts — spread into each scenario.
# price_vs_50d_ma:    (close - 50d SMA) / close  [+ = above MA]
# ma_10d_50d_cross:   (10d SMA - 50d SMA) / close [+ = golden cross]
# drawdown_from_peak: (close - 52w high) / 52w high  [always ≤ 0]
# dist_from_52w_low:  (close - 52w low)  / 52w low   [always ≥ 0]
_STRONG_BULL_REGIME = {
    "price_vs_50d_ma":     0.10,   # 10% above 50d MA
    "ma_10d_50d_cross":    0.025,  # golden cross
    "drawdown_from_peak": -0.03,   # near 52w high
    "dist_from_52w_low":   0.55,   # well above 52w low
}
_BULL_REGIME = {
    "price_vs_50d_ma":     0.07,
    "ma_10d_50d_cross":    0.018,
    "drawdown_from_peak": -0.08,
    "dist_from_52w_low":   0.38,
}
_NEUTRAL_REGIME = {
    "price_vs_50d_ma":     0.01,
    "ma_10d_50d_cross":    0.004,
    "drawdown_from_peak": -0.12,
    "dist_from_52w_low":   0.15,
}
_BEAR_REGIME = {
    "price_vs_50d_ma":    -0.08,
    "ma_10d_50d_cross":   -0.022,
    "drawdown_from_peak": -0.30,
    "dist_from_52w_low":   0.08,
}
_STRONG_BEAR_REGIME = {
    "price_vs_50d_ma":    -0.15,
    "ma_10d_50d_cross":   -0.05,
    "drawdown_from_peak": -0.45,
    "dist_from_52w_low":   0.03,
}

SCENARIOS: list[dict] = [
    # ── Trend continuation ───────────────────────────────────────────────
    {
        "_label":            "Strong bullish (mid-morning)",
        "rsi_14":             72.0,
        "macd_signal":         0.45,
        "bb_position":         0.85,
        "vwap_deviation":      0.008,
        "volume_ratio":        2.1,
        "price_change_5":      0.9,
        "price_change_20":     1.8,
        "price_change_1d":     1.5,
        "price_change_5d":     4.2,
        **_STRONG_BULL_REGIME,
        **_ZERO_SENTIMENT,
        **_MID_MORNING,
    },
    {
        "_label":            "Strong bearish (mid-morning)",
        "rsi_14":             28.0,
        "macd_signal":        -0.52,
        "bb_position":         0.10,
        "vwap_deviation":     -0.012,
        "volume_ratio":        2.4,
        "price_change_5":     -1.1,
        "price_change_20":    -2.3,
        "price_change_1d":    -2.0,
        "price_change_5d":    -5.8,
        **_STRONG_BEAR_REGIME,
        **_ZERO_SENTIMENT,
        **_MID_MORNING,
    },
    {
        "_label":            "Neutral / sideways (mid-morning)",
        "rsi_14":             51.0,
        "macd_signal":         0.02,
        "bb_position":         0.50,
        "vwap_deviation":      0.001,
        "volume_ratio":        0.95,
        "price_change_5":      0.05,
        "price_change_20":     0.12,
        "price_change_1d":     0.1,
        "price_change_5d":     0.3,
        **_NEUTRAL_REGIME,
        **_ZERO_SENTIMENT,
        **_MID_MORNING,
    },
    # ── Gap opens ────────────────────────────────────────────────────────
    {
        "_label":            "Gap up open (strong)",
        "rsi_14":             68.0,
        "macd_signal":         0.30,
        "bb_position":         0.90,
        "vwap_deviation":      0.015,
        "volume_ratio":        4.2,   # huge volume surge at open
        "price_change_5":      1.8,   # 5 bars = 5 min into gap
        "price_change_20":     2.1,
        "price_change_1d":     2.3,   # gap size reflected in 1d
        "price_change_5d":     3.5,
        **_BULL_REGIME,
        **_ZERO_SENTIMENT,
        **_OPEN,
    },
    {
        "_label":            "Gap down open (panic)",
        "rsi_14":             24.0,
        "macd_signal":        -0.40,
        "bb_position":         0.05,
        "vwap_deviation":     -0.018,
        "volume_ratio":        5.1,
        "price_change_5":     -2.1,
        "price_change_20":    -2.8,
        "price_change_1d":    -3.2,
        "price_change_5d":    -6.1,
        **_BEAR_REGIME,
        **_ZERO_SENTIMENT,
        **_OPEN,
    },
    # ── Reversals ────────────────────────────────────────────────────────
    {
        "_label":            "Oversold bounce attempt",
        "rsi_14":             22.0,   # deeply oversold
        "macd_signal":        -0.15,  # MACD still negative but tightening
        "bb_position":         0.04,  # at lower band
        "vwap_deviation":     -0.009,
        "volume_ratio":        1.8,   # volume picking up (buyers entering)
        "price_change_5":      0.3,   # last 5 bars slightly positive (bounce starting)
        "price_change_20":    -1.4,
        "price_change_1d":    -2.5,
        "price_change_5d":    -7.2,
        **_STRONG_BEAR_REGIME,
        **_ZERO_SENTIMENT,
        **_MID_MORNING,
    },
    {
        "_label":            "Overbought exhaustion",
        "rsi_14":             81.0,   # extremely overbought
        "macd_signal":         0.08,  # MACD flattening — momentum fading
        "bb_position":         0.97,  # pressing upper band
        "vwap_deviation":      0.014,
        "volume_ratio":        0.6,   # volume drying up (buyers exhausted)
        "price_change_5":     -0.1,   # starting to stall
        "price_change_20":     2.5,
        "price_change_1d":     3.1,
        "price_change_5d":     8.4,
        "price_vs_50d_ma":     0.12,  # well above MA — near 52w high
        "ma_10d_50d_cross":    0.04,
        "drawdown_from_peak": -0.02,  # nearly at 52w high
        "dist_from_52w_low":   0.65,
        **_ZERO_SENTIMENT,
        **_MID_MORNING,
    },
    {
        "_label":            "Bearish reversal (end of day)",
        "rsi_14":             65.0,
        "macd_signal":        -0.08,
        "bb_position":         0.72,
        "vwap_deviation":      0.003,
        "volume_ratio":        0.7,
        "price_change_5":     -0.3,
        "price_change_20":     1.2,
        "price_change_1d":     0.8,   # was up today, now fading
        "price_change_5d":     2.1,
        "price_vs_50d_ma":     0.03,  # slightly above MA — momentum fading
        "ma_10d_50d_cross":    0.008,
        "drawdown_from_peak": -0.15,
        "dist_from_52w_low":   0.20,
        **_ZERO_SENTIMENT,
        **_END_OF_DAY,
    },
    # ── Bull / bear flags ────────────────────────────────────────────────
    {
        "_label":            "Bull flag (pullback in uptrend)",
        "rsi_14":             52.0,   # RSI reset from overbought — healthy
        "macd_signal":         0.12,  # still positive
        "bb_position":         0.55,
        "vwap_deviation":      0.002,
        "volume_ratio":        0.65,  # low volume on pullback = weak sellers
        "price_change_5":     -0.2,   # small retracement
        "price_change_20":     0.4,
        "price_change_1d":    -0.5,   # slight red day
        "price_change_5d":     5.8,   # strong prior week
        **_BULL_REGIME,
        **_ZERO_SENTIMENT,
        **_MID_MORNING,
    },
    {
        "_label":            "Bear flag (bounce in downtrend)",
        "rsi_14":             46.0,   # RSI bounced from oversold — weak
        "macd_signal":        -0.10,
        "bb_position":         0.42,
        "vwap_deviation":     -0.003,
        "volume_ratio":        0.55,  # low volume on bounce = weak buyers
        "price_change_5":      0.3,   # small bounce
        "price_change_20":    -0.6,
        "price_change_1d":     0.4,   # slight green day
        "price_change_5d":    -6.3,   # bad prior week
        **_BEAR_REGIME,
        **_ZERO_SENTIMENT,
        **_MID_MORNING,
    },
    # ── News-driven ──────────────────────────────────────────────────────
    {
        "_label":            "Bullish with breaking news",
        "rsi_14":             61.0,
        "macd_signal":         0.18,
        "bb_position":         0.70,
        "vwap_deviation":      0.004,
        "volume_ratio":        3.5,
        "price_change_5":      0.6,
        "price_change_20":     0.9,
        "price_change_1d":     1.2,
        "price_change_5d":     2.5,
        **_BULL_REGIME,
        "sentiment_avg_1h":    0.8,
        "sentiment_count_1h":  5.0,
        "sentiment_deviation": 0.2,
        "sentiment_momentum":  0.6,
        "has_breaking_event":  1.0,
        **_MID_MORNING,
    },
    {
        "_label":            "Bearish with negative news",
        "rsi_14":             35.0,
        "macd_signal":        -0.22,
        "bb_position":         0.18,
        "vwap_deviation":     -0.007,
        "volume_ratio":        2.8,
        "price_change_5":     -0.7,
        "price_change_20":    -1.5,
        "price_change_1d":    -1.8,
        "price_change_5d":    -3.2,
        **_BEAR_REGIME,
        "sentiment_avg_1h":   -0.75,
        "sentiment_count_1h":  4.0,
        "sentiment_deviation": 0.15,
        "sentiment_momentum": -0.5,
        "has_breaking_event":  1.0,
        **_MID_MORNING,
    },
    # ── Mixed / conflicting signals ───────────────────────────────────────
    {
        "_label":            "RSI bullish, MACD bearish (conflict)",
        "rsi_14":             62.0,   # RSI says buy
        "macd_signal":        -0.20,  # MACD says sell — divergence
        "bb_position":         0.58,
        "vwap_deviation":      0.001,
        "volume_ratio":        1.0,
        "price_change_5":      0.1,
        "price_change_20":    -0.3,
        "price_change_1d":     0.5,
        "price_change_5d":    -1.1,
        "price_vs_50d_ma":     0.01,  # near MA — truly mixed regime
        "ma_10d_50d_cross":   -0.005, # barely bearish cross
        "drawdown_from_peak": -0.18,
        "dist_from_52w_low":   0.12,
        **_ZERO_SENTIMENT,
        **_MID_MORNING,
    },
    {
        "_label":            "Lunchtime low-volume drift",
        "rsi_14":             49.0,
        "macd_signal":         0.01,
        "bb_position":         0.48,
        "vwap_deviation":      0.000,
        "volume_ratio":        0.40,  # volume collapses at lunch — noise territory
        "price_change_5":      0.02,
        "price_change_20":     0.08,
        "price_change_1d":     0.1,
        "price_change_5d":     0.5,
        **_NEUTRAL_REGIME,
        **_ZERO_SENTIMENT,
        **_LUNCH,
    },
    # ── End-of-week / Monday effects ─────────────────────────────────────
    {
        "_label":            "Strong bearish (end of day)",
        "rsi_14":             28.0,
        "macd_signal":        -0.52,
        "bb_position":         0.10,
        "vwap_deviation":     -0.012,
        "volume_ratio":        2.4,
        "price_change_5":     -1.1,
        "price_change_20":    -2.3,
        "price_change_1d":    -3.1,
        "price_change_5d":    -7.4,
        **_STRONG_BEAR_REGIME,
        **_ZERO_SENTIMENT,
        **_END_OF_DAY,
    },
    {
        "_label":            "Monday gap-up continuation",
        "rsi_14":             58.0,
        "macd_signal":         0.25,
        "bb_position":         0.75,
        "vwap_deviation":      0.006,
        "volume_ratio":        2.8,   # strong Monday open volume
        "price_change_5":      0.5,
        "price_change_20":     1.1,
        "price_change_1d":     1.3,
        "price_change_5d":     3.8,   # last week was strong
        **_BULL_REGIME,
        **_ZERO_SENTIMENT,
        **_MONDAY_OPEN,
    },
    {
        "_label":            "Monday gap-down fear",
        "rsi_14":             31.0,
        "macd_signal":        -0.35,
        "bb_position":         0.12,
        "vwap_deviation":     -0.010,
        "volume_ratio":        3.3,
        "price_change_5":     -1.5,
        "price_change_20":    -2.0,
        "price_change_1d":    -2.8,
        "price_change_5d":    -5.5,   # last week was bad
        **_BEAR_REGIME,
        **_ZERO_SENTIMENT,
        **_MONDAY_OPEN,
    },
]

MODEL_DIR = Path(__file__).resolve().parents[1] / "models"

_ALL_HORIZONS = ["1h", "4h", "1d", "1w", "2w", "1m"]
HORIZONS = [h for h in _ALL_HORIZONS if (MODEL_DIR / f"xgb_{h}.json").exists()]


def load_model(horizon: str) -> xgb.Booster | None:
    path = MODEL_DIR / f"xgb_{horizon}.json"
    if not path.exists():
        print(f"  [WARN] model not found: {path}")
        return None
    model = xgb.Booster()
    model.load_model(str(path))
    return model


def build_matrix(scenario: dict) -> xgb.DMatrix:
    x = np.array(
        [[scenario.get(col, 0.0) for col in FEATURE_COLUMNS]],
        dtype=np.float32,
    )
    return xgb.DMatrix(x, feature_names=FEATURE_COLUMNS)


BULL = "\033[32m▲\033[0m"  # green
BEAR = "\033[31m▼\033[0m"  # red


def _fmt(prob: float) -> str:
    """Format a classifier probability for table display.

    Visible width is always 22 chars: '▲ 0.6123  bull  +0.112'
    """
    arrow = BULL if prob >= 0.5 else BEAR
    label = "bull" if prob >= 0.5 else "bear"
    conv  = prob - 0.5
    return f"{arrow} {prob:.4f}  {label}  {conv:+.3f}"


def _visible(prob: float) -> int:
    """Length of _fmt output without ANSI escape bytes."""
    label = "bull" if prob >= 0.5 else "bear"
    return len(f"▲ {prob:.4f}  {label}  {prob - 0.5:+.3f}")


def main() -> None:
    print(f"\nLoading models from {MODEL_DIR}\n")
    models = {h: load_model(h) for h in HORIZONS}
    active = [h for h in HORIZONS if models[h]]

    if not active:
        print("No models found. Run `python -m training` first.")
        sys.exit(1)

    label_w = max(len(s["_label"]) for s in SCENARIOS) + 2
    col_w   = _visible(0.6123)   # derive from the actual format, not a magic number

    sep    = "+" + "-" * (label_w + 2) + "+" + ("-" * (col_w + 2) + "+") * len(active)
    header = f"| {'Scenario':<{label_w}} |" + "".join(f" {h:^{col_w}} |" for h in active)
    print(sep)
    print(header)
    print(sep)

    for scenario in SCENARIOS:
        label  = scenario["_label"]
        matrix = build_matrix(scenario)
        row    = f"| {label:<{label_w}} |"
        for h in active:
            prob    = float(models[h].predict(matrix)[0])
            cell    = _fmt(prob)
            padding = col_w - _visible(prob)
            row    += f" {cell}{' ' * padding} |"
        print(row)

    print(sep)
    print(
        "\n  prob = P(stock beats SPY) per horizon  |  conv = prob - 0.5  |  trade when |conv| >= 0.10\n"
        "  Sentiment features = 0 until live data retrains model\n"
        "  NOTE: Retrain models after backfilling with new trend-regime features\n"
        "        (price_vs_50d_ma, ma_10d_50d_cross, drawdown_from_peak, dist_from_52w_low)\n"
    )


if __name__ == "__main__":
    main()
