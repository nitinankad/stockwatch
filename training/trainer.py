from __future__ import annotations

import logging
from pathlib import Path

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
    ) -> None:
        self._database_url = database_url
        self._model_dir = Path(model_dir)
        self._model_version = model_version
        self._horizons = horizons
        self._test_split = test_split
        self._min_samples = min_samples

    async def run(self) -> None:
        import xgboost as xgb
        from sklearn.metrics import mean_absolute_error, mean_squared_error
        from sklearn.model_selection import train_test_split

        self._model_dir.mkdir(parents=True, exist_ok=True)

        for horizon in self._horizons:
            async with connect(self._database_url) as conn:
                vectors = await FeatureVectorRepository(conn).get_labeled(horizon)

            if len(vectors) < self._min_samples:
                logger.warning(
                    "training.skip horizon=%s samples=%d min=%d",
                    horizon, len(vectors), self._min_samples,
                )
                continue

            logger.info("training.start horizon=%s samples=%d", horizon, len(vectors))

            X = np.array(
                [[v.features.get(col, 0.0) for col in FEATURE_COLUMNS] for v in vectors],
                dtype=np.float32,
            )
            y = np.array([float(v.actual_pct_change) for v in vectors], dtype=np.float32)

            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=self._test_split, random_state=42
            )

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
