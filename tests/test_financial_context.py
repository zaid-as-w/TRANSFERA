"""Tests for financial environment and revenue context engine."""

import pandas as pd

from src.financial_context import FinancialContextEngine


def test_financial_context_known_club_vs_fallback():
    engine = FinancialContextEngine()
    # Real Madrid (club 418) has published DFML figures
    rm_ctx = engine.get_financial_context(club_id=418, competition_id="ES1", season=2023)
    assert rm_ctx["has_club_financials"] is True
    assert rm_ctx["financial_aggregation_level"] == "club_observed"
    assert rm_ctx["club_revenue_eur"] > 500_000_000

    # Unlisted club in ES1 gets league fallback
    unlisted_ctx = engine.get_financial_context(club_id=999999, competition_id="ES1", season=2023)
    assert unlisted_ctx["has_club_financials"] is False
    assert unlisted_ctx["has_league_financials"] is True
    assert unlisted_ctx["financial_aggregation_level"] == "league_fallback"
    assert unlisted_ctx["club_revenue_eur"] is None
    assert unlisted_ctx["league_average_revenue_eur"] > 0


def test_financial_context_unknown_league():
    engine = FinancialContextEngine()
    ctx = engine.get_financial_context(club_id=999999, competition_id="UNKNOWN_LEAGUE", season=2023)
    assert ctx["has_club_financials"] is False
    assert ctx["has_league_financials"] is False
    assert ctx["financial_aggregation_level"] == "missing"
    assert ctx["club_revenue_eur"] is None
    assert ctx["league_average_revenue_eur"] is None


def test_enrich_features_df():
    engine = FinancialContextEngine()
    df = pd.DataFrame(
        {
            "club_id": [418, 999999],
            "competition_id": ["ES1", "ES1"],
            "season": [2023, 2023],
        }
    )
    enriched = engine.enrich_features_df(df)
    assert "club_revenue_eur" in enriched.columns
    assert "has_club_financials" in enriched.columns
    assert enriched["has_club_financials"].iloc[0]
    assert not enriched["has_club_financials"].iloc[1]
    assert enriched["financial_aggregation_level"].iloc[0] == "club_observed"
    assert enriched["financial_aggregation_level"].iloc[1] == "league_fallback"
