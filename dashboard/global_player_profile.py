"""Player profile view for global players and multi-provider records.

Renders verified biographical attributes, match statistics, and historical
valuation trajectories while maintaining strict integrity standards and clean light UI.
"""

from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st

from dashboard.formatting import get_country_flag
from dashboard.image_service import get_fallback_image, get_player_image
from dashboard.player_data_coverage import render_coverage_badges
from src.coverage_manager import CoverageAssessment


def render_global_player_profile(
    player: dict[str, Any],
    assessment: CoverageAssessment,
    stats: list[dict[str, Any]] | None = None,
    valuations: list[dict[str, Any]] | None = None,
) -> None:
    """Render comprehensive player profile card and diagnostics in clean light aesthetic."""
    render_coverage_badges(assessment)

    name = player.get("full_name") or player.get("name") or player.get("display_name", "Unknown Player")
    pos = player.get("position", "Missing")
    sub_pos = player.get("sub_position") or ""
    club = player.get("current_club_name", "Global Club")
    comp = player.get("current_competition_name") or player.get("current_club_domestic_competition_id", "Global League")
    nat = player.get("nationality") or player.get("country_of_citizenship", "Unknown")
    age = player.get("age") or "N/A"
    height = f"{player.get('height_cm')} cm" if player.get("height_cm") else "N/A"

    pid = player.get("transfermarkt_player_id") or player.get("player_id")
    raw_img = player.get("player_image_url") or player.get("image_url")
    img_url = get_player_image(pid, raw_img)
    fallback_img = get_fallback_image("player")
    c_flag = get_country_flag(nat)

    # Profile Header Box
    st.markdown(
        f"""
        <div class="tm-card" style="padding: 1.25rem; margin-bottom: 1.25rem;">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 1rem;">
                <div style="display: flex; align-items: center; gap: 1.25rem;">
                    <div style="width: 80px; height: 80px; border-radius: 50%; overflow: hidden; border: 2.5px solid #02BFD0; background: #F8F9FA; flex-shrink: 0;">
                        <img src="{img_url}" alt="{name}" style="width: 100%; height: 100%; object-fit: cover;" onerror="this.onerror=null; this.src='{fallback_img}';"/>
                    </div>
                    <div>
                        <h2 style="color: #17212B; font-size: 1.6rem; font-weight: 800; margin: 0 0 0.2rem 0; font-family: 'Manrope', sans-serif;">
                            {name}
                        </h2>
                        <div style="color: #02BFD0; font-size: 0.92rem; font-weight: 600; margin-bottom: 0.2rem;">
                            {club} <span style="color: #8A959E;">·</span> <span style="color: #66727D;">{comp}</span>
                        </div>
                    </div>
                </div>
            </div>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 0.75rem; margin-top: 0.85rem;">
                <div style="background: #F8F9FA; padding: 0.6rem 0.8rem; border-radius: 6px; border: 1px solid #EDF0F2;">
                    <div style="color: #8A959E; font-size: 0.7rem; text-transform: uppercase; font-weight: 600;">Nationality</div>
                    <div style="color: #17212B; font-size: 0.92rem; font-weight: 700;">{c_flag} {nat}</div>
                </div>
                <div style="background: #F8F9FA; padding: 0.6rem 0.8rem; border-radius: 6px; border: 1px solid #EDF0F2;">
                    <div style="color: #8A959E; font-size: 0.7rem; text-transform: uppercase; font-weight: 600;">Position</div>
                    <div style="color: #17212B; font-size: 0.92rem; font-weight: 700;">{pos} {f"({sub_pos})" if sub_pos else ""}</div>
                </div>
                <div style="background: #F8F9FA; padding: 0.6rem 0.8rem; border-radius: 6px; border: 1px solid #EDF0F2;">
                    <div style="color: #8A959E; font-size: 0.7rem; text-transform: uppercase; font-weight: 600;">Age</div>
                    <div style="color: #17212B; font-size: 0.92rem; font-weight: 700;">{age}</div>
                </div>
                <div style="background: #F8F9FA; padding: 0.6rem 0.8rem; border-radius: 6px; border: 1px solid #EDF0F2;">
                    <div style="color: #8A959E; font-size: 0.7rem; text-transform: uppercase; font-weight: 600;">Height</div>
                    <div style="color: #17212B; font-size: 0.92rem; font-weight: 700;">{height}</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Performance Stats Table (if available)
    if stats:
        st.markdown(
            "<h4 style='color: #17212B; margin-top: 1rem; font-size: 1.05rem;'>Verified Match Statistics</h4>",
            unsafe_allow_html=True,
        )
        stats_df = pd.DataFrame(stats)
        cols_to_show = [
            "season",
            "appearances",
            "minutes_played",
            "goals",
            "assists",
            "yellow_cards",
            "goals_per_90",
            "assists_per_90",
        ]
        present_cols = [c for c in cols_to_show if c in stats_df.columns]
        st.dataframe(
            stats_df[present_cols].rename(
                columns={
                    "season": "Season",
                    "appearances": "Apps",
                    "minutes_played": "Minutes",
                    "goals": "Goals",
                    "assists": "Assists",
                    "yellow_cards": "Cards",
                    "goals_per_90": "G/90",
                    "assists_per_90": "A/90",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )

    # Historical Valuations (if available)
    if valuations:
        st.markdown(
            "<h4 style='color: #17212B; margin-top: 1rem; font-size: 1.05rem;'>Historical Valuation Benchmark (€)</h4>",
            unsafe_allow_html=True,
        )
        vdf = pd.DataFrame(valuations)
        if not vdf.empty and "market_value_eur" in vdf.columns and "valuation_date" in vdf.columns:
            vdf["valuation_date"] = pd.to_datetime(vdf["valuation_date"])
            fig = px.line(
                vdf,
                x="valuation_date",
                y="market_value_eur",
                markers=True,
                labels={"market_value_eur": "Market Value (€)", "valuation_date": "Date"},
            )
            fig.update_traces(line_color="#02BFD0", marker=dict(size=6, color="#02BFD0"))
            fig.update_layout(
                paper_bgcolor="#FFFFFF",
                plot_bgcolor="#FFFFFF",
                font=dict(color="#66727D", family="'Inter', sans-serif"),
                xaxis=dict(showgrid=False, tickfont=dict(size=10, color="#66727D")),
                yaxis=dict(showgrid=True, gridcolor="#EDF0F2", tickfont=dict(size=10, color="#66727D")),
                margin=dict(l=20, r=20, t=20, b=20),
                height=260,
            )
            st.plotly_chart(fig, use_container_width=True)
