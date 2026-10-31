"""Tests for player identity resolution and disambiguation."""

from __future__ import annotations

import pytest

from src.player_identity_resolution import IdentityResolver, normalize_name


@pytest.fixture
def resolver():
    return IdentityResolver()


def test_normalize_name():
    """Verify accents and punctuation are stripped while preserving base names."""
    assert normalize_name("Kylian Mbappé") == "kylian mbappe"
    assert normalize_name("Erling Braut Håland") == "erling braut haland"
    assert normalize_name("Gabriel Teodoro Martinelli Silva") == "gabriel teodoro martinelli silva"
    assert normalize_name("J. Bellingham") == "j bellingham"


def test_exact_provider_match(resolver):
    """Verify matching on external provider IDs."""
    cand_a = {"player_id": 418560, "name": "Erling Haaland"}
    cand_b = {"transfermarkt_player_id": 418560, "name": "E. Haaland"}
    is_match, reason, conf = resolver.match_players(cand_a, cand_b)
    assert is_match is True
    assert reason == "EXACT_TRANSFERMARKT_ID"
    assert conf == 1.0


def test_exact_reep_id_match(resolver):
    """Verify matching on Reep canonical IDs."""
    cand_a = {"reep_id": "reep_p12345", "name": "Lionel Messi"}
    cand_b = {"reep_id": "reep_p12345", "name": "L. Messi"}
    is_match, reason, conf = resolver.match_players(cand_a, cand_b)
    assert is_match is True
    assert reason == "EXACT_REEP_ID"
    assert conf == 1.0


def test_dob_and_normalized_name_match(resolver):
    """Verify matching when provider IDs are absent but DOB and name match."""
    cand_a = {"name": "Luka Modrić", "date_of_birth": "1985-09-09", "nationality": "Croatia"}
    cand_b = {"name": "Luka Modric", "date_of_birth": "1985-09-09", "nationality": "Croatia"}
    is_match, reason, conf = resolver.match_players(cand_a, cand_b)
    assert is_match is True
    assert reason == "DOB_AND_NORMALIZED_NAME_MATCH"
    assert conf == 0.95


def test_single_name_no_dob_collision_prevented(resolver):
    """Verify single common names without DOB are NOT merged (prevent collision)."""
    cand_a = {"name": "Gabriel", "date_of_birth": None}
    cand_b = {"name": "Gabriel", "date_of_birth": None}
    is_match, reason, conf = resolver.match_players(cand_a, cand_b)
    assert is_match is False
    assert "COLLISION_PREVENTED" in reason
    assert conf == 0.0


def test_mismatched_dob_same_name_prevented(resolver):
    """Verify two players with the same name but different DOBs are NOT merged."""
    cand_a = {"name": "Luis Suarez", "date_of_birth": "1987-01-24"}
    cand_b = {"name": "Luis Suarez", "date_of_birth": "1997-12-02"}
    is_match, reason, conf = resolver.match_players(cand_a, cand_b)
    assert is_match is False
    assert reason == "DOB_MISMATCH_SAME_NAME"
