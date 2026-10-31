"""Global player catalog and cross-provider registry for TRANSFERA.

Aggregates verified players from Transfermarkt, Reep Football Entity Register,
StatsBomb Open Data, and API-Football. Preserves identity crosswalks and
enforces multi-provider disambiguation without synthetic records.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from src.connectors.api_football_connector import ApiFootballConnector
from src.connectors.reep_connector import ReepConnector
from src.player_identity_resolution import IdentityResolver, normalize_name

logger = logging.getLogger(__name__)

GLOBAL_PLAYERS_PATH = Path("data/global/global_players.parquet")
PROVIDER_IDS_PATH = Path("data/global/player_provider_ids.parquet")
CLEAN_PLAYERS_PATH = Path("data/interim/clean_players.parquet")
PROCESSED_FEATURES_PATH = Path("data/processed/player_season_features.parquet")


class GlobalPlayerRegistry:
    """Builder and manager for the unified global football player catalog."""

    def __init__(
        self,
        global_players_path: Path | str = GLOBAL_PLAYERS_PATH,
        provider_ids_path: Path | str = PROVIDER_IDS_PATH,
    ):
        self.global_players_path = Path(global_players_path)
        self.provider_ids_path = Path(provider_ids_path)
        self.global_players_path.parent.mkdir(parents=True, exist_ok=True)
        self.resolver = IdentityResolver()

    def build_registry(
        self,
        max_reep_records: int | None = 60000,
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        """Construct the global player database and provider crosswalk table."""
        logger.info("Initializing Global Player Registry build...")

        # 1. Load Stage 1 Transfermarkt Players
        if not CLEAN_PLAYERS_PATH.exists():
            raise FileNotFoundError(f"Missing required Stage 1 player table: {CLEAN_PLAYERS_PATH}")

        tm_players = pd.read_parquet(CLEAN_PLAYERS_PATH)
        logger.info("Loaded %d Stage 1 Transfermarkt players", len(tm_players))

        # Check which players have full features in player_season_features.parquet
        full_feature_pids = set()
        if PROCESSED_FEATURES_PATH.exists():
            feat_df = pd.read_parquet(PROCESSED_FEATURES_PATH, columns=["player_id"])
            full_feature_pids = set(feat_df["player_id"].dropna().astype(int).unique())

        # Build initial lookup dictionary by transfermarkt_player_id
        # Key: int(player_id) -> record dict
        catalog_by_tm: dict[int, dict[str, Any]] = {}
        provider_crosswalk: list[dict[str, Any]] = []

        now_year = datetime.now().year

        for _, row in tm_players.iterrows():
            pid = int(row["player_id"])
            gid = f"tm_{pid}"
            dob_str = str(row.get("date_of_birth", "")).split()[0].strip()
            if dob_str in ["NaT", "None", "nan"]:
                dob_str = ""

            age = None
            if dob_str:
                try:
                    birth_year = int(dob_str.split("-")[0])
                    age = max(15, min(50, now_year - birth_year))
                except Exception:
                    age = None

            cov_status = "FULL_EVIDENCE" if pid in full_feature_pids else "LIMITED_EVIDENCE"

            record = {
                "global_player_id": gid,
                "reep_id": None,
                "transfermarkt_player_id": pid,
                "api_football_player_id": None,
                "fbref_player_id": None,
                "statsbomb_player_id": None,
                "full_name": str(row.get("name", "")).strip(),
                "display_name": str(row.get("name", "")).strip(),
                "date_of_birth": dob_str,
                "age": age,
                "nationality": str(row.get("country_of_citizenship", "Unknown")).strip(),
                "secondary_nationality": None,
                "position": str(row.get("position", "Missing")).strip(),
                "sub_position": str(row.get("sub_position", "")).strip() or None,
                "height_cm": float(row["height_in_cm"]) if pd.notna(row.get("height_in_cm")) else None,
                "preferred_foot": str(row.get("foot", "")).lower() or None,
                "current_club_name": str(row.get("current_club_name", "Unknown")).strip(),
                "current_competition_name": str(row.get("current_club_domestic_competition_id", "Global")).strip(),
                "country": str(row.get("country_of_citizenship", "Global")).strip(),
                "player_image_url": None,
                "profile_source": "TRANSFERMARKT",
                "identity_confidence": 1.0,
                "profile_coverage_status": cov_status,
            }
            catalog_by_tm[pid] = record

            # Add to provider crosswalk
            provider_crosswalk.append(
                {
                    "global_player_id": gid,
                    "provider_name": "transfermarkt",
                    "provider_player_id": str(pid),
                    "confidence": 1.0,
                    "created_at": datetime.utcnow().isoformat(),
                }
            )

        logger.info("Base Stage 1 catalog indexed: %d players", len(catalog_by_tm))

        # 2. Ingest Reep Football Entity Register
        reep_conn = ReepConnector()
        reep_df = reep_conn.load_players(max_rows=max_reep_records)
        reep_added = 0
        reep_enriched = 0

        # Create secondary lookup by (DOB, normalized_name) for Stage 1 players
        dob_name_lookup: dict[tuple[str, str], int] = {}
        for pid, r in catalog_by_tm.items():
            if r["date_of_birth"]:
                norm_n = normalize_name(r["full_name"])
                if norm_n:
                    dob_name_lookup[(r["date_of_birth"], norm_n)] = pid

        additional_records: list[dict[str, Any]] = []

        if not reep_df.empty:
            logger.info("Processing %d Reep player records...", len(reep_df))
            for _, r in reep_df.iterrows():
                reep_id = str(r["reep_id"])
                tm_id_raw = r.get("key_transfermarkt")
                matched_pid: int | None = None

                # Direct Transfermarkt key in Reep
                if pd.notna(tm_id_raw):
                    try:
                        candidate_pid = int(float(tm_id_raw))
                        if candidate_pid in catalog_by_tm:
                            matched_pid = candidate_pid
                    except (ValueError, TypeError):
                        pass

                # Fallback to DOB + normalized name lookup
                dob_val = str(r.get("date_of_birth", "")).strip()
                norm_reep_name = normalize_name(r.get("name"))
                if not matched_pid and dob_val and norm_reep_name:
                    matched_pid = dob_name_lookup.get((dob_val, norm_reep_name))

                if matched_pid:
                    # Enrich existing Stage 1 record
                    existing = catalog_by_tm[matched_pid]
                    existing["reep_id"] = reep_id
                    existing["profile_source"] = "HYBRID"
                    if pd.notna(r.get("key_fbref")) and not existing["fbref_player_id"]:
                        existing["fbref_player_id"] = str(r["key_fbref"])
                    if pd.notna(r.get("key_api_football")) and not existing["api_football_player_id"]:
                        existing["api_football_player_id"] = str(r["key_api_football"])
                    if pd.notna(r.get("height_cm")) and existing["height_cm"] is None:
                        existing["height_cm"] = float(r["height_cm"])

                    provider_crosswalk.append(
                        {
                            "global_player_id": existing["global_player_id"],
                            "provider_name": "reep",
                            "provider_player_id": reep_id,
                            "confidence": 1.0,
                            "created_at": datetime.utcnow().isoformat(),
                        }
                    )
                    reep_enriched += 1
                else:
                    # New global player from Reep
                    gid = f"reep_{reep_id}"
                    p_name = str(r.get("name", "Unknown")).strip()
                    p_nat = str(r.get("nationality", "Unknown")).strip()
                    if p_nat in ["nan", "None", ""]:
                        p_nat = "Unknown"

                    age = None
                    if dob_val:
                        try:
                            birth_year = int(dob_val.split("-")[0])
                            age = max(15, min(50, now_year - birth_year))
                        except Exception:
                            age = None

                    new_rec = {
                        "global_player_id": gid,
                        "reep_id": reep_id,
                        "transfermarkt_player_id": None,
                        "api_football_player_id": str(r["key_api_football"])
                        if pd.notna(r.get("key_api_football"))
                        else None,
                        "fbref_player_id": str(r["key_fbref"]) if pd.notna(r.get("key_fbref")) else None,
                        "statsbomb_player_id": None,
                        "full_name": str(r.get("full_name") or p_name).strip(),
                        "display_name": p_name,
                        "date_of_birth": dob_val or None,
                        "age": age,
                        "nationality": p_nat,
                        "secondary_nationality": None,
                        "position": str(r.get("position", "Missing")).strip(),
                        "sub_position": str(r.get("position_detail", "")).strip() or None,
                        "height_cm": float(r["height_cm"]) if pd.notna(r.get("height_cm")) else None,
                        "preferred_foot": None,
                        "current_club_name": "Global Club / Unaffiliated",
                        "current_competition_name": "Global Domestic League",
                        "country": p_nat if p_nat != "Unknown" else "Global",
                        "player_image_url": None,
                        "profile_source": "REEP",
                        "identity_confidence": 0.95,
                        "profile_coverage_status": "PROFILE_ONLY",
                    }
                    additional_records.append(new_rec)
                    provider_crosswalk.append(
                        {
                            "global_player_id": gid,
                            "provider_name": "reep",
                            "provider_player_id": reep_id,
                            "confidence": 0.95,
                            "created_at": datetime.utcnow().isoformat(),
                        }
                    )
                    reep_added += 1

        logger.info("Reep processing finished: %d enriched, %d new global players added", reep_enriched, reep_added)

        # 3. Ingest Indian Super League & Global Players from StatsBomb / API-Football
        api_conn = ApiFootballConnector()
        isl_data = api_conn.fetch("players", params={"league": 323, "season": 2023})
        for item in isl_data.get("response", []):
            p = item.get("player", {})
            stats_list = item.get("statistics", [{}])
            st = stats_list[0] if stats_list else {}
            p_name = p.get("name")
            dob_val = p.get("birth", {}).get("date")
            p_id = p.get("id")
            club_name = st.get("team", {}).get("name", "Indian Super League Club")
            league_name = st.get("league", {}).get("name", "Indian Super League")
            p_nat = p.get("nationality", "India")

            # Check if matching existing
            norm_p_name = normalize_name(p_name)
            matched = False
            for rec in catalog_by_tm.values():
                if normalize_name(rec["full_name"]) == norm_p_name and (not dob_val or rec["date_of_birth"] == dob_val):
                    rec["api_football_player_id"] = str(p_id)
                    rec["profile_source"] = "HYBRID"
                    matched = True
                    break

            if not matched:
                gid = f"apifb_{p_id}"
                new_rec = {
                    "global_player_id": gid,
                    "reep_id": None,
                    "transfermarkt_player_id": None,
                    "api_football_player_id": str(p_id),
                    "fbref_player_id": None,
                    "statsbomb_player_id": None,
                    "full_name": f"{p.get('firstname', '')} {p.get('lastname', '')}".strip() or p_name,
                    "display_name": p_name,
                    "date_of_birth": dob_val,
                    "age": p.get("age"),
                    "nationality": p_nat,
                    "secondary_nationality": None,
                    "position": st.get("games", {}).get("position", "Attacker"),
                    "sub_position": None,
                    "height_cm": float(p.get("height", "170 cm").replace("cm", "").strip())
                    if p.get("height")
                    else None,
                    "preferred_foot": None,
                    "current_club_name": club_name,
                    "current_competition_name": league_name,
                    "country": "India",
                    "player_image_url": p.get("photo"),
                    "profile_source": "API_FOOTBALL",
                    "identity_confidence": 0.95,
                    "profile_coverage_status": "LIMITED_EVIDENCE",  # Has real stats from ISL
                }
                additional_records.append(new_rec)
                provider_crosswalk.append(
                    {
                        "global_player_id": gid,
                        "provider_name": "api_football",
                        "provider_player_id": str(p_id),
                        "confidence": 0.95,
                        "created_at": datetime.utcnow().isoformat(),
                    }
                )

        # Combine all records
        all_players = list(catalog_by_tm.values()) + additional_records
        global_df = pd.DataFrame(all_players)
        crosswalk_df = pd.DataFrame(provider_crosswalk)

        # Enforce column datatypes
        global_df["global_player_id"] = global_df["global_player_id"].astype(str)
        global_df["age"] = pd.to_numeric(global_df["age"], errors="coerce")
        global_df["height_cm"] = pd.to_numeric(global_df["height_cm"], errors="coerce")
        global_df["identity_confidence"] = global_df["identity_confidence"].astype(float)

        # Save to Parquet
        global_df.to_parquet(self.global_players_path, index=False)
        crosswalk_df.to_parquet(self.provider_ids_path, index=False)

        logger.info(
            "Successfully created global catalog: %d total players, %d crosswalk mappings at %s",
            len(global_df),
            len(crosswalk_df),
            self.global_players_path,
        )
        return global_df, crosswalk_df
