"""Tests for prediction coverage tiers (Status A, B, C) and valuation integrity."""

from __future__ import annotations

import pytest

from src.coverage_manager import CoverageManager
from src.predict import ValuationPredictor


@pytest.fixture
def coverage_manager():
    return CoverageManager()


@pytest.fixture
def predictor():
    return ValuationPredictor()


def test_status_a_prediction_available(coverage_manager, predictor):
    """Verify Status A assigns PREDICTION AVAILABLE and runs Stage 1 model."""
    record = {
        "player_id": 418560,
        "name": "Erling Haaland",
        "age": 24.0,
        "position": "Attack",
        "current_club_name": "Manchester City",
        "current_competition_name": "GB1",
        "profile_coverage_status": "FULL_EVIDENCE",
    }
    assessment = coverage_manager.assess_player(
        player_record=record,
        has_performance_data=True,
        has_historical_valuation=True,
        is_stage1_source=True,
    )
    assert assessment.status_code == "STATUS_A"
    assert assessment.can_predict is True
    assert assessment.source_database == "STAGE 1 DATABASE"
    assert len(assessment.missing_fields) == 0


def test_status_b_limited_evidence(coverage_manager):
    """Verify Status B detects partial match records and restricts uncalibrated predictions."""
    record = {
        "global_player_id": "apifb_85001",
        "name": "Sunil Chhetri",
        "age": 39,
        "position": "Attacker",
        "current_club_name": "Bengaluru FC",
        "current_competition_name": "Indian Super League",
        "profile_coverage_status": "LIMITED_EVIDENCE",
    }
    assessment = coverage_manager.assess_player(
        player_record=record,
        has_performance_data=True,
        has_historical_valuation=False,
        is_stage1_source=False,
    )
    assert assessment.status_code == "STATUS_B"
    assert assessment.can_predict is False
    assert assessment.source_database == "GLOBAL DATABASE"
    assert "historical_market_valuation" in assessment.missing_fields
    assert assessment.diagnostic_warning is not None


def test_status_c_profile_only_never_generates_fake_valuation(coverage_manager):
    """Verify Status C displays exact required message and never returns fake valuation."""
    record = {
        "global_player_id": "reep_p999",
        "name": "Emerging Local Player",
        "age": 20,
        "position": "Midfielder",
        "current_club_name": "Regional Club",
        "current_competition_name": "Local Division",
        "profile_coverage_status": "PROFILE_ONLY",
    }
    assessment = coverage_manager.assess_player(
        player_record=record,
        has_performance_data=False,
        has_historical_valuation=False,
        is_stage1_source=False,
    )
    assert assessment.status_code == "STATUS_C"
    assert assessment.can_predict is False
    assert "Reliable market valuation is currently unavailable" in assessment.message
    assert assessment.coverage_score <= 0.30


def test_stage1_champion_model_predictions_intact(predictor):
    """Verify original Stage 1 champion model produces consistent predictions."""
    from src.predict import PlayerInput

    sample_input = PlayerInput(
        age_at_reference_date=24.0,
        position="Attack",
        sub_position="Centre-Forward",
        appearances=35,
        minutes_played=2900,
        goals=30,
        assists=8,
        cards=2,
        foot="left",
        height_in_cm=195.0,
        country_of_citizenship="Norway",
        previous_market_value=170000000.0,
        current_season=2024,
    )
    res = predictor.predict_current_valuation(sample_input, competition_id="GB1", club_id=281)
    assert res.predicted_value_eur > 100000000.0  # > 100M EUR
    assert res.predicted_value_eur < 300000000.0  # < 300M EUR
