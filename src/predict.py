"""Prediction Service for Global Football Transfer Market Valuations.

Supports:
A. Current competition valuation
B. Cross-league transfer scenario benchmarking

Maintains fixed player characteristics and observed evidence while swapping
the competition, club, and financial environment for destination move estimation.
"""

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from config.settings import METADATA_DIR
from src.competition_registry import CompetitionRegistry
from src.financial_context import FinancialContextEngine
from src.league_strength import LeagueStrengthEngine
from src.model_registry import ModelRegistry

logger = logging.getLogger(__name__)


@dataclass
class PlayerInput:
    age_at_reference_date: float
    position: str  # Attack, Midfield, Defender, Goalkeeper
    appearances: int
    minutes_played: int
    goals: int
    assists: int
    sub_position: str = "Unknown"
    foot: str = "Unknown"
    height_in_cm: float | None = 182.0
    country_of_citizenship: str = "Unknown"
    cards: int = 0
    previous_market_value: float | None = None
    reference_date: str | None = None
    current_season: int = 2024


@dataclass
class ValuationResult:
    predicted_value_eur: float
    model_version: str
    reference_date: str
    target_definition: str
    source_competition: str
    destination_competition: str | None = None
    use_case: str = "current_valuation"  # "current_valuation" or "cross_league_scenario"
    evaluation_coverage: str = "SUPPORTED"
    cross_league_delta_eur: float | None = None
    cross_league_delta_pct: float | None = None
    empirical_benchmark_mae_eur: float | None = None
    relevant_data_warnings: list[str] = field(default_factory=list)
    model_limitations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ValuationPredictor:
    """Production-grade valuation prediction service."""

    def __init__(
        self,
        model_path: Path | None = None,
    ) -> None:
        self.registry = CompetitionRegistry()
        self.league_engine = LeagueStrengthEngine()
        self.financial_engine = FinancialContextEngine()
        self.model_reg = ModelRegistry()
        self.pipeline, self.metadata = self.model_reg.load_model(model_path)
        self.use_log_target = self.metadata.use_log_target

        # Load held-out evaluation metrics for empirical benchmark uncertainty reporting
        self.eval_results: dict[str, Any] = {}
        eval_path = METADATA_DIR / "evaluation_results.json"
        if eval_path.exists():
            try:
                with open(eval_path, encoding="utf-8") as f:
                    self.eval_results = json.load(f)
            except Exception:
                self.eval_results = {}

        if not self.league_engine.is_fitted:
            self.league_engine.fit()

    def _get_benchmark_mae(self, competition_id: str) -> float | None:
        """Fetch empirical out-of-time test MAE for the competition, or global fallback."""
        comps = self.eval_results.get("competitions", {})
        comp_m = comps.get(competition_id, {})
        if isinstance(comp_m, dict) and "mae_eur" in comp_m:
            return float(comp_m["mae_eur"])
        gm = self.eval_results.get("global_metrics", {})
        if isinstance(gm, dict) and "mae_eur" in gm:
            return float(gm["mae_eur"])
        return None

    def _build_feature_row(
        self,
        player: PlayerInput,
        competition_id: str,
        club_id: int | None = None,
        season: int | None = None,
    ) -> tuple[pd.DataFrame, list[str]]:
        """Construct model-aligned feature row for a specific competition context."""
        warnings: list[str] = []
        target_season = season or player.current_season

        # Verify competition status
        comp_status = self.registry.get_status(competition_id)
        if comp_status != "SUPPORTED":
            warnings.append(
                f"Competition {competition_id} has reliability status '{comp_status}'. Predictions have higher uncertainty."
            )

        # Performance per-90 metrics
        has_minutes = player.minutes_played > 0
        if not has_minutes:
            warnings.append(
                "Zero minutes played recorded for the season. Valuation is an ML-derived squad/reserve benchmark reflecting position, age, and league tier, not in-match performance form."
            )
        goals_p90 = round((player.goals / player.minutes_played) * 90.0, 3) if has_minutes else 0.0
        assists_p90 = round((player.assists / player.minutes_played) * 90.0, 3) if has_minutes else 0.0
        cards_p90 = round((player.cards / player.minutes_played) * 90.0, 3) if has_minutes else 0.0
        min_p_app = round(player.minutes_played / max(1, player.appearances), 1)

        # League strength
        ls = self.league_engine.get_league_strength(competition_id, target_season)
        if not ls.get("has_cross_league_evidence", False):
            warnings.append(f"Competition {competition_id} has limited cross-league tournament match calibration.")
        im = self.league_engine.get_intensity_metrics(competition_id, target_season)

        # Club Elo
        c_elo = self.league_engine.get_club_elo(club_id) if club_id else ls.get("mean_elo", 1500.0)

        # Financial context
        fc = self.financial_engine.get_financial_context(club_id, competition_id, target_season)
        if not fc.get("has_club_financials"):
            warnings.append(
                f"Audited club-level financial accounts unavailable for club {club_id}. Fallback applied: {fc['financial_aggregation_level']}."
            )

        has_prev_val = player.previous_market_value is not None and player.previous_market_value > 0
        prev_val_eur = player.previous_market_value if has_prev_val else 0.0

        row = {
            "age_at_reference_date": player.age_at_reference_date,
            "appearances": player.appearances,
            "minutes_played": player.minutes_played,
            "goals": player.goals,
            "assists": player.assists,
            "goals_per_90": goals_p90,
            "assists_per_90": assists_p90,
            "cards": player.cards,
            "cards_per_90": cards_p90,
            "minutes_per_appearance": min_p_app,
            "height_in_cm": player.height_in_cm if player.height_in_cm else 182.0,
            "previous_market_value": prev_val_eur,
            "has_previous_valuation": has_prev_val,
            "position": player.position,
            "sub_position": player.sub_position,
            "foot": player.foot,
            "competition_strength": ls.get("competition_strength", 1.0),
            "competition_mean_elo": ls.get("mean_elo", 1500.0),
            "competition_top4_strength": ls.get("top4_strength", 1.0),
            "competition_spread_elo": ls.get("spread_elo", 0.0),
            "club_elo": c_elo,
            "league_goals_per_match": im.get("goals_per_match", 2.7),
            "league_cards_per_match": im.get("cards_per_match", 4.0),
            "competitive_balance_index": im.get("competitive_balance_index", 0.45),
            "club_revenue_eur": fc.get("club_revenue_eur"),
            "league_average_revenue_eur": fc.get("league_average_revenue_eur"),
            "has_club_financials": fc.get("has_club_financials", False),
            "has_league_financials": fc.get("has_league_financials", False),
            "source_coverage_score": 0.8 if has_prev_val else 0.5,
            "competition_id": competition_id,
            "country_of_citizenship": player.country_of_citizenship,
            "financial_aggregation_level": fc.get("financial_aggregation_level", "missing"),
        }

        return pd.DataFrame([row]), warnings

    def predict_current_valuation(
        self,
        player: PlayerInput,
        competition_id: str,
        club_id: int | None = None,
        season: int | None = None,
    ) -> ValuationResult:
        """Estimate current player market value in euros."""
        ref_date = player.reference_date or datetime.now(UTC).strftime("%Y-%m-%d")
        df_row, warnings = self._build_feature_row(player, competition_id, club_id, season)

        raw_pred = self.pipeline.predict(df_row)[0]
        val_eur = float(np.expm1(raw_pred)) if self.use_log_target else float(raw_pred)
        val_eur = max(25000.0, round(val_eur, -4))  # round to nearest 10,000 EUR

        comp_status = self.registry.get_status(competition_id)
        benchmark_mae = self._get_benchmark_mae(competition_id)

        limitations = [
            "Estimates recorded market value benchmark in EUR, not an actual transfer fee or negotiated wage.",
            "Parametric 95% confidence intervals are intentionally withheld by scientific design; empirical out-of-time test MAE is provided instead as the error benchmark.",
            "Based on historical Transfermarkt evaluation distributions and cross-league Elo calibration.",
            "Does not account for private contract clauses, player medical status, or transfer bidding competition.",
        ]

        return ValuationResult(
            predicted_value_eur=val_eur,
            model_version=self.metadata.version,
            reference_date=ref_date,
            target_definition="Historical player market value benchmark in EUR",
            source_competition=competition_id,
            use_case="current_valuation",
            evaluation_coverage=comp_status,
            empirical_benchmark_mae_eur=benchmark_mae,
            relevant_data_warnings=warnings,
            model_limitations=limitations,
        )

    def predict_cross_league_scenario(
        self,
        player: PlayerInput,
        source_competition_id: str,
        destination_competition_id: str,
        source_club_id: int | None = None,
        destination_club_id: int | None = None,
        season: int | None = None,
    ) -> ValuationResult:
        """Estimate valuation benchmark for a hypothetical move to another competition."""
        ref_date = player.reference_date or datetime.now(UTC).strftime("%Y-%m-%d")

        # 1. Base prediction in source league
        base_res = self.predict_current_valuation(player, source_competition_id, source_club_id, season)

        # 2. Prediction in destination league with identical player performance evidence
        df_dest, dest_warnings = self._build_feature_row(
            player, destination_competition_id, destination_club_id, season
        )
        raw_dest_pred = self.pipeline.predict(df_dest)[0]
        dest_val_eur = float(np.expm1(raw_dest_pred)) if self.use_log_target else float(raw_dest_pred)
        dest_val_eur = max(25000.0, round(dest_val_eur, -4))

        delta_eur = round(dest_val_eur - base_res.predicted_value_eur, 2)
        delta_pct = (
            round((delta_eur / base_res.predicted_value_eur) * 100.0, 2) if base_res.predicted_value_eur > 0 else 0.0
        )

        dest_status = self.registry.get_status(destination_competition_id)
        benchmark_mae = self._get_benchmark_mae(destination_competition_id)
        combined_warnings = base_res.relevant_data_warnings + dest_warnings
        if dest_status != "SUPPORTED":
            combined_warnings.append(
                f"Destination league {destination_competition_id} is evaluated as '{dest_status}'. Move benchmark has lower empirical support."
            )
        if delta_eur < 0:
            combined_warnings.append(
                f"Negative cross-league delta ({delta_pct:+.1f}%) reflects destination competition environment factors ({destination_competition_id} scoring tempo: {df_dest['league_goals_per_match'].iloc[0]} goals/match, competitive balance: {df_dest['competitive_balance_index'].iloc[0]}) against which raw counting performance is comparatively evaluated without an assigned elite club revenue context."
            )

        limitations = [
            "Estimates destination league market value benchmark for player performance evidence, NOT player sporting adaptation or future tactical fit.",
            "Parametric 95% confidence intervals are intentionally withheld by scientific design; empirical out-of-time test MAE is provided instead as the error benchmark.",
            "Transfer fees often diverge significantly from valuation benchmarks due to contract length remaining and urgency.",
            "Destination context swaps league strength, intensity, competitive balance, and club revenue tier.",
        ]

        return ValuationResult(
            predicted_value_eur=dest_val_eur,
            model_version=self.metadata.version,
            reference_date=ref_date,
            target_definition="Hypothetical cross-league player market value benchmark in EUR",
            source_competition=source_competition_id,
            destination_competition=destination_competition_id,
            use_case="cross_league_scenario",
            evaluation_coverage=f"Source: {base_res.evaluation_coverage}, Destination: {dest_status}",
            cross_league_delta_eur=delta_eur,
            cross_league_delta_pct=delta_pct,
            empirical_benchmark_mae_eur=benchmark_mae,
            relevant_data_warnings=list(set(combined_warnings)),
            model_limitations=limitations,
        )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    predictor = ValuationPredictor()

    sample_winger = PlayerInput(
        age_at_reference_date=23.5,
        position="Attack",
        sub_position="Left Winger",
        appearances=34,
        minutes_played=2750,
        goals=14,
        assists=9,
        cards=3,
        foot="Right",
        height_in_cm=180.0,
        country_of_citizenship="France",
        previous_market_value=35000000.0,
        reference_date="2024-06-01",
        current_season=2024,
    )

    print("\n--- Use Case A: Current Valuation (Ligue 1 - FR1) ---")
    cur_res = predictor.predict_current_valuation(sample_winger, competition_id="FR1", club_id=583)
    print(f"Estimated Market Value in FR1: €{cur_res.predicted_value_eur:,.2f}")
    print(f"Warnings: {cur_res.relevant_data_warnings}")

    print("\n--- Use Case B: Cross-League Transfer Move (FR1 -> Premier League GB1) ---")
    cross_res = predictor.predict_cross_league_scenario(
        sample_winger,
        source_competition_id="FR1",
        destination_competition_id="GB1",
        source_club_id=583,
        destination_club_id=11,  # Arsenal
    )
    print(f"Estimated Market Value in GB1: €{cross_res.predicted_value_eur:,.2f}")
    print(
        f"Market Value Benchmark Delta: €{cross_res.cross_league_delta_eur:+,.2f} ({cross_res.cross_league_delta_pct:+,.2f}%)"
    )
    print(f"Warnings: {cross_res.relevant_data_warnings}")
