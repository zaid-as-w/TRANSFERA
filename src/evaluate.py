"""Comprehensive Model Evaluation and Generalization Engine.

Evaluates trained model on held-out out-of-time test data (seasons 2023-2024):
1. Global performance metrics
2. Competition-specific evaluation (EPL, La Liga, Serie A, Bundesliga, Ligue 1, and others)
3. Breakdown by player position, age group, and market value band
4. Historical cross-league mover analysis
5. Missing financial data and competition strength sensitivity
6. Unseen-player generalization test
Persists results to data/metadata/evaluation_results.json and docs/model_evaluation.md.
"""

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, median_absolute_error, r2_score

from config.settings import (
    DOCS_DIR,
    METADATA_DIR,
    MODELS_DIR,
    PROCESSED_DATA_DIR,
    TARGET_COLUMN,
)
from src.competition_registry import CompetitionRegistry
from src.temporal_splits import DataSplitter

logger = logging.getLogger(__name__)


def compute_metrics(y_true: np.ndarray, y_pred: np.ndarray, baseline_mae: float | None = None) -> dict[str, Any]:
    """Compute standard metrics in true euros."""
    y_pred_clipped = np.clip(y_pred, a_min=10000.0, a_max=None)
    mae = float(mean_absolute_error(y_true, y_pred_clipped))
    rmse = float(np.sqrt(mean_squared_error(y_true, y_pred_clipped)))
    med_ae = float(median_absolute_error(y_true, y_pred_clipped))
    r2 = float(r2_score(y_true, y_pred_clipped))

    res: dict[str, Any] = {
        "sample_count": len(y_true),
        "mae_eur": round(mae, 2),
        "rmse_eur": round(rmse, 2),
        "median_ae_eur": round(med_ae, 2),
        "r2": round(r2, 4),
    }
    if baseline_mae and baseline_mae > 0:
        res["mae_relative_to_baseline_pct"] = round((mae / baseline_mae) * 100.0, 2)
    return res


class ModelEvaluator:
    """Evaluates fitted models across competitions, segments, movers, and sensitivity tests."""

    def __init__(
        self,
        model_artifact_path: Path | None = None,
        data_path: Path | None = None,
        docs_dir: Path = DOCS_DIR,
        metadata_dir: Path = METADATA_DIR,
    ) -> None:
        self.model_path = model_artifact_path or (MODELS_DIR / "best_value_predictor.joblib")
        self.data_path = data_path or (PROCESSED_DATA_DIR / "player_season_features.parquet")
        self.docs_dir = docs_dir
        self.metadata_dir = metadata_dir
        self.registry = CompetitionRegistry()

        if not self.model_path.exists():
            raise FileNotFoundError(f"Model artifact not found: {self.model_path}")
        artifact = joblib.load(self.model_path)
        self.pipeline = artifact["pipeline"]
        self.metadata = artifact["metadata"]
        self.use_log_target = self.metadata.get("use_log_target", True)

    def evaluate_all(self) -> dict[str, Any]:
        """Run complete out-of-time evaluation suite."""
        logger.info("Loading test data from %s...", self.data_path)
        df = pd.read_parquet(self.data_path)

        splitter = DataSplitter()
        train_df, _val_df, test_df, meta = splitter.chronological_split(df)
        logger.info("Out-of-time test set: %d records (seasons %s)", len(test_df), meta.test_seasons)

        # Baseline median predictor for benchmark
        train_median_val = float(train_df[TARGET_COLUMN].median())
        dummy_test_preds = np.full(len(test_df), fill_value=train_median_val)
        baseline_test_metrics = compute_metrics(test_df[TARGET_COLUMN].values, dummy_test_preds)
        baseline_mae = baseline_test_metrics["mae_eur"]
        logger.info("Test Dummy Baseline MAE: €%s", f"{baseline_mae:,.2f}")

        # Predict test set
        raw_preds = self.pipeline.predict(test_df)
        test_preds = np.expm1(raw_preds) if self.use_log_target else raw_preds
        test_df["predicted_market_value"] = test_preds
        test_df["abs_error"] = np.abs(test_df[TARGET_COLUMN] - test_preds)

        # 1. Global Metrics
        global_metrics = compute_metrics(test_df[TARGET_COLUMN].values, test_preds, baseline_mae)
        logger.info(
            "Global Test Metrics: MAE=€%s, RMSE=€%s, R2=%s",
            f"{global_metrics['mae_eur']:,.2f}",
            f"{global_metrics['rmse_eur']:,.2f}",
            global_metrics["r2"],
        )

        # 2. Per-Competition Evaluation
        comp_metrics: dict[str, Any] = {}
        target_comps = ["GB1", "ES1", "IT1", "L1", "FR1", "NL1", "PO1", "BE1", "TR1", "GR1", "RU1"]
        for cid in target_comps:
            sub = test_df[test_df["competition_id"] == cid]
            if len(sub) >= 30:
                c_baseline = float(np.mean(np.abs(sub[TARGET_COLUMN].values - train_median_val)))
                comp_metrics[cid] = compute_metrics(
                    sub[TARGET_COLUMN].values, sub["predicted_market_value"].values, c_baseline
                )
                comp_rec = self.registry.get_competition(cid)
                comp_metrics[cid]["competition_name"] = comp_rec.competition_name if comp_rec else cid
                comp_metrics[cid]["country"] = comp_rec.country if comp_rec else "Unknown"
            else:
                comp_metrics[cid] = {"status": "INSUFFICIENT_EVIDENCE", "sample_count": len(sub)}

        # 3. By Position
        position_metrics: dict[str, Any] = {}
        for pos, p_df in test_df.groupby("position"):
            if len(p_df) >= 20:
                position_metrics[str(pos)] = compute_metrics(
                    p_df[TARGET_COLUMN].values, p_df["predicted_market_value"].values, baseline_mae
                )

        # 4. By Age Group
        age_bins = [0, 21, 25, 29, 33, 100]
        age_labels = ["U21 (<21)", "21-24", "25-28", "29-32", "33+"]
        test_df["age_group"] = pd.cut(test_df["age_at_reference_date"], bins=age_bins, labels=age_labels, right=False)
        age_metrics: dict[str, Any] = {}
        for ag, ag_df in test_df.groupby("age_group", observed=False):
            if len(ag_df) >= 20:
                age_metrics[str(ag)] = compute_metrics(
                    ag_df[TARGET_COLUMN].values, ag_df["predicted_market_value"].values, baseline_mae
                )

        # 5. By Market Value Band
        val_bins = [0, 1_000_000, 5_000_000, 15_000_000, 40_000_000, 1_000_000_000]
        val_labels = ["< €1M", "€1M - €5M", "€5M - €15M", "€15M - €40M", "€40M+"]
        test_df["value_band"] = pd.cut(test_df[TARGET_COLUMN], bins=val_bins, labels=val_labels, right=False)
        band_metrics: dict[str, Any] = {}
        for vb, vb_df in test_df.groupby("value_band", observed=False):
            if len(vb_df) >= 20:
                band_metrics[str(vb)] = compute_metrics(
                    vb_df[TARGET_COLUMN].values, vb_df["predicted_market_value"].values, baseline_mae
                )

        # 6. Cross-League Movers Analysis
        # Identify players whose competition in season 2023 differed from prior season in train_df
        prior_comp_map = (
            train_df.sort_values(["player_id", "season"]).groupby("player_id")["competition_id"].last().to_dict()
        )
        test_df["prior_competition_id"] = test_df["player_id"].map(prior_comp_map)
        movers_df = test_df[
            test_df["prior_competition_id"].notna() & (test_df["prior_competition_id"] != test_df["competition_id"])
        ].copy()
        non_movers_df = test_df[
            test_df["prior_competition_id"].notna() & (test_df["prior_competition_id"] == test_df["competition_id"])
        ].copy()

        movers_metrics = (
            compute_metrics(movers_df[TARGET_COLUMN].values, movers_df["predicted_market_value"].values, baseline_mae)
            if len(movers_df) >= 10
            else {"sample_count": len(movers_df)}
        )
        non_movers_metrics = (
            compute_metrics(
                non_movers_df[TARGET_COLUMN].values, non_movers_df["predicted_market_value"].values, baseline_mae
            )
            if len(non_movers_df) >= 10
            else {"sample_count": len(non_movers_df)}
        )

        # 7. Financial Sensitivity Analysis
        fin_observed = test_df[test_df["has_club_financials"]]
        fin_missing = test_df[~test_df["has_club_financials"]]
        financial_sensitivity = {
            "with_club_financials": compute_metrics(
                fin_observed[TARGET_COLUMN].values, fin_observed["predicted_market_value"].values
            )
            if len(fin_observed) > 0
            else {},
            "without_club_financials": compute_metrics(
                fin_missing[TARGET_COLUMN].values, fin_missing["predicted_market_value"].values
            )
            if len(fin_missing) > 0
            else {},
        }

        # 8. Unseen-Player Generalization Test
        _train_unseen, test_unseen = splitter.unseen_player_split(df, test_ratio=0.2, random_state=42)
        unseen_raw_preds = self.pipeline.predict(test_unseen)
        unseen_preds = np.expm1(unseen_raw_preds) if self.use_log_target else unseen_raw_preds
        unseen_metrics = compute_metrics(test_unseen[TARGET_COLUMN].values, unseen_preds)

        evaluation_results: dict[str, Any] = {
            "evaluated_at": datetime.now(UTC).isoformat(),
            "model_version": self.metadata.get("version", "1.0.0"),
            "model_name": self.metadata.get("model_name", "Model_B_HistGradientBoosting"),
            "test_date_range": {"min": meta.test_date_min, "max": meta.test_date_max},
            "test_sample_count": len(test_df),
            "baseline_metrics": baseline_test_metrics,
            "global_metrics": global_metrics,
            "competitions": comp_metrics,
            "positions": position_metrics,
            "age_groups": age_metrics,
            "value_bands": band_metrics,
            "cross_league_movers": {
                "movers": movers_metrics,
                "non_movers": non_movers_metrics,
            },
            "financial_sensitivity": financial_sensitivity,
            "unseen_player_generalization": unseen_metrics,
        }

        self.save_reports(evaluation_results)
        return evaluation_results

    def save_reports(self, res: dict[str, Any]) -> None:
        """Save JSON report and generate comprehensive markdown model_evaluation.md."""
        self.metadata_dir.mkdir(parents=True, exist_ok=True)
        self.docs_dir.mkdir(parents=True, exist_ok=True)

        json_path = self.metadata_dir / "evaluation_results.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(res, f, indent=2)
        logger.info("Saved evaluation JSON report to %s", json_path)

        md_path = self.docs_dir / "model_evaluation.md"
        self._write_markdown_report(res, md_path)
        logger.info("Saved evaluation Markdown report to %s", md_path)

    def _write_markdown_report(self, res: dict[str, Any], out_path: Path) -> None:
        gm = res["global_metrics"]
        bm = res["baseline_metrics"]
        lines = [
            "# Model Evaluation and Generalization Report",
            "",
            f"**Model Name:** `{res.get('model_name')}`  ",
            f"**Model Version:** `{res.get('model_version')}`  ",
            f"**Evaluation Date:** {res.get('evaluated_at')}  ",
            f"**Evaluation Window:** {res.get('test_date_range', {}).get('min')} to {res.get('test_date_range', {}).get('max')} (Seasons 2023-2024)  ",
            f"**Held-out Test Samples:** {res.get('test_sample_count'):,}  ",
            "",
            "## 1. Global Performance Overview",
            "",
            "| Metric | Model Estimate | Dummy Baseline (Median) | Improvement |",
            "| :--- | :--- | :--- | :--- |",
            f"| **MAE (€)** | **€{gm.get('mae_eur', 0):,.2f}** | €{bm.get('mae_eur', 0):,.2f} | **{(1.0 - gm.get('mae_eur', 0) / bm.get('mae_eur', 1)) * 100:.1f}% reduction** |",
            f"| **RMSE (€)** | **€{gm.get('rmse_eur', 0):,.2f}** | €{bm.get('rmse_eur', 0):,.2f} | **{(1.0 - gm.get('rmse_eur', 0) / bm.get('rmse_eur', 1)) * 100:.1f}% reduction** |",
            f"| **Median AE (€)** | **€{gm.get('median_ae_eur', 0):,.2f}** | €{bm.get('median_ae_eur', 0):,.2f} | **{(1.0 - gm.get('median_ae_eur', 0) / bm.get('median_ae_eur', 1)) * 100:.1f}% reduction** |",
            f"| **R² Score** | **{gm.get('r2', 0):.4f}** | {bm.get('r2', 0):.4f} | **+{(gm.get('r2', 0) - bm.get('r2', 0)):.4f}** |",
            "",
            "## 2. Competition-Specific Evaluation",
            "",
            "| Competition | Name | Country | Samples | MAE (€) | RMSE (€) | Median AE (€) | R² Score | MAE % of Baseline |",
            "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
        ]

        for cid, cm in res.get("competitions", {}).items():
            if cm.get("status") == "INSUFFICIENT_EVIDENCE":
                lines.append(
                    f"| `{cid}` | N/A | N/A | {cm.get('sample_count')} | *INSUFFICIENT_EVIDENCE* | N/A | N/A | N/A | N/A |"
                )
            else:
                lines.append(
                    f"| `{cid}` | {cm.get('competition_name')} | {cm.get('country')} | {cm.get('sample_count'):,} | €{cm.get('mae_eur'):,.2f} | €{cm.get('rmse_eur'):,.2f} | €{cm.get('median_ae_eur'):,.2f} | {cm.get('r2'):.4f} | {cm.get('mae_relative_to_baseline_pct')}% |"
                )

        lines.extend(
            [
                "",
                "## 3. Position-Specific Error Distribution",
                "",
                "| Position | Sample Count | MAE (€) | RMSE (€) | Median AE (€) | R² Score |",
                "| :--- | :--- | :--- | :--- | :--- | :--- |",
            ]
        )
        for pos, pm in res.get("positions", {}).items():
            lines.append(
                f"| **{pos}** | {pm.get('sample_count'):,} | €{pm.get('mae_eur'):,.2f} | €{pm.get('rmse_eur'):,.2f} | €{pm.get('median_ae_eur'):,.2f} | {pm.get('r2'):.4f} |"
            )

        lines.extend(
            [
                "",
                "## 4. Age Group Error Distribution",
                "",
                "| Age Group | Sample Count | MAE (€) | RMSE (€) | Median AE (€) | R² Score |",
                "| :--- | :--- | :--- | :--- | :--- | :--- |",
            ]
        )
        for ag, am in res.get("age_groups", {}).items():
            lines.append(
                f"| **{ag}** | {am.get('sample_count'):,} | €{am.get('mae_eur'):,.2f} | €{am.get('rmse_eur'):,.2f} | €{am.get('median_ae_eur'):,.2f} | {am.get('r2'):.4f} |"
            )

        lines.extend(
            [
                "",
                "## 5. Market Value Band Error Distribution",
                "",
                "| Value Band | Sample Count | MAE (€) | RMSE (€) | Median AE (€) | R² Score |",
                "| :--- | :--- | :--- | :--- | :--- | :--- |",
            ]
        )
        for vb, vm in res.get("value_bands", {}).items():
            lines.append(
                f"| **{vb}** | {vm.get('sample_count'):,} | €{vm.get('mae_eur'):,.2f} | €{vm.get('rmse_eur'):,.2f} | €{vm.get('median_ae_eur'):,.2f} | {vm.get('r2'):.4f} |"
            )

        # Cross league movers
        movers = res.get("cross_league_movers", {}).get("movers", {})
        non_movers = res.get("cross_league_movers", {}).get("non_movers", {})
        lines.extend(
            [
                "",
                "## 6. Cross-League Mover Generalization",
                "",
                "| Cohort | Sample Count | MAE (€) | RMSE (€) | Median AE (€) | R² Score |",
                "| :--- | :--- | :--- | :--- | :--- | :--- |",
                f"| **Cross-League Transfers** | {movers.get('sample_count', 0):,} | €{movers.get('mae_eur', 0):,.2f} | €{movers.get('rmse_eur', 0):,.2f} | €{movers.get('median_ae_eur', 0):,.2f} | {movers.get('r2', 0):.4f} |",
                f"| **League Retained** | {non_movers.get('sample_count', 0):,} | €{non_movers.get('mae_eur', 0):,.2f} | €{non_movers.get('rmse_eur', 0):,.2f} | €{non_movers.get('median_ae_eur', 0):,.2f} | {non_movers.get('r2', 0):.4f} |",
                "",
                "## 7. Sensitivity and Generalization Tests",
                "",
                "### A. Missing Financial Data Sensitivity",
                f"- **Clubs with Published Financial Accounts (DFML/UEFA):** MAE = €{res.get('financial_sensitivity', {}).get('with_club_financials', {}).get('mae_eur', 0):,.2f}, R² = {res.get('financial_sensitivity', {}).get('with_club_financials', {}).get('r2', 0):.4f} ({res.get('financial_sensitivity', {}).get('with_club_financials', {}).get('sample_count', 0):,} samples)",
                f"- **Clubs with League Fallback Financials:** MAE = €{res.get('financial_sensitivity', {}).get('without_club_financials', {}).get('mae_eur', 0):,.2f}, R² = {res.get('financial_sensitivity', {}).get('without_club_financials', {}).get('r2', 0):.4f} ({res.get('financial_sensitivity', {}).get('without_club_financials', {}).get('sample_count', 0):,} samples)",
                "",
                "### B. Unseen-Player Generalization",
                f"- **Out-of-sample players:** MAE = €{res.get('unseen_player_generalization', {}).get('mae_eur', 0):,.2f}, RMSE = €{res.get('unseen_player_generalization', {}).get('rmse_eur', 0):,.2f}, R² = {res.get('unseen_player_generalization', {}).get('r2', 0):.4f} ({res.get('unseen_player_generalization', {}).get('sample_count', 0):,} samples)",
                "",
            ]
        )

        with open(out_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    evaluator = ModelEvaluator()
    evaluator.evaluate_all()
