"""Formatting utilities for Global Football Analytics Dashboard."""

from typing import Any


def format_currency_eur(val: float | int | None, compact: bool = True) -> str:
    """Format market value or currency in euros.

    Examples:
        180_000_000 -> "€180.0M" (compact) or "€180,000,000"
        250_000 -> "€250K"
        1_200_000_000 -> "€1.2B"
    """
    if val is None or val < 0:
        return "N/A"

    v = float(val)
    if not compact:
        return f"€{v:,.0f}"

    if v >= 1_000_000_000:
        return f"€{v / 1_000_000_000:.1f}B"
    elif v >= 1_000_000:
        return f"€{v / 1_000_000:.1f}M"
    elif v >= 1_000:
        return f"€{v / 1_000:.0f}K"
    else:
        return f"€{v:.0f}"


def format_delta_pct(val: float | None) -> str:
    """Format percentage delta with +/- sign."""
    if val is None:
        return "0.0%"
    sign = "+" if val > 0 else ""
    return f"{sign}{val:.1f}%"


def format_delta_eur(val: float | None) -> str:
    """Format euro delta with +/- sign."""
    if val is None or val == 0:
        return "€0"
    sign = "+" if val > 0 else "-"
    return f"{sign}{format_currency_eur(abs(val), compact=True)}"


# Country flag emoji mapping for football nations
COUNTRY_FLAGS: dict[str, str] = {
    "England": "🏴󠁧󠁢󠁥󠁮󠁧󠁿",
    "Spain": "🇪🇸",
    "Germany": "🇩🇪",
    "Italy": "🇮🇹",
    "France": "🇫🇷",
    "Brazil": "🇧🇷",
    "Argentina": "🇦🇷",
    "Portugal": "🇵🇹",
    "Netherlands": "🇳🇱",
    "Norway": "🇳🇴",
    "Belgium": "🇧🇪",
    "Croatia": "🇭🇷",
    "Uruguay": "🇺🇾",
    "Colombia": "🇨🇴",
    "Nigeria": "🇳🇬",
    "Senegal": "🇸🇳",
    "Ghana": "🇬🇭",
    "Morocco": "🇲🇦",
    "Japan": "🇯🇵",
    "South Korea": "🇰🇷",
    "United States": "🇺🇸",
    "Canada": "🇨🇦",
    "Mexico": "🇲🇽",
    "Denmark": "🇩🇰",
    "Sweden": "🇸🇪",
    "Switzerland": "🇨🇭",
    "Austria": "🇦🇹",
    "Poland": "🇵🇱",
    "Serbia": "🇷🇸",
    "Scotland": "🏴󠁧󠁢󠁳󠁣󠁴󠁿",
    "Wales": "🏴󠁧󠁢󠁷󠁬󠁳󠁿",
    "Northern Ireland": "🇬🇧",
    "Republic of Ireland": "🇮🇪",
    "Ukraine": "🇺🇦",
    "Turkey": "🇹🇷",
    "Greece": "🇬🇷",
    "Czech Republic": "🇨🇿",
}


def get_country_flag(country_name: str | None) -> str:
    """Return flag emoji for a country name, or fallback globe icon."""
    if not country_name:
        return "🌐"
    return COUNTRY_FLAGS.get(country_name, "🌐")


TOP_5_LEAGUE_INFO: dict[str, dict[str, Any]] = {
    "GB1": {
        "name": "Premier League",
        "country": "England",
        "flag": "🏴󠁧󠁢󠁥󠁮󠁧󠁿",
        "color": "#38003c",
        "accent": "#00ff87",
    },
    "ES1": {
        "name": "La Liga",
        "country": "Spain",
        "flag": "🇪🇸",
        "color": "#ee1434",
        "accent": "#ffbe00",
    },
    "L1": {
        "name": "Bundesliga",
        "country": "Germany",
        "flag": "🇩🇪",
        "color": "#d20515",
        "accent": "#ffffff",
    },
    "IT1": {
        "name": "Serie A",
        "country": "Italy",
        "flag": "🇮🇹",
        "color": "#024494",
        "accent": "#008fd7",
    },
    "FR1": {
        "name": "Ligue 1",
        "country": "France",
        "flag": "🇫🇷",
        "color": "#091c3e",
        "accent": "#dae025",
    },
}
