# Data Inventory and Schema Discovery Report

**Generated:** 2026-10-29T17:36:30.224495+00:00  
**Primary Source:** [Transfermarkt Datasets (dcaribou/transfermarkt-datasets)](https://github.com/dcaribou/transfermarkt-datasets)  
**Distribution Endpoint:** `https://pub-e682421888d945d684bcae8890b0ec20.r2.dev/data/`  

## 1. Source Table Summary

| Table Name | File Format | File Size (MB) | Record Count | Distinct Players | Distinct Clubs | Date Range | Usable |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `competitions` | `csv.gz` | 0.0 MB | 65 | N/A | N/A | N/A | Yes |
| `clubs` | `csv.gz` | 0.05 MB | 796 | N/A | 796 | N/A | Yes |
| `players` | `csv.gz` | 4.19 MB | 50,149 | 50,149 | N/A | N/A | Yes |
| `games` | `csv.gz` | 4.76 MB | 88,958 | N/A | N/A | 2006-06-09 to 2026-07-06 | Yes |
| `appearances` | `csv.gz` | 43.16 MB | 1,894,350 | 29,531 | N/A | 2012-07-03 to 2026-06-28 | Yes |
| `player_valuations` | `csv.gz` | 6.86 MB | 656,301 | 41,528 | N/A | 2000-01-20 to 2026-06-12 | Yes |
| `club_games` | `csv.gz` | 2.04 MB | 177,916 | N/A | 3,274 | N/A | Yes |
| `transfers` | `csv.gz` | 5.54 MB | 175,165 | 23,379 | N/A | 1993-07-01 to 2030-06-30 | Yes |
| `countries` | `csv.gz` | 0.0 MB | 124 | N/A | N/A | N/A | Yes |

## 2. Table Column Schema and Missingness

### Table: `competitions`

- **Records:** 65  
- **Columns:** 11  
- **Duplicate Rows:** 0  

| Column Name | Data Type | Null Count | Null % | Distinct Values |
| :--- | :--- | :--- | :--- | :--- |
| `competition_id` | `object` | 0 | 0.0% | 65 |
| `competition_code` | `object` | 0 | 0.0% | 62 |
| `name` | `object` | 0 | 0.0% | 62 |
| `sub_type` | `object` | 0 | 0.0% | 16 |
| `type` | `object` | 0 | 0.0% | 5 |
| `country_id` | `int64` | 0 | 0.0% | 32 |
| `country_name` | `object` | 12 | 18.46% | 31 |
| `domestic_league_code` | `object` | 12 | 18.46% | 31 |
| `confederation` | `object` | 0 | 0.0% | 5 |
| `total_clubs` | `float64` | 15 | 23.08% | 7 |
| `url` | `object` | 0 | 0.0% | 65 |

### Table: `clubs`

- **Records:** 796  
- **Columns:** 17  
- **Duplicate Rows:** 0  

| Column Name | Data Type | Null Count | Null % | Distinct Values |
| :--- | :--- | :--- | :--- | :--- |
| `club_id` | `int64` | 0 | 0.0% | 796 |
| `club_code` | `object` | 0 | 0.0% | 796 |
| `name` | `object` | 0 | 0.0% | 796 |
| `domestic_competition_id` | `object` | 0 | 0.0% | 32 |
| `total_market_value` | `float64` | 796 | 100.0% | 0 |
| `squad_size` | `int64` | 0 | 0.0% | 43 |
| `average_age` | `float64` | 38 | 4.77% | 84 |
| `foreigners_number` | `int64` | 0 | 0.0% | 33 |
| `foreigners_percentage` | `float64` | 60 | 7.54% | 279 |
| `national_team_players` | `int64` | 0 | 0.0% | 24 |
| `stadium_name` | `object` | 0 | 0.0% | 760 |
| `stadium_seats` | `int64` | 0 | 0.0% | 658 |
| `net_transfer_record` | `object` | 0 | 0.0% | 482 |
| `coach_name` | `object` | 393 | 49.37% | 395 |
| `last_season` | `int64` | 0 | 0.0% | 14 |
| `filename` | `object` | 0 | 0.0% | 14 |
| `url` | `object` | 0 | 0.0% | 796 |

### Table: `players`

- **Records:** 50,149  
- **Columns:** 26  
- **Duplicate Rows:** 0  

| Column Name | Data Type | Null Count | Null % | Distinct Values |
| :--- | :--- | :--- | :--- | :--- |
| `player_id` | `int64` | 0 | 0.0% | 50,149 |
| `first_name` | `object` | 3,164 | 6.31% | 10,800 |
| `last_name` | `object` | 0 | 0.0% | 33,876 |
| `name` | `object` | 0 | 0.0% | 48,825 |
| `last_season` | `int64` | 0 | 0.0% | 14 |
| `current_club_id` | `int64` | 0 | 0.0% | 1,852 |
| `player_code` | `object` | 0 | 0.0% | 48,738 |
| `country_of_birth` | `object` | 5,885 | 11.74% | 211 |
| `city_of_birth` | `object` | 5,608 | 11.18% | 12,335 |
| `country_of_citizenship` | `object` | 269 | 0.54% | 202 |
| `date_of_birth` | `object` | 49 | 0.1% | 10,359 |
| `sub_position` | `object` | 586 | 1.17% | 13 |
| `position` | `object` | 0 | 0.0% | 5 |
| `foot` | `object` | 5,893 | 11.75% | 3 |
| `height_in_cm` | `float64` | 4,365 | 8.7% | 58 |
| `contract_expiration_date` | `object` | 18,569 | 37.03% | 241 |
| `agent_name` | `object` | 23,296 | 46.45% | 3,954 |
| `image_url` | `object` | 0 | 0.0% | 41,061 |
| `international_caps` | `float64` | 30,793 | 61.4% | 159 |
| `international_goals` | `float64` | 30,793 | 61.4% | 68 |
| `current_national_team_id` | `float64` | 46,889 | 93.5% | 123 |
| `url` | `object` | 0 | 0.0% | 50,149 |
| `current_club_domestic_competition_id` | `object` | 2,986 | 5.95% | 32 |
| `current_club_name` | `object` | 2,986 | 5.95% | 793 |
| `market_value_in_eur` | `float64` | 8,621 | 17.19% | 121 |
| `highest_market_value_in_eur` | `float64` | 8,621 | 17.19% | 206 |

### Table: `games`

- **Records:** 88,958  
- **Columns:** 23  
- **Duplicate Rows:** 0  

| Column Name | Data Type | Null Count | Null % | Distinct Values |
| :--- | :--- | :--- | :--- | :--- |
| `game_id` | `int64` | 0 | 0.0% | 88,958 |
| `competition_id` | `object` | 0 | 0.0% | 70 |
| `season` | `int64` | 0 | 0.0% | 18 |
| `round` | `object` | 0 | 0.0% | 128 |
| `date` | `object` | 0 | 0.0% | 4,445 |
| `home_club_id` | `int64` | 0 | 0.0% | 2,980 |
| `away_club_id` | `int64` | 0 | 0.0% | 2,634 |
| `home_club_goals` | `int64` | 0 | 0.0% | 16 |
| `away_club_goals` | `int64` | 0 | 0.0% | 18 |
| `home_club_position` | `float64` | 25,377 | 28.53% | 21 |
| `away_club_position` | `float64` | 25,377 | 28.53% | 21 |
| `home_club_manager_name` | `object` | 844 | 0.95% | 6,137 |
| `away_club_manager_name` | `object` | 844 | 0.95% | 5,756 |
| `stadium` | `object` | 242 | 0.27% | 2,968 |
| `attendance` | `float64` | 10,803 | 12.14% | 33,301 |
| `referee` | `object` | 678 | 0.76% | 3,135 |
| `url` | `object` | 0 | 0.0% | 88,958 |
| `home_club_formation` | `object` | 8,200 | 9.22% | 57 |
| `away_club_formation` | `object` | 8,073 | 9.08% | 68 |
| `home_club_name` | `object` | 86 | 0.1% | 2,901 |
| `away_club_name` | `object` | 36 | 0.04% | 2,600 |
| `aggregate` | `object` | 0 | 0.0% | 119 |
| `competition_type` | `object` | 1,214 | 1.36% | 5 |

### Table: `appearances`

- **Records:** 1,894,350  
- **Columns:** 13  
- **Duplicate Rows:** 0  

| Column Name | Data Type | Null Count | Null % | Distinct Values |
| :--- | :--- | :--- | :--- | :--- |
| `appearance_id` | `object` | 0 | 0.0% | 1,894,350 |
| `game_id` | `int64` | 0 | 0.0% | 73,426 |
| `player_id` | `int64` | 0 | 0.0% | 29,531 |
| `player_club_id` | `int64` | 0 | 0.0% | 1,231 |
| `player_current_club_id` | `int64` | 0 | 0.0% | 1,148 |
| `date` | `object` | 0 | 0.0% | 4,108 |
| `player_name` | `object` | 2 | 0.0% | 28,911 |
| `competition_id` | `object` | 0 | 0.0% | 48 |
| `yellow_cards` | `int64` | 0 | 0.0% | 3 |
| `red_cards` | `int64` | 0 | 0.0% | 2 |
| `goals` | `int64` | 0 | 0.0% | 7 |
| `assists` | `int64` | 0 | 0.0% | 7 |
| `minutes_played` | `int64` | 0 | 0.0% | 123 |

### Table: `player_valuations`

- **Records:** 656,301  
- **Columns:** 6  
- **Duplicate Rows:** 0  

| Column Name | Data Type | Null Count | Null % | Distinct Values |
| :--- | :--- | :--- | :--- | :--- |
| `player_id` | `int64` | 0 | 0.0% | 41,528 |
| `date` | `object` | 0 | 0.0% | 5,749 |
| `market_value_in_eur` | `int64` | 0 | 0.0% | 426 |
| `current_club_name` | `object` | 0 | 0.0% | 8,055 |
| `current_club_id` | `int64` | 0 | 0.0% | 5,424 |
| `player_club_domestic_competition_id` | `object` | 92,973 | 14.17% | 32 |

### Table: `club_games`

- **Records:** 177,916  
- **Columns:** 11  
- **Duplicate Rows:** 0  

| Column Name | Data Type | Null Count | Null % | Distinct Values |
| :--- | :--- | :--- | :--- | :--- |
| `game_id` | `int64` | 0 | 0.0% | 88,958 |
| `club_id` | `int64` | 0 | 0.0% | 3,274 |
| `own_goals` | `int64` | 0 | 0.0% | 18 |
| `own_position` | `float64` | 50,754 | 28.53% | 21 |
| `own_manager_name` | `object` | 1,688 | 0.95% | 7,031 |
| `opponent_id` | `int64` | 0 | 0.0% | 3,274 |
| `opponent_goals` | `int64` | 0 | 0.0% | 18 |
| `opponent_position` | `float64` | 50,754 | 28.53% | 21 |
| `opponent_manager_name` | `object` | 1,688 | 0.95% | 7,031 |
| `hosting` | `object` | 0 | 0.0% | 2 |
| `is_win` | `int64` | 0 | 0.0% | 2 |

### Table: `transfers`

- **Records:** 175,165  
- **Columns:** 10  
- **Duplicate Rows:** 0  

| Column Name | Data Type | Null Count | Null % | Distinct Values |
| :--- | :--- | :--- | :--- | :--- |
| `player_id` | `int64` | 0 | 0.0% | 23,379 |
| `transfer_date` | `object` | 0 | 0.0% | 5,634 |
| `transfer_season` | `object` | 0 | 0.0% | 35 |
| `from_club_id` | `int64` | 0 | 0.0% | 17,408 |
| `to_club_id` | `int64` | 0 | 0.0% | 13,208 |
| `from_club_name` | `object` | 0 | 0.0% | 18,285 |
| `to_club_name` | `object` | 0 | 0.0% | 14,086 |
| `transfer_fee` | `float64` | 61,526 | 35.12% | 1,503 |
| `market_value_in_eur` | `float64` | 68,160 | 38.91% | 191 |
| `player_name` | `object` | 0 | 0.0% | 23,036 |

### Table: `countries`

- **Records:** 124  
- **Columns:** 8  
- **Duplicate Rows:** 0  

| Column Name | Data Type | Null Count | Null % | Distinct Values |
| :--- | :--- | :--- | :--- | :--- |
| `country_id` | `int64` | 0 | 0.0% | 124 |
| `country_name` | `object` | 0 | 0.0% | 124 |
| `country_code` | `object` | 0 | 0.0% | 124 |
| `confederation` | `object` | 0 | 0.0% | 4 |
| `total_clubs` | `int64` | 0 | 0.0% | 14 |
| `total_players` | `int64` | 0 | 0.0% | 105 |
| `average_age` | `float64` | 0 | 0.0% | 46 |
| `url` | `object` | 0 | 0.0% | 124 |
