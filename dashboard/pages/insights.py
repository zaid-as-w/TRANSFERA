"""Analytics & Insights Page: TRANSFERA Champion ML Evaluation, Architecture Leaderboard, and League Performance."""

import pandas as pd
import streamlit as st

from dashboard.components.header import render_header
from dashboard.data_service import DataService
from dashboard.formatting import format_currency_eur
from dashboard.prediction_service import DashboardPredictionService


def render_insights_page(data_service: DataService, pred_service: DashboardPredictionService) -> None:
    """Render the Machine Learning Analytics & Scientific Insights page in clean light style."""
    all_comps = data_service.get_competitions()
    render_header(all_comps)

    eval_data = data_service.eval_metrics
    global_m = eval_data.get("global_metrics", {})
    comp_metrics = eval_data.get("competitions", {})

    st.markdown(
        """
        <div style="margin-bottom: 1.25rem;">
            <div style="font-size:0.72rem;font-weight:700;letter-spacing:1px;color:#02BFD0;text-transform:uppercase;font-family:'Inter',sans-serif;">TRANSFERA RESEARCH LABS</div>
            <h1 style="margin: 0.2rem 0; font-size: 1.9rem; font-weight: 800; letter-spacing: -0.5px; text-transform:uppercase; font-family:'Manrope',sans-serif; color:#17212B;">
                ANALYTICS & <span style="color:#02BFD0;">MODEL INSIGHTS</span>
            </h1>
            <p style="margin: 0.2rem 0 1rem 0; color: #66727D; font-size: 0.92rem;">
                Empirical evaluation results, out-of-time test metrics, league breakdown, and scientific architecture behind the TRANSFERA Valuation Engine.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 1. Champion Model Header & Scorecard
    mae_str = format_currency_eur(global_m.get("mae_eur", 1994895))
    r2_str = f"{global_m.get('r2', 0.8332):.4f}"
    rmse_str = format_currency_eur(global_m.get("rmse_eur", 5249453))
    med_str = format_currency_eur(global_m.get("median_ae_eur", 443018))
    m_name = eval_data.get("model_name", "Model_B_HistGradientBoosting")
    m_ver = eval_data.get("model_version", "1.0.0")
    s_count = f"{global_m.get('sample_count', 12408):,}"

    header_html = (
        '<div class="tm-card" style="padding: 1.1rem 1.25rem; margin-bottom: 0.85rem; border-left: 4px solid #02BFD0;">'
        '<div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 0.5rem;">'
        "<div>"
        '<span style="background: #E5F9FB; border: 1px solid rgba(2, 191, 208, 0.4); color: #018591; font-size: 0.72rem; font-weight: 700; padding: 0.22rem 0.55rem; border-radius: 4px; text-transform: uppercase;">'
        "Champion Pipeline"
        "</span>"
        f"<h2 style=\"margin: 0.35rem 0 0 0; font-size: 1.35rem; font-weight: 800; color: #17212B; font-family:'Manrope',sans-serif;\">{m_name} (v{m_ver})</h2>"
        "</div>"
        f'<div style="text-align: right; color: #8A959E; font-size: 0.8rem;">Evaluated on <b>{s_count}</b> Out-of-Time Test Records (2023–2025)</div>'
        "</div>"
        "</div>"
    )
    st.markdown(header_html, unsafe_allow_html=True)

    # 4 Visual KPI Cards matching the exact TRANSFERA design specification
    c_mae, c_r2, c_rmse, c_med = st.columns(4)

    card_style = (
        "padding: 1.1rem 0.8rem; text-align: center; border-radius: 8px; "
        "border: 1px solid #E2E6E9; background: #FFFFFF; box-shadow: 0 1px 3px rgba(0,0,0,0.03);"
    )

    with c_mae:
        st.markdown(
            f'<div class="tm-card" style="{card_style}">'
            '<div style="font-size: 0.74rem; color: #8A959E; font-weight: 800; letter-spacing: 0.5px; text-transform: uppercase;">TEST MAE</div>'
            f"<div style=\"font-size: 1.9rem; font-weight: 800; color: #02BFD0; font-family:'Manrope',sans-serif; margin: 0.3rem 0;\">{mae_str}</div>"
            '<div style="font-size: 0.74rem; color: #20A56B; font-weight: 700;">63.7% Better than Baseline</div>'
            "</div>",
            unsafe_allow_html=True,
        )

    with c_r2:
        st.markdown(
            f'<div class="tm-card" style="{card_style}">'
            '<div style="font-size: 0.74rem; color: #8A959E; font-weight: 800; letter-spacing: 0.5px; text-transform: uppercase;">TEST R²</div>'
            f"<div style=\"font-size: 1.9rem; font-weight: 800; color: #17212B; font-family:'Manrope',sans-serif; margin: 0.3rem 0;\">{r2_str}</div>"
            '<div style="font-size: 0.74rem; color: #018591; font-weight: 700;">Out-of-Time Generalization</div>'
            "</div>",
            unsafe_allow_html=True,
        )

    with c_rmse:
        st.markdown(
            f'<div class="tm-card" style="{card_style}">'
            '<div style="font-size: 0.74rem; color: #8A959E; font-weight: 800; letter-spacing: 0.5px; text-transform: uppercase;">TEST RMSE</div>'
            f"<div style=\"font-size: 1.9rem; font-weight: 800; color: #3185C7; font-family:'Manrope',sans-serif; margin: 0.3rem 0;\">{rmse_str}</div>"
            '<div style="font-size: 0.74rem; color: #3185C7; font-weight: 700;">Penalty on Outliers</div>'
            "</div>",
            unsafe_allow_html=True,
        )

    with c_med:
        st.markdown(
            f'<div class="tm-card" style="{card_style}">'
            '<div style="font-size: 0.74rem; color: #8A959E; font-weight: 800; letter-spacing: 0.5px; text-transform: uppercase;">MEDIAN ABS ERROR</div>'
            f"<div style=\"font-size: 1.9rem; font-weight: 800; color: #E5A52B; font-family:'Manrope',sans-serif; margin: 0.3rem 0;\">{med_str}</div>"
            '<div style="font-size: 0.74rem; color: #B26A00; font-weight: 700;">Typical Player Deviation</div>'
            "</div>",
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height: 0.9rem;'></div>", unsafe_allow_html=True)

    # 2. Out-of-Time League Breakdown Table
    st.markdown(
        """
        <div style="margin-bottom: 0.8rem;">
            <h3 style="margin: 0; font-size: 1.15rem; font-weight: 800; color: #17212B; font-family:'Manrope',sans-serif;">
                🏆 League-by-League Generalization Performance
            </h3>
            <p style="margin: 0.2rem 0; color: #66727D; font-size: 0.85rem;">
                Model accuracy across Europe's Top 5 and domestic leagues evaluated on strictly unseen out-of-time seasons.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    league_rows = []
    for cid, m_info in comp_metrics.items():
        if isinstance(m_info, dict):
            league_rows.append(
                {
                    "League ID": cid,
                    "Competition": m_info.get("competition_name", cid).replace("-", " ").title(),
                    "Country": m_info.get("country", "Global"),
                    "Test Samples": m_info.get("sample_count", 0),
                    "Test MAE": format_currency_eur(m_info.get("mae_eur", 0.0)),
                    "Test RMSE": format_currency_eur(m_info.get("rmse_eur", 0.0)),
                    "Median Error": format_currency_eur(m_info.get("median_ae_eur", 0.0)),
                    "Test R²": round(m_info.get("r2", 0.0), 4),
                }
            )

    if league_rows:
        df_l_eval = pd.DataFrame(league_rows).sort_values("Test Samples", ascending=False)
        st.dataframe(
            df_l_eval,
            hide_index=True,
            use_container_width=True,
        )

    # 3. Model Architecture Leaderboard
    st.markdown("<hr style='border:none; border-top:1px solid #E2E6E9; margin: 1.25rem 0;'>", unsafe_allow_html=True)
    st.markdown(
        """
        <div style="margin-bottom: 0.8rem;">
            <h3 style="margin: 0; font-size: 1.15rem; font-weight: 800; color: #17212B; font-family:'Manrope',sans-serif;">
                🥊 Machine Learning Model Tournament Leaderboard
            </h3>
            <p style="margin: 0.2rem 0; color: #66727D; font-size: 0.85rem;">
                Trained and cross-validated on identical historical data to scientifically select the champion pipeline.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    models_data = [
        {
            "Model": "Model B: HistGradientBoosting (Champion)",
            "Val MAE": "€1.78M",
            "Val RMSE": "€4.67M",
            "Val R²": 0.8399,
            "Features": "32 (All + Context)",
            "Status": "🏆 Champion",
        },
        {
            "Model": "Model B: Random Forest",
            "Val MAE": "€1.86M",
            "Val RMSE": "€4.93M",
            "Val R²": 0.8212,
            "Features": "32 (All + Context)",
            "Status": "Runner-up",
        },
        {
            "Model": "Model A: HistGradientBoosting",
            "Val MAE": "€1.83M",
            "Val RMSE": "€4.85M",
            "Val R²": 0.8270,
            "Features": "16 (Player Only)",
            "Status": "Ablated",
        },
        {
            "Model": "Baseline: Historical Valuation Persistence",
            "Val MAE": "€5.00M",
            "Val RMSE": "€12.45M",
            "Val R²": -0.1381,
            "Features": "1 (Prior Value)",
            "Status": "Baseline",
        },
        {
            "Model": "Model B: Ridge Regression",
            "Val MAE": "€107.3M",
            "Val RMSE": "€5,666M",
            "Val R²": -235913.0,
            "Features": "32 (All + Context)",
            "Status": "Diverged",
        },
    ]
    st.dataframe(pd.DataFrame(models_data), hide_index=True, use_container_width=True)

    # 4. Scientific Architecture & Defensibility Panels
    st.markdown("<hr style='border:none; border-top:1px solid #E2E6E9; margin: 1.25rem 0;'>", unsafe_allow_html=True)
    st.markdown(
        """
        <div style="margin-bottom: 0.8rem;">
            <h3 style="margin: 0; font-size: 1.15rem; font-weight: 800; color: #17212B; font-family:'Manrope',sans-serif;">
                🔬 Scientific Defensibility & Integrity Standards
            </h3>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c_note1, c_note2 = st.columns(2)

    with c_note1:
        st.markdown(
            """
            <div class="tm-card" style="padding: 1.1rem; height: 100%; border-left: 3.5px solid #02BFD0;">
                <div style="font-size: 0.88rem; font-weight: 700; color: #02BFD0; margin-bottom: 0.4rem;">
                    1. Temporal Data Leakage Prevention
                </div>
                <p style="font-size: 0.82rem; color: #66727D; line-height: 1.5; margin: 0;">
                    To prevent lookahead bias, all features are indexed to a specific historical reference date.
                    Training strictly uses seasons &le; 2021, validation uses 2022, and final testing uses 2023–2025.
                    No future performances or subsequent transfer fees leak into any past player valuation record.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c_note2:
        st.markdown(
            """
            <div class="tm-card" style="padding: 1.1rem; height: 100%; border-left: 3.5px solid #20A56B;">
                <div style="font-size: 0.88rem; font-weight: 700; color: #20A56B; margin-bottom: 0.4rem;">
                    2. Empirical Uncertainty vs Arbitrary Intervals
                </div>
                <p style="font-size: 0.82rem; color: #66727D; line-height: 1.5; margin: 0;">
                    Transfer market valuations follow non-Gaussian, fat-tailed Pareto distributions. Displaying an uncalibrated Gaussian 95% confidence interval is scientifically misleading.
                    Instead, TRANSFERA publishes the exact empirical test MAE (±€1.99M globally, ±€5.96M in EPL) benchmarked on 12,408 held-out out-of-time test observations.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
