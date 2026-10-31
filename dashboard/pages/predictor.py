"""TRANSFERA — Hero Transfer Value Predictor Page.

Provides Mode A (Existing Player Search & Prediction), Mode B (Custom Player Simulation),
and Cross-League Transfer Scenario analysis, directly powered by the Stage 1 ValuationPredictor.
"""

import pandas as pd
import streamlit as st

from dashboard.components.header import render_header
from dashboard.components.prediction_card import render_prediction_card
from dashboard.data_service import DataService
from dashboard.formatting import format_currency_eur, format_delta_eur, format_delta_pct
from dashboard.global_player_profile import render_global_player_profile
from dashboard.image_service import get_club_crest_url, get_player_image_url
from dashboard.prediction_service import DashboardPredictionService


def render_predictor_page(data_service: DataService, pred_service: DashboardPredictionService) -> None:
    """Render the Hero Transfer Value Predictor page in clean light style."""
    # Top header
    all_comps = data_service.get_competitions()
    hdr_state = render_header(all_comps)
    hdr_search = (hdr_state.get("search_query") or "").strip()

    # Hero Banner
    banner_html = (
        '<div class="tm-card" style="padding:1.4rem 1.6rem;margin-bottom:1.25rem;">'
        '<div style="display:flex;justify-content:space-between;align-items:flex-start;">'
        "<div>"
        "<div style=\"font-size:0.72rem;font-weight:700;letter-spacing:1px;color:#02BFD0;text-transform:uppercase;font-family:'Inter',sans-serif;\">TRANSFERA INTELLIGENCE ENGINE</div>"
        "<h1 style=\"margin:0.2rem 0;font-size:2rem;font-weight:800;letter-spacing:-0.5px;text-transform:uppercase;font-family:'Manrope',sans-serif;color:#17212B;\">"
        'TRANSFER VALUE <span style="color:#02BFD0;">PREDICTOR</span>'
        "</h1>"
        '<p style="margin:0.2rem 0 0.8rem 0;color:#66727D;font-size:0.92rem;line-height:1.4;">'
        "Discover the market value behind every player using genuine historical football performance and machine learning."
        "</p>"
        "</div>"
        '<div style="background:#F8F9FA;border:1px solid #E2E6E9;border-radius:6px;padding:0.5rem 0.9rem;text-align:center;">'
        '<div style="font-size:0.65rem;color:#8A959E;font-weight:700;letter-spacing:0.8px;text-transform:uppercase;">Engine Status</div>'
        '<div style="font-size:0.82rem;color:#20A56B;font-weight:700;display:flex;align-items:center;gap:0.35rem;margin-top:2px;">'
        '<span style="display:inline-block;width:6px;height:6px;border-radius:50%;background:#20A56B;"></span>'
        "Online (HGB Champion)"
        "</div>"
        "</div>"
        "</div>"
        "</div>"
    )
    st.markdown(banner_html, unsafe_allow_html=True)

    # Persistent Mode Switcher using modern segmented control
    mode_options = [
        "🔍 Predict Existing Player",
        "⚙️ Custom Player Simulation",
        "🌐 Cross-League Transfer Scenario",
    ]
    if "predictor_active_mode" not in st.session_state:
        st.session_state["predictor_active_mode"] = mode_options[0]

    selected_mode = st.segmented_control(
        "Predictor Mode",
        options=mode_options,
        default=st.session_state.get("predictor_active_mode", mode_options[0]),
        label_visibility="collapsed",
        key="predictor_mode_segmented_ctrl",
    )
    if not selected_mode:
        selected_mode = st.session_state.get("predictor_active_mode", mode_options[0])
    st.session_state["predictor_active_mode"] = selected_mode

    st.markdown('<div style="height:0.8rem;"></div>', unsafe_allow_html=True)

    popular_names = [
        "Erling Haaland",
        "Lionel Messi",
        "Cristiano Ronaldo",
        "Kylian Mbappé",
        "Jude Bellingham",
        "Vinicius Junior",
        "Bukayo Saka",
        "Phil Foden",
        "Florian Wirtz",
        "Jamal Musiala",
        "Declan Rice",
        "Rodri",
        "Cole Palmer",
        "Lamine Yamal",
        "Harry Kane",
        "Martin Ødegaard",
        "Federico Valverde",
    ]

    # -------------------------------------------------------------
    # MODE A: PREDICT EXISTING PLAYER
    # -------------------------------------------------------------
    if selected_mode == "🔍 Predict Existing Player":
        st.markdown(
            "<p style='color:#66727D;font-size:0.88rem;margin-bottom:0.8rem;'>Select any registered player from verified datasets to inspect actual recorded market value against the ML model's benchmark valuation.</p>",
            unsafe_allow_html=True,
        )

        col_select, col_meta = st.columns([2, 1])

        with col_select:
            pre_name = st.session_state.get("predictor_selected_player_name")
            active_q = pre_name or hdr_search or ""
            search_query = st.text_input(
                "Search Player by Name",
                value=active_q,
                placeholder="Search players, clubs, leagues or countries (e.g. Haaland, Mbappe, Real Madrid)...",
                key="pred_mode_a_search",
            )

            df_latest = data_service.filter_data(season=2023)
            selected_match = None
            is_global_match = False

            if search_query and len(search_query.strip()) >= 2:
                # Two-Stage Search: Stage 1 first, global fallback ONLY on 0 matches
                stage_matches, search_msg = data_service.search_players_two_stage(search_query, limit=20)
                if not stage_matches:
                    st.warning("No matching players found in the existing database or global player catalog.")
                    selected_match = None
                else:
                    player_choices = {
                        idx: f"[{m.source_database}] {m.name} ({m.current_club_name} · {m.position} · {m.nationality})"
                        for idx, m in enumerate(stage_matches)
                    }
                    sel_idx = st.selectbox(
                        "Choose Player Record",
                        options=list(player_choices.keys()),
                        format_func=lambda i: player_choices[i],
                        key="pred_player_select_dropdown",
                    )
                    selected_match = stage_matches[sel_idx]
                    is_global_match = selected_match.source_database == "GLOBAL DATABASE"
            else:
                # Default popular players across active and historical seasons
                base_matches = []
                for name in popular_names:
                    m = data_service.search_players(name, df_latest, limit=1)
                    if not m:
                        m = data_service.search_players(name, None, limit=1)
                    if m:
                        base_matches.append(m[0])

                if base_matches:
                    player_choices = {
                        idx: f"[STAGE 1 DATABASE] {m['name']} ({m['current_club_name']} · {m['position']} · Season {m['season']})"
                        for idx, m in enumerate(base_matches)
                    }
                    sel_idx = st.selectbox(
                        "Choose Player Record",
                        options=list(player_choices.keys()),
                        format_func=lambda i: player_choices[i],
                        key="pred_player_select_dropdown",
                    )
                    selected_match = base_matches[sel_idx]
                    is_global_match = False

        with col_meta:
            if selected_match:
                if is_global_match:
                    p_name = selected_match.name
                    c_name = selected_match.current_club_name
                    img_url = (
                        selected_match.image_url or "https://images.unsplash.com/photo-1508098682722-e99c43a406b2?w=300"
                    )
                    meta_html = (
                        f'<div class="tm-card" style="padding:1rem;text-align:center;">'
                        f'<img src="{img_url}" style="width:70px;height:70px;border-radius:50%;object-fit:cover;border:2px solid #FFE082;margin-bottom:0.4rem;" onerror="this.onerror=null; this.src=\'https://images.unsplash.com/photo-1508098682722-e99c43a406b2?w=300\';"/>'
                        f"<div style=\"font-weight:700;font-size:1rem;color:#17212B;font-family:'Manrope',sans-serif;\">{p_name}</div>"
                        f'<div style="font-size:0.75rem;color:#B26A00;margin-top:0.2rem;font-weight:600;">GLOBAL CATALOG RECORD</div>'
                        f'<div style="font-size:0.78rem;color:#66727D;">{c_name}</div>'
                        f"</div>"
                    )
                    st.markdown(meta_html, unsafe_allow_html=True)
                else:
                    pid_val = (
                        selected_match["player_id"] if isinstance(selected_match, dict) else selected_match.player_id
                    )
                    p_name = selected_match["name"] if isinstance(selected_match, dict) else selected_match.name
                    c_name = (
                        selected_match.get("current_club_name")
                        if isinstance(selected_match, dict)
                        else selected_match.current_club_name
                    )
                    c_id = selected_match.get("club_id") if isinstance(selected_match, dict) else None
                    img_url = get_player_image_url(
                        pid_val, selected_match.get("image_url") if isinstance(selected_match, dict) else None
                    )
                    crest_url = get_club_crest_url(c_id)
                    meta_html = (
                        f'<div class="tm-card" style="padding:1rem;text-align:center;">'
                        f'<img src="{img_url}" style="width:70px;height:70px;border-radius:50%;object-fit:cover;border:2px solid #02BFD0;margin-bottom:0.4rem;" onerror="this.onerror=null; this.src=\'https://images.unsplash.com/photo-1508098682722-e99c43a406b2?w=300\';"/>'
                        f"<div style=\"font-weight:700;font-size:1rem;color:#17212B;font-family:'Manrope',sans-serif;\">{p_name}</div>"
                        f'<div style="display:flex;align-items:center;justify-content:center;gap:0.4rem;margin-top:0.2rem;">'
                        f'<img src="{crest_url}" style="width:16px;height:16px;object-fit:contain;" onerror="this.style.display=\'none\';"/>'
                        f'<span style="font-size:0.78rem;color:#66727D;">{c_name}</span>'
                        f"</div>"
                        f"</div>"
                    )
                    st.markdown(meta_html, unsafe_allow_html=True)

        if selected_match:
            sep_html = '<hr style="border:none;border-top:1px solid #E2E6E9;margin:1rem 0;"/>'
            st.markdown(sep_html, unsafe_allow_html=True)

            if is_global_match:
                # Render Global Profile and Coverage Diagnostics
                bundle = data_service.get_player_profile_bundle(selected_match.player_id)
                if bundle:
                    render_global_player_profile(
                        player=bundle["record"],
                        assessment=bundle["assessment"],
                        stats=bundle["stats"],
                        valuations=bundle["valuations"],
                    )
            else:
                # Stage 1 Player Record Execution
                col_form, col_pred_card = st.columns([1.3, 1.0])

                # Get rich Stage 1 player dict
                if isinstance(selected_match, dict):
                    stage1_dict = selected_match
                else:
                    try:
                        pid_int = int(selected_match.player_id)
                        sub_p = data_service.df[data_service.df["player_id"] == pid_int].sort_values(
                            "season", ascending=False
                        )
                    except (ValueError, TypeError):
                        sub_p = pd.DataFrame()

                    if not sub_p.empty:
                        r_latest = sub_p.iloc[0]
                        stage1_dict = {
                            "player_id": pid_int,
                            "name": str(r_latest["name"]),
                            "current_club_name": str(r_latest.get("current_club_name", "Unknown")),
                            "club_id": int(r_latest.get("club_id", 0)) if pd.notna(r_latest.get("club_id")) else None,
                            "competition_id": str(r_latest.get("competition_id", "GB1")),
                            "position": str(r_latest.get("position", "Attack")),
                            "sub_position": str(r_latest.get("sub_position", "Unknown")),
                            "age": round(float(r_latest.get("age_at_reference_date", 24.0)), 1),
                            "goals": int(r_latest.get("goals", 0)),
                            "assists": int(r_latest.get("assists", 0)),
                            "appearances": int(r_latest.get("appearances", 0)),
                            "minutes_played": int(r_latest.get("minutes_played", 0)),
                            "market_value_eur": float(r_latest.get("historical_market_value", 0.0)),
                            "previous_market_value": float(r_latest.get("previous_market_value", 0.0))
                            if pd.notna(r_latest.get("previous_market_value"))
                            else None,
                            "season": int(r_latest.get("season", 2023)),
                            "image_url": data_service.image_map.get(pid_int),
                        }
                    else:
                        found = data_service.search_players(selected_match.name, None, limit=1)
                        stage1_dict = found[0] if found else None

                if stage1_dict:
                    with col_form:
                        st.markdown(
                            '<div style="display:flex;gap:0.5rem;align-items:center;margin-bottom:0.6rem;">'
                            '<span style="background:#E5F9FB;border:1px solid rgba(2,191,208,0.4);color:#018591;font-size:0.72rem;font-weight:700;padding:0.25rem 0.6rem;border-radius:4px;">◈ STAGE 1 DATABASE</span>'
                            '<span style="background:#E8F8F1;border:1px solid #A5E4C7;color:#178352;font-size:0.72rem;font-weight:700;padding:0.25rem 0.6rem;border-radius:4px;">● PREDICTION AVAILABLE</span>'
                            "</div>",
                            unsafe_allow_html=True,
                        )
                        st.markdown(
                            '<div style="font-size:0.82rem;color:#02BFD0;font-weight:700;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:0.6rem;">Verified Input Features</div>',
                            unsafe_allow_html=True,
                        )

                        stat_box_html = (
                            f'<div class="tm-card" style="padding:1.1rem;">'
                            f'<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:0.6rem;margin-bottom:0.8rem;">'
                            f'<div style="background:#F8F9FA;padding:0.6rem;border-radius:6px;border:1px solid #EDF0F2;"><div style="font-size:0.68rem;color:#8A959E;font-weight:700;">AGE</div><div style="font-size:1.1rem;font-weight:800;color:#17212B;font-family:\'Manrope\',sans-serif;">{stage1_dict["age"]}</div></div>'
                            f'<div style="background:#F8F9FA;padding:0.6rem;border-radius:6px;border:1px solid #EDF0F2;"><div style="font-size:0.68rem;color:#8A959E;font-weight:700;">POSITION</div><div style="font-size:1.1rem;font-weight:800;color:#17212B;font-family:\'Manrope\',sans-serif;">{stage1_dict["position"]}</div></div>'
                            f'<div style="background:#F8F9FA;padding:0.6rem;border-radius:6px;border:1px solid #EDF0F2;"><div style="font-size:0.68rem;color:#8A959E;font-weight:700;">COMPETITION</div><div style="font-size:1.1rem;font-weight:800;color:#02BFD0;font-family:\'Manrope\',sans-serif;">{stage1_dict["competition_id"]}</div></div>'
                            f'<div style="background:#F8F9FA;padding:0.6rem;border-radius:6px;border:1px solid #EDF0F2;"><div style="font-size:0.68rem;color:#8A959E;font-weight:700;">APPEARANCES</div><div style="font-size:1.1rem;font-weight:800;color:#17212B;font-family:\'Manrope\',sans-serif;">{stage1_dict["appearances"]}</div></div>'
                            f'<div style="background:#F8F9FA;padding:0.6rem;border-radius:6px;border:1px solid #EDF0F2;"><div style="font-size:0.68rem;color:#8A959E;font-weight:700;">MINUTES</div><div style="font-size:1.1rem;font-weight:800;color:#17212B;font-family:\'Manrope\',sans-serif;">{stage1_dict["minutes_played"]:,}</div></div>'
                            f'<div style="background:#F8F9FA;padding:0.6rem;border-radius:6px;border:1px solid #EDF0F2;"><div style="font-size:0.68rem;color:#8A959E;font-weight:700;">GOALS + AST</div><div style="font-size:1.1rem;font-weight:800;color:#20A56B;font-family:\'Manrope\',sans-serif;">{stage1_dict["goals"]}G / {stage1_dict["assists"]}A</div></div>'
                            f"</div>"
                            f"</div>"
                        )
                        st.markdown(stat_box_html, unsafe_allow_html=True)

                        run_mode_a = st.button(
                            "💎 Run TRANSFERA Valuation Engine",
                            key="btn_run_mode_a",
                            type="primary",
                            use_container_width=True,
                        )

                    with col_pred_card:
                        if run_mode_a or "last_mode_a_result" not in st.session_state:
                            with st.spinner("Executing HistGradientBoosting valuation engine..."):
                                res = pred_service.predict_player_record(stage1_dict)
                                st.session_state["last_mode_a_result"] = res

                        res = st.session_state["last_mode_a_result"]
                        render_prediction_card(
                            res,
                            actual_value_eur=stage1_dict["market_value_eur"],
                            club_id=stage1_dict.get("club_id"),
                            club_name=stage1_dict.get("current_club_name"),
                        )
                else:
                    st.info("Selected player record does not have full match features in the active season.")

    # -------------------------------------------------------------
    # MODE B: CUSTOM PLAYER SIMULATION (SIDE-BY-SIDE REACTIVE)
    # -------------------------------------------------------------
    elif selected_mode == "⚙️ Custom Player Simulation":
        st.markdown(
            "<p style='color:#66727D;font-size:0.88rem;margin-bottom:0.8rem;'>Simulate hypothetical player profiles, emerging wonderkids, or custom transfer targets with instant reactive evaluation.</p>",
            unsafe_allow_html=True,
        )

        col_cust_inputs, col_cust_card = st.columns([1.3, 1.0])

        with col_cust_inputs:
            comp_dict = {c["id"]: f"{c['name']} ({c['country']})" for c in all_comps}

            # Group 1: Demographics & Physical
            st.markdown(
                '<div style="font-size:0.8rem;color:#02BFD0;font-weight:700;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:0.4rem;">1. Demographics & Position</div>',
                unsafe_allow_html=True,
            )
            r1_c1, r1_c2, r1_c3 = st.columns([1.2, 1, 1])
            with r1_c1:
                custom_age = st.slider("Age at Reference Date", 16.0, 40.0, 22.0, 0.5, key="cp_age")
            with r1_c2:
                custom_pos = st.selectbox(
                    "Position", ["Attack", "Midfield", "Defender", "Goalkeeper"], index=0, key="cp_pos"
                )
            with r1_c3:
                custom_foot = st.selectbox("Foot", ["right", "left", "both", "Unknown"], index=0, key="cp_foot")

            # Group 2: Match Load & Output
            st.markdown(
                '<div style="font-size:0.8rem;color:#02BFD0;font-weight:700;text-transform:uppercase;letter-spacing:0.5px;margin:0.8rem 0 0.4rem 0;">2. Match Performance & Form</div>',
                unsafe_allow_html=True,
            )
            r2_c1, r2_c2, r2_c3, r2_c4 = st.columns(4)
            with r2_c1:
                custom_goals = st.number_input("Goals", 0, 60, 14, 1, key="cp_goals")
            with r2_c2:
                custom_assists = st.number_input("Assists", 0, 40, 6, 1, key="cp_assists")
            with r2_c3:
                custom_mins = st.number_input("Minutes", 0, 4500, 2100, 50, key="cp_mins")
            with r2_c4:
                custom_apps = st.number_input("Matches", 0, 60, 28, 1, key="cp_apps")

            # Group 3: League & Financial Baseline
            st.markdown(
                '<div style="font-size:0.8rem;color:#02BFD0;font-weight:700;text-transform:uppercase;letter-spacing:0.5px;margin:0.8rem 0 0.4rem 0;">3. Competition & Valuation Context</div>',
                unsafe_allow_html=True,
            )
            r3_c1, r3_c2 = st.columns([1.2, 1])
            with r3_c1:
                custom_comp = st.selectbox(
                    "Competition / League",
                    options=list(comp_dict.keys()),
                    format_func=lambda cid: comp_dict[cid],
                    index=0,
                    key="cp_comp",
                )
            with r3_c2:
                custom_prior_m = st.number_input("Prior Market Value (€M)", 0.0, 200.0, 15.0, 1.0, key="cp_prior_m")

            st.markdown('<div style="height:0.8rem;"></div>', unsafe_allow_html=True)
            btn_run_custom = st.button(
                "⚡ Calculate Custom Player Valuation ➔",
                key="btn_run_custom_eval",
                type="primary",
                use_container_width=True,
            )

        with col_cust_card:
            cust_page_key = f"{custom_age}_{custom_pos}_{custom_foot}_{custom_goals}_{custom_assists}_{custom_mins}_{custom_apps}_{custom_comp}_{custom_prior_m}"
            if (
                btn_run_custom
                or "custom_page_cache_key" not in st.session_state
                or st.session_state.get("custom_page_cache_key") != cust_page_key
            ):
                with st.spinner("Evaluating custom player with champion model..."):
                    custom_prior_eur = (custom_prior_m * 1_000_000.0) if custom_prior_m > 0 else None
                    res_c = pred_service.predict_custom(
                        age=custom_age,
                        position=custom_pos,
                        foot=custom_foot,
                        appearances=custom_apps,
                        minutes_played=custom_mins,
                        goals=custom_goals,
                        assists=custom_assists,
                        competition_id=custom_comp,
                        previous_market_value=custom_prior_eur,
                        season=2023,
                    )
                    st.session_state["custom_pred_saved_res"] = res_c
                    st.session_state["custom_pred_saved_comp"] = custom_comp
                    st.session_state["custom_page_cache_key"] = cust_page_key
                    st.session_state["custom_page_saved_prior"] = custom_prior_eur

            res_display = st.session_state["custom_pred_saved_res"]
            comp_name = comp_dict.get(st.session_state.get("custom_pred_saved_comp", "GB1"), "Custom Squad")
            render_prediction_card(
                result=res_display,
                actual_value_eur=st.session_state.get("custom_page_saved_prior"),
                club_id=None,
                club_name=comp_name,
            )

    # -------------------------------------------------------------
    # MODE C: CROSS-LEAGUE TRANSFER SCENARIOS
    # -------------------------------------------------------------
    elif selected_mode == "🌐 Cross-League Transfer Scenario":
        st.markdown(
            """
            <div style="margin-bottom: 1rem;">
                <h3 style="margin: 0; font-size: 1.15rem; font-weight: 800; color: #17212B; font-family:'Manrope',sans-serif;">
                    🌐 Cross-League Move Simulator
                </h3>
                <p style="margin: 0.2rem 0 0.8rem 0; color: #66727D; font-size: 0.88rem;">
                    Simulate how a player's benchmark market valuation adjusts when transferring from one competition to another, accounting for league strength, competition tempo, and club context.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        xl_c1, xl_c2 = st.columns(2)

        with xl_c1:
            st.markdown(
                "<p style='color: #02BFD0; font-weight: 700; font-size: 0.82rem;'>1. Select Player to Transfer</p>",
                unsafe_allow_html=True,
            )
            xl_player_name = st.selectbox(
                "Player Candidate",
                popular_names,
                index=0,
                key="xl_player_name_sel",
            )
            xl_matches = data_service.search_players(xl_player_name, limit=1)
            if xl_matches:
                p_record = xl_matches[0]
                src_comp_default = p_record.get("competition_id", "GB1")
            else:
                p_record = {
                    "name": xl_player_name,
                    "age": 24,
                    "position": "Attack",
                    "goals": 20,
                    "assists": 5,
                    "minutes_played": 2500,
                    "appearances": 30,
                }
                src_comp_default = "GB1"

        with xl_c2:
            st.markdown(
                "<p style='color: #02BFD0; font-weight: 700; font-size: 0.82rem;'>2. Select Transfer Destination</p>",
                unsafe_allow_html=True,
            )
            dest_comps = [c for c in all_comps if c["id"] != src_comp_default]
            dest_dict = {c["id"]: f"{c['name']} ({c['country']})" for c in dest_comps}
            xl_dest_comp = st.selectbox(
                "Destination League",
                options=list(dest_dict.keys()),
                format_func=lambda cid: dest_dict[cid],
                index=0,
                key="xl_dest_comp_sel",
            )

        btn_xl = st.button(
            "⚡ Simulate Cross-League Transfer Valuation", key="btn_xl_sim", type="primary", use_container_width=True
        )

        if btn_xl or "last_xl_res" not in st.session_state:
            with st.spinner("Simulating multi-league transfer dynamics..."):
                xl_res = pred_service.predict_cross_league(
                    player_data=p_record,
                    source_competition_id=src_comp_default,
                    destination_competition_id=xl_dest_comp,
                    season=2023,
                )
                st.session_state["last_xl_res"] = xl_res
                st.session_state["last_xl_src"] = src_comp_default
                st.session_state["last_xl_dest"] = xl_dest_comp

        xl_res = st.session_state["last_xl_res"]
        src_comp_show = st.session_state.get("last_xl_src", src_comp_default)
        dest_comp_show = st.session_state.get("last_xl_dest", xl_dest_comp)

        st.markdown("<hr style='border:none;border-top:1px solid #E2E6E9;margin:1rem 0;'/>", unsafe_allow_html=True)

        res_c1, res_c2, res_c3 = st.columns([1, 1, 1.2])

        dest_val = xl_res.predicted_value_eur
        diff_eur = xl_res.cross_league_delta_eur or 0.0
        diff_pct = xl_res.cross_league_delta_pct or 0.0
        source_val = dest_val - diff_eur
        diff_color = "#20A56B" if diff_eur >= 0 else "#E05252"

        with res_c1:
            st.markdown(
                f"""
                <div class="tm-card" style="padding: 1rem; text-align: center; border-left: 3.5px solid #00A9B9;">
                    <div style="font-size: 0.68rem; color: #8A959E; font-weight: 700;">SOURCE: {src_comp_show}</div>
                    <div style="font-size: 1.5rem; font-weight: 800; color: #17212B; margin: 0.3rem 0; font-family:'Manrope',sans-serif;">
                        {format_currency_eur(source_val)}
                    </div>
                    <div style="font-size: 0.75rem; color: #018591; font-weight: 600;">Current League Baseline</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with res_c2:
            st.markdown(
                f"""
                <div class="tm-card" style="padding: 1rem; text-align: center; border-left: 3.5px solid #02BFD0;">
                    <div style="font-size: 0.68rem; color: #8A959E; font-weight: 700;">DESTINATION: {dest_comp_show}</div>
                    <div style="font-size: 1.5rem; font-weight: 800; color: #17212B; margin: 0.3rem 0; font-family:'Manrope',sans-serif;">
                        {format_currency_eur(dest_val)}
                    </div>
                    <div style="font-size: 0.82rem; font-weight: 700; color: {diff_color}; font-family:'Manrope',sans-serif;">
                        {format_delta_pct(diff_pct)} ({format_delta_eur(diff_eur)})
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with res_c3:
            warning_texts = (
                "<br>• ".join(xl_res.relevant_data_warnings)
                if xl_res.relevant_data_warnings
                else "Move valuation benchmark calibrated on cross-league Elo strength and scoring tempo."
            )
            explanation = f"• {warning_texts}"
            st.markdown(
                f"""
                <div class="tm-card" style="padding: 1rem;">
                    <div style="font-size: 0.72rem; color: #02BFD0; font-weight: 700; text-transform: uppercase; margin-bottom: 0.4rem;">
                        Scientific Market Explanation
                    </div>
                    <p style="font-size: 0.82rem; color: #66727D; line-height: 1.45; margin: 0;">
                        {explanation}
                    </p>
                </div>
                """,
                unsafe_allow_html=True,
            )
