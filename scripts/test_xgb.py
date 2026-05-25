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
    "hour_of_day":        10.5,   # 10:30 AM ET
    "day_of_week":         1.0,   # Tuesday
    "minutes_since_open": 60.0,   # 60 min after open
}

# End of day: 3:30 PM ET, Friday
_END_OF_DAY = {
    "hour_of_day":        15.5,   # 3:30 PM ET
    "day_of_week":         4.0,   # Friday
    "minutes_since_open": 360.0,  # 6 hours after open
}

_ZERO_SENTIMENT = {
    "sentiment_avg_1h":    0.0,
    "sentiment_count_1h":  0.0,
    "sentiment_deviation": 0.0,
    "sentiment_momentum":  0.0,
    "has_breaking_event":  0.0,
}

SCENARIOS: list[dict] = [
    {
        "_label":            "Strong bullish (mid-morning)",
        "rsi_14":             72.0,
        "macd_signal":         0.45,
        "bb_position":         0.85,
        "vwap_deviation":      0.008,
        "volume_ratio":        2.1,
        "price_change_5":      0.9,
        "price_change_20":     1.8,
        "price_change_1d":     1.5,   # up 1.5% today
        "price_change_5d":     4.2,   # up 4.2% this week
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
        "price_change_1d":    -2.0,   # down 2% today
        "price_change_5d":    -5.8,   # down 5.8% this week
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
        **_ZERO_SENTIMENT,
        **_MID_MORNING,
    },
    {
        "_label":            "Bullish with breaking news (mid-morning)",
        "rsi_14":             61.0,
        "macd_signal":         0.18,
        "bb_position":         0.70,
        "vwap_deviation":      0.004,
        "volume_ratio":        3.5,
        "price_change_5":      0.6,
        "price_change_20":     0.9,
        "price_change_1d":     1.2,
        "price_change_5d":     2.5,
        "sentiment_avg_1h":    0.8,
        "sentiment_count_1h":  5.0,
        "sentiment_deviation": 0.2,
        "sentiment_momentum":  0.6,
        "has_breaking_event":  1.0,
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
        **_ZERO_SENTIMENT,
        **_END_OF_DAY,
    },
    {
        "_label":            "Strong bearish (end of day)",
        "rsi_14":             28.0,
        "macd_signal":        -0.52,
        "bb_position":         0.10,
        "vwap_deviation":     -0.012,
        "volume_ratio":        2.4,
        "price_change_5":     -1.1,
        "price_change_20":    -2.3,
        "price_change_1d":    -3.1,   # severe daily selloff
        "price_change_5d":    -7.4,   # bad week
        **_ZERO_SENTIMENT,
        **_END_OF_DAY,
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
    )


if __name__ == "__main__":
    main()
