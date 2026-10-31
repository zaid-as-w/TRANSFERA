"""Home Page: TRANSFERA Global Football Market Intelligence & Hero Valuation Predictor."""

import streamlit as st

from dashboard.components.charts import (
    render_age_histogram,
    render_country_map,
    render_league_bar_chart,
    render_performance_scatter,
    render_position_donut,
)
from dashboard.components.header import render_header
from dashboard.components.player_card import render_top_players_table
from dashboard.components.prediction_card import render_prediction_card
from dashboard.data_service import DataService
from dashboard.image_service import get_player_image_url
from dashboard.prediction_service import DashboardPredictionService

HAALAND_CUTOUT_URL = "https://images.unsplash.com/photo-1579952363873-27f3bade9f55?w=500&auto=format&fit=crop&q=80"
CUSTOM_SCOUT_URL = "https://images.unsplash.com/photo-1517466787929-bc90951d0974?w=500&auto=format&fit=crop&q=80"


def render_home_page(data_service: DataService, pred_service: DashboardPredictionService) -> None:
    """Render the main landing page matching the TRANSFERA clean light design."""
    # 1. Header with search, top league pills, and country selectors
    all_comps = data_service.get_competitions()
    comp_options = {c["id"]: c["name"] for c in all_comps}
    hdr_state = render_header(all_comps)

    sel_league = hdr_state["selected_league"]
    sel_country = hdr_state["selected_country"]
    search_q = hdr_state["search_query"]

    # Active season data
    latest_season = data_service.get_seasons()[0]
    df_filtered = data_service.filter_data(
        season=latest_season,
        competition_id=sel_league if sel_league != "ALL" else None,
        country=sel_country if sel_country != "ALL" else None,
    )

    # 2. Hero Section: TRANSFERA — THE GLOBAL FOOTBALL MARKET INTELLIGENCE PLATFORM
    hero_headline_html = (
        '<div class="tm-card" style="padding:1.4rem 1.6rem;margin-bottom:1.25rem;">'
        '<div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:0.5rem;">'
        "<div>"
        "<div style=\"font-size:0.72rem;font-weight:700;letter-spacing:1.5px;color:#02BFD0;text-transform:uppercase;font-family:'Inter',sans-serif;\">THE GLOBAL GAME. DECODED.</div>"
        "<h1 style=\"margin:0.2rem 0;font-size:2rem;font-weight:800;letter-spacing:-0.5px;text-transform:uppercase;font-family:'Manrope',sans-serif;color:#17212B;\">"
        'TRANSFER<span style="color:#02BFD0;">A</span> <span style="font-weight:400;color:#8A959E;font-size:1.3rem;">| VALUE PREDICTOR</span>'
        "</h1>"
        '<p style="margin:0.2rem 0 0.8rem 0;color:#66727D;font-size:0.9rem;max-width:850px;line-height:1.45;">'
        "Explore verified global football talent, understand player valuations, and uncover market insights powered by historical benchmarks and machine learning."
        "</p>"
        "</div>"
        "</div>"
        '<div style="display:flex;gap:0.5rem;flex-wrap:wrap;margin-bottom:0.2rem;">'
        '<span style="background:#E5F9FB;border:1px solid rgba(2,191,208,0.35);color:#018591;padding:0.22rem 0.65rem;border-radius:4px;font-size:0.72rem;font-weight:700;">⚡ Real Player Data</span>'
        '<span style="background:#F0F7FF;border:1px solid #C8E1FF;color:#1D68BD;padding:0.22rem 0.65rem;border-radius:4px;font-size:0.72rem;font-weight:700;">🤖 ML Valuation Engine</span>'
        '<span style="background:#E8F8F1;border:1px solid #A5E4C7;color:#178352;padding:0.22rem 0.65rem;border-radius:4px;font-size:0.72rem;font-weight:700;">✓ Actual Market Benchmarks</span>'
        '<span style="background:#F8F9FA;border:1px solid #E2E6E9;color:#66727D;padding:0.22rem 0.65rem;border-radius:4px;font-size:0.72rem;font-weight:700;">📊 Global League Analytics</span>'
        "</div>"
        "</div>"
    )
    st.markdown(hero_headline_html, unsafe_allow_html=True)

    # Mode Selector: Existing Player vs Custom Player Simulation
    hero_mode_options = ["Predict Existing Player", "Custom Player Prediction"]
    if "hero_mode" not in st.session_state:
        st.session_state["hero_mode"] = hero_mode_options[0]

    hero_col_img, hero_col_form, hero_col_res = st.columns([0.8, 1.4, 1.0])

    popular_player_names = [
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
    ]

    with hero_col_form:
        sel_hero_mode = st.segmented_control(
            "Hero Mode",
            options=hero_mode_options,
            default=st.session_state.get("hero_mode", hero_mode_options[0]),
            label_visibility="collapsed",
            key="home_hero_mode_segmented_ctrl",
        )
        if not sel_hero_mode:
            sel_hero_mode = st.session_state.get("hero_mode", hero_mode_options[0])
        st.session_state["hero_mode"] = sel_hero_mode

        st.markdown('<div style="height:0.4rem;"></div>', unsafe_allow_html=True)

        # MODE A: EXISTING PLAYER PREDICTION
        if st.session_state["hero_mode"] == "Predict Existing Player":
            if search_q and len(search_q.strip()) >= 2:
                two_stage_res, _ = data_service.search_players_two_stage(search_q, limit=10)
                player_options = [m.name for m in two_stage_res] if two_stage_res else popular_player_names
            else:
                player_options = popular_player_names

            sel_player_name = st.selectbox(
                "Select Player",
                options=player_options,
                index=0,
                key="home_hero_player",
                label_visibility="collapsed",
            )

            matches = data_service.search_players(sel_player_name, df_filtered, limit=1)
            if not matches:
                matches = data_service.search_players(sel_player_name, None, limit=1)

            if matches:
                p_data = matches[0]
                age_val = int(p_data["age"])
                pos_val = p_data["position"]
                g_val = p_data["goals"]
                a_val = p_data["assists"]
                mins_val = f"{p_data['minutes_played']:,}"
                apps_val = p_data["appearances"]
                club_val = p_data["current_club_name"]

                stat_grid_html = (
                    '<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:0.5rem;background:#F8F9FA;border-radius:6px;padding:0.75rem;margin-bottom:0.75rem;border:1px solid #EDF0F2;">'
                    f'<div><span style="color:#8A959E;font-size:0.65rem;font-weight:700;text-transform:uppercase;">AGE</span><br><b style="font-size:1rem;color:#17212B;font-family:\'Manrope\',sans-serif;">{age_val}</b></div>'
                    f'<div><span style="color:#8A959E;font-size:0.65rem;font-weight:700;text-transform:uppercase;">POSITION</span><br><b style="font-size:1rem;color:#17212B;font-family:\'Manrope\',sans-serif;">{pos_val}</b></div>'
                    f'<div><span style="color:#8A959E;font-size:0.65rem;font-weight:700;text-transform:uppercase;">GOALS</span><br><b style="font-size:1rem;color:#02BFD0;font-family:\'Manrope\',sans-serif;">{g_val}</b></div>'
                    f'<div><span style="color:#8A959E;font-size:0.65rem;font-weight:700;text-transform:uppercase;">ASSISTS</span><br><b style="font-size:1rem;color:#20A56B;font-family:\'Manrope\',sans-serif;">{a_val}</b></div>'
                    f'<div><span style="color:#8A959E;font-size:0.65rem;font-weight:700;text-transform:uppercase;">MINUTES</span><br><b style="font-size:0.9rem;color:#17212B;font-family:\'Manrope\',sans-serif;">{mins_val}</b></div>'
                    f'<div><span style="color:#8A959E;font-size:0.65rem;font-weight:700;text-transform:uppercase;">MATCHES</span><br><b style="font-size:0.9rem;color:#17212B;font-family:\'Manrope\',sans-serif;">{apps_val}</b></div>'
                    f'<div><span style="color:#8A959E;font-size:0.65rem;font-weight:700;text-transform:uppercase;">FOOT</span><br><b style="font-size:0.9rem;color:#17212B;font-family:\'Manrope\',sans-serif;">Left</b></div>'
                    f'<div><span style="color:#8A959E;font-size:0.65rem;font-weight:700;text-transform:uppercase;">CLUB</span><br><b style="font-size:0.8rem;color:#17212B;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{club_val}</b></div>'
                    "</div>"
                )
                st.markdown(stat_grid_html, unsafe_allow_html=True)

                btn_predict = st.button(
                    "⚡ Calculate Market Value ➔", key="home_btn_predict", type="primary", use_container_width=True
                )
            else:
                p_data = None
                btn_predict = False

        # MODE B: CUSTOM PLAYER SIMULATION DIRECTLY IN HERO CARD
        else:
            p_data = None
            btn_predict = False

            c_r1_1, c_r1_2 = st.columns([1, 1])
            with c_r1_1:
                custom_age = st.slider("Age", 16.0, 40.0, 22.0, 0.5, key="hero_cust_age")
            with c_r1_2:
                custom_pos = st.selectbox(
                    "Position", ["Attack", "Midfield", "Defender", "Goalkeeper"], index=0, key="hero_cust_pos"
                )

            c_r2_1, c_r2_2, c_r2_3, c_r2_4 = st.columns(4)
            with c_r2_1:
                custom_goals = st.number_input("Goals", 0, 60, 14, 1, key="hero_cust_goals")
            with c_r2_2:
                custom_assists = st.number_input("Assists", 0, 40, 6, 1, key="hero_cust_ast")
            with c_r2_3:
                custom_mins = st.number_input("Minutes", 0, 4500, 2200, 50, key="hero_cust_mins")
            with c_r2_4:
                custom_apps = st.number_input("Matches", 0, 55, 28, 1, key="hero_cust_apps")

            c_r3_1, c_r3_2 = st.columns([1.2, 1])
            with c_r3_1:
                custom_comp = st.selectbox(
                    "League",
                    options=list(comp_options.keys()),
                    format_func=lambda cid: comp_options[cid],
                    index=0,
                    key="hero_cust_comp",
                )
            with c_r3_2:
                custom_prior_m = st.number_input("Prior Val (€M)", 0.0, 200.0, 15.0, 1.0, key="hero_cust_prior")

            btn_predict_custom = st.button(
                "⚡ Estimate Custom Player Value ➔",
                key="home_btn_predict_custom",
                type="primary",
                use_container_width=True,
            )

    with hero_col_img:
        # Player Hero Cutout Visual in Clean Frame
        if st.session_state["hero_mode"] == "Predict Existing Player":
            if p_data:
                p_img = get_player_image_url(p_data["player_id"], p_data.get("image_url"))
                p_display_name = p_data["name"]
            else:
                p_img = HAALAND_CUTOUT_URL
                p_display_name = "Erling Haaland"
        else:
            p_img = CUSTOM_SCOUT_URL
            p_display_name = "Custom Prospect"

        hero_art_html = (
            '<div style="text-align:center;padding:0.4rem 0;display:flex;flex-direction:column;align-items:center;justify-content:center;height:100%;">'
            f'<div style="position:relative;width:140px;height:175px;border-radius:8px;overflow:hidden;border:1px solid #E2E6E9;box-shadow:0 2px 8px rgba(0,0,0,0.06);background:#F8F9FA;">'
            f'<img src="{p_img}" style="width:100%;height:100%;object-fit:cover;" onerror="this.src=\'{HAALAND_CUTOUT_URL}\';"/>'
            "</div>"
            f"<div style=\"font-family:'Manrope',sans-serif;font-size:1.05rem;font-weight:700;color:#17212B;margin-top:0.45rem;\">{p_display_name}</div>"
            "</div>"
        )
        st.markdown(hero_art_html, unsafe_allow_html=True)

    with hero_col_res:
        if st.session_state["hero_mode"] == "Predict Existing Player":
            if p_data:
                cache_key = f"hero_pred_{p_data['player_id']}_{p_data['season']}"
                if btn_predict or cache_key not in st.session_state:
                    with st.spinner("Evaluating via HGB champion pipeline..."):
                        res = pred_service.predict_player_record(p_data)
                        st.session_state[cache_key] = res

                res = st.session_state[cache_key]
                render_prediction_card(
                    result=res,
                    actual_value_eur=p_data.get("market_value_eur"),
                    club_id=p_data.get("club_id"),
                    club_name=p_data.get("current_club_name"),
                )
        else:
            # Custom prediction mode - reactive to input changes and button clicks
            cust_cache_key = f"{custom_age}_{custom_pos}_{custom_goals}_{custom_assists}_{custom_mins}_{custom_apps}_{custom_comp}_{custom_prior_m}"
            if (
                btn_predict_custom
                or "last_hero_custom_key" not in st.session_state
                or st.session_state.get("last_hero_custom_key") != cust_cache_key
            ):
                with st.spinner("Simulating custom player valuation..."):
                    custom_prior_eur = (custom_prior_m * 1_000_000.0) if custom_prior_m > 0 else None
                    res_cust = pred_service.predict_custom(
                        age=custom_age,
                        position=custom_pos,
                        appearances=custom_apps,
                        minutes_played=custom_mins,
                        goals=custom_goals,
                        assists=custom_assists,
                        competition_id=custom_comp,
                        previous_market_value=custom_prior_eur,
                        season=2023,
                    )
                    st.session_state["last_hero_custom_res"] = res_cust
                    st.session_state["last_hero_custom_comp"] = custom_comp
                    st.session_state["last_hero_custom_key"] = cust_cache_key
                    st.session_state["last_hero_custom_prior"] = custom_prior_eur

            res_c = st.session_state["last_hero_custom_res"]
            render_prediction_card(
                result=res_c,
                actual_value_eur=st.session_state.get("last_hero_custom_prior"),
                club_id=None,
                club_name=comp_options.get(st.session_state.get("last_hero_custom_comp", "GB1"), "Custom Squad"),
            )

    sep_mid = '<div style="height:0.8rem;"></div>'
    st.markdown(sep_mid, unsafe_allow_html=True)

    # 3. Middle Analytics Section (League Bar Chart, Country Map, Top 10 Table)
    mid_c1, mid_c2, mid_c3 = st.columns([1.1, 1.2, 1.3])

    with mid_c1:
        st.markdown('<div class="tm-card">', unsafe_allow_html=True)
        league_df = data_service.get_market_value_by_league(df_filtered)
        fig_league = render_league_bar_chart(league_df)
        st.plotly_chart(fig_league, use_container_width=True, config={"displayModeBar": False})
        st.markdown("</div>", unsafe_allow_html=True)

    with mid_c2:
        st.markdown('<div class="tm-card">', unsafe_allow_html=True)
        country_df = data_service.get_market_value_by_country(df_filtered)
        fig_country = render_country_map(country_df)
        st.plotly_chart(fig_country, use_container_width=True, config={"displayModeBar": False})
        st.markdown("</div>", unsafe_allow_html=True)

    with mid_c3:
        st.markdown('<div class="tm-card">', unsafe_allow_html=True)
        top10_df = data_service.get_top_valuable_players(df_filtered, limit=10)
        render_top_players_table(top10_df)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown(sep_mid, unsafe_allow_html=True)

    # 4. Bottom Analytics Section (Position Donut, Age Histogram, Scatter Plot)
    bot_c0, bot_c1, bot_c2, bot_c3 = st.columns([0.75, 1.0, 1.1, 1.3])

    with bot_c0:
        transfera_motto_html = (
            '<div class="tm-card" style="height:100%;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;padding:1.2rem;">'
            '<div style="width:44px;height:44px;border-radius:8px;border:1.5px solid #02BFD0;display:flex;align-items:center;justify-content:center;background:#E5F9FB;color:#02BFD0;font-size:1.3rem;font-weight:800;box-shadow:0 1px 3px rgba(0,0,0,0.05);">'
            "T"
            "</div>"
            "<div style=\"font-size:0.95rem;font-weight:800;color:#17212B;margin-top:0.6rem;letter-spacing:1px;text-transform:uppercase;font-family:'Manrope',sans-serif;\">"
            'TRANSFER<span style="color:#02BFD0;">A</span>'
            "</div>"
            '<div style="font-size:0.68rem;color:#02BFD0;font-weight:700;letter-spacing:0.8px;margin-top:0.25rem;">THE GLOBAL GAME. DECODED.</div>'
            '<div style="font-size:0.68rem;color:#66727D;margin-top:0.35rem;line-height:1.35;">Real Data · Real Insights · AI Market Valuations</div>'
            "</div>"
        )
        st.markdown(transfera_motto_html, unsafe_allow_html=True)

    with bot_c1:
        st.markdown('<div class="tm-card">', unsafe_allow_html=True)
        fig_pos = render_position_donut(df_filtered)
        st.plotly_chart(fig_pos, use_container_width=True, config={"displayModeBar": False})
        st.markdown("</div>", unsafe_allow_html=True)

    with bot_c2:
        st.markdown('<div class="tm-card">', unsafe_allow_html=True)
        fig_age = render_age_histogram(df_filtered)
        st.plotly_chart(fig_age, use_container_width=True, config={"displayModeBar": False})
        st.markdown("</div>", unsafe_allow_html=True)

    with bot_c3:
        st.markdown('<div class="tm-card">', unsafe_allow_html=True)
        fig_scat = render_performance_scatter(df_filtered)
        st.plotly_chart(fig_scat, use_container_width=True, config={"displayModeBar": False})
        st.markdown("</div>", unsafe_allow_html=True)
