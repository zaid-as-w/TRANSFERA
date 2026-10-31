# Data Dictionary

## 1. Processed Player-Season Feature Table (`player_season_features.parquet`)

The analytical table is keyed on the composite grain: `(player_id, season, competition_id, club_id)`.

| Column Name | Data Type | Units / Range | Description & Temporal Alignment |
| :--- | :--- | :--- | :--- |
| `player_id` | `int64` | Identifier | Unique Transfermarkt player identifier. |
| `season` | `int64` | `2013` - `2024` | Season calendar year (e.g. `2021` represents the 2021/22 season). |
| `competition_id` | `object` | Code (e.g. `GB1`) | Domestic league or tournament competition identifier. |
| `club_id` | `int64` | Identifier | Club identifier for which the player appeared in this competition and season. |
| `historical_market_value` | `float64` | Euros (€) | **Target Variable**. Recorded market value at reference date `valuation_reference_date`. Strictly strictly positive. |
| `valuation_reference_date` | `datetime64[ns]` | ISO Date | Exact date the target market valuation benchmark was recorded. Features strictly use data on or before this date. |
| `previous_market_value` | `float64` | Euros (€) | Latest market valuation recorded strictly *prior* to the start of this season ($< \text{July 1}$). Null if debut season. |
| `previous_valuation_date` | `datetime64[ns]` | ISO Date | Exact date of the prior market valuation. |
| `has_previous_valuation` | `bool` | `True` / `False` | Boolean indicator whether a valid prior valuation exists. |
| `age_at_reference_date` | `float64` | Years | $(T_{\text{ref}} - \text{date\_of\_birth}) / 365.25$. Player age at prediction reference date. |
| `position` | `object` | Category | General position: `Attack`, `Midfield`, `Defender`, `Goalkeeper`. |
| `sub_position` | `object` | Category | Detailed position (e.g. `Left Winger`, `Centre-Forward`, `Central Midfield`). |
| `foot` | `object` | Category | Preferred foot: `Right`, `Left`, `Both`, `Unknown`. |
| `height_in_cm` | `float64` | cm ($150 - 210$) | Player physical height. |
| `country_of_citizenship` | `object` | Country | Player primary nationality. |
| `appearances` | `int64` | $\ge 1$ | Total official appearances in this competition on or before $T_{\text{ref}}$. |
| `minutes_played` | `int64` | $\ge 90$ | Total minutes played on or before $T_{\text{ref}}$. |
| `goals` | `int64` | $\ge 0$ | Total goals scored in this competition on or before $T_{\text{ref}}$. |
| `assists` | `int64` | $\ge 0$ | Total assists registered in this competition on or before $T_{\text{ref}}$. |
| `goals_per_90` | `float64` | Rate | $(\text{goals} / \text{minutes\_played}) \times 90.0$. Computed only when minutes $> 0$. |
| `assists_per_90` | `float64` | Rate | $(\text{assists} / \text{minutes\_played}) \times 90.0$. Computed only when minutes $> 0$. |
| `cards` | `int64` | $\ge 0$ | Total yellow + red cards on or before $T_{\text{ref}}$. |
| `cards_per_90` | `float64` | Rate | $(\text{cards} / \text{minutes\_played}) \times 90.0$. |
| `minutes_per_appearance` | `float64` | Minutes | Average match duration per appearance ($\text{minutes} / \text{appearances}$). |
| `competition_strength` | `float64` | Ratio ($0.8 - 1.3$) | Mean league Elo normalized relative to baseline $1500.0$. Derived from cross-league match evidence. |
| `competition_mean_elo` | `float64` | Rating ($1200 - 1800$) | Cross-league calibrated Elo rating of all active clubs in this competition during season. |
| `competition_top4_strength`| `float64` | Ratio | Top 4 clubs' average calibrated Elo relative to $1500.0$. |
| `competition_spread_elo` | `float64` | Rating Spread | Standard deviation of club Elo ratings within the league (internal competitive balance). |
| `club_elo` | `float64` | Rating | Club-specific cross-league calibrated Elo rating. |
| `league_goals_per_match` | `float64` | Goals/Game | Average match goal tempo in this league and season. |
| `league_cards_per_match` | `float64` | Cards/Game | Average disciplinary card intensity in this league and season. |
| `competitive_balance_index` | `float64` | Index ($0 - 1$) | League parity index: $1.0 / (1.0 + \sigma_{\text{goal\_diff}})$. |
| `club_revenue_eur` | `float64` | Euros (€) | Observed club total annual revenue (Deloitte Money League / audited accounts). Null if unfiled. |
| `league_average_revenue_eur`| `float64` | Euros (€) | Average club revenue for the competition (UEFA Club Finance report). |
| `has_club_financials` | `bool` | `True` / `False` | Boolean indicating whether observed club revenue exists. |
| `has_league_financials` | `bool` | `True` / `False` | Boolean indicating whether league revenue benchmarks exist. |
| `financial_aggregation_level`| `object` | Enum | `club_observed`, `league_fallback`, or `missing`. |
| `source_coverage_score` | `float64` | $[0.0, 1.0]$ | Data completeness metric combining minutes, lag valuation, and financial evidence. |

---

## 2. Competition Registry Table (`data/metadata/competition_registry.json`)

| Field | Type | Description |
| :--- | :--- | :--- |
| `competition_id` | `str` | Competition identifier code. |
| `competition_name` | `str` | Official name of tournament or league. |
| `country` | `str` | Host country or geographic area. |
| `confederation` | `str` | Governing confederation (`UEFA`, `CONMEBOL`, `CONCACAF`, `AFC`, `CAF`). |
| `competition_type` | `str` | `domestic_league`, `domestic_cup`, `international_cup`, `other`. |
| `division` | `str` | League division tier (`1` for top-flight). |
| `currency` | `str` | Base evaluation currency (`EUR`). |
| `matches_available` | `int` | Count of historical match results in games table. |
| `player_statistics_available`| `int` | Count of player appearances recorded. |
| `valuation_coverage` | `int` | Count of player valuations recorded in this competition. |
| `financial_data_coverage` | `bool` | Whether verified audited or league financial reports exist. |
| `strength_estimate_available` | `bool` | Whether $\ge 500$ matches exist for cross-league Elo calibration. |
| `reliability_status` | `str` | Status: `SUPPORTED`, `PARTIAL`, `INSUFFICIENT_DATA`, `UNAVAILABLE`. |

