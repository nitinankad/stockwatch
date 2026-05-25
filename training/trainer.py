from __future__ import annotations

import logging
from pathlib import Path

import boto3
import numpy as np

from feature_eng.indicators import FEATURE_COLUMNS
from shared.db.client import connect
from shared.db.feature_vector_repo import FeatureVectorRepository

logger = logging.getLogger(__name__)


def _compute_metrics(y_true: np.ndarray, y_pred: np.ndarray, total_samples: int = 0) -> dict:
    from sklearn.metrics import mean_absolute_error, mean_squared_error

    pred_up   = y_pred > 0
    pred_dn   = ~pred_up
    actual_up = y_true > 0
    confident = np.abs(y_pred) >= np.percentile(np.abs(y_pred), 75)

    return {
        "total_samples":       total_samples,
        "test_samples":        len(y_true),
        "rmse":                float(mean_squared_error(y_true, y_pred) ** 0.5),
        "mae":                 float(mean_absolute_error(y_true, y_pred)),
        "corr":                float(np.corrcoef(y_true, y_pred)[0, 1]) if len(y_true) > 1 else 0.0,
        "dir_acc":             float(np.mean(pred_up == actual_up)),
        "bullish_precision":   float(np.mean(actual_up[pred_up]))   if pred_up.any()   else float("nan"),
        "bearish_precision":   float(np.mean(~actual_up[pred_dn]))  if pred_dn.any()   else float("nan"),
        "bullish_count":       int(pred_up.sum()),
        "bearish_count":       int(pred_dn.sum()),
        "confident_threshold":  float(np.percentile(np.abs(y_pred), 75)),
        "confident_pct":        25.0,
        "confident_dir_acc":   float(np.mean((y_pred[confident] > 0) == (y_true[confident] > 0)))
                               if confident.any() else float("nan"),
    }


def _log_summary(results: list[tuple[str, int, dict]]) -> None:
    sep = "+" + "-" * 6 + "+" + ("-" * 10 + "+") * 2 + ("-" * 9 + "+") * 7
    header = (
        f"| {'Hz':4} | {'Total':>8} | {'Test':>8} | {'RMSE':>7} | {'MAE':>7} "
        f"| {'Corr':>7} | {'DirAcc':>7} | {'Bull%':>7} | {'Bear%':>7} | {'Conf%':>7} |"
    )
    logger.info("training.summary")
    logger.info(sep)
    logger.info(header)
    logger.info(sep)
    for horizon, best_round, m in results:
        conf_acc = m["confident_dir_acc"]
        bull = m["bullish_precision"]
        bear = m["bearish_precision"]
        logger.info(
            "| %-4s | %8d | %8d | %7.4f | %7.4f | %7.4f | %7.4f | %7.4f | %7.4f | %7.4f | (threshold=%.4f%% round=%d)",
            horizon,
            m["total_samples"],
            m["test_samples"],
            m["rmse"],
            m["mae"],
            m["corr"],
            m["dir_acc"],
            bull if bull == bull else 0.0,
            bear if bear == bear else 0.0,
            conf_acc if conf_acc == conf_acc else 0.0,
            m["confident_threshold"],
            best_round,
        )
    logger.info(sep)


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

        self._model_dir.mkdir(parents=True, exist_ok=True)
        results: list[tuple[str, int, dict]] = []

        async with connect(self._database_url) as conn:
            fv_repo = FeatureVectorRepository(conn)
            for horizon in self._horizons:
                X_chunks, y_chunks = [], []
                async for X_batch, y_batch in fv_repo.iter_labeled_xy(horizon, FEATURE_COLUMNS):
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
                        "max_depth": 4,
                        "learning_rate": 0.05,
                        "subsample": 0.8,
                        "colsample_bytree": 0.8,
                        "min_child_weight": 50,
                        "seed": 42,
                    },
                    dtrain,
                    num_boost_round=500,
                    evals=[(dtest, "test")],
                    verbose_eval=50,
                    early_stopping_rounds=20,
                )
                logger.info(
                    "training.best_round horizon=%s round=%d",
                    horizon, model.best_iteration,
                )

                y_pred = model.predict(dtest, iteration_range=(0, model.best_iteration + 1))
                metrics = _compute_metrics(y_test, y_pred, total_samples=len(X))
                results.append((horizon, model.best_iteration, metrics))

                out_path = self._model_dir / f"xgb_{horizon}.json"
                model.save_model(str(out_path))
                logger.info("training.saved horizon=%s path=%s version=%s", horizon, out_path, self._model_version)

                if self._s3_bucket:
                    self._upload(out_path, horizon)

        if results:
            _log_summary(results)

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
