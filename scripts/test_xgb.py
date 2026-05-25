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
        "_label":          "Strong bullish (mid-morning)",
        "rsi_14":           72.0,
        "macd_signal":       0.45,
        "bb_position":       0.85,
        "vwap_deviation":    0.008,
        "volume_ratio":      2.1,
        "price_change_5":    0.9,
        "price_change_20":   1.8,
        **_ZERO_SENTIMENT,
        **_MID_MORNING,
    },
    {
        "_label":          "Strong bearish (mid-morning)",
        "rsi_14":           28.0,
        "macd_signal":      -0.52,
        "bb_position":       0.10,
        "vwap_deviation":   -0.012,
        "volume_ratio":      2.4,
        "price_change_5":   -1.1,
        "price_change_20":  -2.3,
        **_ZERO_SENTIMENT,
        **_MID_MORNING,
    },
    {
        "_label":          "Neutral / sideways (mid-morning)",
        "rsi_14":           51.0,
        "macd_signal":       0.02,
        "bb_position":       0.50,
        "vwap_deviation":    0.001,
        "volume_ratio":      0.95,
        "price_change_5":    0.05,
        "price_change_20":   0.12,
        **_ZERO_SENTIMENT,
        **_MID_MORNING,
    },
    {
        "_label":          "Bullish with breaking news (mid-morning)",
        "rsi_14":           61.0,
        "macd_signal":       0.18,
        "bb_position":       0.70,
        "vwap_deviation":    0.004,
        "volume_ratio":      3.5,
        "price_change_5":    0.6,
        "price_change_20":   0.9,
        "sentiment_avg_1h":  0.8,
        "sentiment_count_1h": 5.0,
        "sentiment_deviation": 0.2,
        "sentiment_momentum": 0.6,
        "has_breaking_event": 1.0,
        **_MID_MORNING,
    },
    {
        "_label":          "Bearish reversal (end of day)",
        "rsi_14":           65.0,
        "macd_signal":      -0.08,
        "bb_position":       0.72,
        "vwap_deviation":    0.003,
        "volume_ratio":      0.7,
        "price_change_5":   -0.3,
        "price_change_20":   1.2,
        **_ZERO_SENTIMENT,
        **_END_OF_DAY,
    },
    {
        "_label":          "Strong bearish (end of day)",
        "rsi_14":           28.0,
        "macd_signal":      -0.52,
        "bb_position":       0.10,
        "vwap_deviation":   -0.012,
        "volume_ratio":      2.4,
        "price_change_5":   -1.1,
        "price_change_20":  -2.3,
        **_ZERO_SENTIMENT,
        **_END_OF_DAY,
    },
]

HORIZONS = ["1h", "4h", "1d"]
MODEL_DIR = Path(__file__).resolve().parents[1] / "models"


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


def _fmt(pred: float) -> str:
    arrow = BULL if pred >= 0 else BEAR
    label = "bullish" if pred >= 0 else "bearish"
    return f"{arrow} {pred:+.4f}%  {label}"


def main() -> None:
    print(f"\nLoading models from {MODEL_DIR}\n")
    models = {h: load_model(h) for h in HORIZONS}
    active = [h for h in HORIZONS if models[h]]

    if not active:
        print("No models found. Run `python -m training` first.")
        sys.exit(1)

    label_w = max(len(s["_label"]) for s in SCENARIOS) + 2
    col_w   = 22

    # Header
    sep = "+" + "-" * (label_w + 2) + "+" + ("─" * (col_w + 2) + "+") * len(active)
    header = f"| {'Scenario':<{label_w}} |" + "".join(f" {h:^{col_w}} |" for h in active)
    print(sep)
    print(header)
    print(sep)

    for scenario in SCENARIOS:
        label  = scenario["_label"]
        matrix = build_matrix(scenario)
        row    = f"| {label:<{label_w}} |"
        for h in active:
            pred = float(models[h].predict(matrix)[0])
            cell = _fmt(pred)
            # pad to col_w accounting for invisible ANSI escape bytes
            visible_len = len(f"{'▲' if pred >= 0 else '▼'} {pred:+.4f}%  {'bullish' if pred >= 0 else 'bearish'}")
            padding = col_w - visible_len
            row += f" {cell}{' ' * padding} |"
        print(row)

    print(sep)
    print("\n  Predicted % price change per horizon  |  Sentiment features = 0 until live data retrains model\n")


if __name__ == "__main__":
    main()
