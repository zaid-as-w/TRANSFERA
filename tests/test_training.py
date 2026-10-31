"""Tests for model training pipelines, metric calculations, and serialization."""

import joblib
import numpy as np
import pandas as pd
from sklearn.dummy import DummyRegressor
from sklearn.pipeline import Pipeline

from src.model_registry import ModelRegistry
from src.train import (
    MODEL_A_CATEGORICALS,
    MODEL_A_NUMERICS,
    create_preprocessor,
    evaluate_predictions,
)


def test_evaluate_predictions_metrics():
    y_true = np.array([1_000_000, 5_000_000, 10_000_000, 20_000_000])
    y_pred = np.array([1_200_000, 4_800_000, 9_500_000, 21_000_000])

    metrics = evaluate_predictions(y_true, y_pred)
    assert "mae_eur" in metrics
    assert "rmse_eur" in metrics
    assert "median_ae_eur" in metrics
    assert "r2" in metrics
    assert metrics["mae_eur"] > 0
    assert metrics["r2"] > 0.95


def test_preprocessor_pipeline_fit_transform():
    preprocessor = create_preprocessor(MODEL_A_NUMERICS, MODEL_A_CATEGORICALS)
    synthetic_data = pd.DataFrame(
        {
            "age_at_reference_date": [21.0, 25.5, 30.0],
            "appearances": [20, 30, 15],
            "minutes_played": [1500, 2600, 1200],
            "goals": [5, 12, 1],
            "assists": [3, 8, 2],
            "goals_per_90": [0.3, 0.41, 0.07],
            "assists_per_90": [0.18, 0.27, 0.15],
            "cards": [2, 4, 1],
            "cards_per_90": [0.12, 0.14, 0.07],
            "minutes_per_appearance": [75.0, 86.6, 80.0],
            "height_in_cm": [180.0, 185.0, 178.0],
            "previous_market_value": [5000000.0, 15000000.0, 8000000.0],
            "has_previous_valuation": [True, True, True],
            "position": ["Attack", "Attack", "Midfield"],
            "sub_position": ["Left Winger", "Centre-Forward", "Central Midfield"],
            "foot": ["Right", "Both", "Left"],
        }
    )
    transformed = preprocessor.fit_transform(synthetic_data)
    assert transformed.shape[0] == 3
    assert transformed.shape[1] >= len(MODEL_A_NUMERICS)


def test_model_loading_and_prediction(tmp_path):
    pipeline = Pipeline(
        [
            ("preprocessor", create_preprocessor(MODEL_A_NUMERICS, MODEL_A_CATEGORICALS)),
            ("dummy", DummyRegressor(strategy="median")),
        ]
    )
    synthetic_data = pd.DataFrame(
        {
            "age_at_reference_date": [21.0, 25.5],
            "appearances": [20, 30],
            "minutes_played": [1500, 2600],
            "goals": [5, 12],
            "assists": [3, 8],
            "goals_per_90": [0.3, 0.41],
            "assists_per_90": [0.18, 0.27],
            "cards": [2, 4],
            "cards_per_90": [0.12, 0.14],
            "minutes_per_appearance": [75.0, 86.6],
            "height_in_cm": [180.0, 185.0],
            "previous_market_value": [5000000.0, 15000000.0],
            "has_previous_valuation": [True, True],
            "position": ["Attack", "Attack"],
            "sub_position": ["Left Winger", "Centre-Forward"],
            "foot": ["Right", "Both"],
        }
    )
    y = np.array([5000000, 15000000])
    pipeline.fit(synthetic_data, y)

    artifact_path = tmp_path / "test_model.joblib"
    meta = {
        "model_name": "TestDummy",
        "version": "1.0.0",
        "saved_at": "2026-10-29",
        "best_val_mae_eur": 5000.0,
        "features_numeric": MODEL_A_NUMERICS,
        "features_categorical": MODEL_A_CATEGORICALS,
        "use_log_target": False,
    }
    joblib.dump({"pipeline": pipeline, "metadata": meta}, artifact_path)

    registry = ModelRegistry(models_dir=tmp_path)
    loaded_pipeline, loaded_meta = registry.load_model(artifact_path)
    assert loaded_meta.model_name == "TestDummy"

    preds = loaded_pipeline.predict(synthetic_data)
    assert len(preds) == 2
