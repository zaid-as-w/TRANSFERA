"""KPI cards summary component for TRANSFERA."""

from typing import Any

import streamlit as st

from dashboard.formatting import format_currency_eur


def render_kpi_cards(kpis: dict[str, Any]) -> None:
    """Render top metrics KPI cards matching TRANSFERA clean light aesthetic."""
    cols = st.columns(7)

    metrics = [
        ("Total Players", f"{kpis['unique_players']:,}", "Active scouting profiles", "#02BFD0"),
        ("Market Value", format_currency_eur(kpis["total_market_value"]), "Total capital tracked", "#00A9B9"),
        ("Average Value", format_currency_eur(kpis["avg_market_value"]), "Per-player benchmark", "#20A56B"),
        ("Peak Valuation", format_currency_eur(kpis["highest_market_value"]), "World record tier", "#E5A52B"),
        ("Competitions", str(kpis["competitions_count"]), "Covered leagues", "#3185C7"),
        ("Countries", str(kpis["countries_count"]), "Nations represented", "#66727D"),
        ("Seasons", str(kpis["seasons_count"]), "Historical coverage", "#8A959E"),
    ]

    for idx, (title, value, subtext, color) in enumerate(metrics):
        with cols[idx]:
            card_html = (
                f'<div class="tm-kpi" style="border-top:3px solid {color};padding:0.75rem 0.6rem;text-align:center;">'
                f'<div style="font-size:0.68rem;color:#66727D;font-weight:700;letter-spacing:0.5px;text-transform:uppercase;">{title}</div>'
                f"<div style=\"font-size:1.25rem;font-weight:800;color:#17212B;margin:0.25rem 0;font-family:'Manrope',sans-serif;\">{value}</div>"
                f'<div style="font-size:0.62rem;color:#8A959E;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{subtext}</div>'
                f"</div>"
            )
            st.markdown(card_html, unsafe_allow_html=True)
