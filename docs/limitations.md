# System Limitations and Stage 2 Roadmap

## 1. Domain and Data Limitations

### A. Target Benchmark vs Realized Transfer Fees
The model predicts recorded market valuation benchmarks in euros. It does **not** estimate the exact fee negotiated between clubs in a transaction. Realized transfer fees reflect commercial variables that are outside public match box scores:
- Remaining contract length (e.g., a player in their final contract year transfers at a steep discount; a player on a 5-year extension commands a substantial premium).
- Release buyout clauses.
- Club bargaining leverage, financial distress, or urgent deadline-day bidding wars.
- Agent commissions and sell-on percentage clauses.

### B. Upstream Dataset Cutoff
The Transfermarkt automated acquisition pipeline paused automated updates in mid-July 2026. The historical raw files reflect games through July 6, 2026, and player valuations through June 12, 2026. The 2026/27 domestic season is not covered.

### C. Financial Filing Asymmetry
Audited club financial statements (operating revenue, wage bills, matchday/broadcast split) are published primarily for elite European clubs appearing in the Deloitte Football Money League or UEFA compliance catalogs. For smaller domestic clubs, the engine applies verified league-level macro fallbacks (`financial_aggregation_level: 'league_fallback'`). While transparent and leakage-safe, this introduces higher residual variance for lower-tier clubs.

### D. Advanced Spatial Telemetry
The bulk historical source does not contain high-frequency tracking telemetry, expected goals (xG), expected assists (xA), progressive passes, or pressing actions. Performance metrics rely on official match appearances, minutes, goals, assists, and cards.

---

## 2. Demographic and Cohort Specific Error Patterns

From the out-of-time evaluation across 12,408 test observations:
- **Young Breakout Players (U21):** Highest error variance (MAE = €3,013,673, R² = 0.6955). Young players experiencing rapid multi-million euro value surges across few appearances exhibit speculative volatility that historical lag models under-anticipate.
- **Elite Tier (€40M+ Value Band):** The extreme upper tail contains superstar valuations with significant market asymmetry. While the log-target prevents catastrophic under-estimates, absolute euro errors are naturally higher for €100M+ assets.
- **Leagues with Limited Continental Tournament Evidence:** For competitions with fewer than 50 cross-league matches (e.g. non-European domestic leagues), Elo ratings cannot be as tightly calibrated against UEFA competitions. The system outputs explicit warnings when evaluating such leagues.

---

## 3. Uncertainty Estimation and Dashboard Presentation Policy

### Mandatory Scientific Standard for Stage 2:
- **No Arbitrary Parametric Confidence Intervals:** The dashboard must NOT render pseudo-confidence intervals (e.g., claiming a "95% confidence interval") based on arbitrary standard deviation multipliers. Market valuation errors are strictly heteroskedastic and right-skewed.
- **Empirical Context:** Predictions must be accompanied by the empirical out-of-time test MAE for the evaluated league and position group, alongside explicit data quality warnings (e.g. zero minutes played, unlisted club financials).

---

## 4. Stage 2 Technical Roadmap

1. **Contract Expiration and Duration Features:** Integrate contract expiration dates from `players.csv` to model contract-depreciation curves.
2. **Transfer Fee Joint Modeling:** Train a dual-head engine that predicts the Transfermarkt valuation benchmark alongside a separate transfer fee multiplier model using `transfers.csv.gz`.
3. **API Real-Time Refresh Adapter:** Connect verified live APIs (such as Football-Data.org paid tier or Wyscout/StatsBomb feeds) for continuous in-season updating.
4. **Interactive Dashboard:** Build the Stage 2 user interface (Streamlit / React) with player comparison tools, cross-league transfer scenario simulations, and club roster valuations.

