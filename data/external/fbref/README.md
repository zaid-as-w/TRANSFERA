# FBref Data Integration Assessment & Compliance Notice

## Legal, Technical & ToS Evaluation

### 1. Official Terms of Service & robots.txt Evaluation
Sports Reference LLC / FBref (`https://fbref.com/`) strictly regulates automated access to its web properties.
- **robots.txt**: Prohibits aggressive crawling and non-standard bot access.
- **Terms of Service**: Section 5 explicitly prohibits unauthorized commercial extraction, high-frequency automated scraping, or reverse engineering of their data infrastructure.
- **Anti-Bot Defenses**: The domain is protected by Cloudflare Bot Management and Turnstile challenges. Attempting automated bypass of these security controls violates both engineering integrity guidelines and website policies.

### 2. Architecture Decision: Zero Unsanctioned Web Scraping
To protect platform reliability, avoid IP bans, and adhere strictly to ethical data engineering standards:
1. **No direct scraping scripts**: TRANSFERA does not implement automated HTML scraping against `fbref.com`.
2. **Entity Register Crosswalks**: Instead, TRANSFERA utilizes verified open identity registries (such as the Reep Football Entity Register, which indexes canonical `key_fbref` identifier crosswalks).
3. **Audit Trail**: Any FBref player identifiers stored in `data/global/player_provider_ids.parquet` originate exclusively from verified open crosswalk data rather than live HTML scraping.

