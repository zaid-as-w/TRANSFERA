"""Sidebar navigation and branding component for TRANSFERA."""

import streamlit as st

from dashboard.components.logo import get_transfera_brand_html

NAV_PAGES = [
    ("Home", "⚡"),
    ("Players", "👤"),
    ("Leagues", "🏆"),
    ("Countries", "🌐"),
    ("Value Predictor", "💎"),
    ("Player Comparison", "⚔️"),
    ("Analytics & Insights", "📈"),
]

TOP_LEAGUES = [
    ("GB1", "Premier League", "🇬🇧"),
    ("ES1", "La Liga", "🇪🇸"),
    ("L1", "Bundesliga", "🇩🇪"),
    ("IT1", "Serie A", "🇮🇹"),
    ("FR1", "Ligue 1", "🇫🇷"),
]

TOP_COUNTRIES = [
    ("England", "🇬🇧"),
    ("Spain", "🇪🇸"),
    ("Brazil", "🇧🇷"),
    ("France", "🇫🇷"),
    ("Germany", "🇩🇪"),
    ("Argentina", "🇦🇷"),
    ("Portugal", "🇵🇹"),
    ("Netherlands", "🇳🇱"),
]


def render_sidebar() -> str:
    """Render the TRANSFERA sidebar navigation and return selected active page."""
    with st.sidebar:
        # TRANSFERA Official Geometric Logo & Brand Title
        st.markdown(get_transfera_brand_html(compact=False), unsafe_allow_html=True)
        st.markdown(
            '<hr style="border:none;border-top:1px solid #E2E6E9;margin:0.4rem 0 0.8rem 0;"/>', unsafe_allow_html=True
        )

        # Active page selection
        if "active_page" not in st.session_state:
            st.session_state["active_page"] = "Home"

        st.markdown(
            "<p style='font-size:0.68rem; color:#66727D; font-weight:700; text-transform:uppercase; letter-spacing:1px; margin-bottom:0.5rem;'>Console Navigation</p>",
            unsafe_allow_html=True,
        )

        for page_name, icon in NAV_PAGES:
            is_active = st.session_state["active_page"] == page_name
            btn_label = f"{icon}  {page_name}"
            btn_type = "primary" if is_active else "secondary"
            if st.button(btn_label, key=f"nav_{page_name}", type=btn_type, use_container_width=True):
                st.session_state["active_page"] = page_name
                st.rerun()

        st.markdown("<div style='height: 0.8rem;'></div>", unsafe_allow_html=True)

        # Top Leagues Quick Filter
        with st.expander("🏆 Competitions", expanded=True):
            if "selected_league" not in st.session_state:
                st.session_state["selected_league"] = "ALL"

            if st.button(
                "All Competitions",
                key="league_all",
                use_container_width=True,
                type="primary" if st.session_state["selected_league"] == "ALL" else "secondary",
            ):
                st.session_state["selected_league"] = "ALL"
                st.rerun()

            for code, name, flag in TOP_LEAGUES:
                is_sel = st.session_state["selected_league"] == code
                if st.button(
                    f"{flag} {name}",
                    key=f"s_league_{code}",
                    use_container_width=True,
                    type="primary" if is_sel else "secondary",
                ):
                    st.session_state["selected_league"] = code
                    st.rerun()

        # Top Countries Quick Filter
        with st.expander("🌐 Nations", expanded=False):
            if "selected_country" not in st.session_state:
                st.session_state["selected_country"] = "ALL"

            if st.button(
                "All Nations",
                key="country_all",
                use_container_width=True,
                type="primary" if st.session_state["selected_country"] == "ALL" else "secondary",
            ):
                st.session_state["selected_country"] = "ALL"
                st.rerun()

            for c_name, c_flag in TOP_COUNTRIES:
                is_sel_c = st.session_state["selected_country"] == c_name
                if st.button(
                    f"{c_flag} {c_name}",
                    key=f"s_country_{c_name}",
                    use_container_width=True,
                    type="primary" if is_sel_c else "secondary",
                ):
                    st.session_state["selected_country"] = c_name
                    st.rerun()

        st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)

        # Bottom System Indicator
        sys_status_html = (
            '<div style="background:#F8F9FA;border:1px solid #E2E6E9;border-radius:6px;padding:0.6rem 0.8rem;text-align:center;">'
            '<div style="font-size:0.62rem;color:#8A959E;font-weight:700;letter-spacing:0.8px;text-transform:uppercase;">MODEL ENGINE</div>'
            '<div style="font-size:0.75rem;color:#20A56B;font-weight:700;display:flex;align-items:center;justify-content:center;gap:0.35rem;margin-top:2px;">'
            '<span style="display:inline-block;width:6px;height:6px;border-radius:50%;background:#20A56B;"></span>'
            "HistGradientBoosting Online"
            "</div>"
            '<div style="font-size:0.58rem;color:#66727D;margin-top:2px;">32 Verified Features Active</div>'
            "</div>"
        )
        st.markdown(sys_status_html, unsafe_allow_html=True)

    return st.session_state["active_page"]
