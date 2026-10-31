"""Header component featuring league selectors, country pills, and global search for TRANSFERA."""

from typing import Any

import streamlit as st

TOP_LEAGUES = [
    ("GB1", "Premier League", "England", "🇬🇧"),
    ("ES1", "La Liga", "Spain", "🇪🇸"),
    ("L1", "Bundesliga", "Germany", "🇩🇪"),
    ("IT1", "Serie A", "Italy", "🇮🇹"),
    ("FR1", "Ligue 1", "France", "🇫🇷"),
]

TOP_COUNTRIES = [
    ("England", "🇬🇧"),
    ("Brazil", "🇧🇷"),
    ("France", "🇫🇷"),
    ("Spain", "🇪🇸"),
    ("Germany", "🇩🇪"),
    ("Argentina", "🇦🇷"),
    ("Portugal", "🇵🇹"),
    ("Netherlands", "🇳🇱"),
]


def render_header(all_competitions: list[dict[str, Any]]) -> dict[str, Any]:
    """Render top search bar, league selectors, and country pills with clean light styling."""
    # Top Row: Search bar & Tagline
    col_search, col_tagline = st.columns([3.4, 1.6])

    with col_search:
        search_query = st.text_input(
            "Global Search",
            placeholder="Search players, clubs, leagues or countries (e.g. Haaland, Real Madrid, Premier League)...",
            label_visibility="collapsed",
            key="global_search_input",
        )

    with col_tagline:
        tagline_html = (
            '<div style="display:flex;justify-content:flex-end;align-items:center;gap:0.75rem;height:100%;">'
            '<div style="text-align:right;">'
            "<div style=\"font-size:0.72rem;font-weight:700;letter-spacing:1px;color:#02BFD0;text-transform:uppercase;font-family:'Inter',sans-serif;\">THE GLOBAL GAME. DECODED.</div>"
            '<div style="font-size:0.62rem;color:#8A959E;font-weight:600;letter-spacing:0.5px;text-transform:uppercase;">TRANSFERA INTELLIGENCE</div>'
            "</div>"
            '<div style="background:#FFFFFF;border:1px solid #E2E6E9;width:32px;height:32px;border-radius:6px;display:flex;align-items:center;justify-content:center;color:#02BFD0;font-weight:800;font-size:0.9rem;box-shadow:0 1px 3px rgba(0,0,0,0.05);">'
            "T"
            "</div>"
            "</div>"
        )
        st.markdown(tagline_html, unsafe_allow_html=True)

    # Top League Cards Row
    if "selected_league" not in st.session_state:
        st.session_state["selected_league"] = "ALL"

    l_cols = st.columns(6)

    for idx, (code, name, country, flag) in enumerate(TOP_LEAGUES):
        with l_cols[idx]:
            is_active = st.session_state["selected_league"] == code
            if st.button(
                f"{flag} {name}",
                key=f"hdr_lg_{code}",
                use_container_width=True,
                type="primary" if is_active else "secondary",
            ):
                st.session_state["selected_league"] = "ALL" if is_active else code
                st.rerun()

    with l_cols[5]:
        other_comps = [c for c in all_competitions if c["id"] not in [x[0] for x in TOP_LEAGUES]]
        other_options = ["More Competitions..."] + [f"{c['name']} ({c['id']})" for c in other_comps]
        sel_more = st.selectbox(
            "More Leagues",
            options=other_options,
            label_visibility="collapsed",
            key="hdr_more_leagues",
        )
        if sel_more != "More Competitions...":
            cid = sel_more.split("(")[-1].replace(")", "").strip()
            if st.session_state["selected_league"] != cid:
                st.session_state["selected_league"] = cid
                st.rerun()

    # Country Pills Row
    if "selected_country" not in st.session_state:
        st.session_state["selected_country"] = "ALL"

    c_cols = st.columns([1.2] + [1] * len(TOP_COUNTRIES) + [0.8])
    with c_cols[0]:
        is_all_c = st.session_state["selected_country"] == "ALL"
        if st.button(
            "🌐 All Nations", key="hdr_c_all", use_container_width=True, type="primary" if is_all_c else "secondary"
        ):
            st.session_state["selected_country"] = "ALL"
            st.rerun()

    for idx, (c_name, c_flag) in enumerate(TOP_COUNTRIES):
        with c_cols[idx + 1]:
            is_c_active = st.session_state["selected_country"] == c_name
            if st.button(
                f"{c_flag} {c_name}",
                key=f"hdr_c_{c_name}",
                use_container_width=True,
                type="primary" if is_c_active else "secondary",
            ):
                st.session_state["selected_country"] = "ALL" if is_c_active else c_name
                st.rerun()

    with c_cols[-1]:
        if st.button("More +", key="hdr_c_more", use_container_width=True):
            st.session_state["active_page"] = "Countries"
            st.rerun()

    sep_html = '<hr style="border:none;border-top:1px solid #E2E6E9;margin:0.6rem 0 1rem 0;"/>'
    st.markdown(sep_html, unsafe_allow_html=True)

    return {
        "search_query": search_query,
        "selected_league": st.session_state["selected_league"],
        "selected_country": st.session_state["selected_country"],
    }
