"""Players Page: TRANSFERA Player Explorer, Scouting Cards, Historical Valuations, and Radar Analysis."""

import numpy as np
import pandas as pd
import streamlit as st

from dashboard.components.charts import (
    render_historical_valuation_line,
    render_player_radar,
)
from dashboard.components.header import render_header
from dashboard.components.player_card import render_scout_card
from dashboard.data_service import DataService
from dashboard.formatting import format_currency_eur
from dashboard.prediction_service import DashboardPredictionService


def _calculate_player_radar_metrics(player_row: pd.Series, df_pos: pd.DataFrame) -> dict[str, float]:
    """Calculate percentile ranking (0-100) for player radar within their position group."""
    metrics = {
        "Finishing": 50.0,
        "Playmaking": 50.0,
        "Involvement": 50.0,
        "Availability": 50.0,
        "Discipline": 50.0,
    }
    if len(df_pos) == 0:
        return metrics

    try:
        g90 = float(player_row.get("goals_per_90", 0.0))
        g_series = df_pos["goals_per_90"].dropna()
        metrics["Finishing"] = float(np.clip((g_series < g90).mean() * 100, 10, 99))

        a90 = float(player_row.get("assists_per_90", 0.0))
        a_series = df_pos["assists_per_90"].dropna()
        metrics["Playmaking"] = float(np.clip((a_series < a90).mean() * 100, 10, 99))

        ga = float(player_row.get("goals", 0) + player_row.get("assists", 0))
        ga_series = (df_pos["goals"] + df_pos["assists"]).dropna()
        metrics["Involvement"] = float(np.clip((ga_series < ga).mean() * 100, 10, 99))

        mins = float(player_row.get("minutes_played", 0))
        m_series = df_pos["minutes_played"].dropna()
        metrics["Availability"] = float(np.clip((m_series < mins).mean() * 100, 10, 99))

        cards = float(player_row.get("cards", 0))
        c_series = df_pos["cards"].dropna()
        metrics["Discipline"] = float(np.clip((c_series > cards).mean() * 100, 10, 99))
    except Exception:
        pass

    return metrics


def render_players_page(data_service: DataService, pred_service: DashboardPredictionService) -> None:
    """Render the Player Explorer page in TRANSFERA clean light style."""
    all_comps = data_service.get_competitions()
    hdr_state = render_header(all_comps)

    st.markdown(
        """
        <div style="margin-bottom: 1.25rem;">
            <div style="font-size:0.72rem;font-weight:700;letter-spacing:1px;color:#02BFD0;text-transform:uppercase;font-family:'Inter',sans-serif;">TRANSFERA SCOUTING CONSOLE</div>
            <h1 style="margin: 0.2rem 0; font-size: 1.9rem; font-weight: 800; letter-spacing: -0.5px; text-transform:uppercase; font-family:'Manrope',sans-serif; color:#17212B;">
                PLAYER <span style="color:#02BFD0;">EXPLORER</span>
            </h1>
            <p style="margin: 0.2rem 0 1rem 0; color: #66727D; font-size: 0.92rem;">
                Browse, scout, and analyze professional players across Europe's top leagues and verified global competitions.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c_season, c_pos, c_age, c_search = st.columns([1, 1, 1.2, 1.8])
    seasons = data_service.get_seasons()

    with c_season:
        sel_season = st.selectbox("Season", seasons, index=0, key="players_season_sel")
    with c_pos:
        sel_pos = st.selectbox(
            "Position", ["ALL", "Attack", "Midfield", "Defender", "Goalkeeper"], index=0, key="players_pos_sel"
        )
    with c_age:
        age_range = st.slider("Age Range", min_value=16, max_value=40, value=(18, 36), key="players_age_slider")
    with c_search:
        search_input = st.text_input(
            "🔍 Quick Player / Club Search",
            placeholder="e.g. Bellingham, Real Madrid, Saka...",
            key="players_text_search",
        )

    df_filtered = data_service.filter_data(
        season=sel_season,
        competition_id=hdr_state["selected_league"] if hdr_state["selected_league"] != "ALL" else None,
        country=hdr_state["selected_country"] if hdr_state["selected_country"] != "ALL" else None,
        position=sel_pos if sel_pos != "ALL" else None,
        age_range=age_range,
    )

    if search_input and len(search_input.strip()) >= 2:
        q = search_input.strip().lower()
        mask = (
            df_filtered["name"].str.lower().str.contains(q, na=False)
            | df_filtered["current_club_name"].str.lower().str.contains(q, na=False)
            | df_filtered["country_of_citizenship"].str.lower().str.contains(q, na=False)
        )
        df_display = df_filtered[mask]

        # If not present in active season, search across all historical seasons
        if len(df_display) == 0:
            all_source = data_service.df
            mask_all = (
                all_source["name"].str.lower().str.contains(q, na=False)
                | all_source["current_club_name"].str.lower().str.contains(q, na=False)
                | all_source["country_of_citizenship"].str.lower().str.contains(q, na=False)
            )
            df_display = (
                all_source[mask_all].sort_values("season", ascending=False).drop_duplicates(subset=["player_id"])
            )
    else:
        df_display = df_filtered

    st.markdown(
        f"<p style='color: #66727D; font-size: 0.82rem; margin-bottom: 0.8rem;'>"
        f"Showing <b style='color:#02BFD0;'>{len(df_display):,}</b> active players matching filter parameters"
        f"</p>",
        unsafe_allow_html=True,
    )

    if len(df_display) == 0:
        st.warning("No players found matching current filter criteria. Try broadening your filters.")
        return

    top_candidates = df_display.sort_values("historical_market_value", ascending=False).head(100)
    player_options = {
        int(
            r["player_id"]
        ): f"{r['name']} ({r['current_club_name']}) — {format_currency_eur(r['historical_market_value'])}"
        for _, r in top_candidates.iterrows()
    }

    default_pid = int(top_candidates.iloc[0]["player_id"])
    if "selected_player_id" not in st.session_state or st.session_state["selected_player_id"] not in player_options:
        st.session_state["selected_player_id"] = default_pid

    sel_pid = st.selectbox(
        "Select Player for Deep Profile & Scouting Breakdown",
        options=list(player_options.keys()),
        format_func=lambda pid: player_options[pid],
        index=list(player_options.keys()).index(st.session_state["selected_player_id"])
        if st.session_state["selected_player_id"] in player_options
        else 0,
        key="player_inspect_selector",
    )
    st.session_state["selected_player_id"] = sel_pid

    selected_row = df_display[df_display["player_id"] == sel_pid].iloc[0]
    pid = int(selected_row["player_id"])
    p_name = str(selected_row["name"])
    club_name = str(selected_row.get("current_club_name", "Unknown Club"))
    club_id = int(selected_row.get("club_id", 0)) if pd.notna(selected_row.get("club_id")) else None
    pos = str(selected_row.get("position", "Attack"))
    sub_pos = str(selected_row.get("sub_position", "Unknown"))
    age = float(selected_row.get("age_at_reference_date", 24.0))
    val_eur = float(selected_row.get("historical_market_value", 0.0))

    col_card, col_history, col_radar = st.columns([1.1, 1.4, 1.1])

    with col_card:
        player_dict = {
            "player_id": pid,
            "name": p_name,
            "current_club_name": club_name,
            "club_id": club_id,
            "position": pos,
            "sub_position": sub_pos,
            "country_of_citizenship": str(selected_row.get("country_of_citizenship", "Unknown")),
            "age": age,
            "goals": int(selected_row.get("goals", 0)),
            "assists": int(selected_row.get("assists", 0)),
            "market_value_eur": val_eur,
            "image_url": data_service.image_map.get(pid),
        }
        render_scout_card(player_dict)

        if st.button(
            "💎 Predict Market Value in Hero Predictor", key="btn_goto_pred", use_container_width=True, type="primary"
        ):
            st.session_state["active_page"] = "Value Predictor"
            st.session_state["predictor_selected_player_name"] = p_name
            st.session_state["predictor_selected_player_id"] = pid
            st.rerun()

        st.markdown(
            f"""
            <div class="tm-card" style="padding: 0.85rem; margin-top: 0.8rem;">
                <div style="font-size: 0.72rem; color: #8A959E; font-weight: 700; margin-bottom: 0.4rem; text-transform: uppercase;">Technical Attributes</div>
                <div style="display: flex; justify-content: space-between; font-size: 0.85rem; padding: 0.3rem 0; border-bottom: 1px solid #EDF0F2;">
                    <span style="color: #66727D;">Sub-Position</span>
                    <span style="color: #17212B; font-weight: 600;">{sub_pos}</span>
                </div>
                <div style="display: flex; justify-content: space-between; font-size: 0.85rem; padding: 0.3rem 0; border-bottom: 1px solid #EDF0F2;">
                    <span style="color: #66727D;">Preferred Foot</span>
                    <span style="color: #17212B; font-weight: 600;">{selected_row.get("foot", "Unknown")}</span>
                </div>
                <div style="display: flex; justify-content: space-between; font-size: 0.85rem; padding: 0.3rem 0; border-bottom: 1px solid #EDF0F2;">
                    <span style="color: #66727D;">Height</span>
                    <span style="color: #17212B; font-weight: 600;">{selected_row.get("height_in_cm", 182)} cm</span>
                </div>
                <div style="display: flex; justify-content: space-between; font-size: 0.85rem; padding: 0.3rem 0;">
                    <span style="color: #66727D;">Minutes Played</span>
                    <span style="color: #02BFD0; font-weight: 700;">{int(selected_row.get("minutes_played", 0)):,}</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_history:
        st.markdown('<div class="tm-card">', unsafe_allow_html=True)
        history_df = data_service.get_player_history(pid)
        fig_hist = render_historical_valuation_line(history_df)
        st.plotly_chart(fig_hist, use_container_width=True)

        st.markdown(
            f"""
            <div style="padding-top: 0.8rem; margin-top: 0.6rem; border-top: 1px solid #EDF0F2;">
                <div style="font-size: 0.72rem; color: #02BFD0; font-weight: 700; margin-bottom: 0.6rem; text-transform: uppercase;">Season {sel_season} Performance Summary</div>
                <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.5rem; text-align: center;">
                    <div style="background: #F8F9FA; border-radius: 6px; padding: 0.5rem; border:1px solid #EDF0F2;">
                        <div style="font-size: 0.65rem; color: #8A959E; font-weight:700;">MATCHES</div>
                        <div style="font-size: 1.15rem; font-weight: 800; color: #17212B; font-family:'Manrope',sans-serif;">{int(selected_row.get("appearances", 0))}</div>
                    </div>
                    <div style="background: #F8F9FA; border-radius: 6px; padding: 0.5rem; border:1px solid #EDF0F2;">
                        <div style="font-size: 0.65rem; color: #8A959E; font-weight:700;">GOALS</div>
                        <div style="font-size: 1.15rem; font-weight: 800; color: #02BFD0; font-family:'Manrope',sans-serif;">{int(selected_row.get("goals", 0))}</div>
                    </div>
                    <div style="background: #F8F9FA; border-radius: 6px; padding: 0.5rem; border:1px solid #EDF0F2;">
                        <div style="font-size: 0.65rem; color: #8A959E; font-weight:700;">ASSISTS</div>
                        <div style="font-size: 1.15rem; font-weight: 800; color: #20A56B; font-family:'Manrope',sans-serif;">{int(selected_row.get("assists", 0))}</div>
                    </div>
                    <div style="background: #F8F9FA; border-radius: 6px; padding: 0.5rem; border:1px solid #EDF0F2;">
                        <div style="font-size: 0.65rem; color: #8A959E; font-weight:700;">G+A / 90</div>
                        <div style="font-size: 1.15rem; font-weight: 800; color: #3185C7; font-family:'Manrope',sans-serif;">{(selected_row.get("goals_per_90", 0.0) + selected_row.get("assists_per_90", 0.0)):.2f}</div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

    with col_radar:
        st.markdown('<div class="tm-card">', unsafe_allow_html=True)
        df_pos = df_filtered[df_filtered["position"] == pos]
        radar_metrics = _calculate_player_radar_metrics(selected_row, df_pos)
        fig_radar = render_player_radar(radar_metrics, title=f"{pos} Peer Percentiles")
        st.plotly_chart(fig_radar, use_container_width=True)

        st.caption(
            "Percentile ranking (0-100) benchmarked against all registered players in the same positional group."
        )
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<hr style='border:none; border-top:1px solid #E2E6E9; margin: 1.25rem 0;'>", unsafe_allow_html=True)

    st.markdown(
        """
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.8rem;">
            <h3 style="margin: 0; font-size: 1.15rem; font-weight: 800; color: #17212B; font-family:'Manrope',sans-serif;">
                Top Scouting Prospects In View
            </h3>
            <span style="font-size: 0.78rem; color: #8A959E;">Click any player to inspect profile</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    top_12 = df_display.sort_values("historical_market_value", ascending=False).head(12)
    grid_cols = st.columns(4)

    for idx, (_, r) in enumerate(top_12.iterrows()):
        col_idx = idx % 4
        with grid_cols[col_idx]:
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
            render_scout_card(p_dict, key_suffix=f"grid_{idx}")
            if st.button(f"Inspect {r['name'].split()[-1]}", key=f"btn_inspect_{idx}", use_container_width=True):
                st.session_state["selected_player_id"] = int(r["player_id"])
                st.rerun()
