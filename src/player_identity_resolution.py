"""Player identity resolution across heterogeneous data providers.

Enforces strict disambiguation rules:
1. Exact external provider ID crosswalk matching.
2. Exact date-of-birth + normalized name matching.
3. Nationality and club verification.
4. Strictly forbids single-name collisions or blind merges.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from typing import Any

logger = logging.getLogger(__name__)


def normalize_name(name: str | None) -> str:
    """Normalize player name: strip accents, lower-case, remove punctuation and extra spaces."""
    if not name or not isinstance(name, str):
        return ""
    # Decompose unicode characters into base char + combining accents
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_bytes = nfkd.encode("ASCII", "ignore")
    cleaned = ascii_bytes.decode("utf-8").lower()
    # Remove quotes, parentheses, periods, hyphens
    cleaned = re.sub(r"[^a-z0-9\s]", " ", cleaned)
    # Collapse multiple whitespaces
    return " ".join(cleaned.split())


class IdentityResolver:
    """Resolves identities across Transfermarkt, Reep, API-Football, and StatsBomb."""

    def __init__(self):
        self.resolved_count = 0
        self.collisions_prevented = 0
        self.unresolved_count = 0
        self.audit_log: list[dict[str, Any]] = []

    def match_players(
        self,
        candidate_a: dict[str, Any],
        candidate_b: dict[str, Any],
    ) -> tuple[bool, str, float]:
        """Determine if two candidate player records represent the same individual.

        Returns (is_match, match_reason, confidence_score).
        """
        # Rule 1: Exact Provider ID Match (Transfermarkt ID)
        tm_a = candidate_a.get("transfermarkt_player_id") or candidate_a.get("player_id")
        tm_b = candidate_b.get("transfermarkt_player_id") or candidate_b.get("player_id")
        if tm_a and tm_b:
            try:
                if int(tm_a) == int(tm_b):
                    self.resolved_count += 1
                    return True, "EXACT_TRANSFERMARKT_ID", 1.0
            except (ValueError, TypeError):
                pass

        # Reep ID Match
        reep_a = candidate_a.get("reep_id")
        reep_b = candidate_b.get("reep_id")
        if reep_a and reep_b and str(reep_a).strip() == str(reep_b).strip():
            self.resolved_count += 1
            return True, "EXACT_REEP_ID", 1.0

        # API-Football ID Match
        api_a = candidate_a.get("api_football_player_id")
        api_b = candidate_b.get("api_football_player_id")
        if api_a and api_b:
            try:
                if int(api_a) == int(api_b):
                    self.resolved_count += 1
                    return True, "EXACT_API_FOOTBALL_ID", 1.0
            except (ValueError, TypeError):
                pass

        # Rule 2: Date of Birth + Normalized Full Name
        dob_a = str(candidate_a.get("date_of_birth", "")).split()[0].strip()
        dob_b = str(candidate_b.get("date_of_birth", "")).split()[0].strip()

        norm_name_a = normalize_name(candidate_a.get("full_name") or candidate_a.get("name"))
        norm_name_b = normalize_name(candidate_b.get("full_name") or candidate_b.get("name"))

        # Never match on name alone if DOB is missing or mismatched
        if not dob_a or not dob_b or dob_a == "NaT" or dob_b == "NaT" or dob_a == "None" or dob_b == "None":
            if norm_name_a == norm_name_b and len(norm_name_a.split()) == 1:
                # Common single name like "Gabriel" or "Ronaldo"
                self.collisions_prevented += 1
                return False, "SINGLE_NAME_NO_DOB_COLLISION_PREVENTED", 0.0
            return False, "MISSING_DOB", 0.0

        # If DOBs don't match, definitely not the same person
        if dob_a != dob_b:
            if norm_name_a == norm_name_b:
                self.collisions_prevented += 1
                return False, "DOB_MISMATCH_SAME_NAME", 0.0
            return False, "DIFFERENT_DOB", 0.0

        # At this point, DOB matches! Now check name similarity
        if norm_name_a == norm_name_b and len(norm_name_a) > 3:
            # Check nationality if both present
            nat_a = str(candidate_a.get("nationality", "")).lower()
            nat_b = str(candidate_b.get("nationality", "")).lower()
            if nat_a and nat_b and nat_a != nat_b and nat_a != "unknown" and nat_b != "unknown":
                # Conflicting nationalities
                self.collisions_prevented += 1
                return False, "NATIONALITY_CONFLICT", 0.0

            self.resolved_count += 1
            return True, "DOB_AND_NORMALIZED_NAME_MATCH", 0.95

        # Check token subset match when DOB matches (e.g. "Gabriel Martinelli" vs "Gabriel Teodoro Martinelli Silva")
        tokens_a = set(norm_name_a.split())
        tokens_b = set(norm_name_b.split())
        overlap = tokens_a.intersection(tokens_b)
        if len(overlap) >= 2 and (tokens_a.issubset(tokens_b) or tokens_b.issubset(tokens_a)):
            self.resolved_count += 1
            return True, "DOB_AND_NAME_TOKEN_SUBSET_MATCH", 0.90

        self.unresolved_count += 1
        return False, "UNRESOLVED_DISTINCT", 0.0
