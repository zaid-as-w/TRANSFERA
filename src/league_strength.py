"""League Strength and Competition Intensity Engine.

Computes mathematically grounded, cross-league calibrated ratings using
chronological Elo ratings across domestic league games and 3,900+ cross-competition
European tournament matches (Champions League, Europa League, Conference League).

Derives competition intensity, competitive balance, and club-level ratings
without hardcoded arbitrary league multipliers.
"""

import json
import logging
import math
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from config.settings import (
    CONTINENTAL_COMPETITIONS,
    METADATA_DIR,
    RAW_TM_DIR,
)

logger = logging.getLogger(__name__)

INITIAL_ELO = 1500.0
HOME_ADVANTAGE = 65.0
K_DOMESTIC = 20.0
K_CONTINENTAL = 32.0


class LeagueStrengthEngine:
    """Calculates cross-league calibrated Elo ratings and competition intensity."""

    def __init__(
        self,
        ratings_cache_path: Path | None = None,
    ) -> None:
        self.ratings_cache_path = ratings_cache_path or (METADATA_DIR / "league_strength_ratings.json")
        self.club_ratings: dict[int, float] = {}
        self.league_ratings: dict[str, dict[str, Any]] = {}
        self.league_season_ratings: dict[tuple[str, int], dict[str, Any]] = {}
        self.intensity_metrics: dict[tuple[str, int], dict[str, Any]] = {}
        self.is_fitted = False

        if self.ratings_cache_path.exists():
            self._load_cached_ratings()

    def _load_cached_ratings(self) -> None:
        try:
            with open(self.ratings_cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.league_ratings = data.get("league_ratings", {})
                for key_str, val in data.get("league_season_ratings", {}).items():
                    comp_id, season_str = key_str.split("_")
                    self.league_season_ratings[(comp_id, int(season_str))] = val
                for key_str, val in data.get("intensity_metrics", {}).items():
                    comp_id, season_str = key_str.split("_")
                    self.intensity_metrics[(comp_id, int(season_str))] = val
                self.is_fitted = True
            logger.info("Loaded league strength ratings from cache: %s", self.ratings_cache_path.name)
        except Exception as e:
            logger.warning("Could not load ratings cache: %s", e)

    def fit(self, raw_dir: Path = RAW_TM_DIR) -> dict[str, Any]:
        """Fit cross-league Elo model on historical matches chronologically."""
        games_file = raw_dir / "games.csv.gz"
        clubs_file = raw_dir / "clubs.csv.gz"
        apps_file = raw_dir / "appearances.csv.gz"

        if not games_file.exists() or not clubs_file.exists():
            raise FileNotFoundError(f"Required raw files missing: {games_file} or {clubs_file}")

        logger.info("Loading games and clubs for cross-league Elo calibration...")
        games_cols = [
            "game_id",
            "competition_id",
            "season",
            "date",
            "home_club_id",
            "away_club_id",
            "home_club_goals",
            "away_club_goals",
        ]
        games = pd.read_csv(games_file, compression="gzip", low_memory=False, usecols=games_cols)
        clubs = pd.read_csv(
            clubs_file, compression="gzip", low_memory=False, usecols=["club_id", "domestic_competition_id"]
        )

        games = games.dropna(subset=["home_club_id", "away_club_id", "home_club_goals", "away_club_goals", "date"])
        games["date"] = pd.to_datetime(games["date"], errors="coerce")
        games = games.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)

        club_domestic = clubs.set_index("club_id")["domestic_competition_id"].to_dict()

        # Track ratings over time
        ratings: dict[int, float] = {}
        club_seasons_history: dict[tuple[int, int], list[float]] = {}
        cross_league_match_counts: dict[str, int] = {}

        # 1. Simulate matches chronologically
        for _, match in games.iterrows():
            h_id = int(match["home_club_id"])
            a_id = int(match["away_club_id"])
            h_goals = int(match["home_club_goals"])
            a_goals = int(match["away_club_goals"])
            comp_id = str(match["competition_id"])
            season = int(match["season"])

            r_h = ratings.get(h_id, INITIAL_ELO)
            r_a = ratings.get(a_id, INITIAL_ELO)

            is_continental = comp_id in CONTINENTAL_COMPETITIONS
            h_dom = club_domestic.get(h_id)
            a_dom = club_domestic.get(a_id)

            if is_continental and h_dom and a_dom and (h_dom != a_dom):
                cross_league_match_counts[h_dom] = cross_league_match_counts.get(h_dom, 0) + 1
                cross_league_match_counts[a_dom] = cross_league_match_counts.get(a_dom, 0) + 1

            k = K_CONTINENTAL if is_continental else K_DOMESTIC

            # Expected scores
            exp_h = 1.0 / (1.0 + 10.0 ** ((r_a - (r_h + HOME_ADVANTAGE)) / 400.0))
            exp_a = 1.0 - exp_h

            # Actual score
            if h_goals > a_goals:
                act_h, act_a = 1.0, 0.0
            elif h_goals < a_goals:
                act_h, act_a = 0.0, 1.0
            else:
                act_h, act_a = 0.5, 0.5

            goal_diff = abs(h_goals - a_goals)
            margin_multiplier = math.log(goal_diff + 1.0) if goal_diff > 1 else 1.0

            delta_h = k * margin_multiplier * (act_h - exp_h)
            delta_a = k * margin_multiplier * (act_a - exp_a)

            ratings[h_id] = r_h + delta_h
            ratings[a_id] = r_a + delta_a

            club_seasons_history.setdefault((h_id, season), []).append(ratings[h_id])
            club_seasons_history.setdefault((a_id, season), []).append(ratings[a_id])

        self.club_ratings = ratings

        # 2. Aggregate ratings per league and league-season
        league_season_ratings: dict[tuple[str, int], dict[str, Any]] = {}
        all_seasons = sorted(games["season"].unique())
        domestic_comps = set(club_domestic.values())

        for season in all_seasons:
            for comp_id in domestic_comps:
                if not isinstance(comp_id, str):
                    continue
                # Find clubs in this domestic comp that played matches in this season
                comp_clubs = [cid for cid, dcomp in club_domestic.items() if dcomp == comp_id]
                club_elo_values = []
                for cid in comp_clubs:
                    if (cid, season) in club_seasons_history:
                        club_elo_values.append(np.mean(club_seasons_history[(cid, season)]))

                if club_elo_values:
                    mean_elo = float(np.mean(club_elo_values))
                    sorted_elos = sorted(club_elo_values, reverse=True)
                    top4_elo = float(np.mean(sorted_elos[:4])) if len(sorted_elos) >= 4 else mean_elo
                    spread_elo = float(np.std(club_elo_values)) if len(club_elo_values) > 1 else 0.0
                    cross_count = cross_league_match_counts.get(comp_id, 0)
                    has_evidence = cross_count >= 50

                    league_season_ratings[(comp_id, season)] = {
                        "competition_id": comp_id,
                        "season": season,
                        "mean_elo": round(mean_elo, 1),
                        "top4_elo": round(top4_elo, 1),
                        "spread_elo": round(spread_elo, 1),
                        "sample_clubs": len(club_elo_values),
                        "cross_league_matches": cross_count,
                        "has_evidence": has_evidence,
                        "normalized_strength": round(mean_elo / INITIAL_ELO, 4),
                        "top_strength": round(top4_elo / INITIAL_ELO, 4),
                    }

        self.league_season_ratings = league_season_ratings

        # 3. Overall league rating across all seasons
        overall_league: dict[str, dict[str, Any]] = {}
        for comp_id in domestic_comps:
            if not isinstance(comp_id, str):
                continue
            seasons_for_comp = [v for k, v in league_season_ratings.items() if k[0] == comp_id]
            if seasons_for_comp:
                avg_mean = float(np.mean([s["mean_elo"] for s in seasons_for_comp]))
                avg_top4 = float(np.mean([s["top4_elo"] for s in seasons_for_comp]))
                cross_recs = cross_league_match_counts.get(comp_id, 0)
                overall_league[comp_id] = {
                    "competition_id": comp_id,
                    "overall_mean_elo": round(avg_mean, 1),
                    "overall_top4_elo": round(avg_top4, 1),
                    "normalized_strength": round(avg_mean / INITIAL_ELO, 4),
                    "cross_league_matches": cross_recs,
                    "has_cross_league_evidence": cross_recs >= 50,
                    "method": "Multi-season Cross-League Continental Elo Integration",
                }

        self.league_ratings = overall_league

        # 4. Compute competition intensity and competitive balance metrics
        intensity_metrics: dict[tuple[str, int], dict[str, Any]] = {}
        cards_by_comp_season: dict[tuple[str, int], tuple[int, int]] = {}
        if apps_file.exists():
            apps = pd.read_csv(
                apps_file,
                compression="gzip",
                low_memory=False,
                usecols=["competition_id", "game_id", "yellow_cards", "red_cards"],
            )
            apps_with_season = apps.merge(games[["game_id", "season"]], on="game_id", how="inner")
            grouped_cards = apps_with_season.groupby(["competition_id", "season"])[["yellow_cards", "red_cards"]].sum()
            for (cid, s), r in grouped_cards.iterrows():
                cards_by_comp_season[(str(cid), int(s))] = (int(r["yellow_cards"]), int(r["red_cards"]))

        for (comp_id, season), g_sub in games.groupby(["competition_id", "season"]):
            comp_id_str = str(comp_id)
            season_int = int(season)
            match_count = len(g_sub)
            if match_count == 0:
                continue

            total_goals = (g_sub["home_club_goals"] + g_sub["away_club_goals"]).values
            goals_per_match = float(np.mean(total_goals))
            goal_diffs = np.abs(g_sub["home_club_goals"] - g_sub["away_club_goals"]).values
            draws = (g_sub["home_club_goals"] == g_sub["away_club_goals"]).sum()
            draw_pct = float(draws / match_count)
            goal_diff_std = float(np.std(goal_diffs))

            yellows, reds = cards_by_comp_season.get((comp_id_str, season_int), (0, 0))
            cards_per_match = float((yellows + reds) / match_count) if match_count > 0 else 0.0

            intensity_metrics[(comp_id_str, season_int)] = {
                "competition_id": comp_id_str,
                "season": season_int,
                "matches": match_count,
                "goals_per_match": round(goals_per_match, 2),
                "goal_diff_std": round(goal_diff_std, 2),
                "draw_pct": round(draw_pct, 3),
                "cards_per_match": round(cards_per_match, 2),
                "competitive_balance_index": round(1.0 / (1.0 + goal_diff_std), 3),
            }

        self.intensity_metrics = intensity_metrics
        self.is_fitted = True
        self.save_ratings()
        logger.info("Fitted league strength ratings across %d domestic competitions.", len(self.league_ratings))
        return {
            "domestic_competitions_calibrated": len(self.league_ratings),
            "cross_league_matches_analyzed": sum(cross_league_match_counts.values()) // 2,
        }

    def save_ratings(self) -> None:
        self.ratings_cache_path.parent.mkdir(parents=True, exist_ok=True)
        serializable_ls = {f"{k[0]}_{k[1]}": v for k, v in self.league_season_ratings.items()}
        serializable_im = {f"{k[0]}_{k[1]}": v for k, v in self.intensity_metrics.items()}
        payload = {
            "generated_at": datetime.now(UTC).isoformat(),
            "methodology": "Cross-league Elo rating integration with continental tournament calibration",
            "initial_elo": INITIAL_ELO,
            "league_ratings": self.league_ratings,
            "league_season_ratings": serializable_ls,
            "intensity_metrics": serializable_im,
        }

        def _json_serialize(obj: Any) -> Any:
            if isinstance(obj, (np.integer,)):
                return int(obj)
            if isinstance(obj, (np.floating,)):
                return float(obj)
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            return str(obj)

        with open(self.ratings_cache_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, default=_json_serialize)
        logger.info("Saved league strength ratings cache to %s", self.ratings_cache_path)

    def get_league_strength(
        self,
        competition_id: str,
        season: int | None = None,
    ) -> dict[str, Any]:
        """Retrieve competition strength estimate and provenance."""
        if not self.is_fitted:
            raise RuntimeError("LeagueStrengthEngine is not fitted. Call fit() first.")

        # Try season-specific rating
        if season is not None and (competition_id, season) in self.league_season_ratings:
            s_rec = self.league_season_ratings[(competition_id, season)]
            return {
                "competition_id": competition_id,
                "season": season,
                "competition_strength": s_rec["normalized_strength"],
                "top4_strength": s_rec["top_strength"],
                "mean_elo": s_rec["mean_elo"],
                "spread_elo": s_rec["spread_elo"],
                "has_cross_league_evidence": s_rec["has_evidence"],
                "cross_league_matches": s_rec["cross_league_matches"],
                "provenance": "season_cross_league_elo",
            }

        # Fallback to overall league rating
        if competition_id in self.league_ratings:
            o_rec = self.league_ratings[competition_id]
            return {
                "competition_id": competition_id,
                "season": season,
                "competition_strength": o_rec["normalized_strength"],
                "top4_strength": round(o_rec["overall_top4_elo"] / INITIAL_ELO, 4),
                "mean_elo": o_rec["overall_mean_elo"],
                "spread_elo": 0.0,
                "has_cross_league_evidence": o_rec["has_cross_league_evidence"],
                "cross_league_matches": o_rec["cross_league_matches"],
                "provenance": "overall_cross_league_elo",
            }

        # Unknown / insufficient evidence
        return {
            "competition_id": competition_id,
            "season": season,
            "competition_strength": 1.0,
            "top4_strength": 1.0,
            "mean_elo": INITIAL_ELO,
            "spread_elo": 0.0,
            "has_cross_league_evidence": False,
            "cross_league_matches": 0,
            "provenance": "uncalibrated_default",
            "warning": "INSUFFICIENT_EVIDENCE",
        }

    def get_intensity_metrics(
        self,
        competition_id: str,
        season: int | None = None,
    ) -> dict[str, Any]:
        """Retrieve competition intensity and competitive balance metrics."""
        if season is not None and (competition_id, season) in self.intensity_metrics:
            return self.intensity_metrics[(competition_id, season)]
        return {
            "competition_id": competition_id,
            "season": season,
            "goals_per_match": 2.7,
            "goal_diff_std": 1.2,
            "draw_pct": 0.25,
            "cards_per_match": 4.0,
            "competitive_balance_index": 0.45,
            "provenance": "default_intensity",
        }

    def get_club_elo(self, club_id: int) -> float:
        """Get calibrated club Elo rating."""
        return self.club_ratings.get(club_id, INITIAL_ELO)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    engine = LeagueStrengthEngine()
    engine.fit()
    print("\nCalibrated League Strength Estimates:")
    for comp in ["GB1", "ES1", "IT1", "L1", "FR1", "NL1", "PO1", "BE1", "TR1"]:
        st = engine.get_league_strength(comp, 2023)
        intens = engine.get_intensity_metrics(comp, 2023)
        print(
            f"  {comp}: Mean Elo={st['mean_elo']} (Strength={st['competition_strength']}), CrossMatches={st['cross_league_matches']}, Intensity(Goals={intens['goals_per_match']}, Cards={intens['cards_per_match']})"
        )
