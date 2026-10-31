"""Tests for join integrity, foreign key relations, and duplication prevention."""

import pandas as pd


def test_no_cartesian_target_duplication():
    # Synthetic test to verify that joining valuations with appearances
    # does NOT duplicate the valuation target across multiple matches in feature engineering
    vals = pd.DataFrame(
        {
            "player_id": [10, 10],
            "date": pd.to_datetime(["2023-01-15", "2023-06-01"]),
            "market_value_in_eur": [20_000_000, 25_000_000],
        }
    )
    apps = pd.DataFrame(
        {
            "game_id": [101, 102, 103],
            "player_id": [10, 10, 10],
            "club_id": [1, 1, 1],
            "competition_id": ["GB1", "GB1", "GB1"],
            "date": pd.to_datetime(["2023-02-01", "2023-03-01", "2023-04-01"]),
            "minutes_played": [90, 90, 90],
            "goals": [1, 0, 1],
            "assists": [0, 1, 0],
            "yellow_cards": [0, 0, 0],
            "red_cards": [0, 0, 0],
        }
    )

    # Pick canonical valuation (e.g. latest in season window)
    canonical_val = vals.sort_values("date").drop_duplicates(subset=["player_id"], keep="last")

    # Aggregate appearances strictly to 1 row per player-season
    perf = (
        apps.groupby(["player_id", "competition_id", "club_id"])
        .agg(
            appearances=("game_id", "count"),
            minutes_played=("minutes_played", "sum"),
            goals=("goals", "sum"),
            assists=("assists", "sum"),
        )
        .reset_index()
    )

    feature_row = perf.merge(canonical_val, on="player_id", how="inner")
    assert len(feature_row) == 1, "Should produce exactly 1 analytical row per player-season-competition-club"
    assert feature_row["market_value_in_eur"].iloc[0] == 25_000_000
    assert feature_row["appearances"].iloc[0] == 3
    assert feature_row["minutes_played"].iloc[0] == 270
    assert feature_row["goals"].iloc[0] == 2


def test_orphaned_join_handling():
    players = pd.DataFrame({"player_id": [1, 2], "name": ["P1", "P2"]})
    apps = pd.DataFrame({"player_id": [1, 2, 999], "game_id": [10, 20, 30]})

    merged = apps.merge(players, on="player_id", how="left")
    missing_players = merged[merged["name"].isna()]
    assert len(missing_players) == 1
    assert missing_players["player_id"].iloc[0] == 999
