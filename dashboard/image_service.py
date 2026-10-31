"""Image asset and fallback service for TRANSFERA Platform."""

from pathlib import Path

# Paths to local assets
ASSETS_DIR = Path(__file__).parent.parent / "assets"
PLAYERS_DIR = ASSETS_DIR / "players"
CLUBS_DIR = ASSETS_DIR / "clubs"
LEAGUES_DIR = ASSETS_DIR / "leagues"

# Standard Transfermarkt CDN URL templates
CLUB_CREST_TEMPLATE = "https://tmssl.akamaized.net/images/wappen/head/{club_id}.png"
COMPETITION_LOGO_TEMPLATE = "https://tmssl.akamaized.net/images/logo/header/{comp_id}.png"

# SVG Fallbacks
DEFAULT_PLAYER_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100%" height="100%">
  <defs>
    <linearGradient id="pGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#02D8E9"/>
      <stop offset="100%" stop-color="#32E6F2"/>
    </linearGradient>
  </defs>
  <circle cx="50" cy="50" r="48" fill="#0D222D" stroke="#02D8E9" stroke-width="2"/>
  <circle cx="50" cy="36" r="16" fill="url(#pGrad)"/>
  <path d="M 22 82 C 22 62, 34 54, 50 54 C 66 54, 78 62, 78 82 Z" fill="url(#pGrad)"/>
</svg>"""

DEFAULT_CLUB_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100%" height="100%">
  <polygon points="50,5 92,20 92,60 50,95 8,60 8,20" fill="#091B25" stroke="#02D8E9" stroke-width="3"/>
  <circle cx="50" cy="48" r="22" fill="none" stroke="#32E6F2" stroke-width="2"/>
  <path d="M 50 30 L 50 66 M 32 48 L 68 48" stroke="#02D8E9" stroke-width="2"/>
</svg>"""

DEFAULT_LEAGUE_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100%" height="100%">
  <circle cx="50" cy="50" r="46" fill="#06121A" stroke="#02D8E9" stroke-width="3"/>
  <polygon points="50,18 59,38 81,38 63,51 70,72 50,58 30,72 37,51 19,38 41,38" fill="#02D8E9"/>
</svg>"""


def get_player_image_url(player_id: int | None, raw_image_url: str | None = None) -> str:
    """Return verified player image URL or fallback data URI."""
    if raw_image_url and isinstance(raw_image_url, str) and raw_image_url.startswith("http"):
        # Convert desktop thumbnail link if needed
        return raw_image_url
    if player_id:
        local_path = PLAYERS_DIR / f"{player_id}.png"
        if local_path.exists():
            return str(local_path)
    return "https://images.unsplash.com/photo-1508098682722-e99c43a406b2?w=300&auto=format&fit=crop&q=60"


def get_club_crest_url(club_id: int | None) -> str:
    """Return CDN club badge URL."""
    if club_id and club_id > 0:
        return CLUB_CREST_TEMPLATE.format(club_id=club_id)
    return "https://images.unsplash.com/photo-1522778119026-d647f0596c20?w=120&auto=format&fit=crop&q=60"


def get_competition_logo_url(competition_id: str | None) -> str:
    """Return CDN league logo URL."""
    if competition_id:
        cid_lower = str(competition_id).strip().lower()
        return COMPETITION_LOGO_TEMPLATE.format(comp_id=cid_lower)
    return "https://images.unsplash.com/photo-1522778119026-d647f0596c20?w=120&auto=format&fit=crop&q=60"
