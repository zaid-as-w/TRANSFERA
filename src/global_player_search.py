"""Two-stage global player and country search engine for TRANSFERA.

CRITICAL ARCHITECTURE:
- Step 1: Searches original Stage 1 database first. If >= 1 match is found,
  returns immediately with source indicator 'STAGE 1 DATABASE'.
- Step 2: Falls back to 'global_players' ONLY when Stage 1 returns ZERO results.
  Returns matching global records with source indicator 'GLOBAL DATABASE'.
- Step 3: Returns exact message 'No matching players found in the existing database
  or global player catalog.' when both return zero results.
- Distinguishes player nationality from club country and competition country.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from src.player_identity_resolution import normalize_name

logger = logging.getLogger(__name__)

GLOBAL_PLAYERS_PATH = Path("data/global/global_players.parquet")
STAGE1_PLAYERS_PATH = Path("data/interim/clean_players.parquet")
STAGE1_FEATURES_PATH = Path("data/processed/player_season_features.parquet")

NO_RESULTS_MESSAGE = "No matching players found in the existing database or global player catalog."


@dataclass
class SearchResult:
    """Standardized search match result."""

    player_id: str | int  # Either int (Stage 1) or str (global)
    name: str
    display_name: str
    date_of_birth: str | None
    age: int | None
    nationality: str
    current_club_name: str
    current_competition_name: str
    country: str  # Club or competition country
    position: str
    source_database: str  # "STAGE 1 DATABASE" or "GLOBAL DATABASE"
    profile_coverage_status: str  # "FULL_EVIDENCE", "LIMITED_EVIDENCE", "PROFILE_ONLY"
    can_predict: bool
    image_url: str | None = None
    match_field: str = "name"


class TwoStageSearchService:
    """Search engine orchestrating Stage 1 priority lookup with global fallback."""

    def __init__(
        self,
        stage1_path: Path | str = STAGE1_PLAYERS_PATH,
        stage1_feat_path: Path | str = STAGE1_FEATURES_PATH,
        global_path: Path | str = GLOBAL_PLAYERS_PATH,
    ):
        self.stage1_path = Path(stage1_path)
        self.stage1_feat_path = Path(stage1_feat_path)
        self.global_path = Path(global_path)

        self._stage1_df: pd.DataFrame | None = None
        self._global_df: pd.DataFrame | None = None
        self._stage1_players_with_features: set[int] = set()

    def _load_stage1(self) -> pd.DataFrame:
        """Lazy load and index Stage 1 player table."""
        if self._stage1_df is not None:
            return self._stage1_df

        if not self.stage1_path.exists():
            logger.warning("Stage 1 player table missing: %s", self.stage1_path)
            self._stage1_df = pd.DataFrame()
            return self._stage1_df

        df = pd.read_parquet(self.stage1_path)
        df["norm_name"] = df["name"].fillna("").astype(str).apply(normalize_name)
        df["norm_nat"] = df["country_of_citizenship"].fillna("").astype(str).apply(normalize_name)
        df["norm_club"] = df["current_club_name"].fillna("").astype(str).apply(normalize_name)
        df["norm_comp"] = df["current_club_domestic_competition_id"].fillna("").astype(str).str.lower()

        # Check features availability
        if self.stage1_feat_path.exists():
            f_df = pd.read_parquet(self.stage1_feat_path, columns=["player_id"])
            self._stage1_players_with_features = set(f_df["player_id"].dropna().astype(int).unique())

        self._stage1_df = df
        return self._stage1_df

    def _load_global(self) -> pd.DataFrame:
        """Lazy load and index global players catalog."""
        if self._global_df is not None:
            return self._global_df

        if not self.global_path.exists():
            logger.warning("Global players catalog missing: %s", self.global_path)
            self._global_df = pd.DataFrame()
            return self._global_df

        df = pd.read_parquet(self.global_path)
        df["norm_name"] = df["full_name"].fillna("").astype(str).apply(normalize_name)
        df["norm_disp"] = df["display_name"].fillna("").astype(str).apply(normalize_name)
        df["norm_nat"] = df["nationality"].fillna("").astype(str).apply(normalize_name)
        df["norm_club"] = df["current_club_name"].fillna("").astype(str).apply(normalize_name)
        df["norm_comp"] = df["current_competition_name"].fillna("").astype(str).apply(normalize_name)
        df["norm_country"] = df["country"].fillna("").astype(str).apply(normalize_name)

        self._global_df = df
        return self._global_df

    def search(
        self,
        query: str,
        limit: int = 30,
        position_filter: str | None = None,
        country_filter: str | None = None,
    ) -> tuple[list[SearchResult], str]:
        """Execute two-stage search sequence.

        Returns (results_list, status_message).
        """
        raw_query = (query or "").strip()
        if not raw_query and not position_filter and not country_filter:
            return [], ""

        norm_q = normalize_name(raw_query)

        # ---------------------------------------------------------
        # STAGE 1: Search Existing Stage 1 Database First
        # ---------------------------------------------------------
        stage1_matches = self._search_stage1(norm_q, limit, position_filter, country_filter)

        if stage1_matches:
            # Step 1 Success: Found valid results in Stage 1 database!
            # Strictly do NOT query fallback database when original database returns results!
            logger.debug("Query '%s' resolved by STAGE 1 DATABASE (%d matches)", raw_query, len(stage1_matches))
            return stage1_matches, f"Found {len(stage1_matches)} player(s) in Stage 1 database."

        # ---------------------------------------------------------
        # STAGE 2: Fall back to global_players ONLY when Stage 1 is ZERO
        # ---------------------------------------------------------
        logger.debug("Query '%s' returned 0 Stage 1 results; falling back to GLOBAL DATABASE...", raw_query)
        global_matches = self._search_global(norm_q, limit, position_filter, country_filter)

        if global_matches:
            logger.debug("Query '%s' resolved by GLOBAL DATABASE (%d matches)", raw_query, len(global_matches))
            return global_matches, f"Found {len(global_matches)} player(s) in global player catalog."

        # ---------------------------------------------------------
        # STAGE 3: Both returned zero results
        # ---------------------------------------------------------
        return [], NO_RESULTS_MESSAGE

    def _search_stage1(
        self,
        norm_q: str,
        limit: int,
        position_filter: str | None,
        country_filter: str | None,
    ) -> list[SearchResult]:
        """Filter Stage 1 players dataframe."""
        df = self._load_stage1()
        if df.empty:
            return []

        mask = pd.Series(True, index=df.index)

        if norm_q:
            # Match on name, nationality, club, or competition
            m_name = df["norm_name"].str.contains(norm_q, regex=False, na=False)
            m_nat = df["norm_nat"].str.contains(norm_q, regex=False, na=False)
            m_club = df["norm_club"].str.contains(norm_q, regex=False, na=False)
            m_comp = df["norm_comp"].str.contains(norm_q, regex=False, na=False)
            mask = mask & (m_name | m_nat | m_club | m_comp)

        if position_filter and position_filter != "ALL":
            mask = mask & (df["position"].str.lower() == position_filter.lower())

        if country_filter and country_filter != "ALL":
            norm_cf = normalize_name(country_filter)
            # Strictly nationality or club country
            mask = mask & (df["norm_nat"].str.contains(norm_cf, regex=False, na=False))

        sub = df[mask].head(limit)
        results = []
        for _, r in sub.iterrows():
            pid = int(r["player_id"])
            can_pred = pid in self._stage1_players_with_features
            results.append(
                SearchResult(
                    player_id=pid,
                    name=str(r.get("name", "")),
                    display_name=str(r.get("name", "")),
                    date_of_birth=str(r.get("date_of_birth", "")).split()[0]
                    if pd.notna(r.get("date_of_birth"))
                    else None,
                    age=None,  # Will be dynamically computed from DOB
                    nationality=str(r.get("country_of_citizenship", "Unknown")),
                    current_club_name=str(r.get("current_club_name", "Unknown")),
                    current_competition_name=str(r.get("current_club_domestic_competition_id", "Global")),
                    country=str(r.get("country_of_citizenship", "Global")),
                    position=str(r.get("position", "Missing")),
                    source_database="STAGE 1 DATABASE",
                    profile_coverage_status="FULL_EVIDENCE" if can_pred else "LIMITED_EVIDENCE",
                    can_predict=can_pred,
                    image_url=None,
                    match_field="stage1",
                )
            )
        return results

    def _search_global(
        self,
        norm_q: str,
        limit: int,
        position_filter: str | None,
        country_filter: str | None,
    ) -> list[SearchResult]:
        """Filter global players dataframe."""
        df = self._load_global()
        if df.empty:
            return []

        mask = pd.Series(True, index=df.index)

        if norm_q:
            m_name = df["norm_name"].str.contains(norm_q, regex=False, na=False)
            m_disp = df["norm_disp"].str.contains(norm_q, regex=False, na=False)
            m_nat = df["norm_nat"].str.contains(norm_q, regex=False, na=False)
            m_club = df["norm_club"].str.contains(norm_q, regex=False, na=False)
            m_comp = df["norm_comp"].str.contains(norm_q, regex=False, na=False)
            m_cntry = df["norm_country"].str.contains(norm_q, regex=False, na=False)
            mask = mask & (m_name | m_disp | m_nat | m_club | m_comp | m_cntry)

        if position_filter and position_filter != "ALL":
            mask = mask & (df["position"].str.lower() == position_filter.lower())

        if country_filter and country_filter != "ALL":
            norm_cf = normalize_name(country_filter)
            mask = mask & (
                df["norm_nat"].str.contains(norm_cf, regex=False, na=False)
                | df["norm_country"].str.contains(norm_cf, regex=False, na=False)
            )

        sub = df[mask].head(limit)
        results = []
        for _, r in sub.iterrows():
            cov_status = str(r.get("profile_coverage_status", "PROFILE_ONLY"))
            can_pred = cov_status == "FULL_EVIDENCE"
            results.append(
                SearchResult(
                    player_id=str(r.get("global_player_id")),
                    name=str(r.get("full_name", "")),
                    display_name=str(r.get("display_name", "")),
                    date_of_birth=str(r.get("date_of_birth", "")).split()[0]
                    if pd.notna(r.get("date_of_birth"))
                    else None,
                    age=int(r["age"]) if pd.notna(r.get("age")) else None,
                    nationality=str(r.get("nationality", "Unknown")),
                    current_club_name=str(r.get("current_club_name", "Unknown")),
                    current_competition_name=str(r.get("current_competition_name", "Global")),
                    country=str(r.get("country", "Global")),
                    position=str(r.get("position", "Missing")),
                    source_database="GLOBAL DATABASE",
                    profile_coverage_status=cov_status,
                    can_predict=can_pred,
                    image_url=str(r.get("player_image_url")) if pd.notna(r.get("player_image_url")) else None,
                    match_field="global",
                )
            )
        return results

    def get_player_by_id(self, identifier: str | int) -> tuple[dict[str, Any] | None, str]:
        """Retrieve full player profile by ID, identifying database source."""
        # Check Stage 1 if integer or tm_
        if isinstance(identifier, int) or (isinstance(identifier, str) and identifier.isdigit()):
            pid = int(identifier)
            df1 = self._load_stage1()
            row = df1[df1["player_id"] == pid]
            if not row.empty:
                return row.iloc[0].to_dict(), "STAGE 1 DATABASE"

        if isinstance(identifier, str) and identifier.startswith("tm_"):
            try:
                pid = int(identifier.replace("tm_", ""))
                df1 = self._load_stage1()
                row = df1[df1["player_id"] == pid]
                if not row.empty:
                    return row.iloc[0].to_dict(), "STAGE 1 DATABASE"
            except ValueError:
                pass

        # Query global catalog
        df_g = self._load_global()
        if not df_g.empty:
            row_g = df_g[df_g["global_player_id"] == str(identifier)]
            if not row_g.empty:
                return row_g.iloc[0].to_dict(), "GLOBAL DATABASE"

        return None, "UNKNOWN"
