"""Tests for league strength estimation and competition intensity engine."""

from src.league_strength import INITIAL_ELO, LeagueStrengthEngine


def test_league_strength_fallback_on_uncalibrated_league():
    engine = LeagueStrengthEngine()
    engine.is_fitted = True  # Mock fitted status

    res = engine.get_league_strength("UNKNOWN_LEAGUE_99")
    assert res["competition_strength"] == 1.0
    assert res["mean_elo"] == INITIAL_ELO
    assert res["has_cross_league_evidence"] is False
    assert res["warning"] == "INSUFFICIENT_EVIDENCE"


def test_intensity_metrics_default():
    engine = LeagueStrengthEngine()
    engine.is_fitted = True

    im = engine.get_intensity_metrics("NONEXISTENT_COMP", 2023)
    assert "goals_per_match" in im
    assert "cards_per_match" in im
    assert "competitive_balance_index" in im
    assert im["goals_per_match"] > 0
    assert im["cards_per_match"] > 0


def test_cached_ratings_integrity():
    engine = LeagueStrengthEngine()
    if engine.ratings_cache_path.exists():
        engine._load_cached_ratings()
        assert engine.is_fitted
        # Check Top 5 presence
        for comp in ["GB1", "ES1", "IT1", "L1", "FR1"]:
            st = engine.get_league_strength(comp, 2023)
            assert st["competition_strength"] > 1.0, f"Expected {comp} strength > 1.0"
            assert st["has_cross_league_evidence"] is True
            assert st["cross_league_matches"] >= 50
