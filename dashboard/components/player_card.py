"""Player card and ranking table components for TRANSFERA."""

from typing import Any

import pandas as pd
import streamlit as st

from dashboard.formatting import format_currency_eur, get_country_flag
from dashboard.image_service import get_club_crest_url, get_player_image_url


def render_scout_card(player: dict[str, Any], key_suffix: str = "") -> None:
    """Render a clean, structured football scout player card."""
    pid = player.get("player_id")
    img_url = get_player_image_url(pid, player.get("image_url"))
    crest_url = get_club_crest_url(player.get("club_id"))
    flag = get_country_flag(player.get("country_of_citizenship"))
    val_str = format_currency_eur(player.get("market_value_eur", player.get("historical_market_value", 0.0)))
    p_name = player.get("name", "Player")
    c_name = player.get("current_club_name", "Club")
    pos = player.get("position", "FWD")
    age = int(player.get("age", player.get("age_at_reference_date", 24)))
    goals = int(player.get("goals", 0))
    assists = int(player.get("assists", 0))

    html = (
        f'<div class="player-scout-card">'
        f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.5rem;">'
        f'<div><span style="font-size:1.1rem;">{flag}</span><span style="font-size:0.78rem;color:#66727D;margin-left:0.35rem;font-weight:700;">{pos}</span></div>'
        f'<div class="player-val-badge">{val_str}</div>'
        f"</div>"
        f'<div class="player-photo-container">'
        f'<img src="{img_url}" alt="{p_name}" onerror="this.onerror=null; this.src=\'https://images.unsplash.com/photo-1508098682722-e99c43a406b2?w=300\';"/>'
        f"</div>"
        f'<div style="text-align:center;margin-top:0.5rem;">'
        f"<div style=\"font-weight:700;font-size:1rem;color:#17212B;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;font-family:'Manrope',sans-serif;\">{p_name}</div>"
        f'<div style="display:flex;align-items:center;justify-content:center;gap:0.4rem;margin-top:0.2rem;">'
        f'<img src="{crest_url}" style="width:16px;height:16px;object-fit:contain;" onerror="this.style.display=\'none\';"/>'
        f'<span style="font-size:0.78rem;color:#66727D;">{c_name}</span>'
        f"</div>"
        f"</div>"
        f'<div class="player-stat-grid">'
        f'<div class="player-stat-item"><div class="player-stat-label">AGE</div><div class="player-stat-val">{age}</div></div>'
        f'<div class="player-stat-item"><div class="player-stat-label">GOALS</div><div class="player-stat-val" style="color:#02BFD0;">{goals}</div></div>'
        f'<div class="player-stat-item"><div class="player-stat-label">AST</div><div class="player-stat-val" style="color:#20A56B;">{assists}</div></div>'
        f"</div>"
        f"</div>"
    )
    st.markdown(html, unsafe_allow_html=True)


def render_top_players_table(top_df: pd.DataFrame) -> None:
    """Render Top 10 Most Valuable Players table matching Transfermarkt-inspired design."""
    if len(top_df) == 0:
        st.info("No player records available for the current filter criteria.")
        return

    header_html = (
        '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.5rem;padding-bottom:0.4rem;border-bottom:1px solid #EDF0F2;">'
        "<div style=\"font-size:0.88rem;font-weight:700;color:#17212B;text-transform:uppercase;letter-spacing:0.5px;font-family:'Manrope',sans-serif;\">Top 10 Most Valuable Players</div>"
        '<div style="font-size:0.72rem;color:#02BFD0;font-weight:700;letter-spacing:0.5px;">MARKET RANKING</div>'
        "</div>"
    )
    st.markdown(header_html, unsafe_allow_html=True)

    rows = []
    for rank, (_, row) in enumerate(top_df.iterrows(), start=1):
        pid = int(row["player_id"])
        img_url = get_player_image_url(pid, row.get("image_url"))
        crest_url = get_club_crest_url(int(row["club_id"]) if pd.notna(row.get("club_id")) else None)
        flag = get_country_flag(row.get("country_of_citizenship"))
        val_str = format_currency_eur(row.get("historical_market_value", 0.0))
        age = int(round(row.get("age_at_reference_date", 24)))
        p_name = row["name"]
        club_name = row.get("current_club_name", "Unknown")

        row_html = (
            f"<tr>"
            f'<td style="font-weight:700;color:#8A959E;width:24px;padding:6px 4px;font-size:0.8rem;">{rank}</td>'
            f'<td style="display:flex;align-items:center;gap:0.45rem;padding:6px 4px;">'
            f'<img src="{img_url}" style="width:26px;height:26px;border-radius:50%;object-fit:cover;border:1px solid #E2E6E9;" onerror="this.src=\'https://images.unsplash.com/photo-1508098682722-e99c43a406b2?w=100\';"/>'
            f'<span style="font-weight:600;color:#17212B;font-size:0.82rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:115px;">{p_name}</span>'
            f"</td>"
            f'<td style="padding:6px 4px;">'
            f'<div style="display:flex;align-items:center;gap:0.3rem;">'
            f'<img src="{crest_url}" style="width:14px;height:14px;object-fit:contain;" onerror="this.style.display=\'none\';"/>'
            f'<span style="font-size:0.75rem;color:#66727D;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:90px;">{club_name}</span>'
            f"</div>"
            f"</td>"
            f'<td style="font-size:1rem;padding:6px 4px;">{flag}</td>'
            f'<td style="color:#66727D;font-size:0.8rem;padding:6px 4px;font-weight:500;">{age}</td>'
            f"<td style=\"text-align:right;font-weight:700;color:#02BFD0;font-size:0.88rem;padding:6px 4px;font-family:'Manrope',sans-serif;\">{val_str}</td>"
            f"</tr>"
        )
        rows.append(row_html)

    table_html = (
        f'<table class="tm-table" style="width:100%;border-collapse:collapse;font-size:0.82rem;">'
        f"<thead>"
        f'<tr style="background:#F8F9FA;border-bottom:1px solid #E2E6E9;color:#66727D;font-size:0.68rem;text-transform:uppercase;font-weight:700;letter-spacing:0.5px;">'
        f'<th style="padding:6px 4px;text-align:left;">#</th>'
        f'<th style="padding:6px 4px;text-align:left;">Player</th>'
        f'<th style="padding:6px 4px;text-align:left;">Club</th>'
        f'<th style="padding:6px 4px;text-align:left;">Nat</th>'
        f'<th style="padding:6px 4px;text-align:left;">Age</th>'
        f'<th style="padding:6px 4px;text-align:right;">Value</th>'
        f"</tr>"
        f"</thead>"
        f"<tbody>"
        f"{''.join(rows)}"
        f"</tbody>"
        f"</table>"
    )
    st.markdown(table_html, unsafe_allow_html=True)
