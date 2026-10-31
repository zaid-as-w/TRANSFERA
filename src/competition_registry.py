"""Data-driven competition registry for European and worldwide football competitions.

Discovers and evaluates competitions from historical data records rather than
relying on static hardcoded assumptions. Tracks reliability status, match
coverage, valuation coverage, and financial data coverage.
"""

import json
import logging
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from config.settings import (
    CORE_LEAGUE_MAP,
    METADATA_DIR,
    RAW_TM_DIR,
)

logger = logging.getLogger(__name__)

# Standard competition reliability statuses
STATUS_SUPPORTED = "SUPPORTED"
STATUS_PARTIAL = "PARTIAL"
STATUS_INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
STATUS_UNAVAILABLE = "UNAVAILABLE"


@dataclass
class CompetitionRecord:
    competition_id: str
    source_competition_id: str
    competition_name: str
    country: str | None
    confederation: str | None
    competition_type: str
    sub_type: str | None
    division: str | None
    currency: str
    data_source: str
    data_coverage_start: str | None
    data_coverage_end: str | None
    matches_available: int
    player_statistics_available: int
    valuation_coverage: int
    financial_data_coverage: bool
    strength_estimate_available: bool
    reliability_status: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class CompetitionRegistry:
    """Registry managing coverage and reliability across global football competitions."""

    def __init__(self, metadata_path: Path | None = None) -> None:
        self.metadata_path = metadata_path or (METADATA_DIR / "competition_registry.json")
        self.registry: dict[str, CompetitionRecord] = {}
        if self.metadata_path.exists():
            self._load_from_json()

    def _load_from_json(self) -> None:
        try:
            with open(self.metadata_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                for comp_id, rec in data.get("competitions", {}).items():
                    self.registry[comp_id] = CompetitionRecord(**rec)
            logger.info("Loaded %d competitions from %s", len(self.registry), self.metadata_path.name)
        except Exception as e:
            logger.warning("Failed loading competition registry from %s: %s", self.metadata_path, e)

    def build_registry_from_data(self, raw_dir: Path = RAW_TM_DIR) -> dict[str, CompetitionRecord]:
        """Empirically audit raw tables to construct a data-driven competition registry."""
        comp_file = raw_dir / "competitions.csv.gz"
        games_file = raw_dir / "games.csv.gz"
        apps_file = raw_dir / "appearances.csv.gz"
        vals_file = raw_dir / "player_valuations.csv.gz"

        if not comp_file.exists():
            raise FileNotFoundError(f"Missing competitions table at {comp_file}")

        logger.info("Building competition registry from raw Transfermarkt files...")
        comp_df = pd.read_csv(comp_file, compression="gzip", low_memory=False)

        # Count games per competition
        games_counts = {}
        date_ranges = {}
        if games_file.exists():
            games_df = pd.read_csv(games_file, compression="gzip", low_memory=False, usecols=["competition_id", "date"])
            games_counts = games_df["competition_id"].value_counts().to_dict()
            games_df["date"] = pd.to_datetime(games_df["date"], errors="coerce")
            grouped_dates = games_df.groupby("competition_id")["date"].agg(["min", "max"])
            for comp_id, row in grouped_dates.iterrows():
                date_ranges[comp_id] = {
                    "start": row["min"].strftime("%Y-%m-%d") if pd.notna(row["min"]) else None,
                    "end": row["max"].strftime("%Y-%m-%d") if pd.notna(row["max"]) else None,
                }

        # Count appearances per competition
        app_counts = {}
        if apps_file.exists():
            apps_df = pd.read_csv(apps_file, compression="gzip", low_memory=False, usecols=["competition_id"])
            app_counts = apps_df["competition_id"].value_counts().to_dict()

        # Count valuations per domestic competition
        val_counts = {}
        if vals_file.exists():
            vals_df = pd.read_csv(
                vals_file,
                compression="gzip",
                low_memory=False,
                usecols=["player_club_domestic_competition_id"],
            )
            val_counts = vals_df["player_club_domestic_competition_id"].value_counts().to_dict()

        registry: dict[str, CompetitionRecord] = {}

        for _, row in comp_df.iterrows():
            comp_id = str(row["competition_id"]).strip()
            name = str(row.get("name", comp_id)).strip()
            country = str(row["country_name"]) if pd.notna(row.get("country_name")) else None
            confed = str(row["confederation"]) if pd.notna(row.get("confederation")) else None
            comp_type = str(row.get("type", "unknown"))
            sub_type = str(row["sub_type"]) if pd.notna(row.get("sub_type")) else None

            matches = int(games_counts.get(comp_id, 0))
            apps = int(app_counts.get(comp_id, 0))
            vals = int(val_counts.get(comp_id, 0))
            dr = date_ranges.get(comp_id, {})

            # Financial coverage check for Big 5 and known benchmark leagues
            financial_coverage = comp_id in ["GB1", "ES1", "IT1", "L1", "FR1", "NL1", "PO1", "BE1", "TR1", "SC1"]
            has_strength = matches >= 500

            # Determine empirical reliability status
            if (
                comp_id in CORE_LEAGUE_MAP
                or comp_type == "domestic_league"
                and matches >= 2000
                and vals >= 10000
                and apps >= 25000
            ):
                status = STATUS_SUPPORTED
            elif matches >= 500 and (apps >= 5000 or vals >= 2000):
                status = STATUS_PARTIAL
            elif matches > 0:
                status = STATUS_INSUFFICIENT_DATA
            else:
                status = STATUS_UNAVAILABLE

            rec = CompetitionRecord(
                competition_id=comp_id,
                source_competition_id=str(row.get("competition_code", comp_id)),
                competition_name=name,
                country=country,
                confederation=confed,
                competition_type=comp_type,
                sub_type=sub_type,
                division="1" if "first_tier" in str(sub_type).lower() or comp_id in CORE_LEAGUE_MAP else None,
                currency="EUR",
                data_source="Transfermarkt Datasets",
                data_coverage_start=dr.get("start"),
                data_coverage_end=dr.get("end"),
                matches_available=matches,
                player_statistics_available=apps,
                valuation_coverage=vals,
                financial_data_coverage=financial_coverage,
                strength_estimate_available=has_strength,
                reliability_status=status,
            )
            registry[comp_id] = rec

        self.registry = registry
        self.save_to_json()
        logger.info("Compiled competition registry with %d competitions.", len(self.registry))
        return self.registry

    def save_to_json(self) -> None:
        self.metadata_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "generated_at": datetime.now(UTC).isoformat(),
            "total_competitions": len(self.registry),
            "supported_count": sum(1 for r in self.registry.values() if r.reliability_status == STATUS_SUPPORTED),
            "partial_count": sum(1 for r in self.registry.values() if r.reliability_status == STATUS_PARTIAL),
            "insufficient_count": sum(
                1 for r in self.registry.values() if r.reliability_status == STATUS_INSUFFICIENT_DATA
            ),
            "unavailable_count": sum(1 for r in self.registry.values() if r.reliability_status == STATUS_UNAVAILABLE),
            "competitions": {cid: r.to_dict() for cid, r in self.registry.items()},
        }
        with open(self.metadata_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        logger.info("Saved competition registry to %s", self.metadata_path)

    def get_competition(self, comp_id: str) -> CompetitionRecord | None:
        return self.registry.get(comp_id)

    def is_supported(self, comp_id: str) -> bool:
        comp = self.get_competition(comp_id)
        return comp is not None and comp.reliability_status == STATUS_SUPPORTED

    def get_status(self, comp_id: str) -> str:
        comp = self.get_competition(comp_id)
        if comp is None:
            return STATUS_UNAVAILABLE
        return comp.reliability_status

    def list_by_status(self, status: str) -> list[CompetitionRecord]:
        return [r for r in self.registry.values() if r.reliability_status == status]


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    reg = CompetitionRegistry()
    reg.build_registry_from_data()
    print("\nSupported Competitions:")
    for comp in reg.list_by_status(STATUS_SUPPORTED):
        print(
            f"  {comp.competition_id}: {comp.competition_name} ({comp.country}) - {comp.matches_available:,} matches, {comp.valuation_coverage:,} valuations"
        )

    print(f"\nTotal registered: {len(reg.registry)}")
    print(f"Supported: {len(reg.list_by_status(STATUS_SUPPORTED))}")
    print(f"Partial: {len(reg.list_by_status(STATUS_PARTIAL))}")
    print(f"Insufficient Data: {len(reg.list_by_status(STATUS_INSUFFICIENT_DATA))}")
    print(f"Unavailable: {len(reg.list_by_status(STATUS_UNAVAILABLE))}")
