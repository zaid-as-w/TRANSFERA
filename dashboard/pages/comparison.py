"""Player Comparison Page: TRANSFERA Side-by-Side Scout Cards, Overlay Radar, and Stat Breakdown."""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dashboard.components.charts import CHART_THEME
from dashboard.components.header import render_header
from dashboard.components.player_card import render_scout_card
from dashboard.data_service import DataService
from dashboard.formatting import format_currency_eur
from dashboard.prediction_service import DashboardPredictionService


def _calculate_player_radar_metrics(player_row: pd.Series, df_all: pd.DataFrame) -> dict[str, float]:
    """Calculate 0-100 normalized radar metrics against all players."""
    metrics = {
        "Finishing": 50.0,
        "Playmaking": 50.0,
        "Involvement": 50.0,
        "Availability": 50.0,
        "Discipline": 50.0,
    }
    if len(df_all) == 0:
        return metrics

    try:
        g90 = float(player_row.get("goals_per_90", 0.0))
        metrics["Finishing"] = float(np.clip((df_all["goals_per_90"].dropna() < g90).mean() * 100, 10, 99))

        a90 = float(player_row.get("assists_per_90", 0.0))
        metrics["Playmaking"] = float(np.clip((df_all["assists_per_90"].dropna() < a90).mean() * 100, 10, 99))

        ga = float(player_row.get("goals", 0) + player_row.get("assists", 0))
        metrics["Involvement"] = float(
            np.clip(((df_all["goals"] + df_all["assists"]).dropna() < ga).mean() * 100, 10, 99)
        )

        mins = float(player_row.get("minutes_played", 0))
        metrics["Availability"] = float(np.clip((df_all["minutes_played"].dropna() < mins).mean() * 100, 10, 99))

        cards = float(player_row.get("cards", 0))
        metrics["Discipline"] = float(np.clip((df_all["cards"].dropna() > cards).mean() * 100, 10, 99))
    except Exception:
        pass

    return metrics


def render_comparison_page(data_service: DataService, pred_service: DashboardPredictionService) -> None:
    """Render the Player Comparison view in clean light style."""
    all_comps = data_service.get_competitions()
    render_header(all_comps)

    st.markdown(
        """
        <div style="margin-bottom: 1.25rem;">
            <div style="font-size:0.72rem;font-weight:700;letter-spacing:1px;color:#02BFD0;text-transform:uppercase;font-family:'Inter',sans-serif;">TRANSFERA SCOUTING ARENA</div>
            <h1 style="margin: 0.2rem 0; font-size: 1.9rem; font-weight: 800; letter-spacing: -0.5px; text-transform:uppercase; font-family:'Manrope',sans-serif; color:#17212B;">
                PLAYER <span style="color:#02BFD0;">COMPARISON</span>
            </h1>
            <p style="margin: 0.2rem 0 1rem 0; color: #66727D; font-size: 0.92rem;">
                Compare elite football talents head-to-head across market valuations, performance metrics, and scouting radar profiles.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    seasons = data_service.get_seasons()
    sel_season = st.selectbox("Season", seasons, index=0, key="comp_season_sel")
    df_season = data_service.filter_data(season=sel_season)

    top_candidates = (
        df_season.sort_values("historical_market_value", ascending=False).drop_duplicates(subset=["player_id"]).head(80)
    )
    player_options = {
        int(
            r["player_id"]
        ): f"{r['name']} ({r['current_club_name']}) — {format_currency_eur(r['historical_market_value'])}"
        for _, r in top_candidates.iterrows()
    }

    keys_list = list(player_options.keys())
    default_selections = keys_list[:2] if len(keys_list) >= 2 else keys_list

    selected_pids = st.multiselect(
        "Select 2 to 4 Players to Compare",
        options=keys_list,
        default=default_selections,
        format_func=lambda pid: player_options[pid],
        max_selections=4,
        key="compare_multiselect",
    )

    if len(selected_pids) < 2:
        st.info("Please select at least 2 players to view head-to-head comparison.")
        return

    selected_players = []
    for pid in selected_pids:
        rows = df_season[df_season["player_id"] == pid]
        if len(rows) > 0:
            selected_players.append(rows.iloc[0])

    st.markdown("<hr style='border:none; border-top:1px solid #E2E6E9; margin: 1.25rem 0;'>", unsafe_allow_html=True)
    card_cols = st.columns(len(selected_players))

    for idx, (col, r) in enumerate(zip(card_cols, selected_players, strict=False)):
        with col:
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
            render_scout_card(p_dict, key_suffix=f"cmp_{idx}")

    st.markdown("<hr style='border:none; border-top:1px solid #E2E6E9; margin: 1.25rem 0;'>", unsafe_allow_html=True)
    col_radar, col_stats = st.columns([1.2, 1.2])

    colors = ["#02BFD0", "#3185C7", "#20A56B", "#E5A52B"]

    with col_radar:
        st.markdown('<div class="tm-card">', unsafe_allow_html=True)
        st.markdown(
            "<p style='font-weight: 700; color: #17212B; font-size: 0.95rem; font-family:\"Manrope\",sans-serif;'>Scouting Radar Overlay</p>",
            unsafe_allow_html=True,
        )
        fig_radar = go.Figure()

        for idx, r in enumerate(selected_players):
            metrics = _calculate_player_radar_metrics(r, df_season)
            categories = list(metrics.keys())
            values = list(metrics.values())
            categories_closed = categories + [categories[0]]
            values_closed = values + [values[0]]
            c = colors[idx % len(colors)]

            fig_radar.add_trace(
                go.Scatterpolar(
                    r=values_closed,
                    theta=categories_closed,
                    name=r["name"],
                    line=dict(color=c, width=2.5),
                    marker=dict(size=5),
                    fill="toself",
                    fillcolor=f"rgba{tuple(list(bytes.fromhex(c.replace('#', ''))) + [0.12])}",
                )
            )

        fig_radar.update_layout(
            **CHART_THEME,
            polar=dict(
                radialaxis=dict(visible=True, range=[0, 100], showticklabels=False, linecolor="#EDF0F2"),
                angularaxis=dict(linecolor="#E2E6E9", tickfont=dict(size=10, color="#66727D")),
                bgcolor="#F8F9FA",
            ),
            legend=dict(orientation="h", y=1.15, x=0.5, xanchor="center", font=dict(size=10, color="#66727D")),
            height=380,
        )
        st.plotly_chart(fig_radar, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with col_stats:
        st.markdown('<div class="tm-card">', unsafe_allow_html=True)
        st.markdown(
            "<p style='font-weight: 700; color: #17212B; font-size: 0.95rem; font-family:\"Manrope\",sans-serif;'>Head-to-Head Statistics</p>",
            unsafe_allow_html=True,
        )

        rows = []
        for r in selected_players:
            rows.append(
                {
                    "Player": r["name"],
                    "Club": r.get("current_club_name", "Unknown"),
                    "Age": round(float(r.get("age_at_reference_date", 24.0)), 1),
                    "Market Value": format_currency_eur(r["historical_market_value"]),
                    "Goals": int(r.get("goals", 0)),
                    "Assists": int(r.get("assists", 0)),
                    "Minutes": f"{int(r.get('minutes_played', 0)):,}",
                    "G+A / 90": round(float(r.get("goals_per_90", 0.0) + r.get("assists_per_90", 0.0)), 2),
                }
            )

        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

        st.markdown(
            "<p style='font-weight: 700; color: #02BFD0; font-size: 0.88rem; margin-top: 1rem;'>⚡ TRANSFERA Model Valuation Comparison</p>",
            unsafe_allow_html=True,
        )
        pred_rows = []
        for r in selected_players:
            res = pred_service.predict_player_record(r.to_dict())
            diff = res.predicted_value_eur - float(r["historical_market_value"])
            pred_rows.append(
                {
                    "Player": r["name"],
                    "Actual Value": format_currency_eur(r["historical_market_value"]),
                    "Predicted Value": format_currency_eur(res.predicted_value_eur),
                    "Difference": f"{diff:+,.0f} €",
                }
            )
        st.dataframe(pd.DataFrame(pred_rows), hide_index=True, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
