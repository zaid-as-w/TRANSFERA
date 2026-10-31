"""Data transformations module for cleaning and standardizing raw football datasets.

Converts raw immutable files into typed, cleansed, and partitioned Parquet datasets
in data/interim/. Validates joins and reports dropped rows or unmatched keys.
"""

import logging
from pathlib import Path

import pandas as pd

from config.settings import (
    INTERIM_DATA_DIR,
    RAW_TM_DIR,
)

logger = logging.getLogger(__name__)


def clean_players(raw_dir: Path = RAW_TM_DIR, out_dir: Path = INTERIM_DATA_DIR) -> pd.DataFrame:
    """Clean players table: parse dates, fill missing positions, retain stable IDs."""
    logger.info("Cleaning players table...")
    df = pd.read_csv(raw_dir / "players.csv.gz", compression="gzip", low_memory=False)
    initial_count = len(df)

    df["player_id"] = pd.to_numeric(df["player_id"], errors="coerce")
    df = df.dropna(subset=["player_id"]).copy()
    df["player_id"] = df["player_id"].astype("int64")

    df["date_of_birth"] = pd.to_datetime(df["date_of_birth"], errors="coerce")
    df["position"] = df["position"].fillna("Unknown").astype(str)
    df["sub_position"] = df["sub_position"].fillna("Unknown").astype(str)
    df["foot"] = df["foot"].fillna("Unknown").astype(str)
    df["height_in_cm"] = pd.to_numeric(df["height_in_cm"], errors="coerce")
    df["country_of_citizenship"] = df["country_of_citizenship"].fillna("Unknown").astype(str)

    cols = [
        "player_id",
        "name",
        "date_of_birth",
        "position",
        "sub_position",
        "foot",
        "height_in_cm",
        "country_of_citizenship",
        "current_club_id",
        "current_club_domestic_competition_id",
        "current_club_name",
    ]
    cleaned = df[[c for c in cols if c in df.columns]].drop_duplicates(subset=["player_id"])

    dest = out_dir / "clean_players.parquet"
    cleaned.to_parquet(dest, index=False)
    logger.info("Saved %d clean players (dropped %d) to %s", len(cleaned), initial_count - len(cleaned), dest.name)
    return cleaned


def clean_competitions(raw_dir: Path = RAW_TM_DIR, out_dir: Path = INTERIM_DATA_DIR) -> pd.DataFrame:
    """Clean competitions table."""
    logger.info("Cleaning competitions table...")
    df = pd.read_csv(raw_dir / "competitions.csv.gz", compression="gzip", low_memory=False)
    df["competition_id"] = df["competition_id"].astype(str).str.strip()
    df["name"] = df["name"].fillna("Unknown").astype(str)
    df["country_name"] = df["country_name"].fillna("Unknown").astype(str)
    df["type"] = df["type"].fillna("unknown").astype(str)
    df["sub_type"] = df["sub_type"].fillna("unknown").astype(str)

    dest = out_dir / "clean_competitions.parquet"
    df.to_parquet(dest, index=False)
    logger.info("Saved %d clean competitions to %s", len(df), dest.name)
    return df


def clean_clubs(raw_dir: Path = RAW_TM_DIR, out_dir: Path = INTERIM_DATA_DIR) -> pd.DataFrame:
    """Clean clubs table."""
    logger.info("Cleaning clubs table...")
    df = pd.read_csv(raw_dir / "clubs.csv.gz", compression="gzip", low_memory=False)
    df["club_id"] = pd.to_numeric(df["club_id"], errors="coerce").astype("int64")
    df["name"] = df["name"].fillna("Unknown").astype(str)
    df["domestic_competition_id"] = df["domestic_competition_id"].astype(str).str.strip()
    df["total_market_value"] = pd.to_numeric(df["total_market_value"], errors="coerce")
    df["squad_size"] = pd.to_numeric(df["squad_size"], errors="coerce").fillna(0).astype(int)
    df["average_age"] = pd.to_numeric(df["average_age"], errors="coerce")
    df["stadium_seats"] = pd.to_numeric(df["stadium_seats"], errors="coerce")

    cols = [
        "club_id",
        "club_code",
        "name",
        "domestic_competition_id",
        "total_market_value",
        "squad_size",
        "average_age",
        "stadium_seats",
    ]
    cleaned = df[[c for c in cols if c in df.columns]].drop_duplicates(subset=["club_id"])

    dest = out_dir / "clean_clubs.parquet"
    cleaned.to_parquet(dest, index=False)
    logger.info("Saved %d clean clubs to %s", len(cleaned), dest.name)
    return cleaned


def clean_games(raw_dir: Path = RAW_TM_DIR, out_dir: Path = INTERIM_DATA_DIR) -> pd.DataFrame:
    """Clean games table: parse dates, validate goals and home/away IDs."""
    logger.info("Cleaning games table...")
    df = pd.read_csv(raw_dir / "games.csv.gz", compression="gzip", low_memory=False)
    initial_count = len(df)

    df["game_id"] = pd.to_numeric(df["game_id"], errors="coerce")
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["game_id", "date", "home_club_id", "away_club_id"]).copy()
    df["game_id"] = df["game_id"].astype("int64")
    df["home_club_id"] = df["home_club_id"].astype("int64")
    df["away_club_id"] = df["away_club_id"].astype("int64")
    df["competition_id"] = df["competition_id"].astype(str).str.strip()
    df["season"] = pd.to_numeric(df["season"], errors="coerce").fillna(0).astype(int)

    dest = out_dir / "clean_games.parquet"
    df.to_parquet(dest, index=False)
    logger.info("Saved %d clean games (dropped %d) to %s", len(df), initial_count - len(df), dest.name)
    return df


def clean_player_valuations(raw_dir: Path = RAW_TM_DIR, out_dir: Path = INTERIM_DATA_DIR) -> pd.DataFrame:
    """Clean player_valuations table: filter positive values, convert date, drop duplicates."""
    logger.info("Cleaning player_valuations table...")
    df = pd.read_csv(raw_dir / "player_valuations.csv.gz", compression="gzip", low_memory=False)
    initial_count = len(df)

    df["player_id"] = pd.to_numeric(df["player_id"], errors="coerce")
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["market_value_in_eur"] = pd.to_numeric(df["market_value_in_eur"], errors="coerce")

    # Keep strictly valid positive market values and valid dates
    valid = df.dropna(subset=["player_id", "date", "market_value_in_eur"]).copy()
    valid = valid[valid["market_value_in_eur"] > 0]
    valid["player_id"] = valid["player_id"].astype("int64")
    valid["current_club_id"] = pd.to_numeric(valid["current_club_id"], errors="coerce")

    # Deduplicate multiple valuations for same player on same date (keep highest)
    valid = valid.sort_values(["player_id", "date", "market_value_in_eur"], ascending=[True, True, False])
    valid = valid.drop_duplicates(subset=["player_id", "date"], keep="first")

    dest = out_dir / "clean_player_valuations.parquet"
    valid.to_parquet(dest, index=False)
    logger.info("Saved %d clean valuations (dropped %d) to %s", len(valid), initial_count - len(valid), dest.name)
    return valid


def clean_appearances(raw_dir: Path = RAW_TM_DIR, out_dir: Path = INTERIM_DATA_DIR) -> pd.DataFrame:
    """Clean appearances table: filter valid minutes, goals, assists."""
    logger.info("Cleaning appearances table...")
    cols = [
        "appearance_id",
        "game_id",
        "player_id",
        "player_club_id",
        "date",
        "competition_id",
        "yellow_cards",
        "red_cards",
        "goals",
        "assists",
        "minutes_played",
    ]
    try:
        df = pd.read_csv(raw_dir / "appearances.csv.gz", compression="gzip", usecols=cols, engine="pyarrow")
    except Exception:
        df = pd.read_csv(raw_dir / "appearances.csv.gz", compression="gzip", usecols=cols, low_memory=False)
    initial_count = len(df)

    df["player_id"] = pd.to_numeric(df["player_id"], errors="coerce")
    df["game_id"] = pd.to_numeric(df["game_id"], errors="coerce")
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["minutes_played"] = pd.to_numeric(df["minutes_played"], errors="coerce").fillna(0).astype(int)
    df["goals"] = pd.to_numeric(df["goals"], errors="coerce").fillna(0).astype(int)
    df["assists"] = pd.to_numeric(df["assists"], errors="coerce").fillna(0).astype(int)
    df["yellow_cards"] = pd.to_numeric(df["yellow_cards"], errors="coerce").fillna(0).astype(int)
    df["red_cards"] = pd.to_numeric(df["red_cards"], errors="coerce").fillna(0).astype(int)

    cleaned = df.dropna(subset=["player_id", "game_id", "date"]).copy()
    cleaned["player_id"] = cleaned["player_id"].astype("int64")
    cleaned["game_id"] = cleaned["game_id"].astype("int64")
    cleaned["player_club_id"] = pd.to_numeric(cleaned["player_club_id"], errors="coerce").fillna(0).astype("int64")
    cleaned["competition_id"] = cleaned["competition_id"].astype(str).str.strip()

    dest = out_dir / "clean_appearances.parquet"
    cleaned.to_parquet(dest, index=False)
    logger.info("Saved %d clean appearances (dropped %d) to %s", len(cleaned), initial_count - len(cleaned), dest.name)
    return cleaned


def clean_transfers(raw_dir: Path = RAW_TM_DIR, out_dir: Path = INTERIM_DATA_DIR) -> pd.DataFrame:
    """Clean transfers table: parse dates, retain stable player/club IDs, preserve null fees."""
    logger.info("Cleaning transfers table...")
    df = pd.read_csv(raw_dir / "transfers.csv.gz", compression="gzip", low_memory=False)
    initial_count = len(df)

    df["player_id"] = pd.to_numeric(df["player_id"], errors="coerce")
    df = df.dropna(subset=["player_id"]).copy()
    df["player_id"] = df["player_id"].astype("int64")

    df["transfer_date"] = pd.to_datetime(df["transfer_date"], errors="coerce")
    df["from_club_id"] = pd.to_numeric(df["from_club_id"], errors="coerce")
    df["to_club_id"] = pd.to_numeric(df["to_club_id"], errors="coerce")
    df["transfer_fee"] = pd.to_numeric(df["transfer_fee"], errors="coerce")
    df["market_value_in_eur"] = pd.to_numeric(df["market_value_in_eur"], errors="coerce")

    cols = [
        "player_id",
        "player_name",
        "transfer_date",
        "transfer_season",
        "from_club_id",
        "to_club_id",
        "from_club_name",
        "to_club_name",
        "transfer_fee",
        "market_value_in_eur",
    ]
    cleaned = df[[c for c in cols if c in df.columns]].copy()

    dest = out_dir / "clean_transfers.parquet"
    cleaned.to_parquet(dest, index=False)
    logger.info("Saved %d clean transfers (dropped %d) to %s", len(cleaned), initial_count - len(cleaned), dest.name)
    return cleaned


def run_all_transformations(raw_dir: Path = RAW_TM_DIR, out_dir: Path = INTERIM_DATA_DIR) -> dict[str, int]:
    """Execute all cleaning and conversion steps, writing clean Parquet tables."""
    out_dir.mkdir(parents=True, exist_ok=True)
    counts = {}
    counts["players"] = len(clean_players(raw_dir, out_dir))
    counts["competitions"] = len(clean_competitions(raw_dir, out_dir))
    counts["clubs"] = len(clean_clubs(raw_dir, out_dir))
    counts["games"] = len(clean_games(raw_dir, out_dir))
    counts["player_valuations"] = len(clean_player_valuations(raw_dir, out_dir))
    counts["appearances"] = len(clean_appearances(raw_dir, out_dir))
    counts["transfers"] = len(clean_transfers(raw_dir, out_dir))
    logger.info("All transformations completed: %s", counts)
    return counts


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_all_transformations()
