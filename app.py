"""TRANSFERA — The Global Football Market Intelligence Platform.

Main application orchestrator integrating Stage 1 HistGradientBoosting Machine Learning
Valuation Engine with an Aqua PES-inspired professional sports intelligence interface.
"""

import logging
from pathlib import Path

import streamlit as st

from dashboard.components.sidebar import render_sidebar
from dashboard.data_service import DataService
from dashboard.pages.comparison import render_comparison_page
from dashboard.pages.countries import render_countries_page
from dashboard.pages.home import render_home_page
from dashboard.pages.insights import render_insights_page
from dashboard.pages.leagues import render_leagues_page
from dashboard.pages.players import render_players_page
from dashboard.pages.predictor import render_predictor_page
from dashboard.prediction_service import DashboardPredictionService

# Configure page layout and TRANSFERA metadata
st.set_page_config(
    page_title="TRANSFERA | The Global Football Market Intelligence Platform",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("transfera")

# Inject custom TRANSFERA Aqua CSS
CSS_PATH = Path(__file__).parent / "dashboard" / "styles" / "main.css"
if CSS_PATH.exists():
    with open(CSS_PATH, encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
else:
    logger.warning("Custom CSS file not found at %s", CSS_PATH)


@st.cache_resource(show_spinner=False)
def get_services() -> tuple[DataService, DashboardPredictionService]:
    """Initialize and cache singleton data and prediction services."""
    d_service = DataService()
    p_service = DashboardPredictionService()
    return d_service, p_service


def main() -> None:
    """Main application orchestrator and routing loop."""
    try:
        data_service, pred_service = get_services()
    except Exception as e:
        st.error(f"Failed to initialize core data or prediction service: {e}")
        logger.exception("Service initialization failure:")
        return

    # Render sidebar navigation & get active page
    active_page = render_sidebar()

    # Page Router
    if active_page == "Home":
        render_home_page(data_service, pred_service)
    elif active_page == "Players":
        render_players_page(data_service, pred_service)
    elif active_page == "Leagues":
        render_leagues_page(data_service, pred_service)
    elif active_page == "Countries":
        render_countries_page(data_service, pred_service)
    elif active_page == "Value Predictor":
        render_predictor_page(data_service, pred_service)
    elif active_page == "Player Comparison":
        render_comparison_page(data_service, pred_service)
    elif active_page == "Analytics & Insights":
        render_insights_page(data_service, pred_service)
    else:
        st.warning(f"Unknown navigation view: {active_page}. Redirecting to Home...")
        render_home_page(data_service, pred_service)


if __name__ == "__main__":
    main()
