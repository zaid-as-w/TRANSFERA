"""StatsBomb Open Data connector.

Extracts verified player identities, appearances, match events, and
competition metadata from StatsBomb's open repository (https://github.com/statsbomb/open-data).
Supports Indian Super League, African Cup of Nations, and global tournaments.
"""

from __future__ import annotations

import json
import logging
import urllib.request
from pathlib import Path
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)

STATSBOMB_DIR = Path("data/external/statsbomb")
BASE_URL = "https://raw.githubusercontent.com/statsbomb/open-data/master/data"


class StatsBombConnector:
    """Connector for StatsBomb open data repository."""

    def __init__(self, data_dir: Path | str = STATSBOMB_DIR):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.matches_dir = self.data_dir / "matches"
        self.matches_dir.mkdir(parents=True, exist_ok=True)
        self.lineups_dir = self.data_dir / "lineups"
        self.lineups_dir.mkdir(parents=True, exist_ok=True)

    def fetch_competitions(self) -> list[dict[str, Any]]:
        """Fetch list of open competitions."""
        local_path = self.data_dir / "competitions.json"
        if local_path.exists():
            try:
                with open(local_path, encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning("Error reading local competitions.json: %s", e)

        url = f"{BASE_URL}/competitions.json"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "TRANSFERA/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                with open(local_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
                return data
        except Exception as e:
            logger.warning("Could not fetch StatsBomb competitions: %s", e)
            return []

    def fetch_matches(self, competition_id: int, season_id: int) -> list[dict[str, Any]]:
        """Fetch matches for a given competition and season."""
        local_path = self.matches_dir / f"{competition_id}_{season_id}.json"
        if local_path.exists():
            try:
                with open(local_path, encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning("Error reading local matches: %s", e)

        url = f"{BASE_URL}/matches/{competition_id}/{season_id}.json"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "TRANSFERA/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                with open(local_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
                return data
        except Exception as e:
            logger.warning("Could not fetch matches for comp %s: %s", competition_id, e)
            return []

    def fetch_lineup(self, match_id: int) -> list[dict[str, Any]]:
        """Fetch match lineups for a match."""
        local_path = self.lineups_dir / f"{match_id}.json"
        if local_path.exists():
            try:
                with open(local_path, encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning("Error reading local lineup: %s", e)

        url = f"{BASE_URL}/lineups/{match_id}.json"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "TRANSFERA/1.0"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                with open(local_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
                return data
        except Exception as e:
            logger.debug("Lineup fetch failed for match %s: %s", match_id, e)
            return []

    def extract_competition_players(
        self,
        competition_id: int,
        season_id: int,
        max_matches: int = 15,
    ) -> pd.DataFrame:
        """Extract verified player profiles and stats from a competition's matches."""
        matches = self.fetch_matches(competition_id, season_id)
        if not matches:
            return pd.DataFrame()

        player_records: dict[int, dict[str, Any]] = {}

        for match in matches[:max_matches]:
            mid = match["match_id"]
            lineups = self.fetch_lineup(mid)
            for team in lineups:
                team_name = team.get("team_name", "Unknown")
                for p in team.get("lineup", []):
                    pid = p["player_id"]
                    if pid not in player_records:
                        player_records[pid] = {
                            "statsbomb_player_id": pid,
                            "full_name": p.get("player_name"),
                            "display_name": p.get("player_nickname") or p.get("player_name"),
                            "nationality": p.get("country", {}).get("name"),
                            "current_club_name": team_name,
                            "current_competition_name": match.get("competition", {}).get("competition_name"),
                            "country": match.get("competition", {}).get("country_name"),
                            "appearances": 0,
                            "minutes_played": 0,
                            "goals": 0,
                            "assists": 0,
                            "yellow_cards": 0,
                            "red_cards": 0,
                        }

                    # Track appearances and minutes
                    rec = player_records[pid]
                    rec["appearances"] += 1
                    # Rough calculation from positions
                    mins = 0
                    for pos in p.get("positions", []):
                        from_m = pos.get("from", "00:00")
                        to_m = pos.get("to") or "90:00"
                        try:
                            f_min = int(from_m.split(":")[0])
                            t_min = int(to_m.split(":")[0])
                            mins += max(0, t_min - f_min)
                        except Exception:
                            mins += 45
                    rec["minutes_played"] += mins or 90

                    for card in p.get("cards", []):
                        ctype = card.get("card_type", "").lower()
                        if "yellow" in ctype:
                            rec["yellow_cards"] += 1
                        elif "red" in ctype:
                            rec["red_cards"] += 1

        if not player_records:
            return pd.DataFrame()

        return pd.DataFrame(list(player_records.values()))
