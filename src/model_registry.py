"""Model Registry module for managing serialized ML pipelines and metadata."""

import logging
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import joblib

from config.settings import MODELS_DIR

logger = logging.getLogger(__name__)


@dataclass
class ModelMetadata:
    model_name: str
    version: str
    saved_at: str
    best_val_mae_eur: float
    features_numeric: list[str]
    features_categorical: list[str]
    use_log_target: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ModelRegistry:
    """Manages model artifacts, versioning, and loading in models/."""

    def __init__(self, models_dir: Path = MODELS_DIR) -> None:
        self.models_dir = models_dir
        self.models_dir.mkdir(parents=True, exist_ok=True)

    def get_latest_model_path(self) -> Path:
        """Return path to active best model artifact."""
        best_path = self.models_dir / "best_value_predictor.joblib"
        if best_path.exists():
            return best_path
        # Look for any versioned joblib file
        joblibs = sorted(self.models_dir.glob("*.joblib"))
        if joblibs:
            return joblibs[-1]
        raise FileNotFoundError(f"No trained model artifact found in {self.models_dir}")

    def load_model(self, model_path: Path | None = None) -> tuple[Any, ModelMetadata]:
        """Load trained pipeline and its metadata."""
        target_path = model_path or self.get_latest_model_path()
        if not target_path.exists():
            raise FileNotFoundError(f"Artifact does not exist at {target_path}")

        logger.info("Loading model artifact from %s", target_path.name)
        payload = joblib.load(target_path)
        pipeline = payload["pipeline"]
        meta_dict = payload["metadata"]
        metadata = ModelMetadata(**meta_dict)
        return pipeline, metadata

    def list_available_models(self) -> list[dict[str, Any]]:
        """List all model artifacts in registry."""
        results = []
        for p in self.models_dir.glob("*.joblib"):
            try:
                data = joblib.load(p)
                meta = data.get("metadata", {})
                results.append({"path": str(p), "metadata": meta})
            except Exception as e:
                logger.warning("Could not read %s: %s", p.name, e)
        return results
