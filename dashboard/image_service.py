"""Image service module for TRANSFERA dashboard.

Re-exports unified functionality from centralized src.image_service
while maintaining complete backwards compatibility for existing imports.
"""

from src.image_service import (
    ASSETS_DIR,
    CLUB_CREST_TEMPLATE,
    COMPETITION_LOGO_TEMPLATE,
    DEFAULT_HEADERS,
    FALLBACK_DATA_URIS,
    FALLBACK_SVGS,
    PROJECT_ROOT,
    STATIC_DIR,
    fetch_remote_image,
    get_club_crest_url,
    get_club_image,
    get_competition_image,
    get_competition_logo_url,
    get_country_flag,
    get_fallback_image,
    get_player_image,
    get_player_image_url,
    get_project_image_path,
    load_local_image,
    render_image_preview,
    render_player_image,
    validate_image_url,
)

__all__ = [
    "ASSETS_DIR",
    "CLUB_CREST_TEMPLATE",
    "COMPETITION_LOGO_TEMPLATE",
    "DEFAULT_HEADERS",
    "FALLBACK_DATA_URIS",
    "FALLBACK_SVGS",
    "PROJECT_ROOT",
    "STATIC_DIR",
    "fetch_remote_image",
    "get_club_crest_url",
    "get_club_image",
    "get_competition_image",
    "get_competition_logo_url",
    "get_country_flag",
    "get_fallback_image",
    "get_player_image",
    "get_player_image_url",
    "get_project_image_path",
    "load_local_image",
    "render_image_preview",
    "render_player_image",
    "validate_image_url",
]
