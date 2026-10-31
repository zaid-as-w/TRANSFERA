"""Tests for data validation and constraint verification."""

import pandas as pd

from src.data_validation import DataValidator


def test_validator_detects_duplicates(tmp_path):
    # Setup synthetic raw dir with duplicates in players
    players_df = pd.DataFrame(
        {
            "player_id": [101, 101, 102],
            "name": ["Alpha", "Alpha Copy", "Beta"],
            "date_of_birth": ["1998-05-10", "1998-05-10", "2000-01-01"],
        }
    )
    players_df.to_csv(tmp_path / "players.csv.gz", compression="gzip", index=False)

    validator = DataValidator(raw_dir=tmp_path)
    validator._check_identifiers_and_duplicates()
    issues = [i for i in validator.issues if i.check_name == "duplicate_player_id"]
    assert len(issues) == 1
    assert issues[0].severity == "ERROR"
    assert issues[0].count == 1


def test_validator_detects_negative_and_outlier_stats(tmp_path):
    apps_df = pd.DataFrame(
        {
            "appearance_id": [1, 2, 3],
            "minutes_played": [90, -10, 150],
            "goals": [1, -2, 0],
            "assists": [0, 0, 1],
            "yellow_cards": [0, 0, 0],
            "red_cards": [0, 0, 0],
        }
    )
    apps_df.to_csv(tmp_path / "appearances.csv.gz", compression="gzip", index=False)

    validator = DataValidator(raw_dir=tmp_path)
    validator._check_domain_constraints()

    neg_issues = [i for i in validator.issues if i.check_name == "negative_performance_stats"]
    assert len(neg_issues) == 1
    assert neg_issues[0].severity == "ERROR"

    excess_issues = [i for i in validator.issues if i.check_name == "excessive_match_minutes"]
    assert len(excess_issues) == 1
    assert excess_issues[0].severity == "WARNING"


def test_validator_detects_zero_or_negative_market_values(tmp_path):
    vals_df = pd.DataFrame(
        {
            "player_id": [1, 2, 3],
            "date": ["2023-01-01", "2023-02-01", "2023-03-01"],
            "market_value_in_eur": [5000000, -1000, 0],
        }
    )
    vals_df.to_csv(tmp_path / "player_valuations.csv.gz", compression="gzip", index=False)

    validator = DataValidator(raw_dir=tmp_path)
    validator._check_domain_constraints()

    neg_vals = [i for i in validator.issues if i.check_name == "negative_market_value"]
    assert len(neg_vals) == 1
    assert neg_vals[0].severity == "ERROR"

    zero_vals = [i for i in validator.issues if i.check_name == "zero_or_null_market_value"]
    assert len(zero_vals) == 1
    assert zero_vals[0].severity == "WARNING"
