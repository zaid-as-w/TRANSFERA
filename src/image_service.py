"""Centralized Image Service for TRANSFERA Platform.

Handles local asset discovery, remote image fetching, validation, caching,
and resilient Transfermarkt/CDN integration with professional SVG fallbacks.
Supports both local development (Windows) and production hosting (Linux / Streamlit Cloud).
"""

from __future__ import annotations

import base64
import logging
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests
import streamlit as st

logger = logging.getLogger(__name__)

# Repository root and key directory paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ASSETS_DIR = PROJECT_ROOT / "assets"
STATIC_DIR = PROJECT_ROOT / "static"
FALLBACKS_DIR = STATIC_DIR / "images" / "fallbacks"

# CDN URL templates
CLUB_CREST_TEMPLATE = "https://tmssl.akamaized.net/images/wappen/head/{club_id}.png"
COMPETITION_LOGO_TEMPLATE = "https://tmssl.akamaized.net/images/logo/header/{comp_id}.png"

# Default request headers to avoid CDN blocking
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
}

# TRANSFERA Brand Palette Fallback SVGs
FALLBACK_SVGS: dict[str, str] = {
    "player": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 120" width="100%" height="100%">
  <rect width="120" height="120" rx="8" fill="#F8F9FA"/>
  <rect x="0.5" y="0.5" width="119" height="119" rx="7.5" fill="none" stroke="#E2E6E9" stroke-width="1"/>
  <circle cx="60" cy="46" r="20" fill="#CBD5E1"/>
  <path d="M 28 106 C 28 82, 42 74, 60 74 C 78 74, 92 82, 92 106 Z" fill="#94A3B8"/>
  <circle cx="60" cy="46" r="22" fill="none" stroke="#02BFD0" stroke-width="2" stroke-dasharray="4 2"/>
</svg>""",
    "club": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100%" height="100%">
  <rect width="100" height="100" rx="8" fill="#F8F9FA"/>
  <rect x="0.5" y="0.5" width="99" height="99" rx="7.5" fill="none" stroke="#E2E6E9" stroke-width="1"/>
  <polygon points="50,12 84,24 84,56 50,88 16,56 16,24" fill="#FFFFFF" stroke="#02BFD0" stroke-width="2.5"/>
  <circle cx="50" cy="48" r="16" fill="#F1F5F9" stroke="#94A3B8" stroke-width="1.5"/>
  <path d="M 50 32 L 50 64 M 34 48 L 66 48" stroke="#02BFD0" stroke-width="1.5"/>
</svg>""",
    "competition": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100%" height="100%">
  <rect width="100" height="100" rx="8" fill="#F8F9FA"/>
  <rect x="0.5" y="0.5" width="99" height="99" rx="7.5" fill="none" stroke="#E2E6E9" stroke-width="1"/>
  <circle cx="50" cy="50" r="38" fill="#FFFFFF" stroke="#02BFD0" stroke-width="2"/>
  <path d="M 38 28 L 62 28 L 58 48 C 58 54, 52 58, 50 58 C 48 58, 42 54, 42 48 Z" fill="#02BFD0"/>
  <path d="M 46 58 L 46 68 L 36 72 L 64 72 L 54 68 L 54 58" fill="#94A3B8"/>
  <polygon points="50,33 52,37 57,37 53,40 55,44 50,42 45,44 47,40 43,37 48,37" fill="#FFFFFF"/>
</svg>""",
    "country": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100%" height="100%">
  <rect width="100" height="100" rx="8" fill="#F8F9FA"/>
  <rect x="0.5" y="0.5" width="99" height="99" rx="7.5" fill="none" stroke="#E2E6E9" stroke-width="1"/>
  <circle cx="50" cy="50" r="34" fill="#FFFFFF" stroke="#02BFD0" stroke-width="2"/>
  <ellipse cx="50" cy="50" rx="16" ry="34" fill="none" stroke="#94A3B8" stroke-width="1.5"/>
  <line x1="16" y1="50" x2="84" y2="50" stroke="#94A3B8" stroke-width="1.5"/>
  <line x1="22" y1="34" x2="78" y2="34" stroke="#CBD5E1" stroke-width="1"/>
  <line x1="22" y1="66" x2="78" y2="66" stroke="#CBD5E1" stroke-width="1"/>
</svg>""",
    "news": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 180" width="100%" height="100%">
  <rect width="320" height="180" rx="8" fill="#F8F9FA"/>
  <rect x="0.5" y="0.5" width="319" height="179" rx="7.5" fill="none" stroke="#E2E6E9" stroke-width="1"/>
  <rect x="30" y="25" width="260" height="130" rx="4" fill="#FFFFFF" stroke="#EDF0F2" stroke-width="1"/>
  <line x1="160" y1="25" x2="160" y2="155" stroke="#EDF0F2" stroke-width="1.5"/>
  <circle cx="160" cy="90" r="28" fill="none" stroke="#02BFD0" stroke-width="1.5"/>
  <circle cx="160" cy="90" r="3" fill="#02BFD0"/>
  <rect x="30" y="55" width="40" height="70" fill="none" stroke="#EDF0F2" stroke-width="1.5"/>
  <rect x="250" y="55" width="40" height="70" fill="none" stroke="#EDF0F2" stroke-width="1.5"/>
</svg>""",
}

# Precomputed data URIs for instantaneous offline fallbacks
FALLBACK_DATA_URIS: dict[str, str] = {
    k: f"data:image/svg+xml;base64,{base64.b64encode(v.strip().encode('utf-8')).decode('ascii')}"
    for k, v in FALLBACK_SVGS.items()
}


def get_project_image_path(category: str, filename: str) -> Path:
    """Return repository-relative path inside assets or static folder.

    Case-insensitively resolves file existence on Linux if direct lookup misses.
    """
    target_dir = ASSETS_DIR / category
    exact_path = target_dir / filename
    if exact_path.exists():
        return exact_path

    # Try static directory alternative
    static_path = STATIC_DIR / "images" / category / filename
    if static_path.exists():
        return static_path

    # Case-insensitive scan for Linux compatibility
    if target_dir.exists():
        fn_lower = filename.lower()
        for p in target_dir.iterdir():
            if p.name.lower() == fn_lower:
                return p

    return exact_path


def load_local_image(file_path: Path | str) -> bytes | None:
    """Safely load local image bytes. Returns None if file is missing or unreadable."""
    path = Path(file_path) if isinstance(file_path, str) else file_path
    if not path.exists() or not path.is_file():
        return None
    try:
        data = path.read_bytes()
        return data if len(data) > 0 else None
    except Exception as e:
        logger.debug("Failed to read local image %s: %s", path, e)
        return None


def validate_image_url(url: Any) -> bool:
    """Validate whether an input string is a well-formed image URL or data URI."""
    if not url or not isinstance(url, str):
        return False
    url_clean = url.strip()
    if url_clean.startswith("data:image/"):
        return True
    try:
        parsed = urlparse(url_clean)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            return False
        # Disallow localhost or internal network probes
        if parsed.hostname in ("localhost", "127.0.0.1", "0.0.0.0"):
            return False
        return True
    except Exception:
        return False


@st.cache_data(ttl=86400, max_entries=1000, show_spinner=False)
def fetch_remote_image(url: str, timeout: float = 3.0) -> bytes | None:
    """Fetch remote image bytes with safe timeout, user agent, and MIME validation."""
    if not validate_image_url(url) or url.startswith("data:"):
        return None

    try:
        resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=(2.0, timeout), stream=True)
        if resp.status_code != 200:
            return None
        content_type = resp.headers.get("Content-Type", "").lower()
        if not (content_type.startswith("image/") or "octet-stream" in content_type):
            return None

        # Guard against excessively large downloads (limit to 5MB)
        content_length = resp.headers.get("Content-Length")
        if content_length and int(content_length) > 5 * 1024 * 1024:
            return None

        raw_bytes = resp.content
        return raw_bytes if len(raw_bytes) > 50 else None
    except Exception as e:
        logger.debug("Remote image fetch failed for %s: %s", url, e)
        return None


def get_fallback_image(fallback_type: str = "player", as_data_uri: bool = True) -> str:
    """Return verified SVG fallback data URI or static URL for the given asset category."""
    ft = fallback_type.lower().strip()
    if ft not in FALLBACK_DATA_URIS:
        ft = "player"

    if as_data_uri:
        return FALLBACK_DATA_URIS[ft]

    # If static file serving is preferred and file exists
    static_file = FALLBACKS_DIR / f"{ft}.svg"
    if static_file.exists():
        return f"app/static/images/fallbacks/{ft}.svg"
    return FALLBACK_DATA_URIS[ft]


def get_player_image(
    player_id: int | None = None,
    raw_image_url: str | None = None,
    as_data_uri: bool = False,
) -> str:
    """Return player portrait URL, local file data URI, or TRANSFERA player fallback."""
    # 1. Check local assets folder
    if player_id:
        for ext in (".png", ".jpg", ".jpeg", ".webp"):
            local_file = get_project_image_path("players", f"{player_id}{ext}")
            if local_file.exists():
                if as_data_uri:
                    b = load_local_image(local_file)
                    if b:
                        mime = "png" if ext == ".png" else "jpeg"
                        b64 = base64.b64encode(b).decode("ascii")
                        return f"data:image/{mime};base64,{b64}"
                return f"app/static/images/players/{player_id}{ext}"

    # 2. Check remote URL
    if raw_image_url and validate_image_url(raw_image_url):
        clean_url = raw_image_url.strip()
        # Upgrade http to https if applicable
        if clean_url.startswith("http://"):
            clean_url = "https://" + clean_url[7:]
        return clean_url

    # 3. TRANSFERA clean light player silhouette fallback
    return get_fallback_image("player", as_data_uri=True)


def get_club_image(
    club_id: int | None = None,
    raw_image_url: str | None = None,
    as_data_uri: bool = False,
) -> str:
    """Return club crest CDN URL or TRANSFERA club crest fallback."""
    if club_id:
        for ext in (".png", ".svg", ".jpg", ".webp"):
            local_file = get_project_image_path("clubs", f"{club_id}{ext}")
            if local_file.exists():
                return f"app/static/images/clubs/{club_id}{ext}"

    if raw_image_url and validate_image_url(raw_image_url):
        return raw_image_url.strip()

    if club_id and int(club_id) > 0:
        return CLUB_CREST_TEMPLATE.format(club_id=int(club_id))

    return get_fallback_image("club", as_data_uri=True)


def get_competition_image(
    competition_id: str | None = None,
    raw_image_url: str | None = None,
) -> str:
    """Return competition logo CDN URL or TRANSFERA competition fallback."""
    if competition_id:
        cid_clean = str(competition_id).strip().lower()
        for ext in (".png", ".svg", ".jpg"):
            local_file = get_project_image_path("leagues", f"{cid_clean}{ext}")
            if local_file.exists():
                return f"app/static/images/leagues/{cid_clean}{ext}"

        if cid_clean:
            return COMPETITION_LOGO_TEMPLATE.format(comp_id=cid_clean)

    if raw_image_url and validate_image_url(raw_image_url):
        return raw_image_url.strip()

    return get_fallback_image("competition", as_data_uri=True)


def get_country_flag(country_name: str | None) -> str:
    """Return flag emoji for standard countries or globe fallback."""
    from dashboard.formatting import COUNTRY_FLAGS

    if not country_name:
        return "🌐"
    return COUNTRY_FLAGS.get(str(country_name).strip(), "🌐")


def render_player_image(
    player_id: int | None = None,
    raw_image_url: str | None = None,
    name: str = "Player",
    size_px: int = 56,
    border_color: str = "#02BFD0",
    is_circle: bool = True,
    object_fit: str = "cover",
) -> str:
    """Render a resilient HTML <img> tag with self-healing SVG fallback."""
    img_src = get_player_image(player_id, raw_image_url)
    fallback_uri = get_fallback_image("player", as_data_uri=True)

    border_radius = "50%" if is_circle else "8px"
    safe_name = re.sub(r'["<>]', "", str(name))

    return (
        f'<img src="{img_src}" alt="{safe_name}" '
        f'style="width:{size_px}px;height:{size_px}px;border-radius:{border_radius};'
        f'object-fit:{object_fit};border:1.5px solid {border_color};background:#F8F9FA;" '
        f"onerror=\"this.onerror=null; this.src='{fallback_uri}';\"/>"
    )


def render_image_preview(
    url_or_bytes: str | bytes,
    caption: str | None = None,
    width: int = 140,
) -> None:
    """Render image safely using st.image with automatic error handling."""
    fallback_uri = get_fallback_image("player", as_data_uri=True)
    try:
        st.image(url_or_bytes, caption=caption, width=width)
    except Exception as e:
        logger.debug("st.image render error: %s, falling back to SVG", e)
        st.image(fallback_uri, caption=caption, width=width)


# Backwards-compatibility aliases for existing dashboard imports
get_player_image_url = get_player_image
get_club_crest_url = get_club_image
get_competition_logo_url = get_competition_image
