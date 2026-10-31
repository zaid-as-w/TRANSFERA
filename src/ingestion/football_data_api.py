"""Optional Football-Data.org API Client.

Provides cached, rate-limited, and retry-resilient access to Football-Data.org
v4 endpoints. Used as a secondary source for competition metadata and validation.
Operates gracefully without an API key or when network is offline.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config.settings import FOOTBALL_DATA_API_BASE, FOOTBALL_DATA_API_KEY, RAW_DATA_DIR

logger = logging.getLogger(__name__)


class FootballDataClient:
    """Client for Football-Data.org v4 REST API."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = FOOTBALL_DATA_API_BASE,
        cache_dir: Path | None = None,
        timeout: int = 15,
        max_retries: int = 3,
    ) -> None:
        self.api_key = api_key or FOOTBALL_DATA_API_KEY or os.getenv("FOOTBALL_DATA_API_KEY")
        self.base_url = base_url.rstrip("/")
        self.cache_dir = cache_dir or (RAW_DATA_DIR / "football_data_cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.timeout = timeout

        self.session = requests.Session()
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=1.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

        headers = {
            "User-Agent": "GlobalFootballValuationEngine/1.0",
            "Accept": "application/json",
        }
        if self.api_key:
            headers["X-Auth-Token"] = self.api_key
        self.session.headers.update(headers)

    def _get_cache_path(self, endpoint: str, params: dict[str, Any] | None = None) -> Path:
        clean_name = endpoint.replace("/", "_").strip("_")
        if params:
            param_str = "_".join(f"{k}-{v}" for k, v in sorted(params.items()))
            clean_name += f"_{param_str}"
        return self.cache_dir / f"{clean_name}.json"

    def get(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        use_cache: bool = True,
    ) -> dict[str, Any] | None:
        """Perform GET request with caching, backoff, and error safety.

        Returns parsed JSON dict, or None if request fails or rate limits exceeded.
        """
        cache_path = self._get_cache_path(endpoint, params)
        if use_cache and cache_path.exists():
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    logger.debug("Loaded cached response for %s", endpoint)
                    return json.load(f)
            except Exception as e:
                logger.warning("Failed to read cache file %s: %s", cache_path, e)

        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        try:
            logger.info("Requesting Football-Data.org: %s", url)
            response = self.session.get(url, params=params, timeout=self.timeout)

            if response.status_code == 429:
                logger.warning("Football-Data.org rate limit reached. Returning None.")
                return None
            if response.status_code == 403:
                logger.warning("Football-Data.org forbidden (check API key permissions for tier).")
                return None
            response.raise_for_status()

            data = response.json()
            if use_cache:
                with open(cache_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
            return data

        except requests.exceptions.RequestException as e:
            logger.warning("Football-Data.org request failed for %s: %s", endpoint, e)
            return None

    def get_competitions(self) -> list[dict[str, Any]]:
        """Fetch available competitions list."""
        data = self.get("competitions")
        if data and "competitions" in data:
            return data["competitions"]
        return []

    def get_competition(self, competition_code: str) -> dict[str, Any] | None:
        """Fetch metadata for a single competition (e.g. 'PL', 'PD', 'SA', 'BL1', 'FL1')."""
        return self.get(f"competitions/{competition_code}")

    def get_standings(self, competition_code: str, season: int | None = None) -> dict[str, Any] | None:
        """Fetch standings for a competition and season."""
        params = {"season": season} if season else None
        return self.get(f"competitions/{competition_code}/standings", params=params)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    client = FootballDataClient()
    logger.info("Checking Football-Data.org availability...")
    comps = client.get_competitions()
    logger.info("Found %d competitions from Football-Data.org.", len(comps))
