"""Prediction integration service for the Global Football Analytics Dashboard.

Integrates directly with Stage 1 ValuationPredictor and PlayerInput dataclass.
Preserves the exact feature schema and HistGradientBoosting champion model.
"""

import logging
import sys
from typing import Any

# Ensure backward compatibility when unpickling HistGradientBoostingRegressor models
try:
    import sklearn._loss.loss as _sk_loss_loss

    if "_loss" not in sys.modules:
        sys.modules["_loss"] = _sk_loss_loss
except Exception:
    try:
        import sklearn.ensemble._hist_gradient_boosting._loss as _sk_hgbr_loss

        if "_loss" not in sys.modules:
            sys.modules["_loss"] = _sk_hgbr_loss
    except Exception:
        pass

import streamlit as st

from src.predict import PlayerInput, ValuationPredictor, ValuationResult

logger = logging.getLogger(__name__)


@st.cache_resource(show_spinner=False)
def get_predictor_instance() -> ValuationPredictor | None:
    """Load and cache the single Stage 1 ValuationPredictor instance."""
    logger.info("Initializing Stage 1 ValuationPredictor for dashboard session...")
    try:
        return ValuationPredictor()
    except Exception as e:
        logger.exception("Failed to load ValuationPredictor: %s", e)
        return None


class DashboardPredictionService:
    """High-level facade connecting the Streamlit UI to Stage 1 ValuationPredictor."""

    def __init__(self) -> None:
        self.predictor = get_predictor_instance()

    def is_available(self) -> bool:
        return self.predictor is not None

    def get_metadata(self) -> dict[str, Any]:
        """Return model metadata from the fitted champion pipeline."""
        if not self.predictor:
            return {
                "model_name": "HistGradientBoosting (Standby)",
                "version": "1.0.0",
                "saved_at": "Offline",
                "best_val_mae_eur": 1775860.06,
                "use_log_target": True,
                "features_numeric_count": 26,
                "features_categorical_count": 6,
                "features_numeric": [],
                "features_categorical": [],
            }
        m = self.predictor.metadata
        return {
            "model_name": m.model_name,
            "version": m.version,
            "saved_at": m.saved_at,
            "best_val_mae_eur": m.best_val_mae_eur,
            "use_log_target": m.use_log_target,
            "features_numeric_count": len(m.features_numeric),
            "features_categorical_count": len(m.features_categorical),
            "features_numeric": m.features_numeric,
            "features_categorical": m.features_categorical,
        }

    def predict_player_record(
        self,
        record: dict[str, Any],
        competition_id: str | None = None,
        club_id: int | None = None,
        season: int | None = None,
    ) -> ValuationResult:
        """Run valuation prediction for an existing historical player record."""
        target_comp = competition_id or record.get("competition_id", "GB1")
        target_club = club_id if club_id is not None else record.get("club_id")
        target_season = season or record.get("season", 2023)

        player_input = PlayerInput(
            age_at_reference_date=float(record.get("age", record.get("age_at_reference_date", 24.0))),
            position=str(record.get("position", "Attack")),
            appearances=int(record.get("appearances", 0)),
            minutes_played=int(record.get("minutes_played", 0)),
            goals=int(record.get("goals", 0)),
            assists=int(record.get("assists", 0)),
            sub_position=str(record.get("sub_position", "Unknown")),
            foot=str(record.get("foot", "Unknown")),
            height_in_cm=float(record.get("height_in_cm", 182.0)) if record.get("height_in_cm") else 182.0,
            country_of_citizenship=str(record.get("country_of_citizenship", "Unknown")),
            cards=int(record.get("cards", 0)),
            previous_market_value=float(record["previous_market_value"])
            if record.get("previous_market_value")
            else None,
            current_season=int(target_season),
        )

        if not self.predictor:
            base_val = float(record.get("market_value_in_eur", 5000000.0))
            return ValuationResult(
                predicted_value_eur=base_val,
                model_version="1.0.0-fallback",
                reference_date=f"{target_season}-06-30",
                target_definition="market_value_in_eur",
                source_competition=target_comp,
                model_limitations=["Predictor running in standby mode."],
            )

        return self.predictor.predict_current_valuation(
            player=player_input,
            competition_id=target_comp,
            club_id=target_club,
            season=target_season,
        )

    def predict_custom(
        self,
        age: float,
        position: str,
        appearances: int,
        minutes_played: int,
        goals: int,
        assists: int,
        competition_id: str,
        club_id: int | None = None,
        previous_market_value: float | None = None,
        sub_position: str = "Unknown",
        foot: str = "Unknown",
        height_in_cm: float = 182.0,
        cards: int = 0,
        country: str = "Unknown",
        season: int = 2023,
    ) -> ValuationResult:
        """Run valuation prediction for a user-constructed player profile."""
        player_input = PlayerInput(
            age_at_reference_date=float(age),
            position=str(position),
            appearances=int(appearances),
            minutes_played=int(minutes_played),
            goals=int(goals),
            assists=int(assists),
            sub_position=str(sub_position),
            foot=str(foot),
            height_in_cm=float(height_in_cm),
            country_of_citizenship=str(country),
            cards=int(cards),
            previous_market_value=float(previous_market_value) if previous_market_value else None,
            current_season=int(season),
        )

        if not self.predictor:
            fallback_val = float(previous_market_value) if previous_market_value else 10000000.0
            return ValuationResult(
                predicted_value_eur=fallback_val,
                model_version="1.0.0-fallback",
                reference_date=f"{season}-06-30",
                target_definition="market_value_in_eur",
                source_competition=competition_id,
                model_limitations=["Predictor running in standby mode."],
            )

        return self.predictor.predict_current_valuation(
            player=player_input,
            competition_id=competition_id,
            club_id=club_id,
            season=season,
        )

    def predict_cross_league(
        self,
        player_data: dict[str, Any],
        source_competition_id: str,
        destination_competition_id: str,
        source_club_id: int | None = None,
        destination_club_id: int | None = None,
        season: int | None = None,
    ) -> ValuationResult:
        """Run hypothetical cross-league transfer move simulation."""
        target_season = season or player_data.get("season", 2023)
        player_input = PlayerInput(
            age_at_reference_date=float(player_data.get("age", player_data.get("age_at_reference_date", 24.0))),
            position=str(player_data.get("position", "Attack")),
            appearances=int(player_data.get("appearances", 0)),
            minutes_played=int(player_data.get("minutes_played", 0)),
            goals=int(player_data.get("goals", 0)),
            assists=int(player_data.get("assists", 0)),
            sub_position=str(player_data.get("sub_position", "Unknown")),
            foot=str(player_data.get("foot", "Unknown")),
            height_in_cm=float(player_data.get("height_in_cm", 182.0)) if player_data.get("height_in_cm") else 182.0,
            country_of_citizenship=str(player_data.get("country_of_citizenship", "Unknown")),
            cards=int(player_data.get("cards", 0)),
            previous_market_value=float(player_data["previous_market_value"])
            if player_data.get("previous_market_value")
            else None,
            current_season=int(target_season),
        )

        if not self.predictor:
            fallback_val = float(player_data.get("market_value_in_eur", 10000000.0))
            return ValuationResult(
                predicted_value_eur=fallback_val,
                model_version="1.0.0-fallback",
                reference_date=f"{target_season}-06-30",
                target_definition="market_value_in_eur",
                source_competition=source_competition_id,
                destination_competition=destination_competition_id,
                use_case="cross_league_scenario",
                cross_league_delta_eur=0.0,
                cross_league_delta_pct=0.0,
                model_limitations=["Predictor running in standby mode."],
            )

        return self.predictor.predict_cross_league_scenario(
            player=player_input,
            source_competition_id=source_competition_id,
            destination_competition_id=destination_competition_id,
            source_club_id=source_club_id,
            destination_club_id=destination_club_id,
            season=target_season,
        )
