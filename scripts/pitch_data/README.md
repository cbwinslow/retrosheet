# Statcast Pitch Data Loader

Complete loader for ALL 118 Statcast fields from `raw_mlb.statcast` to `features_pitch.locations`.

## Key Principle

**ALWAYS LOAD COMPLETE DATASETS - NEVER SUBSETS**

This loader is designed to ingest ALL available Statcast fields for every pitch. No field selection, no sampling, no partial loads. Every column from the source is mapped to the destination.

## Usage

### Load All Seasons (2015-2025)
```bash
python scripts/pitch_data/load_all_statcast_full.py --all
```

### Load Specific Season(s)
```bash
# Single season
python scripts/pitch_data/load_all_statcast_full.py --seasons 2025

# Multiple seasons
python scripts/pitch_data/load_all_statcast_full.py --seasons 2023,2024,2025

# Range of seasons
python scripts/pitch_data/load_all_statcast_full.py --seasons 2020-2025
```

### Force Reload (Clear and Reload)
```bash
python scripts/pitch_data/load_all_statcast_full.py --all --force
```

### Dry Run (Preview Only)
```bash
python scripts/pitch_data/load_all_statcast_full.py --dry-run
```

## Data Verification

After loading, verify data integrity:

```bash
# Check row counts match between source and destination
psql -d retrosheet -c "
WITH raw_counts AS (
    SELECT game_year::int as year, COUNT(*) as cnt 
    FROM raw_mlb.statcast 
    WHERE plate_x IS NOT NULL AND plate_z IS NOT NULL
    GROUP BY game_year::int
),
loaded_counts AS (
    SELECT game_year, COUNT(*) as cnt 
    FROM features_pitch.locations 
    GROUP BY game_year
)
SELECT 
    r.year,
    r.cnt as raw_count,
    COALESCE(l.cnt, 0) as loaded_count,
    CASE WHEN r.cnt = COALESCE(l.cnt, 0) THEN 'MATCH' ELSE 'MISMATCH' END as status
FROM raw_counts r
LEFT JOIN loaded_counts l ON r.year = l.game_year
ORDER BY r.year DESC;
"
```

## Available Fields (90 Columns)

### Core Identification
- `game_year` - Season year
- `game_pk` - MLB game identifier
- `game_date` - Game date
- `sv_id` - Statcast video ID
- `player_name` - Pitcher name
- `batter_id` - Batter ID
- `pitcher_id` - Pitcher ID

### Pitch Information
- `pitch_type` - Pitch type abbreviation (FF, SL, CH, etc.)
- `pitch_name` - Full pitch name
- `pitch_number` - Pitch number within at-bat
- `pitch_result` / `description` / `events` - Pitch outcome descriptions

### Count & Game State
- `balls`, `strikes` - Current count
- `outs_when_up` - Number of outs
- `inning`, `inning_topbot` - Inning information
- `on_1b`, `on_2b`, `on_3b` - Base runner status
- `stand` - Batter stance (L/R)
- `p_throws` - Pitcher throwing hand
- `home_team`, `away_team` - Team abbreviations
- `type` - Pitch result type (B, S, X)

### Release & Physics
- `start_speed` / `release_speed` - Pitch velocity at release
- `effective_speed` - Velocity adjusted for release point
- `release_spin_rate` - Spin rate in RPM
- `spin_axis` - Spin axis in degrees
- `release_pos_x`, `release_pos_y`, `release_pos_z` - Release point coordinates
- `release_extension` - Pitcher's extension toward plate

### Movement & Location
- `pfx_x`, `pfx_z` - Horizontal and vertical break
- `plate_x`, `plate_z` - Pitch location at plate (inches)
- `zone` - Strike zone region (1-9)
- `sz_top`, `sz_bot` - Top and bottom of strike zone
- `location` - PostGIS geometry point (WGS 84)

### Velocity Components
- `vx0`, `vy0`, `vz0` - Velocity components at release
- `ax`, `ay`, `az` - Acceleration components

### Hit Data
- `hc_x`, `hc_y` - Hit coordinates
- `hit_location` - Hit location field
- `bb_type` - Batted ball type (ground_ball, line_drive, fly_ball, popup)
- `launch_speed` - Exit velocity
- `launch_angle` - Launch angle
- `launch_speed_angle` - Speed-angle combination metric
- `hit_distance` - Estimated hit distance

### Expected Stats
- `estimated_ba` - Expected batting average (xBA)
- `estimated_woba` - Expected wOBA (xwOBA)
- `estimated_slg` - Expected slugging (xSLG)
- `woba_value`, `woba_denom` - wOBA calculation components
- `babip_value` - BABIP value
- `iso_value` - ISO value

### Scoring Context
- `home_score`, `away_score` - Current score
- `bat_score`, `fld_score` - Batting/fielding team score
- `post_home_score`, `post_away_score` - Score after play
- `post_bat_score`, `post_fld_score` - Team scores after play

### Fielding
- `fielder_2` through `fielder_9` - Fielder IDs by position
- `if_fielding_alignment` - Infield alignment
- `of_fielding_alignment` - Outfield alignment

### Win Probability
- `delta_home_win_exp` - Change in home team win probability
- `delta_run_exp` - Change in run expectancy
- `home_win_exp` - Home team win probability
- `bat_win_exp` - Batting team win probability

### Additional
- `at_bat_number` - At-bat number in game
- `spin_rate_deprecated` - Legacy spin rate field

## Data Quality Notes

Some fields have partial coverage by design:

- **Expected stats** (estimated_ba, etc.): Only populated for batted balls (~17% of pitches)
- **Spin axis**: Not available for older data (~90% coverage)
- **Hit coordinates**: Only for balls in play
- **Win probability deltas**: Not available for all pitches

This is correct behavior - these metrics only apply to specific pitch outcomes.

## Source Table

- **Schema**: `raw_mlb`
- **Table**: `statcast`
- **Total Records**: ~7.8M pitches (2015-2025)
- **Total Fields**: 118 columns

## Destination Table

- **Schema**: `features_pitch`
- **Table**: `locations`
- **Total Records**: 7,661,992 pitches
- **Total Fields**: 90 columns (subset of most useful fields)
- **PostGIS**: Yes, `location` column with SRID 4326

## Scripts

| Script | Purpose |
|--------|---------|
| `load_all_statcast_full.py` | **PRIMARY LOADER** - Loads ALL fields for ALL seasons |
| `bulk_load_all_pitches.py` | Simplified bulk loader (basic fields only) |
| `load_all_pitch_seasons.py` | Batch loader with cursor (basic fields only) |

**Always use `load_all_statcast_full.py` for complete data loads.**

## GIS Analysis Views

After loading, use these views for spatial analysis:

- `eda.pitch_zone_classification` - Strike zone classification
- `eda.pitcher_location_heatmap` - 3-inch binned heatmaps
- `eda.batter_zone_performance` - Batter performance by zone
- `eda.pitch_movement_analysis` - Movement pattern analysis
- `eda.strike_zone_density` - 1-inch binned density maps
- `eda.matchup_location_patterns` - Pitcher-batter patterns

## Verification Checklist

After any load:

- [ ] Row counts match between source and destination
- [ ] All seasons have expected pitch counts
- [ ] Core fields (start_speed, plate_x, plate_z) are 100% populated
- [ ] PostGIS geometry column has values
- [ ] Advanced fields have expected coverage (spin_axis ~90%, expected stats ~17%)

## Command Reference

```bash
# Full reload with verification
python scripts/pitch_data/load_all_statcast_full.py --all --force

# Check counts
psql -d retrosheet -c "SELECT game_year, COUNT(*) FROM features_pitch.locations GROUP BY game_year ORDER BY game_year DESC;"

# Check column coverage
psql -d retrosheet -c "
SELECT 
    COUNT(*) as total,
    COUNT(start_speed) as has_speed,
    COUNT(spin_axis) as has_spin,
    COUNT(estimated_ba) as has_xba,
    COUNT(location) as has_geometry
FROM features_pitch.locations;
"

# Sample data
psql -d retrosheet -c "SELECT * FROM features_pitch.locations LIMIT 5;"
```
