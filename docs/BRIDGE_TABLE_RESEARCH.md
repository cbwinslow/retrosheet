# Bridge Table Research and Strategy

**Date:** 2026-04-22
**Purpose:** Document research on baseball ID cross-reference sources and bridge table strategy

## Authoritative ID Mapping Sources

### Chadwick Bureau Register (PRIMARY SOURCE)
- **URL:** https://github.com/chadwickbureau/register
- **Status:** THE canonical source for baseball player ID cross-references
- **Data Files:** people-0.csv through people-f.csv (16 files)
- **ID Systems Mapped:**
  - `key_mlbam` - MLBAM/MLB.com ID (primary for live data)
  - `key_retro` - Retrosheet ID (primary for historical data)
  - `key_bbref` - Baseball Reference ID
  - `key_fangraphs` - FanGraphs ID
  - `key_uuid` - Chadwick Register UUID
- **Additional Fields:** name_first, name_last, birth_year, mlb_played_first, bats, throws
- **Current Project Usage:** `scripts/bridge/populate_bridge_tables.py` downloads and uses this data

### mlb_rosetta
- **URL:** https://github.com/geoffharcourt/mlb_rosetta
- **Purpose:** Universal crosswalk of baseball player ID systems
- **Status:** Alternative source, may have additional mappings not in Chadwick
- **Note:** Chadwick Bureau Register is more actively maintained

### pybaseball
- **Function:** `playerid_lookup()`
- **Source:** Uses Chadwick Bureau Register
- **Usage:** Python library for looking up player IDs by name
- **Note:** Project could use this for ad-hoc lookups, but bulk import is better

### baseballr
- **Package:** baseballr (R)
- **Functions:** `playerid_lookup()`, `playername_lookup()`
- **Source:** Uses Chadwick Bureau Register
- **Note:** R equivalent of pybaseball

## Current Project Bridge Table Implementation

### Existing Bridge Tables

**player_xref** (sql/mlb/100_bridge_tables.sql)
```sql
CREATE TABLE bridge.player_xref (
    retrosheet_player_id TEXT PRIMARY KEY,
    mlb_player_id INTEGER UNIQUE,
    chadwick_register_id TEXT UNIQUE,
    first_name TEXT,
    last_name TEXT,
    bats TEXT CHECK (bats IN ('L', 'R', 'B', 'U')),
    throws TEXT CHECK (throws IN ('L', 'R', 'U')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);
```

**team_xref** (sql/mlb/100_bridge_tables.sql)
```sql
CREATE TABLE bridge.team_xref (
    retrosheet_team_id TEXT PRIMARY KEY,
    mlb_team_id INTEGER UNIQUE,
    team_name TEXT,
    league TEXT,
    division TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);
```

**park_xref** (sql/mlb/100_bridge_tables.sql)
```sql
CREATE TABLE bridge.park_xref (
    retrosheet_park_id TEXT PRIMARY KEY,
    mlb_venue_id INTEGER UNIQUE,
    park_name TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);
```

**game_xref** (sql/mlb/100_bridge_tables.sql)
```sql
CREATE TABLE bridge.game_xref (
    retrosheet_game_id TEXT PRIMARY KEY,
    mlb_game_pk INTEGER UNIQUE,
    game_date DATE,
    retrosheet_home_team_id TEXT,
    retrosheet_away_team_id TEXT,
    mlb_home_team_id INTEGER,
    mlb_away_team_id INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);
```

### Current Population Methods

**Player Mappings** (scripts/bridge/populate_bridge_tables.py)
- Downloads Chadwick Bureau Register from GitHub
- Parses 16 CSV files (people-0.csv through people-f.csv)
- Inserts into bridge.player_xref with ON CONFLICT DO UPDATE
- Maps: retrosheet_id, mlb_id, chadwick_register_id, bbref_id, name, bats, throws

**Team Mappings** (scripts/bridge/populate_bridge_tables.py)
- Uses hardcoded TEAM_ABBREVIATION_TO_RETROSHEET dictionary
- Seasonless (single MLB team ID maps to single Retrosheet team ID)
- Does not handle franchise moves (MON→WAS, FLO→MIA)
- Updated via SQL procedure `bridge.populate_season_aware_team_xref()` (new)

**Park Mappings** (scripts/bridge/populate_bridge_tables.py)
- Uses hardcoded MLB_VENUE_ID_TO_RETROSHEET_PARK dictionary
- Static mappings for 2000-2025 venues
- Updated via SQL procedure `bridge.populate_park_xref()` (new)

**Game Mappings** (sql/bridge/920_game_xref_procedure.sql)
- SQL procedure `bridge.populate_game_xref()`
- Matches by date, team IDs, and game number
- Uses bridge.team_xref for team ID translation
- Handles doubleheaders with DISTINCT ON

## Missing ID Systems

### Not Currently Mapped
- **Baseball Reference ID (bbref_id)**: Available in Chadwick but not stored in player_xref
- **FanGraphs ID (fangraphs_id)**: Available in Chadwick but not stored in player_xref
- **ESPN ID**: For ESPN API integration (issue #59 completed)
- **Statcast ID**: For Statcast data (already in external tables)
- **Lahman ID**: For Lahman database integration

### External Bridge Tables (sql/200_external_data.sql)
The project has external bridge tables for:
- external_player_xref (Statcast, Baseball Reference, Lahman IDs)
- external_team_xref (external team IDs)
- These are separate from the core bridge tables

## Recommendations

### 1. Enhance player_xref Schema
Add missing ID columns from Chadwick Bureau Register:
```sql
ALTER TABLE bridge.player_xref
ADD COLUMN bbref_id TEXT,
ADD COLUMN fangraphs_id INTEGER,
ADD COLUMN mlb_played_first INTEGER,
ADD COLUMN birth_year INTEGER;
```

### 2. Update populate_bridge_tables.py
Include all Chadwick fields in the insert:
- bbref_id (key_bbref)
- fangraphs_id (key_fangraphs)
- mlb_played_first (mlb_played_first)
- birth_year (birth_year)

### 3. Add Confidence Scoring
The project already has confidence scoring framework (sql/bridge/910_confidence_scoring.sql):
- confidence_score (0.0-1.0)
- confidence_source
- Apply to player_xref, team_xref, park_xref, game_xref

### 4. Season-Aware Team Mappings
Already implemented via `bridge.populate_season_aware_team_xref()`:
- valid_from_season
- valid_to_season
- Handles franchise moves (MON→WAS, FLO→MIA)

### 5. Game Matching Strategy
Already implemented via `bridge.populate_game_xref()`:
- Match by date + team IDs + game number
- Use bridge.team_xref for ID translation
- Handle doubleheaders with game number

### 6. External ID Integration
ESPN bridge tables already created (issue #59):
- bridge.external_player_xref
- bridge.external_team_xref
- Populated via `scripts/bridge/populate_espn_bridge.py`

## ID Matching Approaches

### Direct ID Lookup (Best)
- Use Chadwick Bureau Register for direct player ID mapping
- Most accurate and authoritative
- Covers MLBAM, Retrosheet, Baseball Reference, FanGraphs

### Name-Based Matching (Fallback)
- When direct ID not available, match by name + birth year
- Used for coaches, umpires (biofile_legacy)
- Lower confidence (0.7-0.8)

### Context-Based Matching (Game/Team)
- Match games by date + teams + game number
- Match teams by abbreviation + season
- Used when direct ID mapping fails

### Fallback IDs
- Use placeholder IDs (e.g., 'MLB###') when no match found
- Mark with low confidence (0.3)
- Re-process later when better mapping available

## Next Steps

1. **Update player_xref schema** to include bbref_id, fangraphs_id, mlb_played_first, birth_year
2. **Update populate_bridge_tables.py** to include all Chadwick fields
3. **Apply confidence scoring** to all bridge tables (already in place)
4. **Test season-aware team mappings** (already implemented)
5. **Test game matching** (already implemented)
6. **Document bridge table procedures** in PROCEDURES.md

## Conclusion

The project already uses the Chadwick Bureau Register, which is THE authoritative source for baseball ID cross-references. The bridge tables are well-designed and already have most of the necessary infrastructure. The main improvements needed are:

1. Add missing ID columns to player_xref (bbref_id, fangraphs_id, etc.)
2. Update the population script to include all Chadwick fields
3. Ensure confidence scoring is applied consistently

The user's concern about "figuring out how to get matching IDs" is already solved by the Chadwick Bureau Register - it's a comprehensive database of ID mappings that the project already uses.
