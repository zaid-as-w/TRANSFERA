"""Coverage and prediction eligibility manager for TRANSFERA.

Evaluates players against three strict prediction tiers:
- STATUS A: PREDICTION AVAILABLE (full model inputs, calibrated league)
- STATUS B: LIMITED EVIDENCE (profile & partial stats, elevated uncertainty)
- STATUS C: PROFILE ONLY (biographical profile only, zero fake valuations)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.global_competition_catalog import GlobalCompetitionCatalog


@dataclass
class CoverageAssessment:
    """Diagnostic assessment of player data coverage and prediction eligibility."""

    status: str  # "PREDICTION_AVAILABLE" | "LIMITED_EVIDENCE" | "PROFILE_ONLY"
    status_code: str  # "STATUS_A" | "STATUS_B" | "STATUS_C"
    can_predict: bool
    source_database: str  # "STAGE 1 DATABASE" | "GLOBAL DATABASE"
    missing_fields: list[str]
    coverage_score: float
    message: str
    diagnostic_warning: str | None = None


class CoverageManager:
    """Determines prediction availability and diagnostic coverage for any player."""

    def __init__(self, competition_catalog: GlobalCompetitionCatalog | None = None):
        self.catalog = competition_catalog or GlobalCompetitionCatalog()

    def assess_player(
        self,
        player_record: dict[str, Any],
        has_performance_data: bool = False,
        has_historical_valuation: bool = False,
        is_stage1_source: bool = False,
    ) -> CoverageAssessment:
        """Evaluate player data sufficiency and assign Status A, B, or C."""
        missing = []
        source_label = "STAGE 1 DATABASE" if is_stage1_source else "GLOBAL DATABASE"

        # Check basic profile attributes
        if not player_record.get("age"):
            missing.append("age")
        if not player_record.get("position") or player_record.get("position") == "Missing":
            missing.append("position")
        if not player_record.get("current_club_name") or player_record.get("current_club_name") in [
            "Unknown",
            "Global Club / Unaffiliated",
        ]:
            missing.append("club_context")

        comp_id = player_record.get("current_competition_name") or player_record.get("competition_id")
        comp_status = self.catalog.get_competition_status(str(comp_id))

        # STATUS A: Stage 1 player with full evidence OR complete feature set in calibrated league
        if is_stage1_source and (
            has_performance_data or player_record.get("profile_coverage_status") == "FULL_EVIDENCE"
        ):
            if comp_status == "SUPPORTED":
                return CoverageAssessment(
                    status="PREDICTION_AVAILABLE",
                    status_code="STATUS_A",
                    can_predict=True,
                    source_database=source_label,
                    missing_fields=[],
                    coverage_score=0.95,
                    message="Full historical evidence and verified league context available.",
                    diagnostic_warning=None,
                )
            else:
                return CoverageAssessment(
                    status="LIMITED_EVIDENCE",
                    status_code="STATUS_B",
                    can_predict=True,
                    source_database=source_label,
                    missing_fields=["uncalibrated_league_strength"],
                    coverage_score=0.75,
                    message="Player performance verified; league context uses regional strength benchmark.",
                    diagnostic_warning=f"Competition '{comp_id}' operates on regional benchmark calibration.",
                )

        # STATUS B: Has match appearances or partial stats, but incomplete features
        if has_performance_data or player_record.get("profile_coverage_status") == "LIMITED_EVIDENCE":
            if not has_historical_valuation:
                missing.append("historical_market_valuation")
            if comp_status != "SUPPORTED":
                missing.append("calibrated_league_financials")

            return CoverageAssessment(
                status="LIMITED_EVIDENCE",
                status_code="STATUS_B",
                can_predict=False,  # Global Status B has real stats but uncalibrated financial context
                source_database=source_label,
                missing_fields=missing,
                coverage_score=0.55,
                message="Verified match statistics available; market financial calibration is limited.",
                diagnostic_warning=(
                    "Player found with verified match records. Market valuation benchmark is restricted "
                    "because domestic financial and transfer indices are uncalibrated for this competition."
                ),
            )

        # STATUS C: PROFILE ONLY (Zero fake numbers permitted)
        missing.extend(["match_statistics", "historical_market_valuation", "competition_elo"])
        return CoverageAssessment(
            status="PROFILE_ONLY",
            status_code="STATUS_C",
            can_predict=False,
            source_database=source_label,
            missing_fields=missing,
            coverage_score=0.25,
            message="Player found. Reliable market valuation is currently unavailable due to insufficient verified data.",
            diagnostic_warning=(
                "Player found in global registry. Reliable market valuation is currently unavailable "
                "due to insufficient verified match and financial data. No synthetic valuation generated."
            ),
        )
