"""Configuration module for the Global Football Transfer Market Valuation Engine.

Handles paths, competition registries, feature parameters, model parameters,
and external data endpoints.
"""

import os
from pathlib import Path

# Base directories
BASE_DIR: Path = Path(__file__).resolve().parent.parent
CONFIG_DIR: Path = BASE_DIR / "config"
DATA_DIR: Path = BASE_DIR / "data"
RAW_DATA_DIR: Path = DATA_DIR / "raw"
RAW_TM_DIR: Path = RAW_DATA_DIR / "transfermarkt"
RAW_FIN_DIR: Path = RAW_DATA_DIR / "financial"
INTERIM_DATA_DIR: Path = DATA_DIR / "interim"
PROCESSED_DATA_DIR: Path = DATA_DIR / "processed"
METADATA_DIR: Path = DATA_DIR / "metadata"
MODELS_DIR: Path = BASE_DIR / "models"
DOCS_DIR: Path = BASE_DIR / "docs"

for d in [RAW_TM_DIR, RAW_FIN_DIR, INTERIM_DATA_DIR, PROCESSED_DATA_DIR, METADATA_DIR, MODELS_DIR, DOCS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# Transfermarkt Cloudflare R2 mirror configuration
TM_R2_BASE_URL: str = "https://pub-e682421888d945d684bcae8890b0ec20.r2.dev/data/{table}.csv.gz"

CORE_TM_TABLES: list[str] = [
    "competitions",
    "clubs",
    "players",
    "games",
    "appearances",
    "player_valuations",
    "club_games",
    "transfers",
    "countries",
]

# Secondary Data Source: Football-Data.org
FOOTBALL_DATA_API_BASE: str = "https://api.football-data.org/v4"
FOOTBALL_DATA_API_KEY: str | None = os.getenv("FOOTBALL_DATA_API_KEY", None)

# Big 5 Core Competition Identifiers in Transfermarkt
CORE_LEAGUE_MAP: dict[str, dict[str, str]] = {
    "GB1": {"name": "Premier League", "country": "England", "tier": "1", "code": "EPL"},
    "ES1": {"name": "LaLiga", "country": "Spain", "tier": "1", "code": "PD"},
    "IT1": {"name": "Serie A", "country": "Italy", "tier": "1", "code": "SA"},
    "L1": {"name": "Bundesliga", "country": "Germany", "tier": "1", "code": "BL1"},
    "FR1": {"name": "Ligue 1", "country": "France", "tier": "1", "code": "FL1"},
}

# Continental competitions useful for cross-competition club strength estimation
CONTINENTAL_COMPETITIONS: list[str] = ["CL", "EL", "ECLQ", "USC"]

# Temporal splits configuration
TRAIN_SEASONS_MAX: int = 2021  # Up to 2021/2022
VAL_SEASON: int = 2022  # 2022/2023
TEST_SEASON: int = 2023  # 2023/2024 and onwards

# Feature engineering parameters
MIN_MINUTES_PLAYED_FILTER: int = 90
DEFAULT_RANDOM_STATE: int = 42
TARGET_COLUMN: str = "historical_market_value"
LOG_TARGET_COLUMN: str = "log_market_value"
REFERENCE_DATE_COL: str = "valuation_reference_date"
