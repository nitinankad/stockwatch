from __future__ import annotations

import logging
from pathlib import Path

import numpy as np

from shared.db.client import connect
from shared.db.feature_vector_repo import FeatureVectorRepository
from shared.db.prediction_log_repo import PredictionLogRepository
from shared.models.prediction_log import PredictionLog
from shared.queue import RabbitMQQueue

from feature_eng.indicators import FEATURE_COLUMNS

logger = logging.getLogger(__name__)


class PredictionWorker:
    def __init__(
        self,
        queue: RabbitMQQueue,
        database_url: str,
        model_dir: str,
        model_version: str,
    ) -> None:
        self._queue = queue
        self._database_url = database_url
        self._model_dir = Path(model_dir)
        self._model_version = model_version
        self._model_cache: dict[str, object] = {}

    async def run(self) -> None:
        logger.info("prediction.worker.start model_dir=%s", self._model_dir)
        async for message, payload in self._queue.consume():
            fv_id = payload.get("feature_vector_id")
            ticker = payload.get("ticker", "")
            horizon = payload.get("prediction_horizon", "")
            try:
                await self._predict(fv_id, ticker, horizon)
                await message.ack()
            except Exception as exc:
                logger.exception(
                    "prediction.worker.error fv_id=%s error=%s", fv_id, exc
                )
                await message.nack(requeue=True)

    async def _predict(self, fv_id: int, ticker: str, horizon: str) -> None:
        model = self._load_model(horizon)
        if model is None:
            logger.warning(
                "prediction.skip fv_id=%s horizon=%s reason=no_model", fv_id, horizon
            )
            return

        async with connect(self._database_url) as conn:
            fv = await FeatureVectorRepository(conn).get_by_id(fv_id)
            if fv is None:
                logger.warning("prediction.skip fv_id=%s reason=not_found", fv_id)
                return

            x = np.array(
                [[fv.features.get(col, 0.0) for col in FEATURE_COLUMNS]], dtype=np.float32
            )
            import xgboost as xgb
            dmatrix = xgb.DMatrix(x, feature_names=FEATURE_COLUMNS)
            predicted_pct = float(model.predict(dmatrix)[0])
            direction = "bullish" if predicted_pct >= 0 else "bearish"

            log = PredictionLog(
                feature_vector_id=fv_id,
                ticker=ticker,
                model_version=self._model_version,
                predicted_pct_change=predicted_pct,
                derived_direction=direction,
            )
            log_id = await PredictionLogRepository(conn).insert(log)
            logger.info(
                "prediction.done fv_id=%s log_id=%s ticker=%s horizon=%s pct=%.4f dir=%s",
                fv_id, log_id, ticker, horizon, predicted_pct, direction,
            )

    def _load_model(self, horizon: str) -> object | None:
        if horizon in self._model_cache:
            return self._model_cache[horizon]
        path = self._model_dir / f"xgb_{horizon}.json"
        if not path.exists():
            return None
        try:
            import xgboost as xgb
            model = xgb.Booster()
            model.load_model(str(path))
            self._model_cache[horizon] = model
            logger.info("prediction.model_loaded horizon=%s path=%s", horizon, path)
            return model
        except Exception as exc:
            logger.error("prediction.model_load_error horizon=%s error=%s", horizon, exc)
            return None
