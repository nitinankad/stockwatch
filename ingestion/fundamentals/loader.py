from __future__ import annotations

import json
import logging
import math
from datetime import datetime
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

# Feature names exported to FEATURE_COLUMNS — must stay in sync with indicators.py
FUNDAMENTAL_FEATURE_NAMES = [
    "fundamental_gross_margin",
    "fundamental_operating_margin",
    "fundamental_net_margin",
    "fundamental_fcf_margin",
    "fundamental_rd_intensity",
    "fundamental_revenue_growth_yoy",
    "fundamental_revenue_growth_qoq",
    "fundamental_debt_to_equity",
]

_ANNUAL_DAYS    = (340, 380)
_QUARTERLY_DAYS = (80, 100)


class FundamentalsCache:
    """Loads EDGAR JSON files and answers point-in-time fundamental ratio queries.

    Uses `filed` date (not period_end) for lookups to avoid look-ahead bias —
    ratios are only visible after the company actually filed them with the SEC.

    Returns an empty dict when no filing is available so callers can omit the
    keys from the features JSON entirely, letting XGBoost treat them as NaN
    (missing) rather than 0.0 (zero margin / zero growth).
    """

    def __init__(self, data_dir: str | Path) -> None:
        self._annual: dict[str, pd.DataFrame] = {}
        self._quarterly: dict[str, pd.DataFrame] = {}

        data_dir = Path(data_dir)
        for path in sorted(data_dir.glob("*_edgar.json")):
            ticker = path.stem.split("_edgar")[0].upper()
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                annual_df, qoq_df = _build_ratio_series(data)
                if not annual_df.empty:
                    self._annual[ticker] = annual_df
                if not qoq_df.empty:
                    self._quarterly[ticker] = qoq_df
                logger.info(
                    "fundamentals.loaded ticker=%s annual_rows=%d qoq_rows=%d",
                    ticker, len(annual_df), len(qoq_df),
                )
            except Exception as exc:
                logger.warning("fundamentals.load_error ticker=%s error=%s", ticker, exc)

    @property
    def tickers(self) -> list[str]:
        return sorted(self._annual.keys())

    def get_as_of(self, ticker: str, as_of: datetime) -> dict[str, float]:
        """Return the most recently filed fundamental ratios as of `as_of`.

        Returns {} when no filing is available — callers should not add these
        keys to the features dict so XGBoost receives NaN for missing data.
        """
        annual_df = self._annual.get(ticker.upper())
        if annual_df is None:
            return {}

        # replace(tzinfo=None) strips tz without conversion — works in all pandas
        # versions and avoids TypeError when comparing tz-naive filed dates with
        # tz-aware snapshot timestamps from psycopg.
        as_of_ts = pd.Timestamp(as_of).replace(tzinfo=None)

        mask = annual_df["filed"] <= as_of_ts
        if not mask.any():
            return {}

        row = annual_df[mask].iloc[-1]

        rev_growth_qoq = 0.0
        qoq_df = self._quarterly.get(ticker.upper())
        if qoq_df is not None:
            q_mask = qoq_df["filed"] <= as_of_ts
            if q_mask.any():
                rev_growth_qoq = _clip(float(qoq_df[q_mask].iloc[-1]["revenue_growth_qoq"]), -1.0, 5.0)

        return {
            "fundamental_gross_margin":       _clip(row["gross_margin"],         -2.0,  2.0),
            "fundamental_operating_margin":   _clip(row["operating_margin"],     -5.0,  5.0),
            "fundamental_net_margin":         _clip(row["net_margin"],           -5.0,  5.0),
            "fundamental_fcf_margin":         _clip(row["fcf_margin"],           -5.0,  5.0),
            "fundamental_rd_intensity":       _clip(row["rd_intensity"],          0.0,  5.0),
            "fundamental_revenue_growth_yoy": _clip(row["revenue_growth_yoy"],  -1.0, 10.0),
            "fundamental_revenue_growth_qoq": rev_growth_qoq,
            "fundamental_debt_to_equity":     _clip(row["debt_to_equity"],      -10.0, 10.0),
        }

    def make_pointer(self, ticker: str):
        """Return a stateful lookup callable for a single ticker.

        Assumes calls arrive in strictly ascending timestamp order (true during
        backfill). Advances two integer pointers through the sorted filing arrays
        instead of running a full boolean mask on every call — O(n_snapshots +
        n_filings) total vs O(n_snapshots * n_filings) for get_as_of.

        Returns a callable: (datetime) -> dict[str, float]
        """
        annual_df = self._annual.get(ticker.upper())
        if annual_df is None:
            return lambda _: {}

        qoq_df = self._quarterly.get(ticker.upper())

        annual_filed = [t.replace(tzinfo=None) for t in annual_df["filed"]]
        qoq_filed    = [t.replace(tzinfo=None) for t in qoq_df["filed"]] if qoq_df is not None else []

        state = {"a": -1, "q": -1}  # mutable pointer state

        def _row_to_dict(row, qoq_idx: int) -> dict[str, float]:
            rev_growth_qoq = 0.0
            if qoq_idx >= 0 and qoq_df is not None:
                rev_growth_qoq = _clip(float(qoq_df.iloc[qoq_idx]["revenue_growth_qoq"]), -1.0, 5.0)
            return {
                "fundamental_gross_margin":       _clip(row["gross_margin"],         -2.0,  2.0),
                "fundamental_operating_margin":   _clip(row["operating_margin"],     -5.0,  5.0),
                "fundamental_net_margin":         _clip(row["net_margin"],           -5.0,  5.0),
                "fundamental_fcf_margin":         _clip(row["fcf_margin"],           -5.0,  5.0),
                "fundamental_rd_intensity":       _clip(row["rd_intensity"],          0.0,  5.0),
                "fundamental_revenue_growth_yoy": _clip(row["revenue_growth_yoy"],  -1.0, 10.0),
                "fundamental_revenue_growth_qoq": rev_growth_qoq,
                "fundamental_debt_to_equity":     _clip(row["debt_to_equity"],      -10.0, 10.0),
            }

        def lookup(as_of: datetime) -> dict[str, float]:
            ts = pd.Timestamp(as_of).replace(tzinfo=None)

            a = state["a"]
            while a + 1 < len(annual_filed) and annual_filed[a + 1] <= ts:
                a += 1
            state["a"] = a

            if a < 0:
                return {}

            q = state["q"]
            while q + 1 < len(qoq_filed) and qoq_filed[q + 1] <= ts:
                q += 1
            state["q"] = q

            return _row_to_dict(annual_df.iloc[a], q)

        return lookup


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _clip(val: float, lo: float, hi: float) -> float:
    if math.isnan(val) or math.isinf(val):
        return 0.0
    return max(lo, min(hi, val))


def _safe_ratio(num: float, den: float) -> float:
    if math.isnan(num) or math.isnan(den) or den == 0:
        return float("nan")
    return num / den


def _extract_duration_series(records: list[dict], lo: int, hi: int) -> pd.DataFrame:
    rows = []
    for rec in records:
        filed = rec.get("filed")
        period_start = rec.get("period_start")
        period_end = rec.get("period_end")
        if not filed or not period_start or not period_end:
            continue
        days = (pd.Timestamp(period_end) - pd.Timestamp(period_start)).days
        if not (lo <= days <= hi):
            continue
        rows.append({
            "period_end": pd.Timestamp(period_end),
            "filed":      pd.Timestamp(filed),
            "value":      float(rec["value"]),
        })
    if not rows:
        return pd.DataFrame(columns=["period_end", "filed", "value"])
    df = pd.DataFrame(rows)
    df = df.sort_values("filed").drop_duplicates("period_end", keep="last")
    return df.sort_values("period_end").reset_index(drop=True)


def _extract_instant_series(records: list[dict]) -> pd.DataFrame:
    rows = []
    for rec in records:
        filed = rec.get("filed")
        period_end = rec.get("period_end")
        period_start = rec.get("period_start")
        if not filed or not period_end:
            continue
        if period_start:
            days = (pd.Timestamp(period_end) - pd.Timestamp(period_start)).days
            if days >= 10:
                continue
        rows.append({
            "period_end": pd.Timestamp(period_end),
            "filed":      pd.Timestamp(filed),
            "value":      float(rec["value"]),
        })
    if not rows:
        return pd.DataFrame(columns=["period_end", "filed", "value"])
    df = pd.DataFrame(rows)
    df = df.sort_values("filed").drop_duplicates("period_end", keep="last")
    return df.sort_values("period_end").reset_index(drop=True)


def _lookup_nearest(df: pd.DataFrame, target: pd.Timestamp, tol_days: int = 180) -> float:
    if df.empty:
        return float("nan")
    delta = (df["period_end"] - target).abs()
    idx = delta.idxmin()
    if delta[idx].days > tol_days:
        return float("nan")
    return float(df.loc[idx, "value"])


def _lookup_instant_as_of(df: pd.DataFrame, as_of_filed: pd.Timestamp) -> float:
    if df.empty:
        return float("nan")
    mask = df["filed"] <= as_of_filed
    if not mask.any():
        return float("nan")
    return float(df[mask].iloc[-1]["value"])


def _build_ratio_series(data: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    concepts = data.get("concepts", {})
    lo_a, hi_a = _ANNUAL_DAYS
    lo_q, hi_q = _QUARTERLY_DAYS

    rev_a   = _extract_duration_series(concepts.get("revenue", []),             lo_a, hi_a)
    gp_a    = _extract_duration_series(concepts.get("gross_profit", []),        lo_a, hi_a)
    oi_a    = _extract_duration_series(concepts.get("operating_income", []),    lo_a, hi_a)
    ni_a    = _extract_duration_series(concepts.get("net_income", []),          lo_a, hi_a)
    ocf_a   = _extract_duration_series(concepts.get("operating_cash_flow", []), lo_a, hi_a)
    capex_a = _extract_duration_series(concepts.get("capex", []),               lo_a, hi_a)
    rd_a    = _extract_duration_series(concepts.get("rd_expense", []),          lo_a, hi_a)

    equity_i = _extract_instant_series(concepts.get("stockholders_equity", []))
    debt_i   = _extract_instant_series(concepts.get("long_term_debt", []))
    if equity_i.empty:
        equity_i = _extract_duration_series(concepts.get("stockholders_equity", []), lo_a, hi_a)
    if debt_i.empty:
        debt_i = _extract_duration_series(concepts.get("long_term_debt", []), lo_a, hi_a)

    if rev_a.empty:
        return pd.DataFrame(), pd.DataFrame()

    annual_rows = []
    for i, row in rev_a.iterrows():
        period_end = row["period_end"]
        filed      = row["filed"]
        revenue    = row["value"]
        if revenue == 0:
            continue

        gp    = _lookup_nearest(gp_a,    period_end)
        oi    = _lookup_nearest(oi_a,    period_end)
        ni    = _lookup_nearest(ni_a,    period_end)
        ocf   = _lookup_nearest(ocf_a,   period_end)
        capex = _lookup_nearest(capex_a, period_end)
        rd    = _lookup_nearest(rd_a,    period_end)
        eq    = _lookup_instant_as_of(equity_i, filed)
        debt  = _lookup_instant_as_of(debt_i,   filed)

        fcf = ocf - capex if not (math.isnan(ocf) or math.isnan(capex)) else float("nan")
        prior_revenue = float(rev_a.loc[i - 1, "value"]) if i > 0 else float("nan")
        rev_yoy = _safe_ratio(revenue - prior_revenue, abs(prior_revenue)) if not math.isnan(prior_revenue) else float("nan")

        annual_rows.append({
            "filed":              filed,
            "period_end":         period_end,
            "gross_margin":       _safe_ratio(gp,   revenue),
            "operating_margin":   _safe_ratio(oi,   revenue),
            "net_margin":         _safe_ratio(ni,   revenue),
            "fcf_margin":         _safe_ratio(fcf,  revenue),
            "rd_intensity":       _safe_ratio(rd,   revenue),
            "revenue_growth_yoy": rev_yoy,
            "debt_to_equity":     _safe_ratio(debt, eq),
        })

    annual_df = (
        pd.DataFrame(annual_rows).sort_values("filed").reset_index(drop=True)
        if annual_rows else pd.DataFrame()
    )

    rev_q = _extract_duration_series(concepts.get("revenue", []), lo_q, hi_q)
    qoq_rows = []
    for i, row in rev_q.iterrows():
        if i == 0:
            continue
        current = row["value"]
        prior   = float(rev_q.loc[i - 1, "value"])
        if prior == 0:
            continue
        qoq_rows.append({
            "filed":               row["filed"],
            "revenue_growth_qoq":  (current - prior) / abs(prior),
        })
    qoq_df = (
        pd.DataFrame(qoq_rows).sort_values("filed").reset_index(drop=True)
        if qoq_rows else pd.DataFrame()
    )

    return annual_df, qoq_df
