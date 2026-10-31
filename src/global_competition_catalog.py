"""Global competition catalog for TRANSFERA.

Registers and standardizes domestic leagues, lower tiers, continental
tournaments, and international cups across multiple data sources.
Assigns coverage status: SUPPORTED, PARTIAL, or INSUFFICIENT.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import pandas as pd

from src.competition_registry import CompetitionRegistry

logger = logging.getLogger(__name__)

GLOBAL_COMPETITIONS_PATH = Path("data/global/global_competitions.parquet")
REEP_COMPETITIONS_PATH = Path("data/external/reep/competitions.csv")


# Extended global competitions definition with status and tiers
EXPANDED_COMPETITIONS: list[dict[str, Any]] = [
    # Top 5 European Leagues
    {
        "competition_id": "GB1",
        "name": "Premier League",
        "country": "England",
        "tier": 1,
        "confederation": "UEFA",
        "status": "SUPPORTED",
    },
    {
        "competition_id": "ES1",
        "name": "La Liga",
        "country": "Spain",
        "tier": 1,
        "confederation": "UEFA",
        "status": "SUPPORTED",
    },
    {
        "competition_id": "L1",
        "name": "Bundesliga",
        "country": "Germany",
        "tier": 1,
        "confederation": "UEFA",
        "status": "SUPPORTED",
    },
    {
        "competition_id": "IT1",
        "name": "Serie A",
        "country": "Italy",
        "tier": 1,
        "confederation": "UEFA",
        "status": "SUPPORTED",
    },
    {
        "competition_id": "FR1",
        "name": "Ligue 1",
        "country": "France",
        "tier": 1,
        "confederation": "UEFA",
        "status": "SUPPORTED",
    },
    # European Tier 2 and Additional Domestic Leagues
    {
        "competition_id": "GB2",
        "name": "Championship",
        "country": "England",
        "tier": 2,
        "confederation": "UEFA",
        "status": "PARTIAL",
    },
    {
        "competition_id": "ES2",
        "name": "LaLiga 2",
        "country": "Spain",
        "tier": 2,
        "confederation": "UEFA",
        "status": "PARTIAL",
    },
    {
        "competition_id": "L2",
        "name": "2. Bundesliga",
        "country": "Germany",
        "tier": 2,
        "confederation": "UEFA",
        "status": "PARTIAL",
    },
    {
        "competition_id": "IT2",
        "name": "Serie B",
        "country": "Italy",
        "tier": 2,
        "confederation": "UEFA",
        "status": "PARTIAL",
    },
    {
        "competition_id": "FR2",
        "name": "Ligue 2",
        "country": "France",
        "tier": 2,
        "confederation": "UEFA",
        "status": "PARTIAL",
    },
    {
        "competition_id": "NL1",
        "name": "Eredivisie",
        "country": "Netherlands",
        "tier": 1,
        "confederation": "UEFA",
        "status": "SUPPORTED",
    },
    {
        "competition_id": "PO1",
        "name": "Liga Portugal",
        "country": "Portugal",
        "tier": 1,
        "confederation": "UEFA",
        "status": "SUPPORTED",
    },
    {
        "competition_id": "BE1",
        "name": "Jupiler Pro League",
        "country": "Belgium",
        "tier": 1,
        "confederation": "UEFA",
        "status": "SUPPORTED",
    },
    {
        "competition_id": "TR1",
        "name": "Süper Lig",
        "country": "Turkey",
        "tier": 1,
        "confederation": "UEFA",
        "status": "SUPPORTED",
    },
    {
        "competition_id": "SC1",
        "name": "Scottish Premiership",
        "country": "Scotland",
        "tier": 1,
        "confederation": "UEFA",
        "status": "PARTIAL",
    },
    # Americas
    {
        "competition_id": "BRA1",
        "name": "Campeonato Brasileiro Série A",
        "country": "Brazil",
        "tier": 1,
        "confederation": "CONMEBOL",
        "status": "SUPPORTED",
    },
    {
        "competition_id": "BRA2",
        "name": "Campeonato Brasileiro Série B",
        "country": "Brazil",
        "tier": 2,
        "confederation": "CONMEBOL",
        "status": "PARTIAL",
    },
    {
        "competition_id": "ARG1",
        "name": "Liga Profesional de Fútbol",
        "country": "Argentina",
        "tier": 1,
        "confederation": "CONMEBOL",
        "status": "SUPPORTED",
    },
    {
        "competition_id": "MLS1",
        "name": "Major League Soccer",
        "country": "United States",
        "tier": 1,
        "confederation": "CONCACAF",
        "status": "PARTIAL",
    },
    {
        "competition_id": "MEX1",
        "name": "Liga MX",
        "country": "Mexico",
        "tier": 1,
        "confederation": "CONCACAF",
        "status": "PARTIAL",
    },
    {
        "competition_id": "CLI1",
        "name": "Copa Libertadores",
        "country": "South America",
        "tier": 0,
        "confederation": "CONMEBOL",
        "status": "PARTIAL",
    },
    # Asia & Oceania
    {
        "competition_id": "IN1",
        "name": "Indian Super League",
        "country": "India",
        "tier": 1,
        "confederation": "AFC",
        "status": "PARTIAL",
    },
    {
        "competition_id": "IN2",
        "name": "I-League",
        "country": "India",
        "tier": 2,
        "confederation": "AFC",
        "status": "INSUFFICIENT",
    },
    {
        "competition_id": "SA1",
        "name": "Saudi Pro League",
        "country": "Saudi Arabia",
        "tier": 1,
        "confederation": "AFC",
        "status": "PARTIAL",
    },
    {
        "competition_id": "JPN1",
        "name": "J1 League",
        "country": "Japan",
        "tier": 1,
        "confederation": "AFC",
        "status": "PARTIAL",
    },
    {
        "competition_id": "KOR1",
        "name": "K League 1",
        "country": "South Korea",
        "tier": 1,
        "confederation": "AFC",
        "status": "PARTIAL",
    },
    {
        "competition_id": "AUS1",
        "name": "A-League Men",
        "country": "Australia",
        "tier": 1,
        "confederation": "AFC",
        "status": "PARTIAL",
    },
    {
        "competition_id": "AFAC",
        "name": "AFC Asian Cup",
        "country": "Asia",
        "tier": 0,
        "confederation": "AFC",
        "status": "PARTIAL",
    },
    # Africa
    {
        "competition_id": "EGY1",
        "name": "Egyptian Premier League",
        "country": "Egypt",
        "tier": 1,
        "confederation": "CAF",
        "status": "PARTIAL",
    },
    {
        "competition_id": "RSA1",
        "name": "South African Premier Division",
        "country": "South Africa",
        "tier": 1,
        "confederation": "CAF",
        "status": "PARTIAL",
    },
    {
        "competition_id": "SEN1",
        "name": "Senegal Ligue 1",
        "country": "Senegal",
        "tier": 1,
        "confederation": "CAF",
        "status": "INSUFFICIENT",
    },
    {
        "competition_id": "AFCN",
        "name": "Africa Cup of Nations",
        "country": "Africa",
        "tier": 0,
        "confederation": "CAF",
        "status": "PARTIAL",
    },
    {
        "competition_id": "CAF1",
        "name": "CAF Champions League",
        "country": "Africa",
        "tier": 0,
        "confederation": "CAF",
        "status": "INSUFFICIENT",
    },
    # International & Continental
    {
        "competition_id": "CL",
        "name": "UEFA Champions League",
        "country": "Europe",
        "tier": 0,
        "confederation": "UEFA",
        "status": "SUPPORTED",
    },
    {
        "competition_id": "EL",
        "name": "UEFA Europa League",
        "country": "Europe",
        "tier": 0,
        "confederation": "UEFA",
        "status": "SUPPORTED",
    },
    {
        "competition_id": "ECL",
        "name": "UEFA Conference League",
        "country": "Europe",
        "tier": 0,
        "confederation": "UEFA",
        "status": "PARTIAL",
    },
    {
        "competition_id": "WM",
        "name": "FIFA World Cup",
        "country": "International",
        "tier": 0,
        "confederation": "FIFA",
        "status": "SUPPORTED",
    },
]


class GlobalCompetitionCatalog:
    """Manages global competition registry and metadata."""

    def __init__(self, output_path: Path | str = GLOBAL_COMPETITIONS_PATH):
        self.output_path = Path(output_path)
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self.catalog = self._build_catalog()

    def _build_catalog(self) -> pd.DataFrame:
        """Combine Stage 1 registry, expanded manual definitions, and Reep crosswalk."""
        records: dict[str, dict[str, Any]] = {}

        # 1. Start with Stage 1 registry
        try:
            reg = CompetitionRegistry()
            for cid, info in reg.registry.items():
                cname = getattr(info, "competition_name", None) or (
                    info.get("competition_name") if isinstance(info, dict) else cid
                )
                country = getattr(info, "country", None) or (
                    info.get("country") if isinstance(info, dict) else "Global"
                )
                is_first = (
                    getattr(info, "sub_type", "") == "first_tier"
                    if hasattr(info, "sub_type")
                    else (info.get("is_first_tier", False) if isinstance(info, dict) else False)
                )
                rel_status = getattr(info, "reliability_status", None) or (
                    info.get("reliability_status") if isinstance(info, dict) else "SUPPORTED"
                )
                if rel_status == "INSUFFICIENT_DATA":
                    mapped_status = "INSUFFICIENT"
                elif rel_status in ["PARTIALLY_SUPPORTED", "LIMITED_COVERAGE"]:
                    mapped_status = "PARTIAL"
                else:
                    mapped_status = "SUPPORTED"

                records[cid] = {
                    "competition_id": cid,
                    "name": str(cname).replace("-", " ").title(),
                    "country": str(country),
                    "tier": 1 if is_first else 2,
                    "confederation": "UEFA"
                    if str(country)
                    in [
                        "England",
                        "Spain",
                        "Germany",
                        "Italy",
                        "France",
                        "Netherlands",
                        "Portugal",
                        "Belgium",
                        "Turkey",
                    ]
                    else "Other",
                    "status": mapped_status,
                    "reep_id": None,
                    "key_api_football": None,
                    "data_source": "TRANSFERMARKT_STAGE1",
                }
        except Exception as e:
            logger.warning("Could not load CompetitionRegistry: %s", e)

        # 2. Enrich and add Expanded Competitions
        for exp in EXPANDED_COMPETITIONS:
            cid = exp["competition_id"]
            if cid in records:
                records[cid].update(exp)
            else:
                rec = exp.copy()
                rec["reep_id"] = None
                rec["key_api_football"] = None
                rec["data_source"] = "GLOBAL_EXPANSION"
                records[cid] = rec

        # 3. Incorporate Reep Crosswalk if available
        if REEP_COMPETITIONS_PATH.exists():
            try:
                reep_df = pd.read_csv(REEP_COMPETITIONS_PATH, low_memory=False)
                for _, r in reep_df.iterrows():
                    reep_name = str(r.get("name", "")).strip()
                    reep_country = str(r.get("country", "")).strip()
                    reep_id = str(r.get("reep_id", ""))
                    tm_code = str(r.get("key_transfermarkt", "")).strip()

                    # Check if matching existing competition
                    matched = False
                    for cid, item in records.items():
                        if (tm_code and tm_code == cid) or (
                            reep_name.lower() == item["name"].lower()
                            and reep_country.lower() == item["country"].lower()
                        ):
                            item["reep_id"] = reep_id
                            matched = True
                            break

                    if not matched and len(reep_name) > 3 and reep_country not in ["nan", ""]:
                        # Register as newly discovered global competition
                        new_cid = f"REEP_{reep_id[-6:]}" if reep_id else f"COMP_{len(records) + 1}"
                        records[new_cid] = {
                            "competition_id": new_cid,
                            "name": reep_name,
                            "country": reep_country if reep_country != "nan" else "Global",
                            "tier": 1,
                            "confederation": "Other",
                            "status": "INSUFFICIENT",  # Profile only until stats ingested
                            "reep_id": reep_id,
                            "key_api_football": None,
                            "data_source": "REEP_REGISTER",
                        }
            except Exception as e:
                logger.warning("Error parsing Reep competitions: %s", e)

        df = pd.DataFrame(list(records.values()))
        return df

    def save(self) -> Path:
        """Persist catalog to Parquet."""
        self.catalog.to_parquet(self.output_path, index=False)
        logger.info("Saved %d global competitions to %s", len(self.catalog), self.output_path)
        return self.output_path

    def get_competition_status(self, competition_id: str) -> str:
        """Get status for a competition ID."""
        row = self.catalog[self.catalog["competition_id"] == competition_id]
        if not row.empty:
            return str(row.iloc[0]["status"])
        return "INSUFFICIENT"

    def list_supported_competitions(self) -> list[str]:
        """Return list of competition IDs that have full ML calibration."""
        return self.catalog[self.catalog["status"] == "SUPPORTED"]["competition_id"].tolist()
