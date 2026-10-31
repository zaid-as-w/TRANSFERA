"""Financial context module for European and global football competitions.

Provides validated club-level and league-level financial indicators sourced from
Deloitte Football Money League and UEFA European Club Finance and Investment
Landscape reports.

Distinguishes observed club-level financial reports from league-level macro
aggregates, strictly preventing synthetic data fabrication.
"""

import logging
from pathlib import Path
from typing import Any

import pandas as pd

from config.settings import RAW_FIN_DIR

logger = logging.getLogger(__name__)


class FinancialContextEngine:
    """Manages verified financial data for clubs and leagues."""

    def __init__(
        self,
        club_financials_path: Path | None = None,
        league_financials_path: Path | None = None,
    ) -> None:
        self.club_path = club_financials_path or (RAW_FIN_DIR / "club_financials_benchmark.csv")
        self.league_path = league_financials_path or (RAW_FIN_DIR / "league_financial_benchmark.csv")
        self.club_df = self._load_club_data()
        self.league_df = self._load_league_data()

    def _load_club_data(self) -> pd.DataFrame:
        if self.club_path.exists():
            try:
                df = pd.read_csv(self.club_path)
                logger.info("Loaded %d club financial records from %s", len(df), self.club_path.name)
                return df
            except Exception as e:
                logger.warning("Failed loading club financials from %s: %s", self.club_path, e)
        return pd.DataFrame()

    def _load_league_data(self) -> pd.DataFrame:
        if self.league_path.exists():
            try:
                df = pd.read_csv(self.league_path)
                logger.info("Loaded %d league financial records from %s", len(df), self.league_path.name)
                return df
            except Exception as e:
                logger.warning("Failed loading league financials from %s: %s", self.league_path, e)
        return pd.DataFrame()

    def get_financial_context(
        self,
        club_id: int | None,
        competition_id: str | None,
        season: int | None,
    ) -> dict[str, Any]:
        """Retrieve financial context for a club, competition, and season.

        Distinguishes club-level observed data from league-level fallback data.
        Returns missingness flags and aggregation level metadata.
        """
        result: dict[str, Any] = {
            "has_club_financials": False,
            "has_league_financials": False,
            "financial_aggregation_level": "missing",
            "club_revenue_eur": None,
            "matchday_revenue_eur": None,
            "broadcast_revenue_eur": None,
            "commercial_revenue_eur": None,
            "wage_bill_eur": None,
            "league_average_revenue_eur": None,
            "league_total_revenue_eur": None,
            "financial_data_source": "None",
        }

        # 1. Attempt club-level observed financials
        if club_id is not None and season is not None and not self.club_df.empty:
            match = self.club_df[(self.club_df["club_id"] == club_id) & (self.club_df["season"] == season)]
            if not match.empty:
                row = match.iloc[0]
                result["has_club_financials"] = True
                result["financial_aggregation_level"] = "club_observed"
                result["club_revenue_eur"] = float(row["total_revenue_eur"])
                result["matchday_revenue_eur"] = (
                    float(row["matchday_revenue_eur"]) if pd.notna(row.get("matchday_revenue_eur")) else None
                )
                result["broadcast_revenue_eur"] = (
                    float(row["broadcast_revenue_eur"]) if pd.notna(row.get("broadcast_revenue_eur")) else None
                )
                result["commercial_revenue_eur"] = (
                    float(row["commercial_revenue_eur"]) if pd.notna(row.get("commercial_revenue_eur")) else None
                )
                result["wage_bill_eur"] = float(row["wage_bill_eur"]) if pd.notna(row.get("wage_bill_eur")) else None
                result["financial_data_source"] = str(row.get("financial_source", "Deloitte Money League"))

        # 2. Add league-level context
        if competition_id and season is not None and not self.league_df.empty:
            l_match = self.league_df[
                (self.league_df["competition_id"] == competition_id) & (self.league_df["season"] == season)
            ]
            if not l_match.empty:
                l_row = l_match.iloc[0]
                result["has_league_financials"] = True
                result["league_average_revenue_eur"] = float(l_row["average_club_revenue_eur"])
                result["league_total_revenue_eur"] = float(l_row["total_league_revenue_eur"])
                if not result["has_club_financials"]:
                    result["financial_aggregation_level"] = "league_fallback"
                    result["financial_data_source"] = str(l_row.get("financial_source", "UEFA ECFIL Report"))

        return result

    def enrich_features_df(self, df: pd.DataFrame) -> pd.DataFrame:
        """Vectorized enrichment of player-season DataFrame with financial features."""
        enriched = df.copy()

        # Merge club financials on (club_id, season)
        if not self.club_df.empty and "club_id" in enriched.columns and "season" in enriched.columns:
            club_subset = self.club_df[
                [
                    "club_id",
                    "season",
                    "total_revenue_eur",
                    "matchday_revenue_eur",
                    "broadcast_revenue_eur",
                    "commercial_revenue_eur",
                    "wage_bill_eur",
                ]
            ].rename(
                columns={
                    "total_revenue_eur": "club_revenue_eur",
                }
            )
            enriched = enriched.merge(club_subset, on=["club_id", "season"], how="left")
        else:
            enriched["club_revenue_eur"] = None
            enriched["matchday_revenue_eur"] = None
            enriched["broadcast_revenue_eur"] = None
            enriched["commercial_revenue_eur"] = None
            enriched["wage_bill_eur"] = None

        # Merge league financials on (competition_id, season)
        if not self.league_df.empty and "competition_id" in enriched.columns and "season" in enriched.columns:
            league_subset = self.league_df[
                ["competition_id", "season", "average_club_revenue_eur", "total_league_revenue_eur"]
            ].rename(
                columns={
                    "average_club_revenue_eur": "league_average_revenue_eur",
                    "total_league_revenue_eur": "league_total_revenue_eur",
                }
            )
            enriched = enriched.merge(league_subset, on=["competition_id", "season"], how="left")
        else:
            enriched["league_average_revenue_eur"] = None
            enriched["league_total_revenue_eur"] = None

        enriched["has_club_financials"] = enriched["club_revenue_eur"].notna()
        enriched["has_league_financials"] = enriched["league_average_revenue_eur"].notna()
        enriched["financial_aggregation_level"] = "missing"
        enriched.loc[enriched["has_league_financials"], "financial_aggregation_level"] = "league_fallback"
        enriched.loc[enriched["has_club_financials"], "financial_aggregation_level"] = "club_observed"

        return enriched


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    engine = FinancialContextEngine()
    print("Testing financial context for Real Madrid (club 418, 2023 season):")
    ctx = engine.get_financial_context(418, "ES1", 2023)
    print(ctx)
    print("\nTesting financial context for smaller club without audited DFML report (club 9999, ES1, 2023):")
    ctx_fallback = engine.get_financial_context(9999, "ES1", 2023)
    print(ctx_fallback)
