from __future__ import annotations

import logging
from pathlib import Path

import boto3
import numpy as np

from feature_eng.indicators import FEATURE_COLUMNS
from shared.db.client import connect
from shared.db.feature_vector_repo import FeatureVectorRepository

logger = logging.getLogger(__name__)


class Trainer:
    def __init__(
        self,
        database_url: str,
        model_dir: str,
        model_version: str,
        horizons: list[str],
        test_split: float = 0.2,
        min_samples: int = 100,
        s3_bucket: str = "",
        s3_prefix: str = "models",
        s3_endpoint_url: str | None = None,
        s3_region: str = "us-east-1",
    ) -> None:
        self._database_url = database_url
        self._model_dir = Path(model_dir)
        self._model_version = model_version
        self._horizons = horizons
        self._test_split = test_split
        self._min_samples = min_samples
        self._s3_bucket = s3_bucket
        self._s3_prefix = s3_prefix
        self._s3_endpoint_url = s3_endpoint_url
        self._s3_region = s3_region

    async def run(self) -> None:
        import xgboost as xgb
        from sklearn.metrics import mean_absolute_error, mean_squared_error

        self._model_dir.mkdir(parents=True, exist_ok=True)

        for horizon in self._horizons:
            X_chunks, y_chunks = [], []
            async with connect(self._database_url) as conn:
                async for X_batch, y_batch in FeatureVectorRepository(conn).iter_labeled_xy(
                    horizon, FEATURE_COLUMNS
                ):
                    X_chunks.append(X_batch)
                    y_chunks.append(y_batch)

            if not X_chunks:
                logger.warning("training.skip horizon=%s reason=no_data", horizon)
                continue

            X = np.concatenate(X_chunks, axis=0)
            y = np.concatenate(y_chunks, axis=0)

            if len(X) < self._min_samples:
                logger.warning(
                    "training.skip horizon=%s samples=%d min=%d",
                    horizon, len(X), self._min_samples,
                )
                continue

            logger.info("training.start horizon=%s samples=%d", horizon, len(X))

            split = int(len(X) * (1 - self._test_split))
            X_train, X_test = X[:split], X[split:]
            y_train, y_test = y[:split], y[split:]

            dtrain = xgb.DMatrix(X_train, label=y_train, feature_names=FEATURE_COLUMNS)
            dtest = xgb.DMatrix(X_test, label=y_test, feature_names=FEATURE_COLUMNS)

            model = xgb.train(
                {
                    "objective": "reg:squarederror",
                    "max_depth": 6,
                    "learning_rate": 0.05,
                    "subsample": 0.8,
                    "colsample_bytree": 0.8,
                    "seed": 42,
                },
                dtrain,
                num_boost_round=300,
                evals=[(dtest, "test")],
                verbose_eval=50,
            )

            y_pred = model.predict(dtest)
            rmse = float(mean_squared_error(y_test, y_pred) ** 0.5)
            mae = float(mean_absolute_error(y_test, y_pred))
            dir_acc = float(np.mean(np.sign(y_pred) == np.sign(y_test)))

            logger.info(
                "training.metrics horizon=%s rmse=%.4f mae=%.4f dir_acc=%.4f",
                horizon, rmse, mae, dir_acc,
            )

            out_path = self._model_dir / f"xgb_{horizon}.json"
            model.save_model(str(out_path))
            logger.info("training.saved horizon=%s path=%s version=%s", horizon, out_path, self._model_version)

            if self._s3_bucket:
                self._upload(out_path, horizon)

    def _upload(self, local_path: Path, horizon: str) -> None:
        s3_key = f"{self._s3_prefix}/xgb_{horizon}.json"
        try:
            client = boto3.client(
                "s3",
                region_name=self._s3_region,
                endpoint_url=self._s3_endpoint_url,
            )
            client.upload_file(str(local_path), self._s3_bucket, s3_key)
            logger.info("training.s3_upload horizon=%s bucket=%s key=%s", horizon, self._s3_bucket, s3_key)
        except Exception as exc:
            logger.error("training.s3_upload_error horizon=%s error=%s", horizon, exc)
