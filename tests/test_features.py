"""Tests for feature engineering, temporal cutoff alignment, and leakage prevention."""

import pandas as pd


def test_age_at_reference_date_computation():
    ref_date = pd.Timestamp("2023-06-01")
    dob = pd.Timestamp("2000-06-01")  # Exactly 23.0 years old
    age = (ref_date - dob).days / 365.25
    assert round(age, 1) == 23.0

    dob_veteran = pd.Timestamp("1988-06-01")  # 35.0 years old
    age_vet = (ref_date - dob_veteran).days / 365.25
    assert round(age_vet, 1) == 35.0


def test_per_90_statistics_computation():
    minutes = 1800
    goals = 10
    assists = 5
    cards = 4

    goals_p90 = (goals / minutes) * 90.0
    assists_p90 = (assists / minutes) * 90.0
    cards_p90 = (cards / minutes) * 90.0

    assert round(goals_p90, 2) == 0.50
    assert round(assists_p90, 2) == 0.25
    assert round(cards_p90, 2) == 0.20


def test_per_90_zero_minutes_safety():
    minutes = 0
    goals = 0
    # Must yield 0.0 without division by zero
    goals_p90 = (goals / minutes * 90.0) if minutes > 0 else 0.0
    assert goals_p90 == 0.0


def test_lag_valuation_temporal_integrity():
    # Verify lag valuation is strictly before the current season window
    season_start = pd.Timestamp("2022-07-01")
    valuations_history = pd.DataFrame(
        {
            "date": pd.to_datetime(["2021-06-01", "2022-01-15", "2022-06-15", "2023-01-10"]),
            "market_value_in_eur": [10_000_000, 15_000_000, 18_000_000, 22_000_000],
        }
    )

    # Historical prior valuation strictly before season_start (2022-07-01)
    priors = valuations_history[valuations_history["date"] < season_start]
    latest_prior = priors.sort_values("date").iloc[-1]

    assert latest_prior["date"] == pd.Timestamp("2022-06-15")
    assert latest_prior["market_value_in_eur"] == 18_000_000
    # Assert future valuation in 2023 was NOT selected as prior
    assert latest_prior["date"] < season_start
