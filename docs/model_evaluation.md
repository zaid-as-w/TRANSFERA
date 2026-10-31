# Model Evaluation and Generalization Report

**Model Name:** `Model_B_HistGradientBoosting`  
**Model Version:** `1.0.0`  
**Evaluation Date:** 2026-10-29T18:11:34.260829+00:00  
**Evaluation Window:** 2023-12-05 to 2025-07-11 (Seasons 2023-2024)  
**Held-out Test Samples:** 12,408  

## 1. Global Performance Overview

| Metric | Model Estimate | Dummy Baseline (Median) | Improvement |
| :--- | :--- | :--- | :--- |
| **MAE (€)** | **€1,994,895.87** | €5,499,848.08 | **63.7% reduction** |
| **RMSE (€)** | **€5,249,453.94** | €13,755,779.65 | **61.8% reduction** |
| **Median AE (€)** | **€443,018.50** | €1,000,000.00 | **55.7% reduction** |
| **R² Score** | **0.8332** | -0.1453 | **+0.9785** |

## 2. Competition-Specific Evaluation

| Competition | Name | Country | Samples | MAE (€) | RMSE (€) | Median AE (€) | R² Score | MAE % of Baseline |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `GB1` | premier-league | England | 1,035 | €5,955,961.89 | €10,101,560.53 | €2,924,533.66 | 0.7958 | 29.01% |
| `ES1` | laliga | Spain | 986 | €4,227,725.78 | €10,092,382.53 | €1,290,103.54 | 0.7631 | 44.85% |
| `IT1` | serie-a | Italy | 980 | €3,400,637.14 | €6,247,529.68 | €1,400,774.70 | 0.7796 | 38.7% |
| `L1` | bundesliga | Germany | 851 | €3,259,844.49 | €6,524,883.95 | €1,229,523.76 | 0.8245 | 34.97% |
| `FR1` | ligue-1 | France | 814 | €2,681,015.01 | €5,682,347.86 | €1,061,601.97 | 0.8281 | 33.18% |
| `NL1` | eredivisie | Netherlands | 833 | €1,362,276.44 | €3,052,642.20 | €430,422.71 | 0.7399 | 49.28% |
| `PO1` | liga-portugal | Portugal | 887 | €1,346,193.92 | €3,797,513.12 | €377,415.66 | 0.7834 | 39.98% |
| `BE1` | jupiler-pro-league | Belgium | 717 | €1,066,357.30 | €2,216,445.83 | €472,457.40 | 0.6440 | 50.68% |
| `TR1` | super-lig | Türkiye | 907 | €912,876.89 | €2,107,368.93 | €392,061.69 | 0.7291 | 50.16% |
| `GR1` | super-league-1 | Greece | 702 | €363,661.75 | €1,076,979.41 | €83,942.47 | 0.7650 | 28.7% |
| `RU1` | premier-liga | Russia | 809 | €602,013.21 | €1,105,163.87 | €293,928.24 | 0.8754 | 35.15% |

## 3. Position-Specific Error Distribution

| Position | Sample Count | MAE (€) | RMSE (€) | Median AE (€) | R² Score |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Attack** | 3,415 | €2,465,203.37 | €6,683,227.71 | €516,030.98 | 0.8151 |
| **Defender** | 4,326 | €1,712,187.60 | €4,018,050.84 | €396,820.46 | 0.8351 |
| **Goalkeeper** | 1,088 | €1,105,447.23 | €2,611,183.71 | €249,335.21 | 0.8420 |
| **Midfield** | 3,579 | €2,158,242.05 | €5,597,348.11 | €495,880.92 | 0.8480 |

## 4. Age Group Error Distribution

| Age Group | Sample Count | MAE (€) | RMSE (€) | Median AE (€) | R² Score |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **U21 (<21)** | 1,115 | €3,013,673.03 | €7,504,440.44 | €888,887.66 | 0.6955 |
| **21-24** | 3,709 | €2,666,574.32 | €6,417,857.88 | €638,366.32 | 0.8247 |
| **25-28** | 3,910 | €2,204,746.77 | €5,383,816.43 | €534,204.67 | 0.8558 |
| **29-32** | 2,537 | €987,635.30 | €2,203,671.52 | €275,181.77 | 0.9006 |
| **33+** | 1,137 | €330,613.66 | €789,314.20 | €105,725.05 | 0.8674 |

## 5. Market Value Band Error Distribution

| Value Band | Sample Count | MAE (€) | RMSE (€) | Median AE (€) | R² Score |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **< €1M** | 4,808 | €226,813.86 | €394,741.09 | €124,462.49 | -1.8656 |
| **€1M - €5M** | 4,146 | €876,730.63 | €1,327,483.74 | €557,838.46 | -0.7239 |
| **€5M - €15M** | 1,968 | €2,800,944.89 | €3,761,360.48 | €2,077,526.82 | -1.0735 |
| **€15M - €40M** | 1,120 | €7,103,174.38 | €9,456,739.45 | €5,584,799.27 | -1.1373 |
| **€40M+** | 366 | €17,921,876.64 | €23,716,483.04 | €14,071,329.60 | 0.3260 |

## 6. Cross-League Mover Generalization

| Cohort | Sample Count | MAE (€) | RMSE (€) | Median AE (€) | R² Score |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Cross-League Transfers** | 2,648 | €2,456,900.11 | €6,293,008.23 | €627,656.04 | 0.8211 |
| **League Retained** | 4,786 | €2,030,936.27 | €5,302,826.48 | €395,855.68 | 0.8740 |

## 7. Sensitivity and Generalization Tests

### A. Missing Financial Data Sensitivity
- **Clubs with Published Financial Accounts (DFML/UEFA):** MAE = €9,125,195.68, R² = 0.7428 (371 samples)
- **Clubs with League Fallback Financials:** MAE = €1,775,128.38, R² = 0.8216 (12,037 samples)

### B. Unseen-Player Generalization
- **Out-of-sample players:** MAE = €1,390,297.94, RMSE = €3,925,609.35, R² = 0.8566 (13,979 samples)
