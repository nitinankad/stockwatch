from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from shared.alpaca import AlpacaClient
from shared.db.client import connect
from shared.db.feature_vector_repo import FeatureVectorRepository
from shared.db.prediction_log_repo import PredictionLogRepository

logger = logging.getLogger(__name__)

# Minutes to wait after snapshot before exit price is considered final
HORIZON_MINUTES: dict[str, int] = {"1h": 60, "4h": 240, "1d": 390}


class ReconciliationService:
    def __init__(self, alpaca: AlpacaClient, database_url: str) -> None:
        self._alpaca = alpaca
        self._database_url = database_url

    async def run(self) -> None:
        now = datetime.now(timezone.utc)
        logger.info("reconciliation.start at=%s", now.isoformat())

        async with connect(self._database_url) as conn:
            rows = await PredictionLogRepository(conn).get_unresolved_with_context()

        if not rows:
            logger.info("reconciliation.nothing_to_resolve")
            return

        # Only process rows where the horizon has fully elapsed
        eligible = [
            r for r in rows
            if r["snapshot_timestamp"] + timedelta(minutes=HORIZON_MINUTES.get(r["prediction_horizon"], 60)) <= now
        ]
        logger.info("reconciliation.eligible count=%s / %s", len(eligible), len(rows))
        if not eligible:
            return

        tickers = list({r["ticker"] for r in eligible})
        earliest: datetime = min(r["snapshot_timestamp"] for r in eligible)
        latest: datetime = max(
            r["snapshot_timestamp"] + timedelta(minutes=HORIZON_MINUTES.get(r["prediction_horizon"], 60))
            for r in eligible
        )

        bars_by_ticker = await self._alpaca.get_bars(
            tickers,
            start=earliest - timedelta(minutes=5),
            end=latest + timedelta(minutes=5),
        )

        # Build minute-level price lookup per ticker
        price_lookup: dict[str, dict[datetime, float]] = {}
        for ticker, bars in bars_by_ticker.items():
            price_lookup[ticker] = {
                b.timestamp.replace(second=0, microsecond=0): float(b.close)
                for b in bars
            }

        resolved = 0
        async with connect(self._database_url) as conn:
            pl_repo = PredictionLogRepository(conn)
            fv_repo = FeatureVectorRepository(conn)

            for row in eligible:
                ticker = row["ticker"]
                horizon = row["prediction_horizon"]
                horizon_min = HORIZON_MINUTES.get(horizon, 60)
                snapshot = row["snapshot_timestamp"]
                exit_ts = snapshot + timedelta(minutes=horizon_min)

                lookup = price_lookup.get(ticker, {})
                entry_price = lookup.get(snapshot.replace(second=0, microsecond=0))
                exit_price = lookup.get(exit_ts.replace(second=0, microsecond=0))

                if entry_price is None or exit_price is None:
                    logger.warning(
                        "reconciliation.missing_price ticker=%s horizon=%s snapshot=%s",
                        ticker, horizon, snapshot.isoformat(),
                    )
                    continue

                actual_pct = (exit_price - entry_price) / entry_price * 100
                predicted_pct = float(row["predicted_pct_change"])
                error = predicted_pct - actual_pct

                await pl_repo.resolve(row["log_id"], actual_pct, error)
                await fv_repo.update_actual_pct_change(row["feature_vector_id"], actual_pct)
                resolved += 1
                logger.info(
                    "reconciliation.resolved ticker=%s horizon=%s actual=%.4f predicted=%.4f error=%.4f",
                    ticker, horizon, actual_pct, predicted_pct, error,
                )

        logger.info("reconciliation.done resolved=%s", resolved)
