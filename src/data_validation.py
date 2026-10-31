"""Data validation module for raw and interim football datasets.

Enforces schema integrity, entity consistency, foreign key relationships,
temporal validity, and domain constraints across Transfermarkt and external data.
"""

import json
import logging
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from config.settings import METADATA_DIR, RAW_TM_DIR

logger = logging.getLogger(__name__)


@dataclass
class ValidationIssue:
    check_name: str
    severity: str  # "ERROR", "WARNING", "INFO"
    message: str
    count: int = 0
    details: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class DataValidator:
    """Validates schemas, foreign keys, domain boundaries, and data quality."""

    def __init__(self, raw_dir: Path = RAW_TM_DIR) -> None:
        self.raw_dir = raw_dir
        self.issues: list[ValidationIssue] = []

    def validate_all(self) -> dict[str, Any]:
        """Run full suite of validation checks."""
        self.issues.clear()
        logger.info("Starting data validation checks on %s...", self.raw_dir)

        self._check_file_existence()
        self._check_identifiers_and_duplicates()
        self._check_foreign_keys()
        self._check_domain_constraints()
        self._check_dates_and_currencies()

        report = self.generate_report()
        self.save_report(report)
        return report

    def _check_file_existence(self) -> None:
        required = [
            "competitions.csv.gz",
            "clubs.csv.gz",
            "players.csv.gz",
            "games.csv.gz",
            "appearances.csv.gz",
            "player_valuations.csv.gz",
        ]
        for f in required:
            p = self.raw_dir / f
            if not p.exists():
                self.issues.append(
                    ValidationIssue(
                        check_name="file_existence",
                        severity="ERROR",
                        message=f"Missing required raw file: {f}",
                        count=1,
                    )
                )

    def _check_identifiers_and_duplicates(self) -> None:
        # Check players
        players_p = self.raw_dir / "players.csv.gz"
        if players_p.exists():
            df = pd.read_csv(players_p, compression="gzip", usecols=["player_id"], low_memory=False)
            dup_players = int(df["player_id"].duplicated().sum())
            if dup_players > 0:
                self.issues.append(
                    ValidationIssue(
                        check_name="duplicate_player_id",
                        severity="ERROR",
                        message=f"Found {dup_players} duplicate player_id entries in players.csv",
                        count=dup_players,
                    )
                )

        # Check games
        games_p = self.raw_dir / "games.csv.gz"
        if games_p.exists():
            df = pd.read_csv(games_p, compression="gzip", usecols=["game_id"], low_memory=False)
            dup_games = int(df["game_id"].duplicated().sum())
            if dup_games > 0:
                self.issues.append(
                    ValidationIssue(
                        check_name="duplicate_game_id",
                        severity="ERROR",
                        message=f"Found {dup_games} duplicate game_id entries in games.csv",
                        count=dup_games,
                    )
                )

        # Check appearances
        apps_p = self.raw_dir / "appearances.csv.gz"
        if apps_p.exists():
            df = pd.read_csv(apps_p, compression="gzip", usecols=["appearance_id"], low_memory=False)
            dup_apps = int(df["appearance_id"].duplicated().sum())
            if dup_apps > 0:
                self.issues.append(
                    ValidationIssue(
                        check_name="duplicate_appearance_id",
                        severity="WARNING",
                        message=f"Found {dup_apps} duplicate appearance_id entries in appearances.csv",
                        count=dup_apps,
                    )
                )

    def _check_foreign_keys(self) -> None:
        players_p = self.raw_dir / "players.csv.gz"
        apps_p = self.raw_dir / "appearances.csv.gz"
        games_p = self.raw_dir / "games.csv.gz"
        vals_p = self.raw_dir / "player_valuations.csv.gz"

        if players_p.exists() and apps_p.exists():
            p_ids = set(
                pd.read_csv(players_p, compression="gzip", usecols=["player_id"], low_memory=False)["player_id"]
            )
            app_p_ids = set(
                pd.read_csv(apps_p, compression="gzip", usecols=["player_id"], low_memory=False)["player_id"]
            )
            orphan_apps = app_p_ids - p_ids
            if orphan_apps:
                self.issues.append(
                    ValidationIssue(
                        check_name="orphan_appearance_players",
                        severity="WARNING",
                        message=f"{len(orphan_apps)} player_ids in appearances do not exist in players table",
                        count=len(orphan_apps),
                    )
                )

        if games_p.exists() and apps_p.exists():
            g_ids = set(pd.read_csv(games_p, compression="gzip", usecols=["game_id"], low_memory=False)["game_id"])
            app_g_ids = set(pd.read_csv(apps_p, compression="gzip", usecols=["game_id"], low_memory=False)["game_id"])
            orphan_games = app_g_ids - g_ids
            if orphan_games:
                self.issues.append(
                    ValidationIssue(
                        check_name="orphan_appearance_games",
                        severity="WARNING",
                        message=f"{len(orphan_games)} game_ids in appearances do not exist in games table",
                        count=len(orphan_games),
                    )
                )

        if players_p.exists() and vals_p.exists():
            p_ids = set(
                pd.read_csv(players_p, compression="gzip", usecols=["player_id"], low_memory=False)["player_id"]
            )
            val_p_ids = set(
                pd.read_csv(vals_p, compression="gzip", usecols=["player_id"], low_memory=False)["player_id"]
            )
            orphan_vals = val_p_ids - p_ids
            if orphan_vals:
                self.issues.append(
                    ValidationIssue(
                        check_name="orphan_valuation_players",
                        severity="WARNING",
                        message=f"{len(orphan_vals)} player_ids in valuations do not exist in players table",
                        count=len(orphan_vals),
                    )
                )

    def _check_domain_constraints(self) -> None:
        # Check appearances performance stats
        apps_p = self.raw_dir / "appearances.csv.gz"
        if apps_p.exists():
            cols = ["minutes_played", "goals", "assists", "yellow_cards", "red_cards"]
            df = pd.read_csv(apps_p, compression="gzip", usecols=cols, low_memory=False)

            # Negative values
            neg_minutes = int((df["minutes_played"] < 0).sum())
            neg_goals = int((df["goals"] < 0).sum())
            neg_assists = int((df["assists"] < 0).sum())
            if neg_minutes > 0 or neg_goals > 0 or neg_assists > 0:
                self.issues.append(
                    ValidationIssue(
                        check_name="negative_performance_stats",
                        severity="ERROR",
                        message=f"Negative stats detected: minutes={neg_minutes}, goals={neg_goals}, assists={neg_assists}",
                        count=neg_minutes + neg_goals + neg_assists,
                    )
                )

            # Impossible single-match minutes (>130)
            excessive_mins = int((df["minutes_played"] > 130).sum())
            if excessive_mins > 0:
                self.issues.append(
                    ValidationIssue(
                        check_name="excessive_match_minutes",
                        severity="WARNING",
                        message=f"Found {excessive_mins} appearances with >130 minutes played (extra time outlier)",
                        count=excessive_mins,
                    )
                )

            # Zero minute appearances
            zero_mins = int((df["minutes_played"] == 0).sum())
            self.issues.append(
                ValidationIssue(
                    check_name="zero_minute_appearances",
                    severity="INFO",
                    message=f"Found {zero_mins} appearances with 0 minutes (unused substitute or bench event)",
                    count=zero_mins,
                )
            )

        # Check market valuations
        vals_p = self.raw_dir / "player_valuations.csv.gz"
        if vals_p.exists():
            df_vals = pd.read_csv(vals_p, compression="gzip", usecols=["market_value_in_eur"], low_memory=False)
            neg_vals = int((df_vals["market_value_in_eur"] < 0).sum())
            zero_vals = int((df_vals["market_value_in_eur"] == 0).sum())
            null_vals = int(df_vals["market_value_in_eur"].isnull().sum())
            if neg_vals > 0:
                self.issues.append(
                    ValidationIssue(
                        check_name="negative_market_value",
                        severity="ERROR",
                        message=f"Found {neg_vals} negative market values in valuations table",
                        count=neg_vals,
                    )
                )
            if zero_vals > 0 or null_vals > 0:
                self.issues.append(
                    ValidationIssue(
                        check_name="zero_or_null_market_value",
                        severity="WARNING",
                        message=f"Found {zero_vals} zero values and {null_vals} null values in player valuations",
                        count=zero_vals + null_vals,
                    )
                )

    def _check_dates_and_currencies(self) -> None:
        vals_p = self.raw_dir / "player_valuations.csv.gz"
        if vals_p.exists():
            df = pd.read_csv(vals_p, compression="gzip", usecols=["date"], low_memory=False)
            invalid_dates = int(pd.to_datetime(df["date"], errors="coerce").isnull().sum())
            if invalid_dates > 0:
                self.issues.append(
                    ValidationIssue(
                        check_name="invalid_valuation_dates",
                        severity="ERROR",
                        message=f"Found {invalid_dates} unparseable valuation dates",
                        count=invalid_dates,
                    )
                )

        players_p = self.raw_dir / "players.csv.gz"
        if players_p.exists():
            df = pd.read_csv(players_p, compression="gzip", usecols=["date_of_birth"], low_memory=False)
            invalid_dob = int(pd.to_datetime(df["date_of_birth"], errors="coerce").isnull().sum())
            self.issues.append(
                ValidationIssue(
                    check_name="missing_or_invalid_player_dob",
                    severity="WARNING",
                    message=f"Found {invalid_dob} players with missing or unparseable date_of_birth",
                    count=invalid_dob,
                )
            )

    def generate_report(self) -> dict[str, Any]:
        errors = [i for i in self.issues if i.severity == "ERROR"]
        warnings = [i for i in self.issues if i.severity == "WARNING"]
        infos = [i for i in self.issues if i.severity == "INFO"]
        return {
            "validation_timestamp": datetime.now(UTC).isoformat(),
            "status": "FAILED" if errors else "PASSED",
            "error_count": len(errors),
            "warning_count": len(warnings),
            "info_count": len(infos),
            "issues": [i.to_dict() for i in self.issues],
        }

    def save_report(self, report: dict[str, Any], out_path: Path | None = None) -> Path:
        dest = out_path or (METADATA_DIR / "data_validation_report.json")
        dest.parent.mkdir(parents=True, exist_ok=True)
        with open(dest, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        logger.info("Saved data validation report to %s (Status: %s)", dest.name, report["status"])
        return dest


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    validator = DataValidator()
    rep = validator.validate_all()
    print(f"\nData Validation Results: {rep['status']}")
    print(f"Errors: {rep['error_count']}, Warnings: {rep['warning_count']}, Infos: {rep['info_count']}")
    for issue in rep["issues"]:
        print(f"  [{issue['severity']}] {issue['check_name']}: {issue['message']}")
