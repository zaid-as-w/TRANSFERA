"""Countries Page: TRANSFERA Global Geographic Analysis, National Valuations, and Player Talents."""

import pandas as pd
import plotly.express as px
import streamlit as st

from dashboard.components.charts import CHART_THEME, render_country_map
from dashboard.components.header import render_header
from dashboard.components.player_card import render_scout_card
from dashboard.data_service import DataService
from dashboard.formatting import format_currency_eur, get_country_flag
from dashboard.prediction_service import DashboardPredictionService


def render_countries_page(data_service: DataService, pred_service: DashboardPredictionService) -> None:
    """Render the Country Analytics page in clean light style."""
    all_comps = data_service.get_competitions()
    render_header(all_comps)

    st.markdown(
        """
        <div style="margin-bottom: 1.25rem;">
            <div style="font-size:0.72rem;font-weight:700;letter-spacing:1px;color:#02BFD0;text-transform:uppercase;font-family:'Inter',sans-serif;">TRANSFERA GLOBAL CONSOLE</div>
            <h1 style="margin: 0.2rem 0; font-size: 1.9rem; font-weight: 800; letter-spacing: -0.5px; text-transform:uppercase; font-family:'Manrope',sans-serif; color:#17212B;">
                COUNTRY <span style="color:#02BFD0;">ANALYTICS</span>
            </h1>
            <p style="margin: 0.2rem 0 1rem 0; color: #66727D; font-size: 0.92rem;">
                Explore national football talent pools, market value concentrations across sovereign nations, and geographic distributions.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c_s, c_cntry = st.columns([1, 2])
    seasons = data_service.get_seasons()
    with c_s:
        sel_season = st.selectbox("Season", seasons, index=0, key="countries_season_sel")

    countries_list = data_service.get_countries()
    default_idx = countries_list.index("England") if "England" in countries_list else 0
    with c_cntry:
        sel_country = st.selectbox(
            "Inspect Specific Nation", countries_list, index=default_idx, key="countries_nation_sel"
        )

    df_season = data_service.filter_data(season=sel_season)
    country_agg = data_service.get_market_value_by_country(df_season, by_player_nationality=True)

    st.markdown('<div class="tm-card">', unsafe_allow_html=True)
    fig_map = render_country_map(country_agg)
    st.plotly_chart(fig_map, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<hr style='border:none; border-top:1px solid #E2E6E9; margin: 1.25rem 0;'>", unsafe_allow_html=True)

    df_nation = data_service.filter_data(season=sel_season, country=sel_country)
    flag = get_country_flag(sel_country)
    total_val = df_nation["historical_market_value"].sum()
    avg_val = df_nation["historical_market_value"].mean() if len(df_nation) > 0 else 0.0

    st.markdown(
        f"""
        <div class="tm-card" style="padding: 1.2rem; margin-bottom: 1.2rem;">
            <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 1rem;">
                <div style="display: flex; align-items: center; gap: 0.8rem;">
                    <span style="font-size: 2.8rem;">{flag}</span>
                    <div>
                        <div style="font-size: 1.5rem; font-weight: 800; color: #17212B; font-family:'Manrope',sans-serif;">{sel_country}</div>
                        <div style="font-size: 0.82rem; color: #66727D;">
                            Season {sel_season} · {len(df_nation):,} active registered professionals
                        </div>
                    </div>
                </div>
                <div style="display: flex; gap: 1.2rem; text-align: center; flex-wrap: wrap;">
                    <div style="background:#F8F9FA; padding:0.5rem 0.8rem; border-radius:6px; border:1px solid #EDF0F2;">
                        <div style="font-size: 0.65rem; color: #8A959E; font-weight: 700;">TOTAL NATIONAL CAPITAL</div>
                        <div style="font-size: 1.25rem; font-weight: 800; color: #02BFD0; font-family:'Manrope',sans-serif;">
                            {format_currency_eur(total_val)}
                        </div>
                    </div>
                    <div style="background:#F8F9FA; padding:0.5rem 0.8rem; border-radius:6px; border:1px solid #EDF0F2;">
                        <div style="font-size: 0.65rem; color: #8A959E; font-weight: 700;">AVG PLAYER VALUE</div>
                        <div style="font-size: 1.25rem; font-weight: 800; color: #20A56B; font-family:'Manrope',sans-serif;">
                            {format_currency_eur(avg_val)}
                        </div>
                    </div>
                    <div style="background:#F8F9FA; padding:0.5rem 0.8rem; border-radius:6px; border:1px solid #EDF0F2;">
                        <div style="font-size: 0.65rem; color: #8A959E; font-weight: 700;">GLOBAL VALUE RANK</div>
                        <div style="font-size: 1.25rem; font-weight: 800; color: #3185C7; font-family:'Manrope',sans-serif;">
                            #{country_agg[country_agg["country"] == sel_country].index[0] + 1 if sel_country in country_agg["country"].values else "-"}
                        </div>
                    </div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if len(df_nation) > 0:
        col_c_top, col_c_pos = st.columns([1.2, 1.0])

        with col_c_top:
            st.markdown(
                f"<p style='font-weight: 700; color: #17212B; font-size: 0.95rem; font-family:\"Manrope\",sans-serif;'>Top 6 Most Valuable Players from {sel_country}</p>",
                unsafe_allow_html=True,
            )
            top_nation = (
                df_nation.sort_values("historical_market_value", ascending=False)
                .drop_duplicates(subset=["player_id"])
                .head(6)
            )

            n_cols = st.columns(3)
            for idx, (_, r) in enumerate(top_nation.iterrows()):
                c_idx = idx % 3
                with n_cols[c_idx]:
                    p_dict = {
                        "player_id": int(r["player_id"]),
                        "name": str(r["name"]),
                        "current_club_name": str(r.get("current_club_name", "Club")),
                        "club_id": int(r.get("club_id", 0)) if pd.notna(r.get("club_id")) else None,
                        "position": str(r.get("position", "Attack")),
                        "country_of_citizenship": str(r.get("country_of_citizenship", "Unknown")),
                        "age": float(r.get("age_at_reference_date", 24.0)),
                        "goals": int(r.get("goals", 0)),
                        "assists": int(r.get("assists", 0)),
                        "market_value_eur": float(r.get("historical_market_value", 0.0)),
                        "image_url": data_service.image_map.get(int(r["player_id"])),
                    }
                    render_scout_card(p_dict, key_suffix=f"nat_top_{idx}")

        with col_c_pos:
            st.markdown('<div class="tm-card">', unsafe_allow_html=True)
            st.markdown(
                f"<p style='font-weight: 700; color: #17212B; font-size: 0.95rem; font-family:\"Manrope\",sans-serif;'>Position Breakdown for {sel_country}</p>",
                unsafe_allow_html=True,
            )
            pos_df = (
                df_nation.groupby("position")
                .agg(
                    total_val=("historical_market_value", "sum"),
                    avg_val=("historical_market_value", "mean"),
                    count=("player_id", "count"),
                )
                .reset_index()
            )

            fig_p = px.bar(
                pos_df,
                x="position",
                y="total_val",
                color="position",
                color_discrete_map={
                    "Attack": "#02BFD0",
                    "Midfield": "#3185C7",
                    "Defender": "#20A56B",
                    "Goalkeeper": "#E5A52B",
                },
                text=[f"€{v / 1_000_000:.1f}M" for v in pos_df["total_val"]],
            )
            fig_p.update_layout(
                **CHART_THEME,
                height=320,
                showlegend=False,
                xaxis=dict(
                    title=dict(text="Position", font=dict(size=11, color="#66727D")),
                    showgrid=False,
                    tickfont=dict(size=10, color="#66727D"),
                ),
                yaxis=dict(
                    title=dict(text="Total Capital (€)", font=dict(size=11, color="#66727D")),
                    showgrid=True,
                    gridcolor="#EDF0F2",
                    tickfont=dict(size=10, color="#66727D"),
                ),
            )
            st.plotly_chart(fig_p, use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)
