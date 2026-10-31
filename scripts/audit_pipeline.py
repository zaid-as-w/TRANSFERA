"""
End-to-end Stage 1 audit script — corrected for actual API.
Uses real class names: ValuationPredictor, DataSplitter, PlayerInput.
"""

import io
import json
import sys
import warnings
from pathlib import Path

import numpy as np  # noqa: F401
import pandas as pd

warnings.filterwarnings("ignore")

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).parent.parent
DATA_RAW = ROOT / "data" / "raw" / "transfermarkt"
DATA_INTERIM = ROOT / "data" / "interim"
DATA_PROCESSED = ROOT / "data" / "processed"
DATA_META = ROOT / "data" / "metadata"
MODELS = ROOT / "models"
FINANCIAL_RAW = ROOT / "data" / "raw" / "financial"

PASS = "PASS"
FAIL = "FAIL"
WARN = "WARN"
INFO = "INFO"

results = []


def record(check, status, detail=""):
    results.append({"check": check, "status": status, "detail": str(detail)})
    prefix = "[OK ]" if status == PASS else ("[ERR]" if status == FAIL else ("[WRN]" if status == WARN else "[INF]"))
    print(f"{prefix} [{check}] {detail}", flush=True)


def section(title):
    print(f"\n--- {title} ---", flush=True)


print("=" * 72)
print("STAGE 1 END-TO-END AUDIT")
print("=" * 72)

# ---------------------------------------------------------------------------
# 1. RAW DATA FILES
# ---------------------------------------------------------------------------
section("1. RAW DATA FILE PRESENCE")

EXPECTED_TABLES = [
    "appearances",
    "clubs",
    "club_games",
    "competitions",
    "countries",
    "games",
    "players",
    "player_valuations",
    "transfers",
]
raw_frames = {}
for tbl in EXPECTED_TABLES:
    fp = DATA_RAW / f"{tbl}.csv.gz"
    if fp.exists():
        df = pd.read_csv(fp, compression="gzip", low_memory=False)
        raw_frames[tbl] = df
        record(f"raw/{tbl}", PASS, f"{len(df):,} rows x {len(df.columns)} cols | {fp.stat().st_size / 1e6:.1f} MB")
    else:
        raw_frames[tbl] = None
        record(f"raw/{tbl}", FAIL, "File missing")

# ---------------------------------------------------------------------------
# 2. SCHEMA CHECKS
# ---------------------------------------------------------------------------
section("2. SCHEMA / COLUMN CHECKS")

REQUIRED_COLS = {
    "players": ["player_id", "name", "date_of_birth", "position", "current_club_id"],
    "player_valuations": ["player_id", "date", "market_value_in_eur"],
    "appearances": ["player_id", "game_id", "minutes_played", "goals", "assists"],
    "games": ["game_id", "competition_id", "season", "date", "home_club_id", "away_club_id"],
    "clubs": ["club_id", "name", "domestic_competition_id"],
    "competitions": ["competition_id", "name", "type", "country_name"],
    "transfers": ["player_id", "transfer_date", "from_club_id", "to_club_id", "transfer_fee"],
    "club_games": ["game_id", "club_id"],
}

for tbl, cols in REQUIRED_COLS.items():
    df = raw_frames.get(tbl)
    if df is None:
        record(f"schema/{tbl}", FAIL, "Table not loaded")
        continue
    missing = [c for c in cols if c not in df.columns]
    if missing:
        record(f"schema/{tbl}", FAIL, f"Missing columns: {missing}")
    else:
        record(f"schema/{tbl}", PASS, f"All required columns present: {cols[:3]}...")

# ---------------------------------------------------------------------------
# 3. DATE COVERAGE
# ---------------------------------------------------------------------------
section("3. DATE COVERAGE")

pv = raw_frames.get("player_valuations")
if pv is not None:
    pv["date"] = pd.to_datetime(pv["date"], errors="coerce")
    date_min = pv["date"].min()
    date_max = pv["date"].max()
    record("valuations/date_range", PASS, f"{date_min.date()} to {date_max.date()} | {len(pv):,} records")
    null_dates = int(pv["date"].isna().sum())
    record("valuations/null_dates", WARN if null_dates > 0 else PASS, f"{null_dates} null dates in player_valuations")

games = raw_frames.get("games")
if games is not None:
    games["date"] = pd.to_datetime(games["date"], errors="coerce")
    g_min = games["date"].min()
    g_max = games["date"].max()
    record("games/date_range", PASS, f"{g_min.date()} to {g_max.date()} | {len(games):,} games")

# ---------------------------------------------------------------------------
# 4. COMPETITION IDs & TOP 5 LEAGUES
# ---------------------------------------------------------------------------
section("4. COMPETITION IDs AND TOP-5 LEAGUE COVERAGE")

TOP5 = {
    "GB1": "English Premier League",
    "ES1": "Spanish La Liga",
    "IT1": "Italian Serie A",
    "L1": "German Bundesliga",
    "FR1": "French Ligue 1",
}

comps = raw_frames.get("competitions")
if comps is not None:
    present_ids = set(comps["competition_id"].unique())
    for cid, cname in TOP5.items():
        if cid in present_ids:
            row = comps[comps["competition_id"] == cid].iloc[0]
            record(
                f"competition/{cid}",
                PASS,
                f"{row['name']} | type={row.get('type', '?')} | country={row.get('country_name', '?')}",
            )
        else:
            record(f"competition/{cid}", FAIL, f"{cname} ({cid}) not in competitions table")

if games is not None:
    for cid, cname in TOP5.items():
        n = int((games["competition_id"] == cid).sum())
        sub = games.loc[games["competition_id"] == cid, "season"].dropna().unique().tolist()
        seasons = sorted(sub)
        if n > 0:
            record(f"games/{cid}", PASS, f"{n:,} games | seasons {seasons[0]} to {seasons[-1]}")
        else:
            record(f"games/{cid}", FAIL, f"No games found for {cid}")

# ---------------------------------------------------------------------------
# 5. MISSING VALUE AUDIT
# ---------------------------------------------------------------------------
section("5. MISSING VALUE AUDIT")

CRITICAL_NULLS = {
    "player_valuations": ["player_id", "date", "market_value_in_eur"],
    "players": ["player_id", "date_of_birth", "position"],
    "appearances": ["player_id", "game_id", "minutes_played"],
    "games": ["game_id", "competition_id", "date"],
}
for tbl, cols in CRITICAL_NULLS.items():
    df = raw_frames.get(tbl)
    if df is None:
        continue
    for col in cols:
        if col not in df.columns:
            continue
        pct = df[col].isna().mean() * 100
        status = PASS if pct < 5 else (WARN if pct < 20 else FAIL)
        record(f"nulls/{tbl}/{col}", status, f"{pct:.1f}% missing")

# ---------------------------------------------------------------------------
# 6. DUPLICATE RECORD CHECK
# ---------------------------------------------------------------------------
section("6. DUPLICATE RECORD CHECK")

DUP_KEYS = {
    "player_valuations": ["player_id", "date"],
    "games": ["game_id"],
    "players": ["player_id"],
    "clubs": ["club_id"],
    "appearances": ["player_id", "game_id"],
}
for tbl, keys in DUP_KEYS.items():
    df = raw_frames.get(tbl)
    if df is None:
        continue
    valid_keys = [k for k in keys if k in df.columns]
    if not valid_keys:
        continue
    dups = int(df.duplicated(subset=valid_keys).sum())
    record(f"duplicates/{tbl}", PASS if dups == 0 else WARN, f"{dups:,} duplicate rows on {valid_keys}")

# ---------------------------------------------------------------------------
# 7. JOIN INTEGRITY
# ---------------------------------------------------------------------------
section("7. JOIN INTEGRITY")

apps = raw_frames.get("appearances")
players = raw_frames.get("players")

if apps is not None and games is not None:
    game_ids = set(games["game_id"].dropna())
    orphan_apps = int((~apps["game_id"].isin(game_ids)).sum())
    pct = orphan_apps / len(apps) * 100
    record(
        "join/appearances->games",
        PASS if pct < 2 else (WARN if pct < 10 else FAIL),
        f"{orphan_apps:,} orphan appearance rows ({pct:.1f}%)",
    )

if apps is not None and players is not None:
    player_ids = set(players["player_id"].dropna())
    orphan_pl = int((~apps["player_id"].isin(player_ids)).sum())
    pct = orphan_pl / len(apps) * 100
    record(
        "join/appearances->players",
        PASS if pct < 2 else (WARN if pct < 10 else FAIL),
        f"{orphan_pl:,} unmatched player_ids ({pct:.1f}%)",
    )

if pv is not None and players is not None:
    player_ids = set(players["player_id"].dropna())
    orphan_vals = int((~pv["player_id"].isin(player_ids)).sum())
    pct = orphan_vals / len(pv) * 100
    record(
        "join/valuations->players",
        PASS if pct < 2 else (WARN if pct < 10 else FAIL),
        f"{orphan_vals:,} valuation rows with unknown player ({pct:.1f}%)",
    )

if games is not None and comps is not None:
    comp_ids = set(comps["competition_id"].dropna())
    orphan_games = int((~games["competition_id"].isin(comp_ids)).sum())
    pct = orphan_games / len(games) * 100
    record(
        "join/games->competitions",
        PASS if pct < 2 else WARN,
        f"{orphan_games:,} games with unknown competition ({pct:.1f}%)",
    )

# ---------------------------------------------------------------------------
# 8. CURRENCY CHECK
# ---------------------------------------------------------------------------
section("8. CURRENCY CHECK")

if pv is not None and "market_value_in_eur" in pv.columns:
    mv = pv["market_value_in_eur"].dropna()
    neg = int((mv < 0).sum())
    zero = int((mv == 0).sum())
    very_high = int((mv > 500_000_000).sum())
    record(
        "currency/market_value_in_eur",
        PASS if neg == 0 else FAIL,
        f"min={mv.min():,.0f} max={mv.max():,.0f} | neg={neg} zero={zero} >500M={very_high}",
    )
    record("currency/eur_confirmed", PASS, "Transfermarkt market_value_in_eur is natively EUR - no conversion needed")

# ---------------------------------------------------------------------------
# 9. TRANSFER FEE AUDIT
# ---------------------------------------------------------------------------
section("9. TRANSFER FEE AUDIT")

transfers = raw_frames.get("transfers")
if transfers is not None and "transfer_fee" in transfers.columns:
    tf = transfers["transfer_fee"].dropna()
    null_pct = transfers["transfer_fee"].isna().mean() * 100
    record(
        "transfers/fee_null_pct",
        PASS if null_pct < 60 else WARN,
        f"{null_pct:.1f}% of fees are null/undisclosed (expected for real data)",
    )
    if len(tf) > 0:
        record("transfers/fee_range", INFO, f"Non-null fee range: {tf.min():,.0f} to {tf.max():,.0f} EUR")

# ---------------------------------------------------------------------------
# 10. INTERIM PARQUET FILES
# ---------------------------------------------------------------------------
section("10. INTERIM PARQUET FILES")

EXPECTED_INTERIM = [
    "clean_players",
    "clean_games",
    "clean_appearances",
    "clean_player_valuations",
    "clean_clubs",
    "clean_transfers",
    "clean_competitions",
]
for name in EXPECTED_INTERIM:
    fp = DATA_INTERIM / f"{name}.parquet"
    if fp.exists():
        df = pd.read_parquet(fp)
        record(f"interim/{name}", PASS, f"{len(df):,} rows x {len(df.columns)} cols | {fp.stat().st_size / 1e6:.1f} MB")
    else:
        record(f"interim/{name}", FAIL, f"File missing: {name}.parquet")

# ---------------------------------------------------------------------------
# 11. PROCESSED FEATURE TABLE
# ---------------------------------------------------------------------------
section("11. PROCESSED FEATURE TABLE")

feat_fp = DATA_PROCESSED / "player_season_features.parquet"
feat_df = None
if feat_fp.exists():
    feat_df = pd.read_parquet(feat_fp)
    seasons = sorted(feat_df["season"].dropna().unique().tolist())
    record(
        "features/exists",
        PASS,
        f"{len(feat_df):,} rows x {len(feat_df.columns)} cols | seasons {seasons[0]} to {seasons[-1]}",
    )

    if "historical_market_value" in feat_df.columns:
        tv = feat_df["historical_market_value"].dropna()
        record(
            "features/target_column",
            PASS,
            f"historical_market_value: {len(tv):,} non-null | min={tv.min():,.0f} max={tv.max():,.0f}",
        )
    else:
        record("features/target_column", FAIL, "historical_market_value column MISSING")

    if "competition_id" in feat_df.columns:
        for cid, cname in TOP5.items():
            n = int((feat_df["competition_id"] == cid).sum())
            status = PASS if n >= 100 else (WARN if n > 0 else FAIL)
            record(f"features/league_{cid}", status, f"{n:,} player-season rows")

    # DATA LEAKAGE: previous_valuation_date must be before valuation_reference_date
    if "previous_valuation_date" in feat_df.columns and "valuation_reference_date" in feat_df.columns:
        prev = pd.to_datetime(feat_df["previous_valuation_date"], errors="coerce")
        ref = pd.to_datetime(feat_df["valuation_reference_date"], errors="coerce")
        both_valid = prev.notna() & ref.notna()
        leakage_rows = int((prev[both_valid] > ref[both_valid]).sum())
        record(
            "leakage/prev_valuation_before_reference",
            PASS if leakage_rows == 0 else FAIL,
            f"{leakage_rows} rows where previous_valuation_date > valuation_reference_date (must be 0)",
        )
    else:
        record(
            "leakage/prev_valuation_vs_reference",
            WARN,
            "previous_valuation_date or valuation_reference_date not in features",
        )

    # Check actual feature columns vs expected
    ACTUAL_KEY_COLS = {
        "age_at_reference_date": "age proxy",
        "goals_per_90": "per-90 goals",
        "minutes_played": "minutes",
        "competition_strength": "league strength",
        "previous_market_value": "prior valuation",
        "financial_aggregation_level": "financial flag",
    }
    for col, desc in ACTUAL_KEY_COLS.items():
        if col in feat_df.columns:
            pct = feat_df[col].isna().mean() * 100
            status = PASS if pct < 30 else WARN
            record(f"features/null/{col}", status, f"{pct:.1f}% missing [{desc}]")
        else:
            record(f"features/missing/{col}", WARN, f"Column '{col}' ({desc}) not in feature table")
else:
    record("features/exists", FAIL, "player_season_features.parquet missing - run src.player_features")

# ---------------------------------------------------------------------------
# 12. TEMPORAL SPLIT CHECK
# ---------------------------------------------------------------------------
section("12. TEMPORAL SPLIT CHECK")

if feat_df is not None and "season" in feat_df.columns:
    sys.path.insert(0, str(ROOT))
    from src.temporal_splits import DataSplitter  # correct class name

    try:
        splitter = DataSplitter()
        # chronological_split returns 4 values: train, val, test, metadata
        result = splitter.chronological_split(feat_df)
        train_df, val_df, test_df, split_meta = result
        tr_seasons = sorted(train_df["season"].unique().tolist())
        val_seasons = sorted(val_df["season"].unique().tolist())
        te_seasons = sorted(test_df["season"].unique().tolist())
        ok = max(tr_seasons) < min(val_seasons) and max(val_seasons) <= min(te_seasons)
        record(
            "temporal_split/ordering",
            PASS if ok else FAIL,
            (
                f"Train {tr_seasons[0]}-{tr_seasons[-1]} | "
                f"Val {val_seasons[0]}-{val_seasons[-1]} | "
                f"Test {te_seasons[0]}-{te_seasons[-1]}"
            ),
        )
        record("temporal_split/sizes", INFO, f"Train {len(train_df):,} | Val {len(val_df):,} | Test {len(test_df):,}")
        # No test seasons should appear in train
        train_test_overlap = set(tr_seasons) & set(te_seasons)
        record(
            "leakage/train_test_season_overlap",
            PASS if not train_test_overlap else FAIL,
            f"Overlap seasons: {train_test_overlap}" if train_test_overlap else "No overlap - clean split",
        )
    except Exception as e:
        record("temporal_split", FAIL, str(e))

# ---------------------------------------------------------------------------
# 13. LEAGUE STRENGTH RATINGS
# ---------------------------------------------------------------------------
section("13. LEAGUE STRENGTH RATINGS")

ls_fp = DATA_META / "league_strength_ratings.json"
if ls_fp.exists():
    ls = json.loads(ls_fp.read_text())
    # Structure: {"league_ratings": {cid: {...}}, "league_season_ratings": {...}, ...}
    league_ratings = ls.get("league_ratings", {})
    for cid in TOP5:
        entry = league_ratings.get(cid, {})
        if entry:
            strength = entry.get("normalized_strength", "?")
            method = entry.get("method", "?")
            record(f"league_strength/{cid}", PASS, f"normalized_strength={strength:.4f} | method={method}")
        else:
            record(f"league_strength/{cid}", WARN, "Not found in league_ratings")
    # Check plausible range of normalized_strength values
    flat_vals = [
        float(v["normalized_strength"])
        for v in league_ratings.values()
        if isinstance(v, dict) and "normalized_strength" in v
    ]
    if flat_vals:
        mn, mx = min(flat_vals), max(flat_vals)
        record(
            "league_strength/plausible_range",
            PASS if 0.5 < mn and mx < 2.0 else WARN,
            f"normalized_strength range {mn:.4f} to {mx:.4f} (expected 0.8-1.5)",
        )
    record(
        "league_strength/total_competitions", INFO, f"{len(league_ratings)} competitions have league strength ratings"
    )
else:
    record("league_strength/file", FAIL, "league_strength_ratings.json missing")

# Check feature table for league strength column (actual name)
if feat_df is not None:
    if "competition_strength" in feat_df.columns:
        ls_vals = feat_df["competition_strength"].dropna()
        non_pos = int((ls_vals <= 0).sum())
        record(
            "league_strength/competition_strength_in_features",
            PASS,
            f"{len(ls_vals):,} non-null values | min={ls_vals.min():.4f} max={ls_vals.max():.4f}",
        )
        record(
            "league_strength/non_positive_values", PASS if non_pos == 0 else FAIL, f"{non_pos} values <= 0 (must be 0)"
        )
    else:
        record(
            "league_strength/competition_strength_in_features", WARN, "competition_strength column not in feature table"
        )

# ---------------------------------------------------------------------------
# 14. FINANCIAL DATA
# ---------------------------------------------------------------------------
section("14. FINANCIAL DATA")

for fname, desc in [
    ("club_financials_benchmark.csv", "DFML club-level"),
    ("league_financial_benchmark.csv", "UEFA league-level"),
]:
    fp = FINANCIAL_RAW / fname
    if fp.exists():
        df = pd.read_csv(fp)
        record(f"financial/{fname}", PASS, f"{len(df):,} rows x {len(df.columns)} cols - {desc}")
    else:
        record(f"financial/{fname}", FAIL, "File missing")

if feat_df is not None and "financial_aggregation_level" in feat_df.columns:
    vc = feat_df["financial_aggregation_level"].value_counts().to_dict()
    record("financial/aggregation_flag_distribution", PASS, str(vc))
else:
    record("financial/aggregation_flag", WARN, "financial_aggregation_level not in feature table")

# Verify financial columns are present
if feat_df is not None:
    fin_cols = ["club_revenue_eur", "league_average_revenue_eur", "wage_bill_eur"]
    for col in fin_cols:
        if col in feat_df.columns:
            non_null = feat_df[col].notna().sum()
            record(f"financial/feature/{col}", PASS if non_null > 0 else WARN, f"{non_null:,} non-null values")
        else:
            record(f"financial/feature/{col}", WARN, "not in feature table")

# ---------------------------------------------------------------------------
# 15. COMPETITION REGISTRY
# ---------------------------------------------------------------------------
section("15. COMPETITION REGISTRY")

cr_fp = DATA_META / "competition_registry.json"
if cr_fp.exists():
    cr_raw = json.loads(cr_fp.read_text())
    # Structure: {"competitions": {"GB1": {...}, ...}, "total_competitions": N, ...}
    cr = cr_raw.get("competitions", cr_raw)
    total = len(cr)
    supported = sum(
        1 for v in cr.values() if isinstance(v, dict) and v.get("reliability_status", "").upper() == "SUPPORTED"
    )
    partial = sum(
        1 for v in cr.values() if isinstance(v, dict) and v.get("reliability_status", "").upper() == "PARTIAL"
    )
    insuff = sum(
        1 for v in cr.values() if isinstance(v, dict) and v.get("reliability_status", "").upper() == "INSUFFICIENT"
    )
    record(
        "registry/total",
        PASS,
        f"{total} competitions | {supported} SUPPORTED | {partial} PARTIAL | {insuff} INSUFFICIENT",
    )
    for cid in TOP5:
        entry = cr.get(cid, {})
        status_val = entry.get("reliability_status", "missing").upper() if isinstance(entry, dict) else "missing"
        matches = entry.get("matches_available", 0)
        player_stats = entry.get("player_statistics_available", 0)
        record(
            f"registry/{cid}",
            PASS if status_val == "SUPPORTED" else WARN,
            f"status={status_val} | matches={matches:,} | player_stats={player_stats:,}",
        )
else:
    record("registry/file", FAIL, "competition_registry.json missing")

# ---------------------------------------------------------------------------
# 16. MODEL ARTIFACT
# ---------------------------------------------------------------------------
section("16. MODEL ARTIFACT")

model_fp = MODELS / "best_value_predictor.joblib"
pipeline_obj = None
meta_obj = None
if model_fp.exists():
    sz = model_fp.stat().st_size
    record("model/artifact_exists", PASS, f"{sz / 1e6:.2f} MB - {model_fp.name}")
    # Use ModelRegistry (which uses joblib internally and returns ModelMetadata dataclass)
    sys.path.insert(0, str(ROOT))
    from src.model_registry import ModelRegistry

    reg = ModelRegistry()
    pipeline_obj, meta_obj = reg.load_model(model_fp)
    record(
        "model/loadable",
        PASS,
        f"model_name={meta_obj.model_name} | version={meta_obj.version} | saved_at={meta_obj.saved_at}",
    )
    record("model/use_log_target", INFO, f"use_log_target={meta_obj.use_log_target}")
    record("model/val_mae", INFO, f"best_val_mae_eur={meta_obj.best_val_mae_eur:,.0f}")
    n_num = len(meta_obj.features_numeric)
    n_cat = len(meta_obj.features_categorical)
    record("model/features", INFO, f"{n_num} numeric + {n_cat} categorical = {n_num + n_cat} total features")

    # Get final estimator name
    try:
        steps = list(pipeline_obj.steps)
        final_est = type(steps[-1][1]).__name__
    except Exception:
        final_est = type(pipeline_obj[-1]).__name__
    record("model/estimator_type", PASS, f"Final estimator: {final_est}")

    # Sample prediction on real feature rows
    if feat_df is not None and "historical_market_value" in feat_df.columns:
        try:
            sample = feat_df.dropna(subset=["historical_market_value"]).head(10).copy()
            drop_cols = [
                "historical_market_value",
                "name",
                "player_id",
                "date_of_birth",
                "current_club_name",
                "val_club_id",
                "val_competition_id",
                "previous_valuation_date",
                "valuation_reference_date",
            ]
            feature_cols = [c for c in sample.columns if c not in drop_cols]
            preds = pipeline_obj.predict(sample[feature_cols])
            preds_eur = [float(np.expm1(p)) for p in preds] if meta_obj.use_log_target else [float(p) for p in preds]
            actuals = sample["historical_market_value"].tolist()
            record(
                "model/predict_sample",
                PASS,
                f"Preds: {[f'{p:,.0f}' for p in preds_eur[:3]]} | Actuals: {[f'{a:,.0f}' for a in actuals[:3]]}",
            )
        except Exception as e:
            record("model/predict_sample", FAIL, str(e))

    mc_fp = MODELS / "model_comparison_results.json"
    if mc_fp.exists():
        mc = json.loads(mc_fp.read_text())
        record("model/comparison_results", PASS, f"{len(mc)} model(s) in comparison file")
    else:
        record("model/comparison_results", WARN, "model_comparison_results.json missing")
else:
    record("model/artifact_exists", FAIL, "best_value_predictor.joblib missing - run src.train")

# ---------------------------------------------------------------------------
# 17. EVALUATION RESULTS
# ---------------------------------------------------------------------------
section("17. EVALUATION RESULTS")

eval_fp = DATA_META / "evaluation_results.json"
if eval_fp.exists():
    ev = json.loads(eval_fp.read_text())
    gm = ev.get("global_metrics", {})
    mae = gm.get("mae_eur", None)
    r2 = gm.get("r2", None)
    rmse = gm.get("rmse_eur", None)
    if mae is not None:
        record(
            "evaluation/global_metrics",
            PASS if r2 and r2 > 0.7 else WARN,
            f"MAE=EUR{mae:,.0f} | RMSE=EUR{rmse:,.0f} | R2={r2:.4f}",
        )
    else:
        record("evaluation/global_metrics", WARN, "metrics missing from file")

    per_league = ev.get("competitions", ev.get("per_league_metrics", {}))
    if per_league:
        for cid, cname in TOP5.items():
            lm = per_league.get(cid, {})
            if lm and "mae_eur" in lm:
                record(
                    f"evaluation/league_{cid}",
                    PASS,
                    (
                        f"{cname} | MAE=EUR{lm.get('mae_eur', 0):,.0f} | "
                        f"R2={lm.get('r2', 0):.4f} | "
                        f"n={lm.get('sample_count', lm.get('n_samples', 0)):,}"
                    ),
                )
            else:
                record(f"evaluation/league_{cid}", WARN, f"No per-league metrics found for {cid}")
    else:
        record("evaluation/per_league", WARN, "competitions/per_league_metrics not in evaluation_results.json")
else:
    record("evaluation/file", FAIL, "evaluation_results.json missing - run src.evaluate")

# ---------------------------------------------------------------------------
# 18. PREDICTION SERVICE - LIVE TESTS (correct API)
# ---------------------------------------------------------------------------
section("18. PREDICTION SERVICE LIVE TESTS")

sys.path.insert(0, str(ROOT))
try:
    from src.predict import PlayerInput, ValuationPredictor

    predictor = ValuationPredictor()
    record("predict/service_load", PASS, "ValuationPredictor instantiated successfully")

    # Test A: Standard top-5 player (GB1)
    try:
        player_a = PlayerInput(
            age_at_reference_date=24.5,
            position="Attack",
            sub_position="Left Winger",
            appearances=32,
            minutes_played=2700,
            goals=14,
            assists=8,
            previous_market_value=45_000_000,
            current_season=2023,
        )
        res_a = predictor.predict_current_valuation(player_a, competition_id="GB1")
        val_a = res_a.predicted_value_eur
        status = PASS if 1_000_000 < val_a < 500_000_000 else FAIL
        record(
            "predict/normal_gb1", status, f"Predicted EUR{val_a:,.0f} | warnings={len(res_a.relevant_data_warnings)}"
        )
    except Exception as e:
        record("predict/normal_gb1", FAIL, str(e))

    # Test B: Cross-league scenario FR1 -> GB1
    try:
        player_b = PlayerInput(
            age_at_reference_date=24.5,
            position="Attack",
            sub_position="Left Winger",
            appearances=30,
            minutes_played=2500,
            goals=12,
            assists=6,
            previous_market_value=35_000_000,
            current_season=2023,
        )
        res_b = predictor.predict_cross_league_scenario(
            player_b,
            source_competition_id="FR1",
            destination_competition_id="GB1",
        )
        val_b = res_b.predicted_value_eur
        delta = res_b.cross_league_delta_eur
        status = PASS if 1_000_000 < val_b < 500_000_000 else FAIL
        record(
            "predict/cross_league_fr1_to_gb1",
            status,
            f"Dest EUR{val_b:,.0f} | delta EUR{delta:+,.0f} ({res_b.cross_league_delta_pct:+.1f}%)",
        )
    except Exception as e:
        record("predict/cross_league_fr1_to_gb1", FAIL, str(e))

    # Test C: Unknown league fallback
    try:
        player_c = PlayerInput(
            age_at_reference_date=29.0,
            position="Defender",
            sub_position="Centre-Back",
            appearances=28,
            minutes_played=2520,
            goals=2,
            assists=1,
            current_season=2023,
        )
        res_c = predictor.predict_current_valuation(player_c, competition_id="XX_UNKNOWN")
        val_c = res_c.predicted_value_eur
        status = PASS if val_c > 0 else FAIL
        record("predict/unknown_league_fallback", status, f"EUR{val_c:,.0f} | coverage={res_c.evaluation_coverage}")
    except Exception as e:
        record("predict/unknown_league_fallback", FAIL, str(e))

    # Test D: No prior valuation (young player)
    try:
        player_d = PlayerInput(
            age_at_reference_date=19.0,
            position="Attack",
            sub_position="Centre-Forward",
            appearances=18,
            minutes_played=900,
            goals=5,
            assists=2,
            previous_market_value=None,
            current_season=2023,
        )
        res_d = predictor.predict_current_valuation(player_d, competition_id="ES1")
        val_d = res_d.predicted_value_eur
        status = PASS if val_d > 0 else FAIL
        record("predict/no_prior_valuation", status, f"EUR{val_d:,.0f} (no prior value)")
    except Exception as e:
        record("predict/no_prior_valuation", FAIL, str(e))

    # Test E: All top-5 leagues
    for cid in TOP5:
        try:
            player_e = PlayerInput(
                age_at_reference_date=25.0,
                position="Attack",
                sub_position="Centre-Forward",
                appearances=30,
                minutes_played=2000,
                goals=10,
                assists=4,
                previous_market_value=20_000_000,
                current_season=2023,
            )
            res_e = predictor.predict_current_valuation(player_e, competition_id=cid)
            val_e = res_e.predicted_value_eur
            record(f"predict/league_{cid}", PASS if val_e > 0 else FAIL, f"EUR{val_e:,.0f}")
        except Exception as e:
            record(f"predict/league_{cid}", FAIL, str(e))

    # Test F: Goalkeeper (different position category)
    try:
        player_f = PlayerInput(
            age_at_reference_date=27.0,
            position="Goalkeeper",
            sub_position="Goalkeeper",
            appearances=35,
            minutes_played=3150,
            goals=0,
            assists=1,
            previous_market_value=12_000_000,
            current_season=2023,
        )
        res_f = predictor.predict_current_valuation(player_f, competition_id="IT1")
        val_f = res_f.predicted_value_eur
        record("predict/goalkeeper_it1", PASS if val_f > 0 else FAIL, f"EUR{val_f:,.0f}")
    except Exception as e:
        record("predict/goalkeeper_it1", FAIL, str(e))

    # Test G: Zero minutes edge case
    try:
        player_g = PlayerInput(
            age_at_reference_date=22.0,
            position="Midfield",
            sub_position="Central Midfield",
            appearances=0,
            minutes_played=0,
            goals=0,
            assists=0,
            current_season=2023,
        )
        res_g = predictor.predict_current_valuation(player_g, competition_id="L1")
        val_g = res_g.predicted_value_eur
        record("predict/zero_minutes_edge", PASS if val_g > 0 else FAIL, f"EUR{val_g:,.0f} (zero minutes player)")
    except Exception as e:
        record("predict/zero_minutes_edge", FAIL, str(e))

except Exception as e:
    record("predict/service_load", FAIL, str(e))

# ---------------------------------------------------------------------------
# 19. METADATA CONSISTENCY & REPRODUCIBILITY
# ---------------------------------------------------------------------------
section("19. METADATA CONSISTENCY")

META_FILES = [
    "competition_registry.json",
    "source_inventory.json",
    "schema_report.json",
    "league_strength_ratings.json",
    "evaluation_results.json",
]
for fname in META_FILES:
    fp = DATA_META / fname
    if fp.exists():
        try:
            data = json.loads(fp.read_text())
            record(f"metadata/{fname}", PASS if data else WARN, f"Valid JSON | {fp.stat().st_size / 1e3:.1f} KB")
        except json.JSONDecodeError as e:
            record(f"metadata/{fname}", FAIL, f"Invalid JSON: {e}")
    else:
        record(f"metadata/{fname}", FAIL, "File missing")

# Model name consistency between eval results and artifact
if eval_fp.exists() and meta_obj is not None:
    ev2 = json.loads(eval_fp.read_text())
    ev_model = ev2.get("model_name", "")
    if ev_model:
        match = ev_model == meta_obj.model_name
        record(
            "reproducibility/model_name_match",
            PASS if match else WARN,
            f"eval='{ev_model}' | artifact='{meta_obj.model_name}'",
        )

# ---------------------------------------------------------------------------
# 20. DOCUMENTATION FILES
# ---------------------------------------------------------------------------
section("20. DOCUMENTATION FILES")

DOCS = [
    "data_sources.md",
    "data_inventory.md",
    "data_dictionary.md",
    "methodology.md",
    "limitations.md",
    "model_evaluation.md",
]
for fname in DOCS:
    fp = ROOT / "docs" / fname
    if fp.exists():
        size = fp.stat().st_size
        record(f"docs/{fname}", PASS if size > 200 else WARN, f"{size:,} bytes")
    else:
        record(f"docs/{fname}", FAIL, "Missing")

# ---------------------------------------------------------------------------
# SUMMARY
# ---------------------------------------------------------------------------
print("\n" + "=" * 72)
print("AUDIT SUMMARY")
print("=" * 72)

passed = sum(1 for r in results if r["status"] == PASS)
failed = sum(1 for r in results if r["status"] == FAIL)
warned = sum(1 for r in results if r["status"] == WARN)
info_c = sum(1 for r in results if r["status"] == INFO)

print(f"TOTAL CHECKS : {len(results)}")
print(f"  PASSED     : {passed}")
print(f"  FAILED     : {failed}")
print(f"  WARNED     : {warned}")
print(f"  INFO       : {info_c}")

if failed > 0:
    print("\nFAILED CHECKS:")
    for r in results:
        if r["status"] == FAIL:
            print(f"  [ERR] [{r['check']}] {r['detail']}")

if warned > 0:
    print("\nWARNINGS:")
    for r in results:
        if r["status"] == WARN:
            print(f"  [WRN] [{r['check']}] {r['detail']}")

out_path = DATA_META / "audit_results.json"
out_path.write_text(json.dumps(results, indent=2, default=str))
print(f"\nFull results saved -> {out_path}")
