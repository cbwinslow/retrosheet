# Issue #10: Statcast Pitch-Level Data Ingestion

## Status: Completed

## Date
Started: April 19, 2026
Completed: April 19, 2026

## Objective
Ingest comprehensive Statcast pitch-level tracking data from Baseball Savant (MLB Stats API) to supplement historical Retrosheet data with advanced metrics.

## Background
Statcast provides pitch-level tracking data including spin rate, launch angle, exit velocity, swing mechanics, and other advanced metrics. This data is available from 2015 onwards and serves as a supplement to the canonical Retrosheet play-by-play data.

## Implementation

### Schema Updates
- Updated `sql/200_external_data.sql` to include all 118 Statcast fields (up from 12)
- Fields include: pitch_type, release_speed, release_spin_rate, launch_angle, launch_speed, hit_distance_sc, bat_speed, swing_length, hyper_speed, arm_angle, attack_angle, and 100+ additional metrics
- Primary key: (game_pk, at_bat_number, pitch_number)

### Script Updates
- Updated `scripts/external_data/load_statcast.py`:
  - Staging table now includes all 118 Statcast fields
  - Added deduplication logic to handle duplicate rows within CSV files
  - Upsert logic maps all fields with proper type casting

### Data Downloaded
- 2015: 734,737 rows → 712,844 loaded (after deduplication)
- 2016: 751,741 rows → 725,932 loaded
- 2017: 761,081 rows → 735,954 loaded
- 2018: 761,643 rows → 734,567 loaded
- 2019: 789,896 rows → 763,198 loaded
- 2020: 293,871 rows → 280,398 loaded (COVID shortened season)
- 2021: 786,227 rows → 764,572 loaded
- 2022: 803,088 rows → 774,488 loaded
- 2023: 801,276 rows → 774,038 loaded
- 2024: 788,753 rows → 760,248 loaded
- 2025: 800,635 rows → 770,795 loaded (partial season, Spring Training data)

### Final Statistics
- Total rows: 7,797,034 pitches
- Seasons: 2015-2025 (11 seasons)
- Distinct games: 24,079+ (2015-2024) + additional 2025 games
- Distinct batters: 4,229+
- Distinct pitchers: 3,251+
- Fields: 118 columns (all Statcast fields)

### Data Quality
- release_speed: 6,910,400 non-null (98.4%)
- launch_speed: 2,029,162 non-null (29.0% - only on batted balls)
- bat_speed: 472,248 non-null (6.8% - newer metric, limited availability)

## Documentation Updates
- Updated `docs/agents/FILE_INVENTORY.md` with Statcast status
- Updated `AGENTS.md` with Statcast workflow steps
- Updated `sql/200_external_data.sql` with full Statcast schema

## Scripts Used
- `scripts/download_statcast_pitch_level.py`: Downloads Statcast data via pybaseball library
- `scripts/external_data/load_statcast.py`: Loads Statcast CSV files into PostgreSQL

## Data Source
- Source: Baseball Savant Statcast API (via pybaseball library)
- URL: https://baseballsavant.mlb.com/
- Availability: 2015 onwards

## Relationship to Other Data Sources
- **Statcast vs MLB PBP**: Statcast is advanced pitch-tracking metrics from Baseball Savant, separate from the official MLB play-by-play data in `core.mlb_pbp` (from MLB Stats API / GUMBO)
- **Statcast vs Retrosheet**: Statcast provides supplementary advanced metrics that can be joined to Retrosheet game/event data via game_pk, batter, and pitcher IDs

## Next Steps
- Create analysis views combining Statcast metrics with Retrosheet game states
- Build ML features using Statcast advanced metrics
- Explore additional Statcast data types (e.g., catcher framing, defensive metrics)
- Set up ongoing Statcast ingestion for current season

## Related Documentation
- [FILE_INVENTORY.md](../docs/agents/FILE_INVENTORY.md)
- [AGENTS.md](../AGENTS.md)
- [sql/200_external_data.sql](../sql/200_external_data.sql)
