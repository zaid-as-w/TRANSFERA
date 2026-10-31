"""Tests for Dashboard Data Service, Formatting, and Image Resolving."""

import pytest

from dashboard.data_service import DataService
from dashboard.formatting import format_currency_eur, format_delta_eur, format_delta_pct, get_country_flag
from dashboard.image_service import get_club_crest_url, get_competition_logo_url, get_player_image_url


@pytest.fixture(scope="module")
def data_service() -> DataService:
    return DataService()


def test_data_service_initialization(data_service: DataService):
    assert data_service.df is not None
    assert len(data_service.df) > 50000
    assert "historical_market_value" in data_service.df.columns
    assert len(data_service.registry) > 0
    assert len(data_service.league_strengths) > 0


def test_seasons_and_competitions(data_service: DataService):
    seasons = data_service.get_seasons()
    assert len(seasons) >= 10
    assert 2023 in seasons

    comps = data_service.get_competitions()
    assert len(comps) >= 5
    comp_ids = [c["id"] for c in comps]
    for core_id in ["GB1", "ES1", "IT1", "L1", "FR1"]:
        assert core_id in comp_ids


def test_filtering_and_kpis(data_service: DataService):
    df_filtered = data_service.filter_data(season=2023, competition_id="GB1")
    assert len(df_filtered) > 0
    assert (df_filtered["season"] == 2023).all()
    assert (df_filtered["competition_id"] == "GB1").all()

    kpis = data_service.get_kpis(df_filtered)
    assert kpis["total_records"] == len(df_filtered)
    assert kpis["total_market_value"] > 0
    assert kpis["highest_market_value"] >= 100_000_000  # Haaland / Bellingham tier


def test_player_search(data_service: DataService):
    results = data_service.search_players("Haaland", limit=5)
    assert len(results) > 0
    assert any("haaland" in r["name"].lower() for r in results)
    first = results[0]
    assert "player_id" in first
    assert "age" in first
    assert "goals" in first
    assert "market_value_eur" in first


def test_formatting_helpers():
    assert format_currency_eur(180_000_000) == "€180.0M"
    assert format_currency_eur(250_000) == "€250K"
    assert format_currency_eur(1_500_000_000) == "€1.5B"
    assert format_currency_eur(0) == "€0"

    assert format_delta_pct(5.23) == "+5.2%"
    assert format_delta_pct(-3.45) == "-3.5%"

    assert format_delta_eur(500_000) == "+€500K"
    assert format_delta_eur(-2_000_000) == "-€2.0M"

    assert get_country_flag("England") == "🏴󠁧󠁢󠁥󠁮󠁧󠁿"
    assert get_country_flag("Brazil") == "🇧🇷"
    assert get_country_flag("Unknown") == "🌐"


def test_image_resolvers():
    # Player image
    img = get_player_image_url(418560, "https://example.com/erling.jpg")
    assert img == "https://example.com/erling.jpg"

    # Club crest
    crest = get_club_crest_url(281)
    assert "281" in crest

    # Competition logo
    logo = get_competition_logo_url("GB1")
    assert "gb1" in logo.lower() or "premier-league" in logo.lower()
