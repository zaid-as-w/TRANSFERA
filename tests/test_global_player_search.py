"""Tests for two-stage player and country search engine."""

from __future__ import annotations

import pytest

from src.global_player_search import NO_RESULTS_MESSAGE, TwoStageSearchService


@pytest.fixture
def search_service():
    """Create fresh instance of two-stage search service."""
    return TwoStageSearchService()


def test_stage1_search_priority(search_service):
    """Verify that Stage 1 database is queried first and returns STAGE 1 DATABASE tag."""
    # Erling Haaland is a well-known Stage 1 player
    results, msg = search_service.search("Haaland", limit=5)
    assert len(results) > 0
    assert results[0].source_database == "STAGE 1 DATABASE"
    assert "Haaland" in results[0].name
    assert results[0].can_predict is True


def test_global_fallback_triggers_only_on_zero_stage1(search_service):
    """Verify that global fallback triggers automatically when Stage 1 has zero results."""
    # Aad Andriessen is a verified player present only in the global entity register
    results, msg = search_service.search("Aad Andriessen", limit=5)
    assert len(results) > 0
    assert results[0].source_database == "GLOBAL DATABASE"
    assert "Andriessen" in results[0].name


def test_no_results_message(search_service):
    """Verify exact no-results message when player does not exist in either database."""
    results, msg = search_service.search("NonexistentXyzFictionalPlayer999")
    assert len(results) == 0
    assert msg == NO_RESULTS_MESSAGE


def test_country_search_distinguishes_nationality_from_club_country(search_service):
    """Verify country search correctly identifies nationality vs club country."""
    # Search for Brazil should return Brazilian nationals
    results, msg = search_service.search("Brazil", limit=10)
    assert len(results) > 0
    # Every player returned in Stage 1 Brazil search has Brazilian nationality or Brazil club
    for r in results:
        assert (
            "brazil" in r.nationality.lower()
            or "brazil" in r.country.lower()
            or "bra1" in r.current_competition_name.lower()
        )


def test_search_pagination_and_limits(search_service):
    """Verify search respects user-defined limit."""
    results, _ = search_service.search("a", limit=7)
    assert len(results) <= 7


def test_get_player_by_id_identifies_source(search_service):
    """Verify get_player_by_id correctly identifies database origin."""
    # Stage 1 ID (e.g. integer 10 Miroslav Klose)
    rec, source = search_service.get_player_by_id(10)
    assert rec is not None
    assert source == "STAGE 1 DATABASE"

    # Global ID
    rec_g, source_g = search_service.get_player_by_id("apifb_85002")
    assert rec_g is not None
    assert source_g == "GLOBAL DATABASE"
