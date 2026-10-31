"""Streamlit cached interface for the Two-Stage Global Player Search.

Ensures lightning-fast debounced lookups and clean isolation between
the Stage 1 model records and the global fallback catalog.
"""

from __future__ import annotations

import streamlit as st

from src.global_player_search import SearchResult, TwoStageSearchService


@st.cache_resource(show_spinner=False)
def get_two_stage_search_service() -> TwoStageSearchService:
    """Singleton cached instance of the two-stage search service."""
    return TwoStageSearchService()


def search_players_interactive(
    query: str,
    limit: int = 30,
    position_filter: str | None = None,
    country_filter: str | None = None,
) -> tuple[list[SearchResult], str]:
    """Execute two-stage search for the interactive dashboard."""
    svc = get_two_stage_search_service()
    return svc.search(
        query=query,
        limit=limit,
        position_filter=position_filter,
        country_filter=country_filter,
    )


def get_player_details(identifier: str | int) -> tuple[dict | None, str]:
    """Retrieve full player record and identify database source."""
    svc = get_two_stage_search_service()
    return svc.get_player_by_id(identifier)
