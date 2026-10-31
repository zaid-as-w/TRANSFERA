"""Leagues Page: TRANSFERA League Analytics, Cross-League Strength Ratings, and Valuation Capital."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dashboard.components.charts import CHART_THEME, render_league_bar_chart
from dashboard.components.header import render_header
from dashboard.components.player_card import render_scout_card
from dashboard.data_service import DataService
from dashboard.formatting import format_currency_eur, get_country_flag
from dashboard.image_service import get_competition_logo_url
from dashboard.prediction_service import DashboardPredictionService


def render_leagues_page(data_service: DataService, pred_service: DashboardPredictionService) -> None:
    """Render the League Analytics page in clean light style."""
    all_comps = data_service.get_competitions()
    render_header(all_comps)

    st.markdown(
        """
        <div style="margin-bottom: 1.25rem;">
            <div style="font-size:0.72rem;font-weight:700;letter-spacing:1px;color:#02BFD0;text-transform:uppercase;font-family:'Inter',sans-serif;">TRANSFERA COMPETITION CONSOLE</div>
            <h1 style="margin: 0.2rem 0; font-size: 1.9rem; font-weight: 800; letter-spacing: -0.5px; text-transform:uppercase; font-family:'Manrope',sans-serif; color:#17212B;">
                LEAGUE <span style="color:#02BFD0;">ANALYTICS</span>
            </h1>
            <p style="margin: 0.2rem 0 1rem 0; color: #66727D; font-size: 0.92rem;">
                Cross-competition financial power, calibrated Elo strength ratings, and club valuation distributions across European and global football.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c_s, c_comp = st.columns([1, 2])
    seasons = data_service.get_seasons()
    with c_s:
        sel_season = st.selectbox("Season", seasons, index=0, key="leagues_season_sel")

    comp_options = {c["id"]: f"{c['name']} ({c['country']})" for c in all_comps}
    with c_comp:
        sel_comp_id = st.selectbox(
            "Inspect Specific League",
            options=list(comp_options.keys()),
            format_func=lambda cid: comp_options[cid],
            index=0,
            key="leagues_comp_sel",
        )

    df_season = data_service.filter_data(season=sel_season)
    league_agg = data_service.get_market_value_by_league(df_season)

    # Metric Selector using modern segmented control
    metric_options = ["Total Market Capital", "Average Player Value", "Median Player Value"]
    metric_choice = st.segmented_control(
        "Metric",
        options=metric_options,
        default="Total Market Capital",
        key="league_chart_metric_segmented",
        label_visibility="collapsed",
    )
    if not metric_choice:
        metric_choice = "Total Market Capital"

    metric_map = {
        "Total Market Capital": "total_market_value",
        "Average Player Value": "avg_market_value",
        "Median Player Value": "median_market_value",
    }

    st.markdown('<div class="tm-card">', unsafe_allow_html=True)
    fig_leagues = render_league_bar_chart(league_agg, metric=metric_map[metric_choice])
    st.plotly_chart(fig_leagues, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<hr style='border:none; border-top:1px solid #E2E6E9; margin: 1.25rem 0;'>", unsafe_allow_html=True)

    df_single = data_service.filter_data(season=sel_season, competition_id=sel_comp_id)
    comp_info = next((c for c in all_comps if c["id"] == sel_comp_id), {"name": sel_comp_id, "country": "Global"})
    flag = get_country_flag(comp_info.get("country"))
    logo_url = get_competition_logo_url(sel_comp_id)

    ratings_dict = data_service.league_strengths.get("league_ratings", {})
    comp_strength = ratings_dict.get(sel_comp_id, {})
    mean_elo = comp_strength.get("overall_mean_elo", 1500.0)
    top4_elo = comp_strength.get("overall_top4_elo", 1500.0)
    norm_strength = comp_strength.get("normalized_strength", 1.0)
    xl_matches = comp_strength.get("cross_league_matches", 0)

    # League Header Card
    st.markdown(
        f"""
        <div class="tm-card" style="padding: 1.2rem; margin-bottom: 1.2rem;">
            <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 1rem;">
                <div style="display: flex; align-items: center; gap: 1rem;">
                    <img src="{logo_url}" style="width: 48px; height: 48px; object-fit: contain;" onerror="this.style.display='none';"/>
                    <div>
                        <div style="font-size: 1.4rem; font-weight: 800; color: #17212B; font-family:'Manrope',sans-serif;">
                            {flag} {comp_info["name"]}
                        </div>
                        <div style="font-size: 0.82rem; color: #66727D;">
                            Season {sel_season} · {len(df_single):,} active player profiles
                        </div>
                    </div>
                </div>
                <div style="display: flex; gap: 1.2rem; text-align: center; flex-wrap: wrap;">
                    <div style="background:#F8F9FA; padding:0.5rem 0.8rem; border-radius:6px; border:1px solid #EDF0F2;">
                        <div style="font-size: 0.65rem; color: #8A959E; font-weight: 700;">TOTAL CAPITAL</div>
                        <div style="font-size: 1.2rem; font-weight: 800; color: #02BFD0; font-family:'Manrope',sans-serif;">
                            {format_currency_eur(df_single["historical_market_value"].sum())}
                        </div>
                    </div>
                    <div style="background:#F8F9FA; padding:0.5rem 0.8rem; border-radius:6px; border:1px solid #EDF0F2;">
                        <div style="font-size: 0.65rem; color: #8A959E; font-weight: 700;">AVG VALUE</div>
                        <div style="font-size: 1.2rem; font-weight: 800; color: #20A56B; font-family:'Manrope',sans-serif;">
                            {format_currency_eur(df_single["historical_market_value"].mean()) if len(df_single) > 0 else "€0"}
                        </div>
                    </div>
                    <div style="background:#F8F9FA; padding:0.5rem 0.8rem; border-radius:6px; border:1px solid #EDF0F2;">
                        <div style="font-size: 0.65rem; color: #8A959E; font-weight: 700;">MEAN ELO</div>
                        <div style="font-size: 1.2rem; font-weight: 800; color: #17212B; font-family:'Manrope',sans-serif;">
                            {mean_elo:.1f}
                        </div>
                    </div>
                    <div style="background:#F8F9FA; padding:0.5rem 0.8rem; border-radius:6px; border:1px solid #EDF0F2;">
                        <div style="font-size: 0.65rem; color: #8A959E; font-weight: 700;">TOP 4 ELO</div>
                        <div style="font-size: 1.2rem; font-weight: 800; color: #E5A52B; font-family:'Manrope',sans-serif;">
                            {top4_elo:.1f}
                        </div>
                    </div>
                    <div style="background:#F8F9FA; padding:0.5rem 0.8rem; border-radius:6px; border:1px solid #EDF0F2;">
                        <div style="font-size: 0.65rem; color: #8A959E; font-weight: 700;">REL STRENGTH</div>
                        <div style="font-size: 1.2rem; font-weight: 800; color: #02BFD0; font-family:'Manrope',sans-serif;">
                            {norm_strength:.2f}x
                        </div>
                    </div>
                    <div style="background:#F8F9FA; padding:0.5rem 0.8rem; border-radius:6px; border:1px solid #EDF0F2;">
                        <div style="font-size: 0.65rem; color: #8A959E; font-weight: 700;">XL MATCHES</div>
                        <div style="font-size: 1.2rem; font-weight: 800; color: #3185C7; font-family:'Manrope',sans-serif;">
                            {xl_matches}
                        </div>
                    </div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if len(df_single) > 0:
        col_clubs, col_top_p = st.columns([1.2, 1.0])

        with col_clubs:
            st.markdown('<div class="tm-card">', unsafe_allow_html=True)
            st.markdown(
                "<p style='font-weight: 700; color: #17212B; font-size: 0.95rem; font-family:\"Manrope\",sans-serif;'>Club Market Capital Distribution</p>",
                unsafe_allow_html=True,
            )
            club_agg = (
                df_single.groupby("current_club_name")
                .agg(
                    total_val=("historical_market_value", "sum"),
                    avg_val=("historical_market_value", "mean"),
                    player_count=("player_id", "nunique"),
                )
                .reset_index()
                .sort_values("total_val", ascending=False)
                .head(15)
            )

            fig_clubs = go.Figure(
                data=[
                    go.Bar(
                        x=club_agg["total_val"] / 1_000_000,
                        y=club_agg["current_club_name"],
                        orientation="h",
                        marker=dict(
                            color=club_agg["total_val"],
                            colorscale=[[0, "#E5F9FB"], [0.3, "#02BFD0"], [1, "#008594"]],
                            line=dict(color="#E2E6E9", width=1),
                        ),
                        text=[f"€{v / 1_000_000:.1f}M" for v in club_agg["total_val"]],
                        textposition="outside",
                        hovertemplate="<b>%{y}</b><br>Total Value: €%{x:.1f}M<extra></extra>",
                    )
                ]
            )
            fig_clubs.update_layout(
                **CHART_THEME,
                height=380,
                xaxis=dict(
                    title=dict(text="Squad Valuation (€ Millions)", font=dict(size=11, color="#66727D")),
                    showgrid=True,
                    gridcolor="#EDF0F2",
                    tickfont=dict(size=10, color="#66727D"),
                ),
                yaxis=dict(autorange="reversed", showgrid=False, tickfont=dict(size=10, color="#66727D")),
            )
            st.plotly_chart(fig_clubs, use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

        with col_top_p:
            st.markdown(
                "<p style='font-weight: 700; color: #17212B; font-size: 0.95rem; font-family:\"Manrope\",sans-serif;'>Top 5 Most Valuable in League</p>",
                unsafe_allow_html=True,
            )
            top_5_league = (
                df_single.sort_values("historical_market_value", ascending=False)
                .drop_duplicates(subset=["player_id"])
                .head(5)
            )
            for idx, (_, r) in enumerate(top_5_league.iterrows()):
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
                render_scout_card(p_dict, key_suffix=f"l_top_{idx}")

    st.markdown("<hr style='border:none; border-top:1px solid #E2E6E9; margin: 1.25rem 0;'>", unsafe_allow_html=True)
    st.markdown(
        """
        <div style="margin-bottom: 0.8rem;">
            <h3 style="margin: 0; font-size: 1.15rem; font-weight: 800; color: #17212B; font-family:'Manrope',sans-serif;">
                📊 Calibrated Cross-League Strength Ratings
            </h3>
            <p style="margin: 0.2rem 0; color: #66727D; font-size: 0.85rem;">
                Scientifically calibrated using multi-season continental club results, eliminating arbitrary manual league coefficients.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    rows = []
    comp_names_map = {c["id"]: c["name"] for c in all_comps}
    comp_countries_map = {c["id"]: c["country"] for c in all_comps}

    for cid, s_info in ratings_dict.items():
        if isinstance(s_info, dict):
            rows.append(
                {
                    "Code": cid,
                    "League": comp_names_map.get(cid, cid),
                    "Country": comp_countries_map.get(cid, "Global"),
                    "Mean Elo": round(s_info.get("overall_mean_elo", 1500.0), 1),
                    "Top 4 Elo": round(s_info.get("overall_top4_elo", 1500.0), 1),
                    "Relative Strength": round(s_info.get("normalized_strength", 1.0), 4),
                    "Continental Matches": s_info.get("cross_league_matches", 0),
                    "Verified Evidence": "✓ Confirmed" if s_info.get("has_cross_league_evidence") else "Baseline",
                }
            )

    if rows:
        elo_df = pd.DataFrame(rows).sort_values("Mean Elo", ascending=False)
        st.dataframe(
            elo_df,
            column_config={
                "Relative Strength": st.column_config.ProgressColumn(
                    "Relative Strength",
                    min_value=0.9,
                    max_value=1.15,
                    format="%.4f",
                ),
            },
            hide_index=True,
            use_container_width=True,
        )
