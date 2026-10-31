# Scientific and Machine Learning Methodology

## 1. Problem Formulation and Target Definition

The primary objective of the valuation engine is answering the real-world question:
> *"Given official player performance, biographical data, and environmental evidence genuinely available on or before reference date $T$, what benchmark market value in euros would be estimated for this player?"*

### Target Variable
The target variable is:
$$Y = \text{historical\_market\_value} \in \mathbb{R}^+ \quad (\text{Euros, EUR})$$
It represents the consensus benchmark recorded by Transfermarkt at the reference date $T$. It is distinct from:
- Realized transfer fees (which incorporate contract duration remaining, release clauses, agent fees, and emergency buyer distress).
- Player wages or release clauses.
- Club operating revenue.

---

## 2. Temporal Design and Leakage Prevention

To guarantee zero data leakage into future events:
1. **Reference Date Cutoff ($T$):** Every player-season example has an explicit reference date $T = \text{valuation\_reference\_date}$.
2. **Feature Window Causality:** Only appearances, minutes, goals, assists, and disciplinary cards occurring strictly on or before $T$ are aggregated:
   $$\text{Minutes}(P, S, T) = \sum_{m \in \text{Matches}(P, S) \mid \text{Date}(m) \le T} \text{Minutes}(m)$$
3. **Age Calculation:** Age is calculated strictly as of reference date $T$, never current age applied retrospectively:
   $$\text{Age}(P, T) = \frac{T - \text{DateOfBirth}(P)}{365.25}$$
4. **Lag Valuation:** Prior market value $V_{\text{prev}}$ must have an evaluation date strictly *prior* to the start of the season ($< \text{July 1}$ of season $S$). Future in-season or next-season valuations are barred from input features.
5. **No Cartesian Expansion:** Appearance rows are aggregated to the analytical grain `(player_id, season, competition_id, club_id)` before joining valuations, guaranteeing that individual match rows never duplicate the target.

---

## 3. League Strength and Cross-League Elo Calibration

Rather than applying arbitrary manual coefficients (e.g. $\text{EPL} = 1.0, \text{LaLiga} = 0.9$), the engine calibrates competition quality through an empirical **Cross-League Elo System** using over 3,900 competitive European tournament matches (Champions League, Europa League, Conference League, Super Cup) played between clubs from different domestic leagues between 2012 and 2025.

### Model Formulation:
- Initial club rating: $R_0 = 1500.0$
- Home Field Advantage: $\text{HFA} = 65.0$
- Expected Match Outcome:
  $$E_{\text{home}} = \frac{1}{1 + 10^{(R_{\text{away}} - (R_{\text{home}} + \text{HFA})) / 400}}$$
- Rating Update:
  $$\Delta R_{\text{home}} = K \cdot M(\Delta \text{goals}) \cdot (S_{\text{home}} - E_{\text{home}})$$
  Where $K = 32.0$ for continental fixtures and $20.0$ for domestic matches. The goal margin multiplier $M(\Delta \text{goals}) = \ln(|\Delta \text{goals}| + 1.0)$ accounts for victory margin.
- **League-Level Aggregation:**
  $$\text{Mean Elo}(C, S) = \frac{1}{|K_C|} \sum_{k \in K_C} R_k(S)$$
  $$\text{Competition Strength}(C, S) = \frac{\text{Mean Elo}(C, S)}{1500.0}$$
  $$\text{Top 4 Strength}(C, S) = \frac{\text{Top 4 Mean Elo}(C, S)}{1500.0}$$

### Competition Intensity and Competitive Balance:
- **Card Intensity:** Disciplinary cards per match in league $C$ and season $S$.
- **Goal Tempo:** Mean total goals per match in league $C$ and season $S$.
- **Parity Index:**
  $$\text{Parity Index}(C, S) = \frac{1.0}{1.0 + \sigma(\text{Goal Difference})}$$

---

## 4. Target Transformation and Preprocessing

Market values follow a heavy log-normal distribution, ranging from €100,000 to over €200,000,000. Regressing raw euros directly causes linear models to over-weight elite outliers and predict negative values for low-tier players.

The pipeline applies a log1p transformation to the target:
$$z = \ln(1 + y)$$
Predictions $\hat{z}$ are mapped back to euros via the inverse transform:
$$\hat{y} = \max\left(10000.0, \; \exp(\hat{z}) - 1\right)$$

### Preprocessing Pipelines:
All feature transformations are encapsulated within `sklearn.compose.ColumnTransformer` inside an immutable pipeline:
- Numeric features: Median imputation followed by `RobustScaler`.
- Categorical features: Constant imputation followed by `OneHotEncoder(handle_unknown='ignore')`.

Imputation and scaling parameters are strictly fitted **only on the training split**, preventing test contamination.

---

## 5. Model Architectures and Empirical Selection

The engine evaluates and compares three progressive paradigms:

- **Model A: Global Baseline**
  Includes biographical features (age, position, foot, height) and on-pitch performance statistics (appearances, minutes, goals, assists, cards, per-90s, lag valuation). Evaluates pure player-level signals without competition or financial context.

- **Model B: Competition-Aware Engine**
  Expands Model A with cross-league calibrated Elo strength, top-4 concentration, internal league competitive balance, card/goal intensity, observed club operating revenue, league average broadcast pool, and country context.

- **Model C: Competition-Adjusted Model**
  Regularized gradient boosted decision trees (`HistGradientBoostingRegressor`) with explicit depth limits, minimum leaf samples, and L2 regularization to capture non-linear interactions between competition tier and performance rates.

### Selection Criterion:
Models are benchmarked on out-of-time validation data (Season 2022/23). `Model_B_HistGradientBoosting` achieved the highest validation performance:
- Validation MAE: **€1,775,860** (vs baseline €4,995,148 — a 64.5% error reduction)
- Validation R²: **0.8399**

---

## 7. Cross-League Transfer Mechanics & Zero-Minute Behavior

### A. Cross-League Simulation Dynamics
When evaluating a player under `predict_cross_league_scenario(C_src, C_dest)`:
- Fixed variables: Biographical attributes (age, position, foot, height) and historical match counting metrics (minutes, goals, assists, cards).
- Swapped variables: Competition strength, competitive balance, league goal-scoring tempo, card intensity, and club financial context.

**Why a Ligue 1 to Premier League move can show a modest negative delta (-8.4%) without an assigned elite club:**
- Premier League categorical coefficient, overall league revenue (€345M vs €133M), and top-4 Elo strength all exert positive upward adjustments (+€3.6M total).
- However, the Premier League features a higher goal tempo (3.28 goals/match vs 2.70 in Ligue 1) and a wider club Elo spread (156.3 vs 99.3). In an unassigned club context (where club revenue defaults to median without an elite revenue boost), scoring 12 goals in a 2.70 goals/game league represents a higher individual share of league output than in a 3.28 goals/game league.
- When an elite Premier League club is explicitly specified (e.g. Manchester City or Arsenal with observed €700M+ revenue), the club financial context substantially offsets this macro adjustment.

### B. Zero-Minute Reserve Players
For players with 0 appearances and 0 minutes played:
- The €250,000 output is **not** a hardcoded heuristic or clip floor (the pipeline clip floor is €25,000).
- It is the model's regression prediction ($\exp(12.4139) - 1 \approx \text{€}246,214$, rounded to €250,000) based on age, position, and league tier priors for squad-depth bench players.
- The prediction service flags this explicitly via `relevant_data_warnings`, alerting users that the valuation is a squad reserve prior rather than active in-match form.

---

## 8. Uncertainty Estimation and Dashboard Presentation Policy

### Mandatory Scientific Standard:
1. **No Arbitrary Parametric Confidence Intervals:** The Stage 2 dashboard MUST NOT display uncalibrated "95% confidence intervals" (such as $\hat{y} \pm 1.96 \cdot \hat{\sigma}$ or heuristic $\pm 10\%$ bands). Market value residuals are non-Gaussian, right-skewed, and heavily heteroskedastic (variance scales with player valuation tier).
2. **Empirical Benchmarking Standard:** The UI must display:
   - The model point estimate ($\hat{y}_{\text{EUR}}$).
   - The empirical held-out test Mean Absolute Error (MAE) specific to the competition (e.g. EPL: ±€5.96M, Bundesliga: ±€3.26M, Ligue 1: ±€2.68M).
   - The competition reliability status (`SUPPORTED`, `PARTIAL`, `INSUFFICIENT`).
   - Relevant diagnostic data warnings (e.g., missing club financials, zero match minutes).

   - **Environment Swap:** Only destination league strength, destination competitive balance, intensity, and destination club revenue context are substituted.
   - Computes benchmark valuation delta (€ and %) while outputting explicit warnings if the destination league has limited cross-league tournament evidence.

