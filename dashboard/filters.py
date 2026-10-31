"""Global filter component for dashboard pages."""

from typing import Any

import streamlit as st

from dashboard.data_service import DataService


def render_filter_bar(data_service: DataService) -> dict[str, Any]:
    """Render expandable global filter panel across relevant pages."""
    with st.expander("⚙️ Global Scouting & Market Filters", expanded=False):
        c1, c2, c3, c4 = st.columns(4)

        with c1:
            seasons = data_service.get_seasons()
            default_season_idx = 0 if seasons else 0
            sel_season = st.selectbox("Season", options=seasons, index=default_season_idx, key="flt_season")

        with c2:
            comps = data_service.get_competitions()
            comp_options = ["ALL"] + [c["id"] for c in comps]
            comp_labels = {"ALL": "🌐 All Competitions"}
            for c in comps:
                comp_labels[c["id"]] = f"{c['name']} ({c['id']})"

            # Use sidebar selection if set
            current_league = st.session_state.get("selected_league", "ALL")
            def_idx = comp_options.index(current_league) if current_league in comp_options else 0
            sel_comp = st.selectbox(
                "Competition",
                options=comp_options,
                format_func=lambda x: comp_labels.get(x, x),
                index=def_idx,
                key="flt_comp",
            )
            # Sync back to session state
            st.session_state["selected_league"] = sel_comp

        with c3:
            countries = ["ALL"] + data_service.get_countries()
            current_c = st.session_state.get("selected_country", "ALL")
            c_idx = countries.index(current_c) if current_c in countries else 0
            sel_country = st.selectbox("Player Nationality", options=countries, index=c_idx, key="flt_country")
            st.session_state["selected_country"] = sel_country

        with c4:
            clubs = [{"id": 0, "name": "🏢 All Clubs"}] + data_service.get_clubs(sel_comp, sel_season)
            sel_club = st.selectbox(
                "Club",
                options=[c["id"] for c in clubs],
                format_func=lambda x: next(c["name"] for c in clubs if c["id"] == x),
                key="flt_club",
            )

        c5, c6, c7 = st.columns(3)

        with c5:
            positions = ["ALL", "Attack", "Midfield", "Defender", "Goalkeeper"]
            sel_pos = st.selectbox("Position Group", options=positions, key="flt_position")

        with c6:
            age_range = st.slider("Age Range", min_value=16, max_value=42, value=(16, 40), key="flt_age")

        with c7:
            val_range_m = st.slider(
                "Market Value (€ Millions)",
                min_value=0.0,
                max_value=200.0,
                value=(0.0, 200.0),
                step=1.0,
                key="flt_val",
            )
            val_range_eur = (val_range_m[0] * 1_000_000, val_range_m[1] * 1_000_000)

        btn_c1, btn_c2 = st.columns([1, 5])
        with btn_c1:
            if st.button("Reset Filters", key="flt_reset"):
                st.session_state["selected_league"] = "ALL"
                st.session_state["selected_country"] = "ALL"
                st.rerun()

    return {
        "season": sel_season,
        "competition_id": sel_comp,
        "country": sel_country,
        "club_id": sel_club,
        "position": sel_pos,
        "age_range": age_range,
        "value_range_eur": val_range_eur,
    }
