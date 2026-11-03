"""TRANSFERA — Image Diagnostics and Integrity Audit Script.

Inspects local assets, static fallbacks, parquet image registries, and verifies
remote CDN connectivity with bounded rate limits and offline mode support.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd  # noqa: E402

from src.image_service import (  # noqa: E402
    ASSETS_DIR,
    FALLBACK_DATA_URIS,
    FALLBACK_SVGS,
    FALLBACKS_DIR,
    fetch_remote_image,
    load_local_image,
    validate_image_url,
)


def run_image_audit(sample_size: int = 50, offline: bool = False) -> dict[str, Any]:
    """Execute comprehensive audit across local files, static assets, and remote URLs."""
    print("=" * 60)
    print("TRANSFERA IMAGE AUDIT")
    print("=" * 60)

    # 1. Audit Local Static Fallbacks
    fallbacks_found = 0
    fallbacks_missing = 0
    required_fallbacks = ["player.svg", "club.svg", "competition.svg", "country.svg", "news.svg"]
    for fb in required_fallbacks:
        fb_path = FALLBACKS_DIR / fb
        if fb_path.exists() and fb_path.stat().st_size > 50:
            fallbacks_found += 1
        else:
            fallbacks_missing += 1

    # 2. Audit Local Assets
    local_images_found = 0
    local_images_missing = 0
    for category in ["players", "clubs", "leagues"]:
        cat_dir = ASSETS_DIR / category
        if cat_dir.exists():
            for f in cat_dir.glob("*"):
                if f.name != ".gitkeep" and f.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp", ".svg"):
                    b = load_local_image(f)
                    if b and len(b) > 0:
                        local_images_found += 1
                    else:
                        local_images_missing += 1

    # 3. Audit Player Image Map Parquet
    pq_path = PROJECT_ROOT / "data" / "metadata" / "player_image_map.parquet"
    total_references = 0
    invalid_references = 0
    duplicate_references = 0
    sample_urls: list[str] = []

    if pq_path.exists():
        try:
            df_map = pd.read_parquet(pq_path)
            total_references = len(df_map)
            valid_mask = df_map["image_url"].apply(validate_image_url)
            invalid_references = int((~valid_mask).sum())
            duplicate_references = int(df_map["image_url"].duplicated().sum())

            # Sample remote URLs for connectivity checking
            valid_urls = df_map[valid_mask]["image_url"].drop_duplicates()
            sample_urls = valid_urls.head(sample_size).tolist()
        except Exception as e:
            print(f"Warning reading image parquet: {e}")

    # 4. Probe Remote URLs (if online)
    remote_checked = 0
    remote_verified = 0
    remote_failed = 0

    if not offline and sample_urls:
        print(f"Checking {len(sample_urls)} remote URLs (bounded timeout)...")
        for u in sample_urls:
            remote_checked += 1
            data = fetch_remote_image(u, timeout=2.5)
            if data is not None and len(data) > 100:
                remote_verified += 1
            else:
                remote_failed += 1
    else:
        if offline:
            print("Offline mode active: skipped remote network probes.")

    # 5. Report Summary
    print("\nTotal image references:      ", total_references)
    print("Local images found:          ", local_images_found)
    print("Local images missing:        ", local_images_missing)
    print("Static fallbacks available:  ", f"{fallbacks_found}/{len(required_fallbacks)}")
    print("Embedded SVG fallbacks:      ", f"{len(FALLBACK_DATA_URIS)}/{len(FALLBACK_SVGS)}")
    print("Remote URLs checked:         ", remote_checked)
    print("Remote images verified:      ", remote_verified)
    print("Remote images failed:        ", remote_failed)
    print("Invalid image references:    ", invalid_references)
    print("Duplicate image references:  ", duplicate_references)
    print(
        "Fallback images required:    ", (total_references - remote_verified) if remote_checked else "Ready (on-demand)"
    )
    print("=" * 60)

    return {
        "total_references": total_references,
        "local_images_found": local_images_found,
        "local_images_missing": local_images_missing,
        "fallbacks_found": fallbacks_found,
        "remote_checked": remote_checked,
        "remote_verified": remote_verified,
        "remote_failed": remote_failed,
        "invalid_references": invalid_references,
        "duplicate_references": duplicate_references,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="TRANSFERA Image Integrity Auditor")
    parser.add_argument("--sample", type=int, default=20, help="Number of remote URLs to verify")
    parser.add_argument("--offline", action="store_true", help="Run audit without external network calls")
    args = parser.parse_args()

    run_image_audit(sample_size=args.sample, offline=args.offline)


if __name__ == "__main__":
    main()
