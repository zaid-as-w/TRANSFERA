"""Tests for external data connectors (API-Football, Reep, StatsBomb)."""

from __future__ import annotations

from src.connectors.api_football_connector import ApiFootballConnector
from src.connectors.reep_connector import ReepConnector
from src.connectors.statsbomb_connector import StatsBombConnector


def test_api_football_offline_graceful_fallback():
    """Verify API-Football provides verified mock fixtures without credentials."""
    conn = ApiFootballConnector(api_key=None)
    assert conn.is_configured is False

    # Query Indian Super League (league 323)
    data = conn.fetch("players", params={"league": 323, "season": 2023})
    assert "response" in data
    assert len(data["response"]) > 0

    first_player = data["response"][0]["player"]
    assert first_player["name"] == "Sunil Chhetri"
    assert first_player["nationality"] == "India"


def test_reep_connector_excludes_coaches():
    """Verify Reep connector excludes coaches and preserves verified players."""
    conn = ReepConnector()
    df = conn.load_players(max_rows=100)
    if not df.empty:
        # Strictly no coaches
        assert "coach" not in df["type"].values
        assert (df["type"] == "player").all()


def test_statsbomb_connector_open_competitions():
    """Verify StatsBomb connector loads competition metadata."""
    conn = StatsBombConnector()
    comps = conn.fetch_competitions()
    assert len(comps) > 0
    names = [c.get("competition_name") for c in comps]
    assert any("Bundesliga" in n or "Champions League" in n or "Indian" in n for n in names)
