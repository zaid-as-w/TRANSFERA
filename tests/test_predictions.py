"""Tests for prediction service, inference workflows, and edge cases."""

import pytest

from src.predict import PlayerInput, ValuationPredictor


@pytest.fixture(scope="module")
def predictor():
    return ValuationPredictor()


def test_predict_current_valuation_valid(predictor):
    player = PlayerInput(
        age_at_reference_date=24.0,
        position="Attack",
        sub_position="Centre-Forward",
        appearances=30,
        minutes_played=2500,
        goals=18,
        assists=6,
        cards=2,
        previous_market_value=25_000_000.0,
        country_of_citizenship="Spain",
        current_season=2024,
    )
    result = predictor.predict_current_valuation(player, competition_id="ES1", club_id=418)

    assert result.predicted_value_eur > 0
    assert result.use_case == "current_valuation"
    assert result.source_competition == "ES1"
    assert result.destination_competition is None
    assert result.target_definition == "Historical player market value benchmark in EUR"
    assert len(result.model_limitations) > 0


def test_predict_cross_league_scenario(predictor):
    player = PlayerInput(
        age_at_reference_date=22.0,
        position="Midfield",
        sub_position="Attacking Midfield",
        appearances=28,
        minutes_played=2200,
        goals=8,
        assists=10,
        cards=1,
        previous_market_value=20_000_000.0,
        country_of_citizenship="France",
        current_season=2024,
    )
    res = predictor.predict_cross_league_scenario(
        player,
        source_competition_id="FR1",
        destination_competition_id="GB1",
        source_club_id=583,
        destination_club_id=11,
    )

    assert res.predicted_value_eur > 0
    assert res.use_case == "cross_league_scenario"
    assert res.source_competition == "FR1"
    assert res.destination_competition == "GB1"
    assert res.cross_league_delta_eur is not None
    assert res.cross_league_delta_pct is not None


def test_predict_missing_optional_financials_and_prior_valuation(predictor):
    # Missing previous valuation and unlisted club with zero financial records
    player = PlayerInput(
        age_at_reference_date=19.5,
        position="Defender",
        sub_position="Centre-Back",
        appearances=15,
        minutes_played=1200,
        goals=1,
        assists=0,
        cards=3,
        previous_market_value=None,  # Debutant without prior valuation
        country_of_citizenship="Brazil",
        current_season=2024,
    )
    # Must NOT crash on unlisted club or missing previous valuation
    res = predictor.predict_current_valuation(player, competition_id="PO1", club_id=9999999)
    assert res.predicted_value_eur > 0
    assert any("Audited club-level financial accounts unavailable" in w for w in res.relevant_data_warnings)


def test_predict_zero_minutes_warning(predictor):
    player = PlayerInput(
        age_at_reference_date=21.0,
        position="Midfield",
        sub_position="Central Midfield",
        appearances=0,
        minutes_played=0,
        goals=0,
        assists=0,
        cards=0,
        current_season=2024,
    )
    res = predictor.predict_current_valuation(player, competition_id="L1")
    assert res.predicted_value_eur > 0
    assert any("Zero minutes played" in w for w in res.relevant_data_warnings)
    assert res.empirical_benchmark_mae_eur is not None
