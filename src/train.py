"""Model training and architecture comparison engine.

Trains and evaluates Scikit-learn candidate models:
1. DummyRegressor
2. Linear Regression
3. Ridge Regression
4. Random Forest Regressor
5. HistGradientBoostingRegressor

Compares Model A (Global Baseline), Model B (Competition-Aware), and Model C
(Competition-Adjusted), evaluating raw vs log1p target transformations.
"""

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, median_absolute_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, RobustScaler

from config.settings import (
    DEFAULT_RANDOM_STATE,
    MODELS_DIR,
    PROCESSED_DATA_DIR,
    TARGET_COLUMN,
)
from src.temporal_splits import DataSplitter

logger = logging.getLogger(__name__)

# Feature sets definition
MODEL_A_NUMERICS = [
    "age_at_reference_date",
    "appearances",
    "minutes_played",
    "goals",
    "assists",
    "goals_per_90",
    "assists_per_90",
    "cards",
    "cards_per_90",
    "minutes_per_appearance",
    "height_in_cm",
    "previous_market_value",
    "has_previous_valuation",
]

MODEL_A_CATEGORICALS = [
    "position",
    "sub_position",
    "foot",
]

MODEL_B_ADDITIONAL_NUMERICS = [
    "competition_strength",
    "competition_mean_elo",
    "competition_top4_strength",
    "competition_spread_elo",
    "club_elo",
    "league_goals_per_match",
    "league_cards_per_match",
    "competitive_balance_index",
    "club_revenue_eur",
    "league_average_revenue_eur",
    "has_club_financials",
    "has_league_financials",
    "source_coverage_score",
]

MODEL_B_ADDITIONAL_CATEGORICALS = [
    "competition_id",
    "country_of_citizenship",
    "financial_aggregation_level",
]

MODEL_B_NUMERICS = MODEL_A_NUMERICS + MODEL_B_ADDITIONAL_NUMERICS
MODEL_B_CATEGORICALS = MODEL_A_CATEGORICALS + MODEL_B_ADDITIONAL_CATEGORICALS


def create_preprocessor(numeric_cols: list[str], categorical_cols: list[str]) -> ColumnTransformer:
    """Build leakage-safe preprocessing pipeline for numeric and categorical features."""
    num_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", RobustScaler()),
        ]
    )
    cat_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="constant", fill_value="Unknown")),
            ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
        ]
    )
    preprocessor = ColumnTransformer(
        transformers=[
            ("num", num_pipeline, numeric_cols),
            ("cat", cat_pipeline, categorical_cols),
        ]
    )
    return preprocessor


def evaluate_predictions(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    """Compute standard metrics in true euros."""
    # Ensure non-negative predictions
    y_pred_clipped = np.clip(y_pred, a_min=10000.0, a_max=None)
    mae = float(mean_absolute_error(y_true, y_pred_clipped))
    rmse = float(np.sqrt(mean_squared_error(y_true, y_pred_clipped)))
    med_ae = float(median_absolute_error(y_true, y_pred_clipped))
    r2 = float(r2_score(y_true, y_pred_clipped))
    return {
        "mae_eur": round(mae, 2),
        "rmse_eur": round(rmse, 2),
        "median_ae_eur": round(med_ae, 2),
        "r2": round(r2, 4),
    }


class ModelTrainer:
    """Trains and benchmarks Scikit-learn pipelines with out-of-time validation."""

    def __init__(
        self,
        data_path: Path | None = None,
        models_dir: Path = MODELS_DIR,
        random_state: int = DEFAULT_RANDOM_STATE,
    ) -> None:
        self.data_path = data_path or (PROCESSED_DATA_DIR / "player_season_features.parquet")
        self.models_dir = models_dir
        self.random_state = random_state
        self.models_dir.mkdir(parents=True, exist_ok=True)

    def train_and_compare(self) -> dict[str, Any]:
        """Execute full training and benchmarking workflow."""
        logger.info("Loading processed dataset from %s...", self.data_path)
        df = pd.read_parquet(self.data_path)

        splitter = DataSplitter()
        train_df, val_df, test_df, meta = splitter.chronological_split(df)
        logger.info(
            "Training set: %d rows, Validation set: %d rows, Test set: %d rows",
            len(train_df),
            len(val_df),
            len(test_df),
        )

        y_train = train_df[TARGET_COLUMN].values
        y_val = val_df[TARGET_COLUMN].values
        y_train_log = np.log1p(y_train)

        # Baseline DummyRegressor
        dummy = DummyRegressor(strategy="median")
        dummy.fit(train_df, y_train)
        dummy_preds = dummy.predict(val_df)
        dummy_metrics = evaluate_predictions(y_val, dummy_preds)
        baseline_mae = dummy_metrics["mae_eur"]
        logger.info(
            "Baseline DummyRegressor (Median): MAE=€%s, RMSE=€%s, R2=%s",
            f"{baseline_mae:,.2f}",
            f"{dummy_metrics['rmse_eur']:,.2f}",
            dummy_metrics["r2"],
        )

        results: dict[str, Any] = {
            "trained_at": datetime.now(UTC).isoformat(),
            "split_metadata": meta.__dict__,
            "baseline_metrics": dummy_metrics,
            "models": {},
        }

        # Model configs to evaluate: (name, architecture, num_cols, cat_cols, use_log_target, estimator)
        experiments = [
            # Model A: Global Baseline (Linear)
            (
                "Model_A_Linear",
                "Model A (Global Baseline)",
                MODEL_A_NUMERICS,
                MODEL_A_CATEGORICALS,
                True,
                LinearRegression(),
            ),
            # Model A: Ridge
            (
                "Model_A_Ridge",
                "Model A (Global Baseline)",
                MODEL_A_NUMERICS,
                MODEL_A_CATEGORICALS,
                True,
                Ridge(alpha=10.0, random_state=self.random_state),
            ),
            # Model A: HistGradientBoosting
            (
                "Model_A_HistGradientBoosting",
                "Model A (Global Baseline)",
                MODEL_A_NUMERICS,
                MODEL_A_CATEGORICALS,
                True,
                HistGradientBoostingRegressor(max_iter=150, max_depth=8, random_state=self.random_state),
            ),
            # Model B: Competition-Aware Ridge
            (
                "Model_B_Ridge",
                "Model B (Competition-Aware)",
                MODEL_B_NUMERICS,
                MODEL_B_CATEGORICALS,
                True,
                Ridge(alpha=10.0, random_state=self.random_state),
            ),
            # Model B: Competition-Aware HistGradientBoosting
            (
                "Model_B_HistGradientBoosting",
                "Model B (Competition-Aware)",
                MODEL_B_NUMERICS,
                MODEL_B_CATEGORICALS,
                True,
                HistGradientBoostingRegressor(
                    max_iter=200, max_depth=9, min_samples_leaf=30, random_state=self.random_state
                ),
            ),
            # Model B: Random Forest
            (
                "Model_B_RandomForest",
                "Model B (Competition-Aware)",
                MODEL_B_NUMERICS,
                MODEL_B_CATEGORICALS,
                True,
                RandomForestRegressor(n_estimators=100, max_depth=14, n_jobs=-1, random_state=self.random_state),
            ),
            # Model C: Competition-Adjusted Gradient Boosting (Hierarchical feature interaction)
            (
                "Model_C_CompetitionAdjusted_GBM",
                "Model C (Competition-Adjusted)",
                MODEL_B_NUMERICS,
                MODEL_B_CATEGORICALS,
                True,
                HistGradientBoostingRegressor(
                    max_iter=250,
                    max_depth=10,
                    learning_rate=0.08,
                    min_samples_leaf=25,
                    l2_regularization=1.5,
                    random_state=self.random_state,
                ),
            ),
        ]

        best_model_name = None
        best_val_mae = float("inf")
        best_pipeline = None

        for exp_id, arch, num_cols, cat_cols, use_log, estimator in experiments:
            logger.info("Training experiment %s (%s)...", exp_id, arch)
            preprocessor = create_preprocessor(num_cols, cat_cols)
            pipeline = Pipeline(
                steps=[
                    ("preprocessor", preprocessor),
                    ("regressor", estimator),
                ]
            )

            # Fit on training data
            target = y_train_log if use_log else y_train
            pipeline.fit(train_df, target)

            # Predict validation
            preds = pipeline.predict(val_df)
            if use_log:
                preds_eur = np.expm1(preds)
            else:
                preds_eur = preds

            metrics = evaluate_predictions(y_val, preds_eur)
            mae_rel_baseline = round((metrics["mae_eur"] / baseline_mae) * 100.0, 2)
            metrics["mae_relative_to_baseline_pct"] = mae_rel_baseline
            metrics["architecture"] = arch
            metrics["use_log_target"] = use_log

            logger.info(
                "  %s -> Val MAE: €%s, RMSE: €%s, R2: %s (%.1f%% of baseline)",
                exp_id,
                f"{metrics['mae_eur']:,.2f}",
                f"{metrics['rmse_eur']:,.2f}",
                metrics["r2"],
                mae_rel_baseline,
            )

            results["models"][exp_id] = {
                "metrics": metrics,
                "features_numeric": num_cols,
                "features_categorical": cat_cols,
            }

            if metrics["mae_eur"] < best_val_mae:
                best_val_mae = metrics["mae_eur"]
                best_model_name = exp_id
                best_pipeline = pipeline

        results["best_model_name"] = best_model_name
        results["best_val_mae_eur"] = best_val_mae
        logger.info("Best model selected by Validation MAE: %s (Val MAE: €%s)", best_model_name, f"{best_val_mae:,.2f}")

        # Save artifacts
        results_file = self.models_dir / "model_comparison_results.json"
        with open(results_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)

        # Save best pipeline
        best_artifact_path = self.models_dir / "best_value_predictor.joblib"
        best_meta = {
            "model_name": best_model_name,
            "version": "1.0.0",
            "saved_at": datetime.now(UTC).isoformat(),
            "best_val_mae_eur": best_val_mae,
            "features_numeric": results["models"][best_model_name]["features_numeric"],
            "features_categorical": results["models"][best_model_name]["features_categorical"],
            "use_log_target": True,
        }
        joblib.dump({"pipeline": best_pipeline, "metadata": best_meta}, best_artifact_path)
        logger.info("Saved best pipeline artifact to %s", best_artifact_path)

        return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    trainer = ModelTrainer()
    trainer.train_and_compare()
