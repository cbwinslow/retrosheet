# PostGIS Pitch Location Mapping Research

**Date:** 2026-04-23
**Purpose:** Research for mapping pitch locations using PostGIS

## Key Sources

### 1. baseball-field-viz Python Library
- **URL:** https://github.com/yasumorishima/baseball-field-viz
- **Purpose:** Drawing baseball fields and spray charts from Statcast data
- **Key Functions:**
  - `transform_coords(df)` - Convert Statcast hc_x/hc_y to feet coordinates
  - `draw_strike_zone()` - Draw strike zone rectangle
  - `pitch_zone_chart()` - Plot pitch locations with strike zone overlay
- **Coordinate System:** Uses `plate_x` / `plate_z` columns (Statcast standard)
- **Strike Zone:** Auto-sized from per-pitch Hawk-Eye measurements (sz_top/sz_bot)

### 2. CalledStrike R Package
- **URL:** https://bayesball.github.io/Intro_to_CalledStrike_Package.html
- **Purpose:** Visualizations of smoothed measures over the zone
- **Functions:**
  - `location_count()` - Pitch locations for specific pitcher on count
  - `pitch_value_contour()` - Contour graph of smoothed pitch values
  - `PitchLocation()` - Shiny app for comparing pitch locations

### 3. PITCHf/x Strike Zone Analysis (UPenn)
- **URL:** http://stat.wharton.upenn.edu/~moneyball/ps5.html
- **Coordinate System:**
  - X: Horizontal coordinate in inches (center of home plate = 0)
  - Z: Vertical coordinate in inches
  - Negative X = Left from catcher's perspective (RHB side)
  - Positive X = Right from catcher's perspective (LHB side)
- **Strike Zone:** Rectangular region: home plate width, knee to mid-chest

### 4. GitHub: strike_zone Project
- **URL:** https://github.com/MarcLinderGit/strike_zone
- **Purpose:** SVM to uncover strike zone decision boundary
- **Data:** Aaron Judge and Jose Altuve 2017 season

### 5. PostgreSQL Import Scripts (mlbatbat_pgsql)
- **URL:** https://github.com/brianhuey/mlbatbat_pgsql
- **Purpose:** Scripts for importing MLB AtBat/PitchFX/Statcast to Postgres

## Implementation Plan

### Step 1: Install PostGIS
```sql
CREATE EXTENSION IF NOT EXISTS postgis;
```

### Step 2: Pitch Location Columns
The data uses plate_x (horizontal) and plate_z (vertical) coordinates:
- plate_x: -17 to +17 inches (from catcher's view)
- plate_z: 0 to ~5 feet (height)

### Step 3: Strike Zone Geometry
Standard strike zone varies by batter stance:
- Width: 17 inches (width of home plate)
- Height: Knee to midpoint of torso (~1.5 to ~3.5 feet)

### Step 4: Visualization Approaches
1. **PostGIS:** Store as GEOMETRY points, query spatial joins
2. **Python:** baseball-field-viz for matplotlib charts
3. **R:** CalledStrike package
4. **pgAdmin:** Connect directly via PostGIS

## Key Data Columns Needed (from Statcast)
| Column | Description |
|--------|-------------|
| plate_x | Horizontal location (-17 to +17 inches) |
| plate_z | Vertical location (feet) |
| sz_top | Top of strike zone for batter |
| sz_bottom | Bottom of strike zone for batter |
| p_throws | Pitcher handedness (L/R) |
| stand | Batter handedness (L/R) |
| pitch_type | fastball, curve, slider, etc. |
| launch_speed | Exit velocity |
| launch_angle | Batted ball angle |

## Research Questions
1. How to compute strike zone probability per location?
2. How to map pitch movement (acceleration x/y)?
3. Best visualization approach for spray charts?

## Implementation: Python Loader Script

Created: `scripts/ingestion/load_statcast_pitch_data.py`

This script:
1. Creates `features_pitch.statcast_pitches` table matching Baseball Savant schema
2. Loads all seasons (2008-2025) from `raw_mlb.statcast`
3. Adds PostGIS geometry columns for pitch location
4. Creates EDA views for analysis

### Usage
```bash
# Load all seasons
python scripts/ingestion/load_statcast_pitch_data.py --all

# Load specific seasons
python scripts/ingestion/load_statcast_pitch_data.py --seasons 2023,2024

# Create table only
python scripts/ingestion/load_statcast_pitch_data.py --create-only
```

### Schema
Based on Baseball Savant CSV documentation:
- 118 columns matching official Statcast export
- PostGIS geometry: `location_point` (POINT)
- Indexes on: game_year, game_pk, pitcher, batter, pitch_type

## References and Bibliography

### Primary Sources
1. **Baseball Savant CSV Documentation** - https://baseballsavant.mlb.com/csv-docs
   - Official MLB Statcast data documentation
   - 118 columns of pitch-level data

2. **pybaseball Python Library** - https://github.com/jldbc/pybaseball
   - Author: jldbc (2K+ stars)
   - Python package for baseball data analysis
   - Statcast: pitch-level data from Baseball Savant

3. **baseball-field-viz Python Library** - https://github.com/yasumorishima/baseball-field-viz
   - Author: Yasuhisa Morishima
   - Purpose: Drawing baseball fields and spray charts from Statcast data

4. **CalledStrike R Package** - https://bayesball.github.io/Intro_to_CalledStrike_Package.html
   - Author: Jim Albert
   - Purpose: Visualizations of smoothed measures over the zone

5. **PITCHf/x Strike Zone Analysis** - http://stat.wharton.upenn.edu/~moneyball/ps5.html
   - Institution: University of Pennsylvania Wharton
   - Course: STAT 471 - Moneyball

6. **strike_zone Project** - https://github.com/MarcLinderGit/strike_zone
   - Author: Marc Linder
   - Purpose: SVM strike zone decision boundary

7. **mlbatbat_pgsql** - https://github.com/brianhuey/mlbatbat_pgsql
   - Author: Brian Huey
   - Purpose: PostgreSQL scripts for MLB AtBat/PitchFX/Statcast

---
*Last updated: 2026-04-23*
*Researcher: AI Agent*
*Sources cited per research methodology*