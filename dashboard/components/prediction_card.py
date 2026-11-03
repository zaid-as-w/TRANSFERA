"""Prediction result card component for TRANSFERA."""

import streamlit as st

from dashboard.formatting import format_currency_eur, format_delta_eur, format_delta_pct
from dashboard.image_service import get_club_crest_url, get_fallback_image
from src.predict import ValuationResult


def render_prediction_card(
    result: ValuationResult,
    actual_value_eur: float | None = None,
    club_id: int | None = None,
    club_name: str | None = None,
) -> None:
    """Render the clean Transfermarkt-styled valuation result card with benchmark and delta metrics."""
    pred_val = result.predicted_value_eur
    pred_str = format_currency_eur(pred_val)
    crest_url = get_club_crest_url(club_id)
    c_fallback = get_fallback_image("club")
    benchmark_mae = result.empirical_benchmark_mae_eur

    # Delta vs actual or prior baseline if available
    has_actual = actual_value_eur is not None and actual_value_eur > 0
    if has_actual:
        diff_eur = pred_val - actual_value_eur
        diff_pct = (diff_eur / actual_value_eur) * 100.0
        delta_color = "#20A56B" if diff_eur >= 0 else "#E05252"
        delta_bg = "#E8F8F1" if diff_eur >= 0 else "#FDF0ED"
        delta_str = f"{format_delta_pct(diff_pct)} ({format_delta_eur(diff_eur)})"
    else:
        delta_color = "#018591"
        delta_bg = "#E5F9FB"
        delta_str = "ML Valuation Estimate"
        diff_eur = 0.0
        diff_pct = 0.0

    # Uncertainty benchmark text
    if benchmark_mae:
        uncertainty_text = f"Empirical Error Benchmark: ±{format_currency_eur(benchmark_mae)} (Test MAE)"
    else:
        uncertainty_text = "Empirical Error Benchmark: ±€1.99M (Global Held-Out MAE)"

    # Club or competition title
    club_title = club_name or result.source_competition

    # Build clean light prediction card
    card_html = (
        f'<div class="tm-card" style="text-align:center;border-top:3.5px solid #02BFD0;padding:1.25rem 1rem;">'
        f'<div style="font-size:0.72rem;font-weight:700;letter-spacing:1px;color:#02BFD0;text-transform:uppercase;margin-bottom:0.3rem;">PREDICTED MARKET VALUE</div>'
        f'<div style="display:flex;align-items:center;justify-content:center;gap:0.45rem;margin-bottom:0.6rem;">'
        f'<img src="{crest_url}" style="width:18px;height:18px;object-fit:contain;" onerror="this.onerror=null; this.src=\'{c_fallback}\';"/>'
        f'<span style="font-size:0.85rem;color:#66727D;font-weight:600;">{club_title}</span>'
        f"</div>"
        f"<div style=\"font-size:2.3rem;font-weight:800;color:#17212B;font-family:'Manrope',sans-serif;line-height:1.1;letter-spacing:-0.5px;\">{pred_str}</div>"
        f'<div style="margin:0.5rem 0;">'
        f'<span style="background:{delta_bg};color:{delta_color};padding:0.25rem 0.65rem;border-radius:4px;font-size:0.78rem;font-weight:700;display:inline-block;">'
        f"{delta_str}"
        f"</span>"
        f"</div>"
        f'<div style="background:#E5F9FB;border:1px solid rgba(2,191,208,0.3);border-radius:6px;padding:0.4rem 0.75rem;margin-top:0.75rem;font-size:0.72rem;color:#018591;font-weight:600;">'
        f"{uncertainty_text}"
        f"</div>"
        f"</div>"
    )
    st.markdown(card_html, unsafe_allow_html=True)

    # Actual Market Value Comparison Section
    if has_actual:
        act_str = format_currency_eur(actual_value_eur)
        comp_color = "#20A56B" if diff_eur >= 0 else "#E05252"
        actual_html = (
            f'<div class="tm-card" style="margin-top:0.5rem;padding:0.9rem 1.1rem;">'
            f'<div style="display:flex;justify-content:space-between;align-items:center;">'
            f"<div>"
            f'<div style="font-size:0.68rem;color:#8A959E;text-transform:uppercase;letter-spacing:0.8px;font-weight:700;">BENCHMARK BASELINE</div>'
            f"<div style=\"font-size:1.35rem;font-weight:800;color:#17212B;display:flex;align-items:center;gap:0.4rem;font-family:'Manrope',sans-serif;\">"
            f"<span>{act_str}</span>"
            f'<span style="color:#02BFD0;font-size:1rem;">✓</span>'
            f"</div>"
            f"</div>"
            f'<div style="text-align:right;">'
            f'<div style="font-size:0.68rem;color:#8A959E;font-weight:700;text-transform:uppercase;">Variance</div>'
            f"<div style=\"font-size:1.05rem;font-weight:800;color:{comp_color};font-family:'Manrope',sans-serif;\">"
            f"{format_delta_pct(diff_pct)}"
            f"</div>"
            f"</div>"
            f"</div>"
            f"</div>"
        )
        st.markdown(actual_html, unsafe_allow_html=True)
    else:
        empty_html = (
            '<div class="tm-card" style="margin-top:0.5rem;padding:0.75rem;text-align:center;color:#8A959E;font-size:0.75rem;">'
            "Historical benchmark baseline not directly recorded for this exact entry."
            "</div>"
        )
        st.markdown(empty_html, unsafe_allow_html=True)

    # Diagnostics expander if warnings exist
    if result.relevant_data_warnings:
        with st.expander("ℹ️ Engine Coverage & Diagnostics", expanded=False):
            for w in result.relevant_data_warnings:
                st.caption(f"• {w}")
