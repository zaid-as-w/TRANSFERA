"""Tests for ingestion and external data clients."""

import pandas as pd

from config.settings import CORE_TM_TABLES, TM_R2_BASE_URL
from src.ingestion.football_data_api import FootballDataClient
from src.ingestion.transfermarkt import inspect_table_schema


def test_core_tables_configuration():
    assert "competitions" in CORE_TM_TABLES
    assert "players" in CORE_TM_TABLES
    assert "games" in CORE_TM_TABLES
    assert "appearances" in CORE_TM_TABLES
    assert "player_valuations" in CORE_TM_TABLES
    assert len(CORE_TM_TABLES) >= 8


def test_r2_url_template():
    url = TM_R2_BASE_URL.format(table="competitions")
    assert url.startswith("https://pub-")
    assert url.endswith("competitions.csv.gz")


def test_schema_inspector_on_synthetic_data():
    df = pd.DataFrame(
        {
            "player_id": [1, 2, 3],
            "name": ["A", "B", "C"],
            "date": ["2023-01-01", "2023-06-01", "2023-12-01"],
            "goals": [5, None, 2],
        }
    )
    schema = inspect_table_schema("test_table", df)
    assert schema["record_count"] == 3
    assert schema["column_count"] == 4
    assert schema["duplicate_rows"] == 0
    assert schema["distinct_players"] == 3
    assert schema["date_range"]["min"] == "2023-01-01"
    assert schema["date_range"]["max"] == "2023-12-01"
    assert schema["columns"]["goals"]["null_count"] == 1


def test_football_data_client_graceful_offline(tmp_path):
    client = FootballDataClient(api_key=None, base_url="http://invalid.nonexistent.domain", cache_dir=tmp_path)
    res = client.get("competitions", use_cache=False)
    assert res is None, "Should gracefully return None on network failure without crashing"
