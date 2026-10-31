"""Historical player-season feature engineering module.

Constructs leakage-safe analytical dataset at the player-season-competition-club
grain. Computes reference-date aligned age, performance statistics, lag market
valuations, competition strength, club strength, and financial features.
"""

import logging
from pathlib import Path

import pandas as pd

from config.settings import (
    INTERIM_DATA_DIR,
    MIN_MINUTES_PLAYED_FILTER,
    PROCESSED_DATA_DIR,
)
from src.competition_registry import CompetitionRegistry
from src.financial_context import FinancialContextEngine
from src.league_strength import LeagueStrengthEngine

logger = logging.getLogger(__name__)


class PlayerFeatureEngineer:
    """Builds reproducible player-season features with strict temporal cutoff alignment."""

    def __init__(
        self,
        interim_dir: Path = INTERIM_DATA_DIR,
        out_dir: Path = PROCESSED_DATA_DIR,
        min_minutes: int = MIN_MINUTES_PLAYED_FILTER,
    ) -> None:
        self.interim_dir = interim_dir
        self.out_dir = out_dir
        self.min_minutes = min_minutes
        self.registry = CompetitionRegistry()
        self.league_engine = LeagueStrengthEngine()
        self.financial_engine = FinancialContextEngine()

    def build_feature_table(
        self,
        seasons: list[int] | None = None,
        competitions: list[str] | None = None,
    ) -> pd.DataFrame:
        """Construct the analytical player-season feature dataset."""
        self.out_dir.mkdir(parents=True, exist_ok=True)
        if not self.league_engine.is_fitted:
            logger.info("Fitting LeagueStrengthEngine...")
            self.league_engine.fit()

        logger.info("Loading cleaned interim datasets from %s...", self.interim_dir)
        vals = pd.read_parquet(self.interim_dir / "clean_player_valuations.parquet")
        players = pd.read_parquet(self.interim_dir / "clean_players.parquet")
        apps = pd.read_parquet(self.interim_dir / "clean_appearances.parquet")
        games = pd.read_parquet(self.interim_dir / "clean_games.parquet", columns=["game_id", "season", "date"])

        # Link appearances with game season and match date
        logger.info("Merging appearances with games...")
        apps_merged = apps.merge(games[["game_id", "season"]], on="game_id", how="inner")

        # Determine target seasons (default 2013 to 2024 where appearances + valuations overlap)
        available_seasons = sorted([int(s) for s in apps_merged["season"].unique() if s >= 2013 and s <= 2024])
        target_seasons = seasons or available_seasons
        logger.info("Processing target seasons: %s", target_seasons)

        season_frames: list[pd.DataFrame] = []

        for season in target_seasons:
            season_start = pd.Timestamp(year=season, month=7, day=1)
            season_end = pd.Timestamp(year=season + 1, month=7, day=15)
            valuation_window_start = pd.Timestamp(year=season, month=11, day=1)

            logger.info(
                "Extracting features for Season %d (window: %s to %s)...",
                season,
                season_start.date(),
                season_end.date(),
            )

            # 1. Target valuations for this season: latest valuation within the season window
            season_vals = vals[(vals["date"] >= valuation_window_start) & (vals["date"] <= season_end)].copy()
            if season_vals.empty:
                logger.warning("No valuations found for season %d", season)
                continue

            season_vals = season_vals.sort_values(["player_id", "date"], ascending=[True, True])
            latest_vals = season_vals.drop_duplicates(subset=["player_id"], keep="last").copy()
            latest_vals = latest_vals.rename(
                columns={
                    "market_value_in_eur": "historical_market_value",
                    "date": "valuation_reference_date",
                    "player_club_domestic_competition_id": "val_competition_id",
                    "current_club_id": "val_club_id",
                }
            )

            # 2. Lag valuation: latest valuation strictly before season start (date < season_start)
            prior_vals = vals[vals["date"] < season_start].sort_values(["player_id", "date"], ascending=[True, True])
            lag_vals = prior_vals.drop_duplicates(subset=["player_id"], keep="last")[
                ["player_id", "market_value_in_eur", "date"]
            ].rename(
                columns={
                    "market_value_in_eur": "previous_market_value",
                    "date": "previous_valuation_date",
                }
            )

            # 3. Appearances up to each player's valuation reference date
            season_apps = apps_merged[apps_merged["season"] == season].copy()
            apps_with_ref = season_apps.merge(
                latest_vals[["player_id", "valuation_reference_date"]], on="player_id", how="inner"
            )

            # Strict temporal condition: appearance date must be on or before reference date!
            apps_valid = apps_with_ref[apps_with_ref["date"] <= apps_with_ref["valuation_reference_date"]].copy()
            if apps_valid.empty:
                logger.warning("No valid appearances before reference date for season %d", season)
                continue

            # Group performance by player_id, competition_id, player_club_id
            perf = (
                apps_valid.groupby(["player_id", "competition_id", "player_club_id"])
                .agg(
                    appearances=("game_id", "count"),
                    minutes_played=("minutes_played", "sum"),
                    goals=("goals", "sum"),
                    assists=("assists", "sum"),
                    yellow_cards=("yellow_cards", "sum"),
                    red_cards=("red_cards", "sum"),
                )
                .reset_index()
                .rename(columns={"player_club_id": "club_id"})
            )

            # Merge performance with target valuation
            merged_season = perf.merge(latest_vals, on="player_id", how="inner")
            # If club or competition was missing in valuation table, use appearance club/competition
            merged_season["competition_id"] = merged_season["val_competition_id"].fillna(
                merged_season["competition_id"]
            )
            merged_season["club_id"] = merged_season["val_club_id"].fillna(merged_season["club_id"]).astype("int64")
            merged_season["season"] = season

            # Merge lag valuation
            merged_season = merged_season.merge(lag_vals, on="player_id", how="left")
            merged_season["has_previous_valuation"] = merged_season["previous_market_value"].notna()

            # Merge player static info
            merged_season = merged_season.merge(
                players[
                    [
                        "player_id",
                        "name",
                        "date_of_birth",
                        "position",
                        "sub_position",
                        "foot",
                        "height_in_cm",
                        "country_of_citizenship",
                    ]
                ],
                on="player_id",
                how="inner",
            )

            season_frames.append(merged_season)

        if not season_frames:
            raise RuntimeError("No feature records could be constructed from available data.")

        df_all = pd.concat(season_frames, ignore_index=True)
        logger.info("Constructed %d raw player-season records before feature enrichment.", len(df_all))

        # 4. Compute age at reference date
        df_all["age_at_reference_date"] = (
            (df_all["valuation_reference_date"] - df_all["date_of_birth"]).dt.days / 365.25
        ).round(2)
        # Fallback for unparseable DoB: median age 25.0
        df_all["age_at_reference_date"] = df_all["age_at_reference_date"].fillna(25.0)

        # 5. Compute per-90 metrics (only when minutes > 0)
        df_all["cards"] = df_all["yellow_cards"] + df_all["red_cards"]
        has_minutes = df_all["minutes_played"] > 0
        df_all["goals_per_90"] = 0.0
        df_all["assists_per_90"] = 0.0
        df_all["cards_per_90"] = 0.0
        df_all.loc[has_minutes, "goals_per_90"] = (
            (df_all.loc[has_minutes, "goals"] / df_all.loc[has_minutes, "minutes_played"]) * 90.0
        ).round(3)
        df_all.loc[has_minutes, "assists_per_90"] = (
            (df_all.loc[has_minutes, "assists"] / df_all.loc[has_minutes, "minutes_played"]) * 90.0
        ).round(3)
        df_all.loc[has_minutes, "cards_per_90"] = (
            (df_all.loc[has_minutes, "cards"] / df_all.loc[has_minutes, "minutes_played"]) * 90.0
        ).round(3)
        df_all["minutes_per_appearance"] = (df_all["minutes_played"] / df_all["appearances"].clip(lower=1)).round(1)

        # 6. Enrich with League Strength and Competition Intensity
        logger.info("Enriching with league strength ratings...")
        comp_strengths = []
        comp_mean_elos = []
        comp_top4_elos = []
        comp_spread_elos = []
        goals_intensity = []
        cards_intensity = []
        balance_indices = []

        for _, row in df_all.iterrows():
            cid = str(row["competition_id"])
            s = int(row["season"])
            ls = self.league_engine.get_league_strength(cid, s)
            im = self.league_engine.get_intensity_metrics(cid, s)
            comp_strengths.append(ls["competition_strength"])
            comp_mean_elos.append(ls["mean_elo"])
            comp_top4_elos.append(ls["top4_strength"])
            comp_spread_elos.append(ls.get("spread_elo", 0.0))
            goals_intensity.append(im.get("goals_per_match", 2.7))
            cards_intensity.append(im.get("cards_per_match", 4.0))
            balance_indices.append(im.get("competitive_balance_index", 0.45))

        df_all["competition_strength"] = comp_strengths
        df_all["competition_mean_elo"] = comp_mean_elos
        df_all["competition_top4_strength"] = comp_top4_elos
        df_all["competition_spread_elo"] = comp_spread_elos
        df_all["league_goals_per_match"] = goals_intensity
        df_all["league_cards_per_match"] = cards_intensity
        df_all["competitive_balance_index"] = balance_indices

        # Club Elo rating
        df_all["club_elo"] = df_all["club_id"].apply(self.league_engine.get_club_elo)

        # 7. Enrich with Financial Context
        logger.info("Enriching with financial context...")
        df_all = self.financial_engine.enrich_features_df(df_all)

        # 8. Source coverage score
        coverage_score = (
            (df_all["minutes_played"] >= 90).astype(float) * 0.3
            + df_all["has_previous_valuation"].astype(float) * 0.3
            + (df_all["has_club_financials"] | df_all["has_league_financials"]).astype(float) * 0.2
            + (df_all["competition_strength"] > 1.0).astype(float) * 0.2
        )
        df_all["source_coverage_score"] = coverage_score.round(2)

        # Apply minimum minutes filter
        initial_rows = len(df_all)
        filtered = df_all[df_all["minutes_played"] >= self.min_minutes].copy()
        logger.info("Filtered %d -> %d records with min_minutes >= %d", initial_rows, len(filtered), self.min_minutes)

        # Drop duplicates on analytical grain (player_id, season, competition_id, club_id)
        filtered = filtered.drop_duplicates(subset=["player_id", "season", "competition_id", "club_id"])

        # Filter by competitions if requested
        if competitions:
            filtered = filtered[filtered["competition_id"].isin(competitions)].copy()

        dest_file = self.out_dir / "player_season_features.parquet"
        filtered.to_parquet(dest_file, index=False)
        logger.info("Saved %d player-season feature records to %s", len(filtered), dest_file)
        return filtered


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    engineer = PlayerFeatureEngineer()
    df_features = engineer.build_feature_table()
    print("\nFeature Table Overview:")
    print(f"Total Rows: {len(df_features):,}")
    print(f"Competitions: {df_features['competition_id'].value_counts().head(10).to_dict()}")
    print(f"Seasons: {df_features['season'].value_counts().sort_index().to_dict()}")
    print("\nSample records:")
    print(
        df_features[
            [
                "player_id",
                "name",
                "season",
                "competition_id",
                "age_at_reference_date",
                "minutes_played",
                "goals",
                "assists",
                "historical_market_value",
                "competition_strength",
            ]
        ].head(5)
    )
