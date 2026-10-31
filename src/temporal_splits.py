"""Temporal and Player-Generalization Data Splitting Module.

Enforces strict chronological train/val/test splits to reflect real-world
forecasting scenarios without data leakage. Also supports unseen-player splits
to evaluate generalization to new players.
"""

import logging
from dataclasses import dataclass

import numpy as np
import pandas as pd

from config.settings import TEST_SEASON, TRAIN_SEASONS_MAX, VAL_SEASON

logger = logging.getLogger(__name__)


@dataclass
class SplitMetadata:
    train_count: int
    val_count: int
    test_count: int
    train_seasons: list[int]
    val_seasons: list[int]
    test_seasons: list[int]
    train_date_min: str
    train_date_max: str
    val_date_min: str
    val_date_max: str
    test_date_min: str
    test_date_max: str
    train_unique_players: int
    val_unique_players: int
    test_unique_players: int


class DataSplitter:
    """Provides leakage-safe chronological and player-grouped data partitioning."""

    def __init__(
        self,
        train_max_season: int = TRAIN_SEASONS_MAX,
        val_season: int = VAL_SEASON,
        test_season: int = TEST_SEASON,
    ) -> None:
        self.train_max_season = train_max_season
        self.val_season = val_season
        self.test_season = test_season

    def chronological_split(
        self,
        df: pd.DataFrame,
    ) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, SplitMetadata]:
        """Split data chronologically by season.

        Train: season <= train_max_season
        Val: season == val_season
        Test: season >= test_season
        """
        train_df = df[df["season"] <= self.train_max_season].copy()
        val_df = df[df["season"] == self.val_season].copy()
        test_df = df[df["season"] >= self.test_season].copy()

        # Sanity assertions
        if train_df.empty:
            raise ValueError(f"Training set is empty for seasons <= {self.train_max_season}")
        if val_df.empty:
            raise ValueError(f"Validation set is empty for season {self.val_season}")
        if test_df.empty:
            raise ValueError(f"Test set is empty for seasons >= {self.test_season}")

        def _fmt_date(s: pd.Series, func: str) -> str:
            dates = pd.to_datetime(s, errors="coerce").dropna()
            if dates.empty:
                return "N/A"
            dt = dates.min() if func == "min" else dates.max()
            return dt.strftime("%Y-%m-%d")

        meta = SplitMetadata(
            train_count=len(train_df),
            val_count=len(val_df),
            test_count=len(test_df),
            train_seasons=sorted(train_df["season"].unique().tolist()),
            val_seasons=sorted(val_df["season"].unique().tolist()),
            test_seasons=sorted(test_df["season"].unique().tolist()),
            train_date_min=_fmt_date(train_df["valuation_reference_date"], "min"),
            train_date_max=_fmt_date(train_df["valuation_reference_date"], "max"),
            val_date_min=_fmt_date(val_df["valuation_reference_date"], "min"),
            val_date_max=_fmt_date(val_df["valuation_reference_date"], "max"),
            test_date_min=_fmt_date(test_df["valuation_reference_date"], "min"),
            test_date_max=_fmt_date(test_df["valuation_reference_date"], "max"),
            train_unique_players=int(train_df["player_id"].nunique()),
            val_unique_players=int(val_df["player_id"].nunique()),
            test_unique_players=int(test_df["player_id"].nunique()),
        )

        logger.info(
            "Chronological Split: Train=%d (%s to %s), Val=%d (%s), Test=%d (%s)",
            meta.train_count,
            meta.train_seasons[0],
            meta.train_seasons[-1],
            meta.val_count,
            meta.val_seasons,
            meta.test_count,
            meta.test_seasons,
        )
        return train_df, val_df, test_df, meta

    def unseen_player_split(
        self,
        df: pd.DataFrame,
        test_ratio: float = 0.2,
        random_state: int = 42,
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        """Split dataframe keeping all observations of a player exclusively in either train or test."""
        unique_players = df["player_id"].drop_duplicates().values
        rng = np.random.default_rng(random_state)
        shuffled = rng.permutation(unique_players)

        split_idx = int(len(shuffled) * (1.0 - test_ratio))
        train_pids = set(shuffled[:split_idx])
        test_pids = set(shuffled[split_idx:])

        train_df = df[df["player_id"].isin(train_pids)].copy()
        test_df = df[df["player_id"].isin(test_pids)].copy()

        assert len(set(train_df["player_id"]).intersection(set(test_df["player_id"]))) == 0, (
            "Data leakage in unseen player split!"
        )
        logger.info(
            "Unseen Player Split: Train=%d rows (%d players), Test=%d rows (%d players)",
            len(train_df),
            len(train_pids),
            len(test_df),
            len(test_pids),
        )
        return train_df, test_df


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    from config.settings import PROCESSED_DATA_DIR

    feat_path = PROCESSED_DATA_DIR / "player_season_features.parquet"
    if feat_path.exists():
        df = pd.read_parquet(feat_path)
        splitter = DataSplitter()
        tr, va, te, meta = splitter.chronological_split(df)
        print("\nSplit Metadata:")
        print(meta)
