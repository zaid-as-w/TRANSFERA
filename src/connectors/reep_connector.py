"""Reep Football Entity Register connector.

Acquires and maps global football identities, canonical IDs, and crosswalk
mappings from the Reep project (https://github.com/withqwerty/reep).
Filters out coaches to maintain an exclusive player catalog.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)

REEP_DIR = Path("data/external/reep")


class ReepConnector:
    """Connector for Reep football entity register."""

    def __init__(self, data_dir: Path | str = REEP_DIR):
        self.data_dir = Path(data_dir)
        self.people_path = self.data_dir / "people.csv"
        self.teams_path = self.data_dir / "teams.csv"
        self.competitions_path = self.data_dir / "competitions.csv"

    def load_competitions(self) -> pd.DataFrame:
        """Load Reep competitions crosswalk table."""
        if not self.competitions_path.exists():
            logger.warning("Reep competitions file missing: %s", self.competitions_path)
            return pd.DataFrame()

        df = pd.read_csv(self.competitions_path, low_memory=False)
        return df

    def load_teams(self) -> pd.DataFrame:
        """Load Reep teams crosswalk table."""
        if not self.teams_path.exists():
            logger.warning("Reep teams file missing: %s", self.teams_path)
            return pd.DataFrame()

        df = pd.read_csv(self.teams_path, low_memory=False)
        return df

    def load_players(
        self,
        max_rows: int | None = None,
        include_unlinked: bool = True,
    ) -> pd.DataFrame:
        """Load and normalize player records from Reep entity register.

        Excludes coaches (type == 'coach') and retains only verified players.
        """
        if not self.people_path.exists():
            logger.warning("Reep people file missing: %s", self.people_path)
            return pd.DataFrame()

        usecols = [
            "reep_id",
            "key_wikidata",
            "type",
            "name",
            "full_name",
            "date_of_birth",
            "nationality",
            "position",
            "position_detail",
            "height_cm",
            "key_transfermarkt",
            "key_fbref",
            "key_api_football",
            "key_sofascore",
            "key_fotmob",
            "key_wyscout",
        ]

        try:
            df = pd.read_csv(
                self.people_path,
                usecols=usecols,
                nrows=max_rows,
                low_memory=False,
            )
        except Exception as e:
            logger.error("Error reading Reep people.csv: %s", e)
            return pd.DataFrame()

        # Filter strictly for players (exclude coaches/managers)
        df = df[df["type"] == "player"].copy()

        # Normalize names
        df["full_name"] = df["full_name"].fillna(df["name"])
        df["display_name"] = df["name"].fillna(df["full_name"])

        # Normalize DOB
        df["date_of_birth"] = pd.to_datetime(df["date_of_birth"], errors="coerce").dt.strftime("%Y-%m-%d")

        # Convert height
        df["height_cm"] = pd.to_numeric(df["height_cm"], errors="coerce")

        if not include_unlinked:
            has_provider = (
                df["key_transfermarkt"].notna()
                | df["key_api_football"].notna()
                | df["key_fbref"].notna()
                | df["key_wikidata"].notna()
            )
            df = df[has_provider].copy()

        return df

    def get_summary_statistics(self) -> dict[str, Any]:
        """Return audit summary of Reep entities."""
        comps = self.load_competitions()
        teams = self.load_teams()
        return {
            "competitions_count": len(comps),
            "teams_count": len(teams),
            "data_present": self.people_path.exists(),
        }
