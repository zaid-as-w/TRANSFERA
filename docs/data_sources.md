# Data Sources and Scientific Provenance

## 1. Primary Historical Data Source: Transfermarkt Datasets

- **Source Name:** Transfermarkt Clean Historical Football Datasets
- **Curator:** David Cariboo (`dcaribou/transfermarkt-datasets`)
- **Repository URL:** [https://github.com/dcaribou/transfermarkt-datasets](https://github.com/dcaribou/transfermarkt-datasets)
- **Distribution Endpoint:** Cloudflare R2 bucket mirror: `https://pub-e682421888d945d684bcae8890b0ec20.r2.dev/data/{table}.csv.gz`
- **Acquired Tables:**
  - `competitions.csv.gz` (65 competitions)
  - `clubs.csv.gz` (796 clubs)
  - `players.csv.gz` (50,149 player profiles)
  - `games.csv.gz` (88,958 match results)
  - `appearances.csv.gz` (1,894,350 match appearances)
  - `player_valuations.csv.gz` (656,301 historical valuations)
  - `club_games.csv.gz` (177,916 club game records)
  - `transfers.csv.gz` (175,165 historical transfers)
  - `countries.csv.gz` (124 countries)
- **Date Coverage:**
  - Valuations: 2000-01-20 to 2026-06-12
  - Games: 2006-06-09 to 2026-07-06
  - Appearances: 2012-07-03 to 2026-06-28
- **Operational Status:**
  Automated upstream scraping was paused in July 2026. The historical dataset is frozen and stable up to early July 2026.
- **Licensing & Usage:**
  Public historical dataset released under CC0: Public Domain / Open Data terms. Commercial redistribution requires compliance with Transfermarkt terms of service.
- **Data Quality Considerations:**
  - Market values reflect crowd-calibrated editorial consensus benchmarks in euros, not contract buyouts or actual fees.
  - Granularity is match-appearance level for appearances, and periodic valuation updates for market values.

---

## 2. Secondary Football Data Source: Football-Data.org API

- **Service Name:** Football-Data.org v4 REST API
- **Documentation:** [https://www.football-data.org/documentation/api](https://www.football-data.org/documentation/api)
- **Coverage:** [https://www.football-data.org/coverage](https://www.football-data.org/coverage)
- **Implementation:**
  Modular client in `src/ingestion/football_data_api.py` with:
  - Local JSON response caching in `data/raw/football_data_cache/`
  - Exponential backoff retry adapter (HTTP 429, 500, 502, 503, 504)
  - Optional `FOOTBALL_DATA_API_KEY` token support
  - Seamless offline degradation (pipeline executes fully from historical raw files when token or network is unavailable)
- **Scope & Limitations:**
  Used for secondary competition registry verification, league codes, and tier structures. Does not provide deep historical player-minute records or granular market values on free tiers.

---

## 3. Financial Environment Sources

### A. Deloitte Football Money League (DFML)
- **Source:** Deloitte Sports Business Group Annual Reports (2020 through 2025 editions)
- **Coverage:** Top European revenue-generating clubs (Real Madrid, Man City, PSG, Barcelona, Man United, Bayern Munich, Liverpool, Tottenham, Chelsea, Arsenal, Juventus, Milan, Inter, Dortmund, Atlético Madrid, Newcastle).
- **Captured Variables:** Total Revenue, Matchday Revenue, Broadcast Revenue, Commercial Revenue (all recorded in EUR).
- **Grain:** Club-season.

### B. UEFA European Club Finance and Investment Landscape (ECFIL)
- **Source:** UEFA Intelligence Centre & Financial Fair Play Compliance Reports
- **Coverage:** League-level aggregate broadcast pools and average club revenues for European first tiers (EPL, La Liga, Serie A, Bundesliga, Ligue 1, Eredivisie, Liga Portugal, Jupiler Pro League, Süper Lig, Scottish Premiership).
- **Methodology Rule:**
  Audited club revenue is strictly separated from league-level macro aggregates. When a club has no audited public report, `has_club_financials` is set to `False` and `financial_aggregation_level` is flagged as `league_fallback` or `missing`. No revenue numbers are ever invented.

