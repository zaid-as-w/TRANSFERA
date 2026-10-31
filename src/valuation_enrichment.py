"""Historical market valuation enrichment service.

Maintains historical valuation points from verified sources (Transfermarkt, public fees).
Strictly prohibits generating synthetic, fake, or fabricated market values.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)

VALUATIONS_PARQUET_PATH = Path("data/global/player_valuations.parquet")
CLEAN_VALUATIONS_PATH = Path("data/interim/clean_player_valuations.parquet")


class ValuationEnrichmentService:
    """Manages verified historical market valuation data points."""

    def __init__(self, output_path: Path | str = VALUATIONS_PARQUET_PATH):
        self.output_path = Path(output_path)
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

    def build_valuations_table(self) -> pd.DataFrame:
        """Build player_valuations.parquet from clean Transfermarkt valuation records."""
        logger.info("Building historical valuations table from clean_player_valuations...")
        if not CLEAN_VALUATIONS_PATH.exists():
            logger.warning("Clean valuations file missing: %s", CLEAN_VALUATIONS_PATH)
            return pd.DataFrame()

        clean_val = pd.read_parquet(CLEAN_VALUATIONS_PATH)
        records: list[dict[str, Any]] = []

        for _, r in clean_val.iterrows():
            pid = int(r["player_id"])
            val_eur = float(r["market_value_in_eur"])
            if val_eur <= 0:
                continue

            records.append(
                {
                    "global_player_id": f"tm_{pid}",
                    "valuation_date": str(r["date"]).split()[0],
                    "market_value_eur": val_eur,
                    "currency": "EUR",
                    "source": "TRANSFERMARKT_VERIFIED",
                    "is_verified": True,
                }
            )

        df = pd.DataFrame(records)
        df.to_parquet(self.output_path, index=False)
        logger.info("Saved %d verified valuations to %s", len(df), self.output_path)
        return df

    def get_valuation_history(self, global_player_id: str) -> list[dict[str, Any]]:
        """Retrieve verified historical valuations for a player."""
        if not self.output_path.exists():
            return []
        df = pd.read_parquet(self.output_path)
        sub = df[df["global_player_id"] == global_player_id].sort_values("valuation_date")
        if sub.empty:
            return []
        return sub.to_dict(orient="records")
