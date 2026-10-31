"""Data access and analytics service for Global Football Analytics Dashboard."""

import json
import logging
from typing import Any

import pandas as pd
import streamlit as st

from config.settings import (
    METADATA_DIR,
    PROCESSED_DATA_DIR,
    RAW_TM_DIR,
    TARGET_COLUMN,
)
from src.coverage_manager import CoverageManager
from src.global_player_search import SearchResult, TwoStageSearchService
from src.performance_enrichment import PerformanceEnrichmentService
from src.valuation_enrichment import ValuationEnrichmentService

logger = logging.getLogger(__name__)


@st.cache_data(show_spinner=False)
def load_processed_features() -> pd.DataFrame:
    """Load analytical feature dataset (70k+ player-season rows)."""
    feat_path = PROCESSED_DATA_DIR / "player_season_features.parquet"
    if not feat_path.exists():
        raise FileNotFoundError(f"Processed feature file not found: {feat_path}")
    df = pd.read_parquet(feat_path)

    # Ensure numeric types and clean formats
    df["historical_market_value"] = pd.to_numeric(df[TARGET_COLUMN], errors="coerce").fillna(0.0)
    df["age_at_reference_date"] = pd.to_numeric(df["age_at_reference_date"], errors="coerce")
    df["season"] = pd.to_numeric(df["season"], errors="coerce").astype(int)
    return df


@st.cache_data(show_spinner=False)
def load_player_image_map() -> dict[int, str]:
    """Load player_id -> image_url mapping from raw players table."""
    p_path = RAW_TM_DIR / "players.csv.gz"
    if not p_path.exists():
        return {}
    try:
        pdf = pd.read_csv(p_path, compression="gzip", usecols=["player_id", "image_url"], low_memory=False)
        pdf = pdf.dropna(subset=["player_id", "image_url"])
        pdf["player_id"] = pd.to_numeric(pdf["player_id"], errors="coerce").astype("int64")
        return dict(zip(pdf["player_id"], pdf["image_url"], strict=False))
    except Exception as e:
        logger.warning("Could not load player image map: %s", e)
        return {}


@st.cache_data(show_spinner=False)
def load_competition_registry() -> dict[str, Any]:
    """Load competition registry metadata."""
    reg_path = METADATA_DIR / "competition_registry.json"
    if not reg_path.exists():
        return {}
    try:
        with open(reg_path, encoding="utf-8") as f:
            data = json.load(f)
            return data.get("competitions", data)
    except Exception as e:
        logger.warning("Error loading competition registry: %s", e)
        return {}


@st.cache_data(show_spinner=False)
def load_league_strength_ratings() -> dict[str, Any]:
    """Load cross-league Elo ratings metadata."""
    ls_path = METADATA_DIR / "league_strength_ratings.json"
    if not ls_path.exists():
        return {}
    try:
        with open(ls_path, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning("Error loading league strength ratings: %s", e)
        return {}


@st.cache_data(show_spinner=False)
def load_evaluation_metrics() -> dict[str, Any]:
    """Load model evaluation results."""
    eval_path = METADATA_DIR / "evaluation_results.json"
    if not eval_path.exists():
        return {}
    try:
        with open(eval_path, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning("Error loading evaluation metrics: %s", e)
        return {}


class DataService:
    """High-level query and filtering engine for dashboard components."""

    def __init__(self) -> None:
        self.df = load_processed_features()
        self.image_map = load_player_image_map()
        self.registry = load_competition_registry()
        self.league_strengths = load_league_strength_ratings()
        self.eval_metrics = load_evaluation_metrics()
        self.search_service = TwoStageSearchService()
        self.coverage_manager = CoverageManager()
        self.perf_service = PerformanceEnrichmentService()
        self.val_service = ValuationEnrichmentService()

    def get_seasons(self) -> list[int]:
        """Return list of available historical seasons, descending."""
        return sorted(self.df["season"].dropna().unique().tolist(), reverse=True)

    def get_competitions(self) -> list[dict[str, Any]]:
        """Return list of registered competitions with code, name, and country."""
        comps = []
        for cid, info in self.registry.items():
            if isinstance(info, dict):
                comps.append(
                    {
                        "id": cid,
                        "name": info.get("competition_name", cid).replace("-", " ").title(),
                        "country": info.get("country", "Global"),
                        "status": info.get("reliability_status", "SUPPORTED"),
                        "matches": info.get("matches_available", 0),
                    }
                )
        # Sort Top 5 first, then alphabetical
        top5_order = ["GB1", "ES1", "L1", "IT1", "FR1"]
        return sorted(comps, key=lambda c: (top5_order.index(c["id"]) if c["id"] in top5_order else 99, c["name"]))

    def get_countries(self) -> list[str]:
        """Return unique nationalities of players."""
        countries = self.df["country_of_citizenship"].dropna().unique().tolist()
        return [c for c in sorted(countries) if c and c != "Unknown"]

    def get_clubs(self, competition_id: str | None = None, season: int | None = None) -> list[dict[str, Any]]:
        """Return clubs matching the competition and season context."""
        sub = self.df
        if season:
            sub = sub[sub["season"] == season]
        if competition_id and competition_id != "ALL":
            sub = sub[sub["competition_id"] == competition_id]

        clubs = (
            sub[["club_id", "current_club_name"]]
            .dropna()
            .drop_duplicates(subset=["club_id"])
            .sort_values("current_club_name")
        )
        return [{"id": int(r["club_id"]), "name": str(r["current_club_name"])} for _, r in clubs.iterrows()]

    def filter_data(
        self,
        season: int | None = None,
        competition_id: str | None = None,
        country: str | None = None,
        club_id: int | None = None,
        position: str | None = None,
        age_range: tuple[int, int] | None = None,
        value_range_eur: tuple[float, float] | None = None,
    ) -> pd.DataFrame:
        """Apply dynamic filters to the dataset."""
        df_filtered = self.df
        if season:
            df_filtered = df_filtered[df_filtered["season"] == season]
        if competition_id and competition_id != "ALL":
            df_filtered = df_filtered[df_filtered["competition_id"] == competition_id]
        if country and country != "ALL":
            df_filtered = df_filtered[df_filtered["country_of_citizenship"] == country]
        if club_id and club_id != 0:
            df_filtered = df_filtered[df_filtered["club_id"] == club_id]
        if position and position != "ALL":
            df_filtered = df_filtered[df_filtered["position"] == position]
        if age_range:
            min_age, max_age = age_range
            df_filtered = df_filtered[df_filtered["age_at_reference_date"].between(min_age, max_age)]
        if value_range_eur:
            min_v, max_v = value_range_eur
            df_filtered = df_filtered[df_filtered["historical_market_value"].between(min_v, max_v)]

        return df_filtered

    def get_kpis(self, df: pd.DataFrame) -> dict[str, Any]:
        """Compute top-level KPI metrics from filtered data."""
        if len(df) == 0:
            return {
                "unique_players": 0,
                "total_records": 0,
                "total_market_value": 0.0,
                "avg_market_value": 0.0,
                "highest_market_value": 0.0,
                "competitions_count": 0,
                "countries_count": 0,
                "seasons_count": 0,
            }

        return {
            "unique_players": int(df["player_id"].nunique()),
            "total_records": len(df),
            "total_market_value": float(df["historical_market_value"].sum()),
            "avg_market_value": float(df["historical_market_value"].mean()),
            "highest_market_value": float(df["historical_market_value"].max()),
            "competitions_count": int(df["competition_id"].nunique()),
            "countries_count": int(df["country_of_citizenship"].nunique()),
            "seasons_count": int(df["season"].nunique()),
        }

    def get_top_valuable_players(self, df: pd.DataFrame, limit: int = 10) -> pd.DataFrame:
        """Fetch top N most valuable players from the current filtered view."""
        if len(df) == 0:
            return pd.DataFrame()

        top = (
            df.sort_values("historical_market_value", ascending=False)
            .drop_duplicates(subset=["player_id"])
            .head(limit)
            .copy()
        )
        top["image_url"] = top["player_id"].map(self.image_map)
        return top

    def get_market_value_by_league(self, df: pd.DataFrame) -> pd.DataFrame:
        """Aggregate total, average, and median market value by league."""
        if len(df) == 0:
            return pd.DataFrame()

        agg = (
            df.groupby("competition_id")
            .agg(
                total_market_value=("historical_market_value", "sum"),
                avg_market_value=("historical_market_value", "mean"),
                median_market_value=("historical_market_value", "median"),
                player_count=("player_id", "nunique"),
            )
            .reset_index()
        )

        # Add human-readable league names
        comp_names = {
            cid: info.get("competition_name", cid).replace("-", " ").title()
            for cid, info in self.registry.items()
            if isinstance(info, dict)
        }
        agg["league_name"] = agg["competition_id"].map(comp_names).fillna(agg["competition_id"])
        return agg.sort_values("total_market_value", ascending=False)

    def get_market_value_by_country(self, df: pd.DataFrame, by_player_nationality: bool = True) -> pd.DataFrame:
        """Aggregate market value by country (either player nationality or league country)."""
        if len(df) == 0:
            return pd.DataFrame()

        col = "country_of_citizenship" if by_player_nationality else "competition_country"
        if col not in df.columns and not by_player_nationality:
            col = "country_of_citizenship"

        agg = (
            df.groupby(col)
            .agg(
                total_market_value=("historical_market_value", "sum"),
                avg_market_value=("historical_market_value", "mean"),
                player_count=("player_id", "nunique"),
            )
            .reset_index()
            .rename(columns={col: "country"})
        )
        agg = agg[agg["country"] != "Unknown"]
        return agg.sort_values("total_market_value", ascending=False)

    def search_players(self, query: str, df: pd.DataFrame | None = None, limit: int = 15) -> list[dict[str, Any]]:
        """Fast player search by name, club, or nationality."""
        source = df if df is not None else self.df
        if not query or len(query.strip()) < 2:
            return []

        q = query.strip().lower()
        mask = (
            source["name"].str.lower().str.contains(q, na=False)
            | source["current_club_name"].str.lower().str.contains(q, na=False)
            | source["country_of_citizenship"].str.lower().str.contains(q, na=False)
        )
        matches = source[mask].sort_values("season", ascending=False).drop_duplicates(subset=["player_id"]).head(limit)

        results = []
        for _, r in matches.iterrows():
            pid = int(r["player_id"])
            results.append(
                {
                    "player_id": pid,
                    "name": str(r["name"]),
                    "current_club_name": str(r.get("current_club_name", "Unknown")),
                    "club_id": int(r.get("club_id", 0)) if pd.notna(r.get("club_id")) else None,
                    "competition_id": str(r.get("competition_id", "GB1")),
                    "position": str(r.get("position", "Attack")),
                    "sub_position": str(r.get("sub_position", "Unknown")),
                    "age": round(float(r.get("age_at_reference_date", 24.0)), 1),
                    "goals": int(r.get("goals", 0)),
                    "assists": int(r.get("assists", 0)),
                    "appearances": int(r.get("appearances", 0)),
                    "minutes_played": int(r.get("minutes_played", 0)),
                    "market_value_eur": float(r.get("historical_market_value", 0.0)),
                    "previous_market_value": float(r.get("previous_market_value", 0.0))
                    if pd.notna(r.get("previous_market_value"))
                    else None,
                    "season": int(r.get("season", 2023)),
                    "image_url": self.image_map.get(pid),
                }
            )
        return results

    def get_player_history(self, player_id: int) -> pd.DataFrame:
        """Fetch historical seasons and valuations for a specific player."""
        sub = self.df[self.df["player_id"] == player_id].sort_values("season")
        return sub

    def search_players_two_stage(
        self,
        query: str,
        limit: int = 30,
        position_filter: str | None = None,
        country_filter: str | None = None,
    ) -> tuple[list[SearchResult], str]:
        """Execute two-stage search: Stage 1 priority with automatic global fallback."""
        return self.search_service.search(
            query=query,
            limit=limit,
            position_filter=position_filter,
            country_filter=country_filter,
        )

    def get_player_profile_bundle(self, identifier: str | int) -> dict[str, Any] | None:
        """Retrieve complete player bundle: profile, coverage assessment, stats, valuations."""
        record, source_db = self.search_service.get_player_by_id(identifier)
        if not record:
            return None

        gid = record.get("global_player_id") or f"tm_{record.get('player_id')}"
        stats = self.perf_service.get_player_stats(str(gid))
        vals = self.val_service.get_valuation_history(str(gid))

        assessment = self.coverage_manager.assess_player(
            player_record=record,
            has_performance_data=len(stats) > 0,
            has_historical_valuation=len(vals) > 0,
            is_stage1_source=(source_db == "STAGE 1 DATABASE"),
        )

        return {
            "record": record,
            "source_database": source_db,
            "assessment": assessment,
            "stats": stats,
            "valuations": vals,
        }
