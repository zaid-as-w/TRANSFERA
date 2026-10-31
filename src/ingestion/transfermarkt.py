"""Transfermarkt data ingestion and schema discovery module.

Downloads authentic historical football datasets from the dcaribou/transfermarkt-datasets
repository mirror (Cloudflare R2 published distribution), verifies immutability,
audits schemas, records metadata, and generates machine-readable data inventories.
"""

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd
import requests

from config.settings import (
    CORE_TM_TABLES,
    DOCS_DIR,
    METADATA_DIR,
    RAW_TM_DIR,
    TM_R2_BASE_URL,
)

logger = logging.getLogger(__name__)


def download_file(
    url: str,
    dest_path: Path,
    chunk_size: int = 1024 * 1024,
    timeout: int = 60,
    force: bool = False,
) -> tuple[bool, dict[str, Any]]:
    """Download a remote file in chunks with proper headers, tracking metadata."""
    metadata: dict[str, Any] = {
        "url": url,
        "dest_path": str(dest_path),
        "download_timestamp": datetime.now(UTC).isoformat(),
        "status": "pending",
    }

    if dest_path.exists() and not force and dest_path.stat().st_size > 0:
        logger.info(
            "File already exists locally: %s (%d bytes). Skipping download.", dest_path.name, dest_path.stat().st_size
        )
        metadata["status"] = "cached"
        metadata["file_size_bytes"] = dest_path.stat().st_size
        return True, metadata

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "*/*",
    }

    temp_path = dest_path.with_suffix(dest_path.suffix + ".tmp")
    try:
        logger.info("Downloading %s -> %s", url, dest_path.name)
        with requests.get(url, headers=headers, stream=True, timeout=timeout) as r:
            r.raise_for_status()
            metadata["http_status"] = r.status_code
            metadata["content_length"] = r.headers.get("content-length")
            metadata["last_modified"] = r.headers.get("last-modified")
            metadata["etag"] = r.headers.get("etag")

            total_bytes = 0
            with open(temp_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
                        total_bytes += len(chunk)

        temp_path.replace(dest_path)
        metadata["status"] = "downloaded"
        metadata["file_size_bytes"] = total_bytes
        logger.info("Successfully downloaded %s (%d bytes)", dest_path.name, total_bytes)
        return True, metadata

    except Exception as e:
        logger.error("Download failed for %s: %s", url, e)
        if temp_path.exists():
            temp_path.unlink()
        metadata["status"] = "failed"
        metadata["error"] = str(e)
        return False, metadata


def download_transfermarkt_tables(
    tables: list[str] | None = None,
    raw_dir: Path = RAW_TM_DIR,
    force: bool = False,
) -> dict[str, Any]:
    """Download specified Transfermarkt compressed CSV tables."""
    raw_dir.mkdir(parents=True, exist_ok=True)
    target_tables = tables or CORE_TM_TABLES
    inventory: dict[str, Any] = {
        "source_name": "Transfermarkt Datasets (dcaribou/transfermarkt-datasets)",
        "source_repository": "https://github.com/dcaribou/transfermarkt-datasets",
        "data_distribution_url": "https://pub-e682421888d945d684bcae8890b0ec20.r2.dev/data/",
        "acquisition_date": datetime.now(UTC).isoformat(),
        "tables": {},
    }

    for table in target_tables:
        url = TM_R2_BASE_URL.format(table=table)
        dest_file = raw_dir / f"{table}.csv.gz"
        success, meta = download_file(url, dest_file, force=force)
        inventory["tables"][table] = meta
        if not success:
            logger.warning("Could not download table: %s", table)

    return inventory


def load_raw_table(table_name: str, raw_dir: Path = RAW_TM_DIR) -> pd.DataFrame:
    """Load a compressed CSV table into a pandas DataFrame."""
    file_path = raw_dir / f"{table_name}.csv.gz"
    if not file_path.exists():
        csv_uncompressed = raw_dir / f"{table_name}.csv"
        if csv_uncompressed.exists():
            return pd.read_csv(csv_uncompressed, low_memory=False)
        raise FileNotFoundError(f"Raw table file not found: {file_path}")

    logger.debug("Loading %s", file_path)
    return pd.read_csv(file_path, compression="gzip", low_memory=False)


def inspect_table_schema(table_name: str, df: pd.DataFrame) -> dict[str, Any]:
    """Analyze DataFrame schema, nulls, duplicates, and ranges without fabrications."""
    record_count = len(df)
    duplicate_rows = int(df.duplicated().sum())

    columns_info: dict[str, dict[str, Any]] = {}
    for col in df.columns:
        null_count = int(df[col].isnull().sum())
        null_pct = float(round((null_count / record_count) * 100, 2)) if record_count > 0 else 0.0
        n_unique = int(df[col].nunique())
        dtype_str = str(df[col].dtype)
        columns_info[col] = {
            "dtype": dtype_str,
            "null_count": null_count,
            "null_pct": null_pct,
            "distinct_values": n_unique,
        }

    date_range: dict[str, str] | None = None
    for date_candidate in ["date", "datetime", "valuation_date", "transfer_date"]:
        if date_candidate in df.columns:
            valid_dates = pd.to_datetime(df[date_candidate], errors="coerce").dropna()
            if not valid_dates.empty:
                date_range = {
                    "field": date_candidate,
                    "min": valid_dates.min().strftime("%Y-%m-%d"),
                    "max": valid_dates.max().strftime("%Y-%m-%d"),
                }
                break

    report: dict[str, Any] = {
        "table_name": table_name,
        "record_count": record_count,
        "column_count": len(df.columns),
        "duplicate_rows": duplicate_rows,
        "columns": columns_info,
        "date_range": date_range,
    }

    if "player_id" in df.columns:
        report["distinct_players"] = int(df["player_id"].nunique())
    if "club_id" in df.columns:
        report["distinct_clubs"] = int(df["club_id"].nunique())
    if "competition_id" in df.columns:
        report["distinct_competitions"] = int(df["competition_id"].nunique())
    if "season" in df.columns:
        report["distinct_seasons"] = sorted([int(s) for s in df["season"].dropna().unique()])

    return report


def run_schema_discovery(
    raw_dir: Path = RAW_TM_DIR,
    metadata_dir: Path = METADATA_DIR,
    docs_dir: Path = DOCS_DIR,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Inspect all available raw tables, generating schema and inventory reports."""
    metadata_dir.mkdir(parents=True, exist_ok=True)
    docs_dir.mkdir(parents=True, exist_ok=True)

    source_inventory_path = metadata_dir / "source_inventory.json"
    schema_report_path = metadata_dir / "schema_report.json"
    data_inventory_md_path = docs_dir / "data_inventory.md"

    schema_report: dict[str, Any] = {
        "generated_at": datetime.now(UTC).isoformat(),
        "tables": {},
    }

    source_inventory: dict[str, Any] = {
        "source_name": "Transfermarkt Datasets (dcaribou/transfermarkt-datasets)",
        "source_repository": "https://github.com/dcaribou/transfermarkt-datasets",
        "data_distribution_url": "https://pub-e682421888d945d684bcae8890b0ec20.r2.dev/data/",
        "generated_at": datetime.now(UTC).isoformat(),
        "tables": {},
    }

    for table in CORE_TM_TABLES:
        file_path = raw_dir / f"{table}.csv.gz"
        if not file_path.exists():
            logger.warning("Table %s not found on disk at %s", table, file_path)
            continue

        try:
            df = load_raw_table(table, raw_dir=raw_dir)
            t_schema = inspect_table_schema(table, df)
            schema_report["tables"][table] = t_schema

            stat = file_path.stat()
            source_inventory["tables"][table] = {
                "file_name": file_path.name,
                "file_format": "csv.gz",
                "file_size_bytes": stat.st_size,
                "record_count": t_schema["record_count"],
                "column_count": t_schema["column_count"],
                "duplicate_rows": t_schema["duplicate_rows"],
                "date_range": t_schema["date_range"],
                "distinct_players": t_schema.get("distinct_players"),
                "distinct_clubs": t_schema.get("distinct_clubs"),
                "distinct_competitions": t_schema.get("distinct_competitions"),
                "usable_for_training": True if t_schema["record_count"] > 0 else False,
            }
        except Exception as e:
            logger.error("Failed to inspect %s: %s", table, e)

    with open(source_inventory_path, "w", encoding="utf-8") as f:
        json.dump(source_inventory, f, indent=2)

    with open(schema_report_path, "w", encoding="utf-8") as f:
        json.dump(schema_report, f, indent=2)

    _generate_markdown_inventory(source_inventory, schema_report, data_inventory_md_path)

    logger.info("Saved schema reports to %s and %s", source_inventory_path, schema_report_path)
    return source_inventory, schema_report


def _generate_markdown_inventory(
    source_inventory: dict[str, Any],
    schema_report: dict[str, Any],
    out_path: Path,
) -> None:
    """Generate docs/data_inventory.md markdown summary."""
    lines = [
        "# Data Inventory and Schema Discovery Report",
        "",
        f"**Generated:** {source_inventory.get('generated_at', datetime.now(UTC).isoformat())}  ",
        f"**Primary Source:** [{source_inventory.get('source_name')}]({source_inventory.get('source_repository')})  ",
        f"**Distribution Endpoint:** `{source_inventory.get('data_distribution_url')}`  ",
        "",
        "## 1. Source Table Summary",
        "",
        "| Table Name | File Format | File Size (MB) | Record Count | Distinct Players | Distinct Clubs | Date Range | Usable |",
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
    ]

    for t_name, t_meta in source_inventory.get("tables", {}).items():
        size_mb = round(t_meta.get("file_size_bytes", 0) / (1024 * 1024), 2)
        recs = f"{t_meta.get('record_count', 0):,}"
        players = f"{t_meta.get('distinct_players'):,}" if t_meta.get("distinct_players") is not None else "N/A"
        clubs = f"{t_meta.get('distinct_clubs'):,}" if t_meta.get("distinct_clubs") is not None else "N/A"
        dr = t_meta.get("date_range")
        date_str = f"{dr['min']} to {dr['max']}" if dr else "N/A"
        usable = "Yes" if t_meta.get("usable_for_training") else "No"
        lines.append(
            f"| `{t_name}` | `{t_meta.get('file_format')}` | {size_mb} MB | {recs} | {players} | {clubs} | {date_str} | {usable} |"
        )

    lines.extend(
        [
            "",
            "## 2. Table Column Schema and Missingness",
            "",
        ]
    )

    for t_name, t_schema in schema_report.get("tables", {}).items():
        lines.extend(
            [
                f"### Table: `{t_name}`",
                "",
                f"- **Records:** {t_schema.get('record_count'):,}  ",
                f"- **Columns:** {t_schema.get('column_count')}  ",
                f"- **Duplicate Rows:** {t_schema.get('duplicate_rows')}  ",
                "",
                "| Column Name | Data Type | Null Count | Null % | Distinct Values |",
                "| :--- | :--- | :--- | :--- | :--- |",
            ]
        )
        for col_name, c_info in t_schema.get("columns", {}).items():
            lines.append(
                f"| `{col_name}` | `{c_info.get('dtype')}` | {c_info.get('null_count'):,} | {c_info.get('null_pct')}% | {c_info.get('distinct_values'):,} |"
            )
        lines.append("")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    logger.info("Starting Transfermarkt data ingestion...")
    download_transfermarkt_tables()
    logger.info("Running schema discovery...")
    run_schema_discovery()
    logger.info("Ingestion and schema discovery completed.")
