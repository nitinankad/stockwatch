from __future__ import annotations

import logging
from pathlib import Path

import boto3
import numpy as np

from ingestion.feature_eng.indicators import FEATURE_COLUMNS
from shared.db.client import connect
from shared.db.feature_vector_repo import FeatureVectorRepository

logger = logging.getLogger(__name__)


def _compute_metrics(y_true: np.ndarray, y_prob: np.ndarray, total_samples: int = 0) -> dict:
    from sklearn.metrics import accuracy_score, log_loss, roc_auc_score

    y_true_bin = (y_true > 0).astype(int)
    y_pred_bin = (y_prob >= 0.5).astype(int)

    bull_mask  = y_pred_bin == 1
    bear_mask  = y_pred_bin == 0
    # High conviction: prob outside the 40–60% band
    hi_conf    = (y_prob > 0.60) | (y_prob < 0.40)

    bull_prec = (
        float(np.mean(y_true_bin[bull_mask])) if bull_mask.any() else float("nan")
    )
    bear_prec = (
        float(np.mean(1 - y_true_bin[bear_mask])) if bear_mask.any() else float("nan")
    )
    hi_acc = (
        float(accuracy_score(y_true_bin[hi_conf], y_pred_bin[hi_conf]))
        if hi_conf.any() else float("nan")
    )

    return {
        "total_samples":    total_samples,
        "test_samples":     len(y_true),
        "accuracy":         float(accuracy_score(y_true_bin, y_pred_bin)),
        "auc":              float(roc_auc_score(y_true_bin, y_prob)),
        "log_loss":         float(log_loss(y_true_bin, y_prob)),
        "bullish_precision": bull_prec,
        "bearish_precision": bear_prec,
        "bullish_count":    int(bull_mask.sum()),
        "bearish_count":    int(bear_mask.sum()),
        "bull_rate":        float(bull_mask.mean()),
        "hi_conf_count":    int(hi_conf.sum()),
        "hi_conf_accuracy": hi_acc,
    }


def _log_summary(results: list[tuple[str, int, dict]]) -> None:
    sep = "+" + "-" * 6 + "+" + ("-" * 10 + "+") * 2 + ("-" * 9 + "+") * 7
    header = (
        f"| {'Hz':4} | {'Total':>8} | {'Test':>8} | {'Acc':>7} | {'AUC':>7} "
        f"| {'LogLoss':>7} | {'Bull%':>7} | {'Bear%':>7} | {'HiConf':>7} | {'HiCAcc':>7} |"
    )
    logger.info("training.summary")
    logger.info(sep)
    logger.info(header)
    logger.info(sep)
    for horizon, best_round, m in results:
        bull = m["bullish_precision"]
        bear = m["bearish_precision"]
        hi   = m["hi_conf_accuracy"]
        logger.info(
            "| %-4s | %8d | %8d | %7.4f | %7.4f | %7.4f | %7.4f | %7.4f | %7d | %7.4f |"
            " (bull_rate=%.2f round=%d)",
            horizon,
            m["total_samples"],
            m["test_samples"],
            m["accuracy"],
            m["auc"],
            m["log_loss"],
            bull if bull == bull else 0.0,
            bear if bear == bear else 0.0,
            m["hi_conf_count"],
            hi   if hi   == hi   else 0.0,
            m["bull_rate"],
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
                async for X_batch, y_batch in fv_repo.iter_alpha_xy(horizon, FEATURE_COLUMNS):
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

                # Binarise: 1 = price went up, 0 = price went down or flat
                y_bin = (y > 0).astype(np.float32)

                pos = int(y_bin.sum())
                neg = len(y_bin) - pos
                logger.info(
                    "training.start horizon=%s samples=%d pos=%d neg=%d outperform_rate=%.2f"
                    " (y=stock_return-SPY_return, pos=stock_beat_SPY)",
                    horizon, len(X), pos, neg, pos / len(y_bin),
                )

                split = int(len(X) * (1 - self._test_split))
                X_train, X_test = X[:split], X[split:]
                y_train, y_test = y_bin[:split], y_bin[split:]

                dtrain = xgb.DMatrix(X_train, label=y_train, feature_names=FEATURE_COLUMNS)
                dtest  = xgb.DMatrix(X_test,  label=y_test,  feature_names=FEATURE_COLUMNS)

                model = xgb.train(
                    {
                        "objective":        "binary:logistic",
                        # AUC rewards discrimination (ranking up vs down), not calibration.
                        # Logloss plateaus when predictions cluster near the base rate and
                        # fires early stopping before the model finds any real signal.
                        "eval_metric":      "auc",
                        "max_depth":        5,
                        "learning_rate":    0.05,
                        "subsample":        0.8,
                        "colsample_bytree": 0.8,
                        "min_child_weight": 5,
                        # No scale_pos_weight: in a bull-market dataset positives are the
                        # majority, so neg/pos < 1 would downweight them and collapse every
                        # prediction to 0.5.  Let the natural class distribution guide the
                        # model — a slight bullish bias in output is correct for the data.
                        "seed":             42,
                    },
                    dtrain,
                    num_boost_round=500,
                    evals=[(dtest, "test")],
                    verbose_eval=50,
                    early_stopping_rounds=30,
                    maximize=True,   # AUC is maximised, not minimised
                )
                logger.info(
                    "training.best_round horizon=%s round=%d",
                    horizon, model.best_iteration,
                )

                y_prob = model.predict(dtest, iteration_range=(0, model.best_iteration + 1))
                # Pass original continuous y_test so metrics can re-binarise consistently
                metrics = _compute_metrics(y[split:], y_prob, total_samples=len(X))
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
