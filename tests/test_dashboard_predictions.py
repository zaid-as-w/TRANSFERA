"""Tests for Dashboard Prediction Service Facade and Hero Predictor Workflows."""

import pytest

from dashboard.prediction_service import DashboardPredictionService


@pytest.fixture(scope="module")
def pred_service() -> DashboardPredictionService:
    return DashboardPredictionService()


def test_prediction_metadata(pred_service: DashboardPredictionService):
    meta = pred_service.get_metadata()
    assert meta["model_name"] == "Model_B_HistGradientBoosting"
    assert meta["use_log_target"] is True
    assert meta["features_numeric_count"] >= 16
    assert meta["best_val_mae_eur"] < 2_500_000


def test_predict_existing_player_record(pred_service: DashboardPredictionService):
    record = {
        "player_id": 418560,
        "name": "Erling Haaland",
        "age": 23.0,
        "position": "Attack",
        "sub_position": "Centre-Forward",
        "foot": "left",
        "height_in_cm": 195.0,
        "country_of_citizenship": "Norway",
        "competition_id": "GB1",
        "club_id": 281,
        "appearances": 31,
        "minutes_played": 2558,
        "goals": 27,
        "assists": 5,
        "cards": 1,
        "previous_market_value": 180_000_000.0,
        "season": 2023,
    }
    result = pred_service.predict_player_record(record)
    assert result.predicted_value_eur > 50_000_000
    assert result.source_competition == "GB1"
    assert result.empirical_benchmark_mae_eur is not None
    assert result.empirical_benchmark_mae_eur > 0


def test_predict_custom_simulation(pred_service: DashboardPredictionService):
    res = pred_service.predict_custom(
        age=20.0,
        position="Attack",
        appearances=25,
        minutes_played=1800,
        goals=14,
        assists=4,
        competition_id="GB1",
        club_id=281,
        previous_market_value=10_000_000.0,
        season=2023,
    )
    assert res.predicted_value_eur > 1_000_000
    assert res.source_competition == "GB1"


def test_cross_league_scenario(pred_service: DashboardPredictionService):
    player = {
        "name": "Kylian Mbappé",
        "age": 25.0,
        "position": "Attack",
        "goals": 27,
        "assists": 7,
        "appearances": 29,
        "minutes_played": 2150,
        "competition_id": "FR1",
        "club_id": 583,
        "previous_market_value": 180_000_000.0,
        "season": 2023,
    }
    res = pred_service.predict_cross_league(
        player_data=player,
        source_competition_id="FR1",
        destination_competition_id="GB1",
        source_club_id=583,
        destination_club_id=281,
        season=2023,
    )
    assert res.use_case == "cross_league_scenario"
    assert res.source_competition == "FR1"
    assert res.destination_competition == "GB1"
    assert res.cross_league_delta_eur is not None
    assert res.cross_league_delta_pct is not None


def test_zero_minute_diagnostic_warning(pred_service: DashboardPredictionService):
    res = pred_service.predict_custom(
        age=19.0,
        position="Midfield",
        appearances=0,
        minutes_played=0,
        goals=0,
        assists=0,
        competition_id="GB1",
        previous_market_value=None,
        season=2023,
    )
    # Zero minutes must trigger diagnostic warning and produce a sensible valuation
    assert res.predicted_value_eur > 0
    assert len(res.relevant_data_warnings) > 0
    assert any("zero minutes" in w.lower() for w in res.relevant_data_warnings)
