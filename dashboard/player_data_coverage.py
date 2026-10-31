"""UI component for player data coverage and prediction eligibility badges.

Renders Transfermarkt-inspired clean light badges for:
- Source Database: [STAGE 1 DATABASE] or [GLOBAL DATABASE]
- Prediction Status: [STATUS A: PREDICTION AVAILABLE], [STATUS B: LIMITED EVIDENCE], [STATUS C: PROFILE ONLY]
- Data completeness diagnostics and missing field audits.
"""

from __future__ import annotations

import streamlit as st

from src.coverage_manager import CoverageAssessment


def render_coverage_badges(
    assessment: CoverageAssessment,
    compact: bool = False,
) -> None:
    """Render high-contrast badges for database source and prediction status with clean light styling."""
    # Source badge color
    if assessment.source_database == "STAGE 1 DATABASE":
        source_bg = "#E5F9FB"
        source_border = "rgba(2, 191, 208, 0.45)"
        source_color = "#018591"
    else:
        source_bg = "#FFF8E6"
        source_border = "#FFE082"
        source_color = "#B26A00"

    # Status badge color
    if assessment.status_code == "STATUS_A":
        status_bg = "#E8F8F1"
        status_border = "#A5E4C7"
        status_color = "#178352"
        status_label = "PREDICTION AVAILABLE"
    elif assessment.status_code == "STATUS_B":
        status_bg = "#FFF4E5"
        status_border = "#FFD8A8"
        status_color = "#B26A00"
        status_label = "LIMITED EVIDENCE"
    else:
        status_bg = "#F1F3F5"
        status_border = "#DDE1E5"
        status_color = "#495057"
        status_label = "PROFILE ONLY"

    badge_html = f"""
    <div style="display: flex; gap: 0.6rem; align-items: center; margin-bottom: 0.75rem; flex-wrap: wrap;">
        <span style="background: {source_bg}; border: 1px solid {source_border}; color: {source_color};
                     font-size: 0.72rem; font-weight: 700; letter-spacing: 0.04em; padding: 0.25rem 0.6rem;
                     border-radius: 4px; text-transform: uppercase;">
            ◈ {assessment.source_database}
        </span>
        <span style="background: {status_bg}; border: 1px solid {status_border}; color: {status_color};
                     font-size: 0.72rem; font-weight: 700; letter-spacing: 0.04em; padding: 0.25rem 0.6rem;
                     border-radius: 4px; text-transform: uppercase;">
            ● {status_label}
        </span>
    </div>
    """
    st.markdown(badge_html, unsafe_allow_html=True)

    if not compact:
        if assessment.status_code == "STATUS_C":
            st.markdown(
                f"""
                <div style="background: #FFFDF9; border: 1px solid #FFE6C7; border-left: 4px solid #E5A52B; border-radius: 6px;
                            padding: 0.85rem 1.1rem; margin-top: 0.5rem; margin-bottom: 1rem;">
                    <div style="color: #B26A00; font-weight: 700; font-size: 0.88rem; margin-bottom: 0.2rem;">
                        ⚠️ Valuation Restricted
                    </div>
                    <div style="color: #495057; font-size: 0.82rem; line-height: 1.45;">
                        {assessment.message}
                    </div>
                    <div style="color: #8A959E; font-size: 0.75rem; margin-top: 0.4rem;">
                        Missing verified features: <code style="background:#F1F3F5; color:#17212B; padding:2px 4px; border-radius:3px;">{", ".join(assessment.missing_fields)}</code>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        elif assessment.status_code == "STATUS_B" and assessment.diagnostic_warning:
            st.markdown(
                f"""
                <div style="background: #F8FDFF; border: 1px solid #C4F3F8; border-left: 4px solid #02BFD0; border-radius: 6px;
                            padding: 0.85rem 1.1rem; margin-top: 0.5rem; margin-bottom: 1rem;">
                    <div style="color: #018591; font-weight: 700; font-size: 0.88rem; margin-bottom: 0.2rem;">
                        ℹ️ Partial Evidence Diagnostics
                    </div>
                    <div style="color: #495057; font-size: 0.82rem; line-height: 1.45;">
                        {assessment.diagnostic_warning}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
