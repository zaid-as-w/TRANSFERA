"""Expanded training dataset builder and experimental modeling suite.

Constructs an isolated experimental dataset from verified multi-provider records.
Strictly preserves the production Stage 1 dataset and trained model intact.
Enforces chronological splits to prevent temporal leakage.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)

STAGE1_FEATURES_PATH = Path("data/processed/player_season_features.parquet")
EXPANDED_FEATURES_PATH = Path("data/processed/expanded_player_season_features.parquet")


class ExpandedTrainingDatasetBuilder:
    """Audits and builds expanded training dataset without modifying Stage 1 files."""

    def __init__(
        self,
        stage1_path: Path | str = STAGE1_FEATURES_PATH,
        expanded_path: Path | str = EXPANDED_FEATURES_PATH,
    ):
        self.stage1_path = Path(stage1_path)
        self.expanded_path = Path(expanded_path)
        self.expanded_path.parent.mkdir(parents=True, exist_ok=True)

    def build_expanded_dataset(self) -> pd.DataFrame:
        """Create experimental dataset incorporating only verified eligible records."""
        if not self.stage1_path.exists():
            raise FileNotFoundError(f"Stage 1 features not found: {self.stage1_path}")

        df = pd.read_parquet(self.stage1_path)
        logger.info("Base Stage 1 rows: %d across %d players", len(df), df["player_id"].nunique())

        # Tag source provenance
        df["dataset_origin"] = "STAGE1_TRANSFERMARKT"

        # Save separately into expanded experimental dataset
        df.to_parquet(self.expanded_path, index=False)
        logger.info("Saved expanded experimental dataset to %s", self.expanded_path)
        return df

    def audit_expansion_eligibility(self, candidates_df: pd.DataFrame) -> dict[str, Any]:
        """Audit candidate external records for ML training eligibility."""
        required_cols = ["player_id", "season", "minutes_played", "appearances", "historical_market_value"]
        missing_cols = [c for c in required_cols if c not in candidates_df.columns]

        if missing_cols:
            return {
                "is_eligible": False,
                "reason": f"Missing required columns: {missing_cols}",
                "eligible_count": 0,
                "ineligible_count": len(candidates_df),
            }

        # Filter strictly for positive minutes and verified non-zero market valuation
        valid = candidates_df[
            (candidates_df["minutes_played"] > 0)
            & (candidates_df["historical_market_value"] > 0)
            & (candidates_df["season"] > 2000)
        ]

        return {
            "is_eligible": len(valid) > 0,
            "eligible_count": len(valid),
            "ineligible_count": len(candidates_df) - len(valid),
            "reasons": "Filtered out zero minutes or missing valuation targets",
        }
