"""Tests for chronological and unseen-player data partitioning."""

import pandas as pd
import pytest

from src.temporal_splits import DataSplitter


@pytest.fixture
def sample_feature_df():
    data = []
    # Seasons 2018 to 2023
    for s in range(2018, 2024):
        for pid in range(1, 21):
            data.append(
                {
                    "player_id": pid,
                    "season": s,
                    "valuation_reference_date": f"{s + 1}-06-01",
                    "historical_market_value": 1000000 * pid,
                    "minutes_played": 1500,
                }
            )
    return pd.DataFrame(data)


def test_chronological_split_strict_ordering(sample_feature_df):
    splitter = DataSplitter(train_max_season=2020, val_season=2021, test_season=2022)
    train_df, val_df, test_df, meta = splitter.chronological_split(sample_feature_df)

    assert meta.train_seasons == [2018, 2019, 2020]
    assert meta.val_seasons == [2021]
    assert meta.test_seasons == [2022, 2023]

    assert meta.train_date_max < meta.val_date_min
    assert meta.val_date_max < meta.test_date_min
    assert len(train_df) + len(val_df) + len(test_df) == len(sample_feature_df)


def test_unseen_player_split_zero_leakage(sample_feature_df):
    splitter = DataSplitter()
    train_df, test_df = splitter.unseen_player_split(sample_feature_df, test_ratio=0.25, random_state=42)

    train_players = set(train_df["player_id"])
    test_players = set(test_df["player_id"])

    intersection = train_players.intersection(test_players)
    assert len(intersection) == 0, f"Found leaked players: {intersection}"
    assert len(train_players) + len(test_players) == sample_feature_df["player_id"].nunique()


def test_empty_split_exception():
    empty_df = pd.DataFrame({"player_id": [], "season": [], "valuation_reference_date": []})
    splitter = DataSplitter()
    with pytest.raises(ValueError, match="Training set is empty"):
        splitter.chronological_split(empty_df)
