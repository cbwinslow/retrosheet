# Bridge Table Implementation Details

This document provides detailed implementation guidance for building and maintaining bridge tables in the retrosheet baseball prediction warehouse.

## Table of Contents

- [Overview](#overview)
- [Design Patterns](#design-patterns)
- [Existing Bridge Tables](#existing-bridge-tables)
- [ID Format Details](#id-format-details)
- [Implementation Strategies](#implementation-strategies)
- [Monitoring and Validation](#monitoring-and-validation)
- [Common Issues and Solutions](#common-issues-and-solutions)
- [Best Practices](#best-practices)

---

## Overview

Bridge tables in this project serve as cross-reference mappings between different baseball data source identifier systems. They enable seamless data integration across Retrosheet, MLB Stats API, Lahman, ESPN, Statcast, Baseball Reference, and other sources.

### Purpose

- **ID Translation**: Convert IDs from one system to another (e.g., Retrosheet ID → MLB ID)
- **Data Integration**: Join data from multiple sources using canonical IDs
- **Entity Resolution**: Match entities across systems when direct ID mapping unavailable
- **Historical Tracking**: Track changes in IDs over time (franchise moves, name changes)

### Architecture

```
Source Data → Raw Tables → Bridge Tables → Core Tables → Features → Predictions
```

Bridge tables sit between raw data ingestion and core canonical tables, providing the translation layer needed to integrate data from multiple sources.

---

## Design Patterns

### Cross-Reference Pattern

The primary pattern used is the cross-reference table, which maps IDs from multiple systems to a canonical ID.

**Schema Pattern**:
```sql
CREATE TABLE bridge.entity_xref (
    canonical_id TEXT PRIMARY KEY,
    source_system_1_id TEXT UNIQUE,
    source_system_2_id INTEGER UNIQUE,
    source_system_3_id TEXT UNIQUE,
    -- Additional attributes for matching/validation
    name TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);
```

**Key Design Decisions**:
- **Primary Key**: Use the most stable/authoritative system's ID as primary key (Retrosheet for this project)
- **Unique Constraints**: Add UNIQUE constraints on each source system's ID to prevent duplicates
- **Nullable Foreign IDs**: Allow NULL for unmapped entities
- **Timestamps**: Track creation and update times for audit purposes
- **Indexes**: Create indexes on all ID columns for lookup performance

### Multi-System Pattern

For entities that exist across multiple systems, use the multi-system pattern with per-system unique constraints:

```sql
CREATE TABLE bridge.coach_xref (
    retrosheet_coach_id TEXT,
    mlb_coach_id TEXT,
    lahman_coach_id TEXT,
    espn_coach_id TEXT,
    source_system TEXT NOT NULL,
    coach_name TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    
    CONSTRAINT uk_coach_xref_retrosheet UNIQUE (retrosheet_coach_id),
    CONSTRAINT uk_coach_xref_mlb UNIQUE (mlb_coach_id),
    CONSTRAINT uk_coach_xref_lahman UNIQUE (lahman_coach_id),
    CONSTRAINT uk_coach_xref_espn UNIQUE (espn_coach_id)
);
```

**When to Use**:
- When no single system is clearly authoritative
- When entities exist in multiple systems but no canonical source
- When you need to track mappings across all systems

### Season-Aware Pattern

For entities that change over time (teams, parks), use season-aware mappings:

```sql
CREATE TABLE bridge.team_xref (
    retrosheet_team_id TEXT PRIMARY KEY,
    mlb_team_id INTEGER UNIQUE,
    team_name TEXT,
    league TEXT,
    division TEXT,
    valid_from_season INTEGER,
    valid_to_season INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);
```

**When to Use**:
- Franchise moves (Montreal Expos → Washington Nationals)
- Name changes (Florida Marlins → Miami Marlins)
- League realignment
- Park renovations/relocations

### External Source Pattern

For external sources that don't have a direct mapping to the canonical system, use the external source pattern:

```sql
CREATE TABLE bridge.external_player_xref (
    external_source TEXT NOT NULL,
    external_player_id TEXT NOT NULL,
    retrosheet_player_id TEXT NOT NULL,
    PRIMARY KEY (external_source, external_player_id)
);
```

**When to Use**:
- Fantasy platforms (Yahoo!, CBS, ESPN)
- Statistical databases (Statcast, Baseball Reference)
- External APIs with their own ID systems
- When you need to map many external sources to one canonical system

---

## Existing Bridge Tables

### player_xref

**Purpose**: Map player IDs between Retrosheet, MLB, and Chadwick Register

**Schema**:
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

**Population**: `scripts/populate_bridge_tables.py` (downloads Chadwick Register)

**Key Features**:
- Chadwick Register as authoritative source
- Includes biographical data for matching
- Handedness constraints for validation
- Indexed on mlb_player_id and chadwick_register_id

### team_xref

**Purpose**: Map team IDs between Retrosheet and MLB, with season-awareness

**Schema**:
```sql
CREATE TABLE bridge.team_xref (
    retrosheet_team_id TEXT PRIMARY KEY,
    mlb_team_id INTEGER UNIQUE,
    team_name TEXT,
    league TEXT,
    division TEXT,
    valid_from_season INTEGER,
    valid_to_season INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);
```

**Population**: 
- `scripts/populate_bridge_tables.py` (basic mappings)
- `scripts/bridge/populate_season_aware_team_xref.py` (season ranges)

**Key Features**:
- Season-aware for franchise moves
- Handles Montreal Expos → Washington Nationals (1969-2004, 2005-present)
- Handles Florida Marlins → Miami Marlins (1993-2011, 2012-present)
- Indexed on mlb_team_id

**Franchise Move Examples**:
```sql
-- Montreal Expos
('MON', 120, 'Montreal Expos', 'NL', 'East', 1969, 2004)

-- Washington Nationals
('WSN', 120, 'Washington Nationals', 'NL', 'East', 2005, NULL)

-- Florida Marlins
('FLO', 146, 'Florida Marlins', 'NL', 'East', 1993, 2011)

-- Miami Marlins
('MIA', 146, 'Miami Marlins', 'NL', 'East', 2012, NULL)
```

### park_xref

**Purpose**: Map park/venue IDs between Retrosheet and MLB

**Schema**:
```sql
CREATE TABLE bridge.park_xref (
    retrosheet_park_id TEXT PRIMARY KEY,
    mlb_venue_id INTEGER UNIQUE,
    park_name TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);
```

**Population**: `scripts/populate_bridge_tables.py` (downloads Chadwick Register)

**Key Features**:
- Simple mapping for parks
- No season-awareness (parks typically stable)
- Can be extended for historical park changes if needed

### game_xref

**Purpose**: Map game IDs between Retrosheet and MLB

**Schema**:
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

**Population**: `scripts/bridge/populate_game_xref.py`

**Matching Strategy**:
```sql
-- Match games using date and team IDs with bridge.team_xref translation
SELECT 
    rg.game_id AS retrosheet_game_id,
    mg.mlb_game_pk,
    rg.game_date,
    rg.home_team_id AS retrosheet_home_team_id,
    rg.away_team_id AS retrosheet_away_team_id,
    mg.mlb_home_id AS mlb_home_team_id,
    mg.mlb_away_id AS mlb_away_team_id
FROM core.games rg
JOIN mlb_games mg ON rg.game_date = mg.game_date_parsed
JOIN bridge.team_xref txh ON mg.mlb_home_id = txh.mlb_team_id 
    AND rg.home_team_id = txh.retrosheet_team_id
JOIN bridge.team_xref txa ON mg.mlb_away_id = txa.mlb_team_id 
    AND rg.away_team_id = txa.retrosheet_team_id
```

**Key Features**:
- Multi-field matching (date + home team + away team)
- Uses team_xref for ID translation
- Handles doubleheader games via game number
- Indexed on mlb_game_pk and game_date

### coach_xref

**Purpose**: Map coach IDs across Retrosheet, MLB, Lahman, and ESPN

**Schema**:
```sql
CREATE TABLE bridge.coach_xref (
    retrosheet_coach_id TEXT,
    mlb_coach_id TEXT,
    lahman_coach_id TEXT,
    espn_coach_id TEXT,
    source_system TEXT NOT NULL,
    coach_name TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    
    CONSTRAINT uk_coach_xref_retrosheet UNIQUE (retrosheet_coach_id),
    CONSTRAINT uk_coach_xref_mlb UNIQUE (mlb_coach_id),
    CONSTRAINT uk_coach_xref_lahman UNIQUE (lahman_coach_id),
    CONSTRAINT uk_coach_xref_espn UNIQUE (espn_coach_id)
);
```

**Population**: `scripts/bridge/populate_coach_umpire_bridge.py`

**Source Data**: `raw_retrosheet.coaches`
```sql
CREATE TABLE raw_retrosheet.coaches (
    source_row_number integer PRIMARY KEY,
    coach_id text NOT NULL,
    season integer NOT NULL,
    team_id text NOT NULL,
    role text,
    start_date text,
    end_date text,
    loaded_at timestamptz NOT NULL DEFAULT now()
);
```

**Key Features**:
- Multi-system pattern (no single authoritative source)
- Per-system unique constraints
- Source system tracking
- Indexed on all ID columns
- Updated_at trigger for audit trail

**Known Limitations**:
- Coach names not available in raw_retrosheet.coaches (currently using coach_id as placeholder)
- Would need additional data source for coach names
- MLB, Lahman, ESPN mappings not yet implemented

### umpire_xref

**Purpose**: Map umpire IDs across Retrosheet, MLB, Lahman, and ESPN

**Schema**:
```sql
CREATE TABLE bridge.umpire_xref (
    retrosheet_umpire_id TEXT,
    mlb_umpire_id TEXT,
    lahman_umpire_id TEXT,
    espn_umpire_id TEXT,
    source_system TEXT NOT NULL,
    umpire_name TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    
    CONSTRAINT uk_umpire_xref_retrosheet UNIQUE (retrosheet_umpire_id),
    CONSTRAINT uk_umpire_xref_mlb UNIQUE (mlb_umpire_id),
    CONSTRAINT uk_umpire_xref_lahman UNIQUE (lahman_umpire_id),
    CONSTRAINT uk_umpire_xref_espn UNIQUE (espn_umpire_id)
);
```

**Population**: `scripts/bridge/populate_coach_umpire_bridge.py`

**Source Data**: `raw_retrosheet.season_umpires`
```sql
CREATE TABLE raw_retrosheet.season_umpires (
    source_file text NOT NULL,
    source_row_number integer NOT NULL,
    season integer NOT NULL,
    umpire_id text NOT NULL,
    last_name text,
    first_name text,
    loaded_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (source_file, source_row_number)
);
```

**Key Features**:
- Multi-system pattern (no single authoritative source)
- Per-system unique constraints
- Source system tracking
- Name available from raw data (first_name + last_name)
- Indexed on all ID columns
- Updated_at trigger for audit trail

**Known Limitations**:
- MLB, Lahman, ESPN mappings not yet implemented
- Would need to extract umpire IDs from MLB game feeds

### external_player_xref

**Purpose**: Map external player IDs (Statcast, Baseball Reference, Lahman) to Retrosheet IDs

**Schema**:
```sql
CREATE TABLE bridge.external_player_xref (
    external_source TEXT NOT NULL,
    external_player_id TEXT NOT NULL,
    retrosheet_player_id TEXT NOT NULL,
    PRIMARY KEY (external_source, external_player_id)
);
```

**Population**: `scripts/bridge/populate_external_bridge.py`

**Mapping Strategies**:
```sql
-- Statcast: Use bridge.player_xref mlb_id mappings
INSERT INTO bridge.external_player_xref (external_source, external_player_id, retrosheet_player_id)
SELECT DISTINCT 
    'statcast' as external_source,
    s.batter::text as external_player_id,
    px.retrosheet_id as retrosheet_player_id
FROM raw_mlb.statcast s
JOIN bridge.player_xref px ON s.batter = px.mlb_id
WHERE s.batter IS NOT NULL
AND px.mlb_id IS NOT NULL 
AND px.retrosheet_id IS NOT NULL 
AND px.retrosheet_id != '';

-- Baseball Reference: Use bridge.player_xref baseball_reference_id mappings
INSERT INTO bridge.external_player_xref (external_source, external_player_id, retrosheet_player_id)
SELECT DISTINCT 
    'baseball_reference' as external_source,
    px.baseball_reference_id as external_player_id,
    px.retrosheet_id as retrosheet_player_id
FROM bridge.player_xref px
WHERE px.baseball_reference_id IS NOT NULL
AND px.baseball_reference_id != ''
AND px.retrosheet_id IS NOT NULL
AND px.retrosheet_id != '';

-- Lahman: Use Lahman People table retroID column
INSERT INTO bridge.external_player_xref (external_source, external_player_id, retrosheet_player_id)
SELECT DISTINCT 
    'lahman' as external_source,
    l."playerID" as external_player_id,
    l."retroID" as retrosheet_player_id
FROM lahman.people l
WHERE l."retroID" IS NOT NULL
AND l."retroID" != '';
```

**Key Features**:
- External source pattern (many sources → one canonical)
- Composite primary key (source + external_id)
- Uses bridge.player_xref as source of truth for Statcast and Baseball Reference
- Direct Lahman mapping via retroID column
- UPSERT behavior with ON CONFLICT

### external_team_xref

**Purpose**: Map external team IDs to Retrosheet IDs

**Schema**:
```sql
CREATE TABLE bridge.external_team_xref (
    external_source TEXT NOT NULL,
    external_team_id TEXT NOT NULL,
    retrosheet_team_id TEXT NOT NULL,
    PRIMARY KEY (external_source, external_team_id)
);
```

**Population**: Not yet implemented (placeholder for future ESPN, fantasy platform mappings)

**Key Features**:
- External source pattern
- Composite primary key
- Placeholder for future implementation

---

## ID Format Details

### Retrosheet Player IDs

**Format**: 8-character alphanumeric code
**Structure**: First 4 letters of last name + first initial + 3-digit number

**Examples**:
- `kersc001` - Kershaw, Clayton
- `troutm01` - Trout, Mike
- `judgea01` - Judge, Aaron

**Characteristics**:
- Case-insensitive (typically lowercase)
- Numeric suffix disambiguates players with same name
- Stable over time
- Used as canonical ID in this project

### Retrosheet Team IDs

**Format**: 3-character alphabetic code
**Examples**:
- `BOS` - Boston Red Sox
- `NYY` - New York Yankees
- `LAD` - Los Angeles Dodgers
- `MON` - Montreal Expos (historical)
- `WSN` - Washington Nationals

**Characteristics**:
- Uppercase
- Based on team abbreviations
- Historical teams retain original IDs (MON, FLO)
- Used as canonical ID in this project

### Retrosheet Game IDs

**Format**: 12-character code
**Structure**: Home team (3 chars) + Year (2 digits) + Month (2 digits) + Day (2 digits) + Game number (1 digit)

**Examples**:
- `BAL198304040` - Baltimore Orioles, April 4, 1983, game 0 (single game)
- `NYM198605251` - New York Mets, May 25, 1986, game 1 (first of doubleheader)
- `NYM198605252` - New York Mets, May 25, 1986, game 2 (second of doubleheader)

**Characteristics**:
- Encodes date and game number in ID
- Game number: 0=single, 1=first DH, 2=second DH
- Used as canonical ID in this project

### Retrosheet Park IDs

**Format**: Variable-length alphanumeric code
**Examples**:
- `BOS01` - Fenway Park
- `NYC16` - Yankee Stadium (current)
- `NYC17` - Yankee Stadium (old, 1923-2008)

**Characteristics**:
- City code + sequential number
- Multiple IDs for same park if renovated/relocated
- Historical parks retained in system

### Retrosheet Coach IDs

**Format**: Text (no documented format standard)
**Source**: `raw_retrosheet.coaches.coach_id`

**Characteristics**:
- Format not standardized in Retrosheet documentation
- Appears to be text-based
- No name information in raw_retrosheet.coaches table
- Currently using coach_id as placeholder for coach_name

### Retrosheet Umpire IDs

**Format**: Text (no documented format standard)
**Source**: `raw_retrosheet.season_umpires.umpire_id`

**Characteristics**:
- Format not standardized in Retrosheet documentation
- Appears to be text-based
- Name available (first_name + last_name) in raw_retrosheet.season_umpires
- Populated via `scripts/bridge/populate_coach_umpire_bridge.py`

### MLB Player IDs (MLBAM)

**Format**: Integer
**Examples**:
- `477132` - Clayton Kershaw
- `545361` - Mike Trout
- `592450` - Aaron Judge

**Characteristics**:
- Integer format
- Used by MLB Stats API, Statcast, Baseball Savant
- Stable over time
- Considered "universal" key for modern baseball data

### MLB Team IDs

**Format**: Integer
**Examples**:
- `111` - Boston Red Sox
- `147` - New York Yankees
- `119` - Los Angeles Dodgers

**Characteristics**:
- Integer format
- Used by MLB Stats API
- Stable over time
- Mapped to Retrosheet IDs via bridge.team_xref

### MLB Game PK

**Format**: Integer
**Examples**:
- `632850` - Example game ID

**Characteristics**:
- Integer format
- Not human-readable
- Must be looked up via schedule API
- Unique per game
- Mapped to Retrosheet IDs via bridge.game_xref

### MLB Venue IDs

**Format**: Integer
**Examples**:
- `3` - Fenway Park
- `31` - Yankee Stadium

**Characteristics**:
- Integer format
- Used by MLB Stats API
- Mapped to Retrosheet IDs via bridge.park_xref

### Lahman Player IDs

**Format**: Alphanumeric code
**Structure**: Last name (up to 7 chars) + first initial + 2-digit number

**Examples**:
- `kersc001` - Kershaw, Clayton
- `troutmi01` - Trout, Mike
- `judgeaa01` - Judge, Aaron

**Characteristics**:
- Similar to Retrosheet format but slightly different
- Includes retroID column in People table for direct Retrosheet mapping
- Widely used in baseball analytics community

### Baseball Reference Player IDs

**Format**: Alphanumeric code (lowercase)
**Structure**: Last name (up to 7 chars) + first initial + 2-digit number

**Examples**:
- `kershcl01` - Kershaw, Clayton
- `troutmi01` - Trout, Mike
- `judgeaa01` - Judge, Aaron

**Characteristics**:
- Lowercase
- Similar to Lahman format
- Mapped via Chadwick Register
- Available in bridge.player_xref.baseball_reference_id

### ESPN Player IDs

**Format**: Integer
**Examples**:
- `33859` - Rafael Devers
- `40539` - Example player ID

**Characteristics**:
- Integer format (same as MLBAM IDs)
- Used in ESPN API responses
- Can be matched to Retrosheet via bridge.player_xref.mlb_id
- Located in JSON at `events[].competitors[].leaders[].athlete.id`
- Also in `events[].competitors[].roster[].player.id`

### ESPN Team IDs

**Format**: Integer
**Examples**:
- `2` - Boston Red Sox
- `16` - Example team ID

**Characteristics**:
- Integer format (same as MLB team IDs)
- Used in ESPN API responses
- Can be matched to Retrosheet via bridge.team_xref.mlb_team_id
- Located in JSON at `events[].competitors[].team.id`
- Also has UID field with structured string (e.g., "s:1~l:10~t:2")

### ESPN Game IDs

**Format**: Integer
**Examples**:
- `401568712` - Example game ID

**Characteristics**:
- Integer format
- Not human-readable
- Located in JSON at `events[].id`
- Would need to be mapped to Retrosheet game IDs via bridge.game_xref

### ESPN Venue IDs

**Format**: Integer
**Examples**:
- `2` - Fenway Park

**Characteristics**:
- Integer format
- Located in JSON at `events[].competitions[].venue.id`
- Can be matched to Retrosheet via bridge.park_xref

### Statcast Player IDs

**Format**: Integer (same as MLBAM IDs)
**Characteristics**:
- Uses MLBAM IDs (same system)
- Available in raw_mlb.statcast.batter and raw_mlb.statcast.pitcher
- Mapped via bridge.player_xref.mlb_id
- Populated in bridge.external_player_xref with source='statcast'

---

## Implementation Strategies

### Population Strategy: Chadwick Register First

**When**: For player and team mappings

**Why**: Chadwick Register is the authoritative, actively maintained crosswalk

**How**:
```python
# Download Chadwick Register
# Parse player and team mappings
# Populate bridge.player_xref and bridge.team_xref
```

**Script**: `scripts/populate_bridge_tables.py`

### Population Strategy: Multi-Field Matching

**When**: For game mappings where direct ID crosswalk unavailable

**Why**: Game IDs encode date and teams, making multi-field matching reliable

**How**:
```sql
-- Match on date + home team + away team
-- Use bridge.team_xref for team ID translation
-- Handle doubleheader via game number
```

**Script**: `scripts/bridge/populate_game_xref.py`

### Population Strategy: External Source Mapping

**When**: For Statcast, Baseball Reference, Lahman mappings

**Why**: These sources use their own ID systems but can be mapped via known crosswalks

**How**:
```sql
-- Statcast: Use bridge.player_xref.mlb_id
-- Baseball Reference: Use bridge.player_xref.baseball_reference_id
-- Lahman: Use Lahman.people.retroID column
```

**Script**: `scripts/bridge/populate_external_bridge.py`

### Population Strategy: Season-Aware Team Mapping

**When**: For team mappings with franchise moves

**Why**: Teams change locations/names over time

**How**:
```sql
-- Populate basic season ranges from core.games
-- Insert historical entries for franchise moves
-- Set valid_to_season = NULL for active teams
```

**Script**: `scripts/bridge/populate_season_aware_team_xref.py`

### Population Strategy: Name-Based Matching

**When**: For coach/umpire mappings where no crosswalk available

**Why**: Names are the only available identifier

**How**:
```python
# Extract from raw_retrosheet tables
# For umpires: first_name + last_name available
# For coaches: only coach_id available (name placeholder)
# Future: Would need additional data sources for coach names
```

**Script**: `scripts/bridge/populate_coach_umpire_bridge.py`

---

## Monitoring and Validation

### Monitoring Views

**bridge.bridge_table_counts**
```sql
-- Row counts and ID coverage statistics for all bridge tables
SELECT 
    table_name,
    total_rows,
    retrosheet_ids,
    mlb_ids,
    bref_ids
FROM bridge.bridge_table_counts
```

**bridge.external_player_coverage**
```sql
-- Coverage statistics for external player ID mappings by source
SELECT 
    external_source,
    total_mappings,
    unique_retrosheet_players,
    unique_external_ids
FROM bridge.external_player_coverage
ORDER BY total_mappings DESC
```

**bridge.player_mapping_summary**
```sql
-- Summary of all ID mappings for each player across all sources
SELECT 
    px.retrosheet_id,
    px.name_first,
    px.name_last,
    px.mlb_id,
    ep.statcast_external_id,
    ep.lahman_external_id,
    ep.bref_external_id
FROM bridge.player_xref px
LEFT JOIN bridge.external_player_xref ep ON px.retrosheet_id = ep.retrosheet_player_id
```

**bridge.bridge_data_quality_checks**
```sql
-- Data quality checks for bridge tables
-- Checks for NULL values, missing mappings, date mismatches
```

### Validation Queries

**Check for Unmapped MLB Games**
```sql
SELECT COUNT(*) 
FROM core.live_games 
WHERE mlb_game_pk IS NOT NULL 
AND game_date_parsed IS NOT NULL
AND retrosheet_game_id NOT IN (
    SELECT retrosheet_game_id FROM bridge.game_xref WHERE retrosheet_game_id IS NOT NULL
)
```

**Check for Unmapped Retrosheet Games**
```sql
SELECT COUNT(*) 
FROM core.games 
WHERE game_date >= '2026-01-01'
AND game_id NOT IN (
    SELECT retrosheet_game_id FROM bridge.game_xref
)
```

**Check for NULL Mappings**
```sql
-- Players without MLB IDs
SELECT COUNT(*) FROM bridge.player_xref WHERE mlb_id IS NULL;

-- Teams without MLB IDs
SELECT COUNT(*) FROM bridge.team_xref WHERE mlb_team_id IS NULL;

-- External players with NULL retrosheet IDs
SELECT COUNT(*) FROM bridge.external_player_xref 
WHERE retrosheet_player_id IS NULL OR retrosheet_player_id = '0';
```

**Check for Duplicate Mappings**
```sql
-- Should return 0 if unique constraints working
SELECT retrosheet_player_id, COUNT(*) 
FROM bridge.player_xref 
GROUP BY retrosheet_player_id 
HAVING COUNT(*) > 1;
```

---

## Common Issues and Solutions

### Issue: Rate Limits on External APIs

**Problem**: ESPN API or other external APIs rate limit requests

**Solution**:
- Implement exponential backoff
- Use checksum-based deduplication to avoid re-fetching
- Cache responses in raw tables
- Schedule fetches during off-peak hours

**Implementation**: `scripts/fetch_espn_mlb.py` uses checksum-based deduplication

### Issue: Franchise Moves Causing Mismatches

**Problem**: Team ID mismatches due to franchise moves (Expos → Nationals)

**Solution**:
- Use season-aware team mappings
- Insert historical entries for old franchise
- Set valid_from_season and valid_to_season appropriately
- Query with season filter to get correct mapping

**Implementation**: `scripts/bridge/populate_season_aware_team_xref.py`

### Issue: Missing Coach Names

**Problem**: `raw_retrosheet.coaches` table doesn't include coach names

**Current Workaround**: Using coach_id as placeholder for coach_name

**Future Solution**:
- Source coach names from MLB API
- Source coach names from Baseball Reference
- Manual data entry for historical coaches
- Community-sourced coach database

### Issue: Umpire Name Duplicates

**Problem**: Same umpire name across seasons, need to deduplicate

**Solution**:
```sql
SELECT DISTINCT ON (umpire_id)
    umpire_id,
    'retrosheet' as source_system,
    first_name || ' ' || last_name as umpire_name
FROM raw_retrosheet.season_umpires
WHERE umpire_id IS NOT NULL
ORDER BY umpire_id, season
```

**Implementation**: `scripts/bridge/populate_coach_umpire_bridge.py`

### Issue: Doubleheader Game Matching

**Problem**: Doubleheader games have same date and teams, need game number

**Solution**:
- Extract game number from Retrosheet game ID (last character)
- Match on date + teams + game number
- Handle single games (game number 0)

**Implementation**: `scripts/bridge/populate_game_xref.py`

### Issue: Statcast Player ID Coverage

**Problem**: Not all players in bridge.player_xref have Statcast data

**Solution**:
- Filter for valid retrosheet_id before mapping
- Accept partial coverage (Statcast only for modern era)
- Document coverage gaps in monitoring views

**Implementation**: `scripts/bridge/populate_external_bridge.py` filters for valid retrosheet_id

### Issue: ESPN ID Format Unknown

**Problem**: ESPN API ID format not documented

**Current Status**: Placeholder columns in bridge tables (espn_coach_id, espn_umpire_id)

**Future Solution**:
- Inspect ESPN API response structure
- Extract IDs from raw_espn.game_snapshots
- Document ID format once understood
- Implement mapping logic

---

## Best Practices

### 1. Use Authoritative Crosswalks First

Always use Chadwick Register as the primary source for player and team mappings. It is:
- Actively maintained
- Comprehensive
- Standardized across the industry
- Free for research purposes

### 2. Implement Unique Constraints

Add UNIQUE constraints on each source system's ID to prevent duplicate mappings:
```sql
CONSTRAINT uk_player_xref_mlb UNIQUE (mlb_player_id)
```

### 3. Index All ID Columns

Create indexes on all ID columns for lookup performance:
```sql
CREATE INDEX player_xref_mlb_id_idx ON bridge.player_xref (mlb_player_id);
```

### 4. Use UPSERT Behavior

Use ON CONFLICT for idempotent updates:
```sql
INSERT INTO bridge.player_xref (...)
VALUES (...)
ON CONFLICT (retrosheet_player_id) DO UPDATE SET
    mlb_player_id = EXCLUDED.mlb_player_id,
    updated_at = NOW();
```

### 5. Filter for Valid IDs

Filter out NULL and empty string IDs before mapping:
```sql
WHERE px.mlb_id IS NOT NULL 
AND px.retrosheet_id IS NOT NULL 
AND px.retrosheet_id != ''
```

### 6. Track Audit Information

Include created_at and updated_at timestamps:
```sql
created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
```

Add trigger to auto-update updated_at:
```sql
CREATE TRIGGER update_player_xref_updated_at
    BEFORE UPDATE ON bridge.player_xref
    FOR EACH ROW
    EXECUTE FUNCTION bridge.update_updated_at_column();
```

### 7. Use Season-Aware Mappings for Temporal Entities

For teams, parks, and other entities that change over time:
```sql
valid_from_season INTEGER,
valid_to_season INTEGER
```

### 8. Monitor Coverage and Quality

Create monitoring views to track:
- Row counts per bridge table
- ID coverage per source system
- NULL/missing mappings
- Data quality issues

### 9. Document ID Formats

Document the format and characteristics of each ID system:
- Format (integer, text, alphanumeric)
- Structure (how the ID is constructed)
- Examples
- Characteristics (case sensitivity, stability)

### 10. Handle Edge Cases Explicitly

Explicitly handle:
- Doubleheader games
- Franchise moves
- Name changes
- Historical coverage gaps
- NULL/empty IDs

---

## Related Documentation

- `docs/ID_RECONCILIATION.md` - Comprehensive ID reconciliation methods and strategies
- `docs/DATA_MODELS.md` - Data model documentation for all sources
- `docs/agents/PROCEDURES.md` - Canonical workflows for bridge table population
- `sql/mlb/100_bridge_tables.sql` - Bridge table schema definitions
- `sql/core/040_coach_umpire_bridge_tables.sql` - Coach/umpire bridge table schema
- `sql/bridge/900_bridge_monitoring_views.sql` - Monitoring and validation views

---

## Scripts Reference

### Bridge Table Population Scripts

- `scripts/populate_bridge_tables.py` - Populate player_xref, team_xref, park_xref from Chadwick Register
- `scripts/bridge/populate_game_xref.py` - Populate game_xref by matching games
- `scripts/bridge/populate_season_aware_team_xref.py` - Add season ranges to team_xref
- `scripts/bridge/populate_external_bridge.py` - Populate external_player_xref for Statcast, Baseball Reference, Lahman
- `scripts/bridge/populate_coach_umpire_bridge.py` - Populate coach_xref and umpire_xref from Retrosheet

### Data Fetching Scripts

- `scripts/fetch_espn_mlb.py` - Fetch ESPN API data with checksum-based deduplication

---

## Future Enhancements

### ESPN ID Mapping
- Inspect ESPN API response structure to understand ID formats
- Extract player, team, coach, umpire IDs from raw_espn tables
- Implement mapping logic for ESPN IDs
- Populate espn_coach_id, espn_umpire_id columns

### Coach Name Resolution
- Source coach names from MLB API
- Source coach names from Baseball Reference
- Implement name-based matching for historical coaches
- Update coach_xref with actual coach names

### Umpire MLB Mapping
- Extract umpire IDs from MLB game feeds
- Implement umpire ID mapping logic
- Populate mlb_umpire_id column in umpire_xref

### Historical Coverage
- Add Negro Leagues ID mappings
- Add minor league ID mappings
- Add international league ID mappings (NPB, KBO)

### Confidence Scoring
- Add confidence_score column to bridge tables
- Implement confidence scoring for fuzzy matches
- Create manual review queue for low-confidence matches
- Track manual review decisions

### Audit Trail
- Add reconciliation_audit_log table
- Track all reconciliation decisions
- Record match method and confidence
- Enable traceability and debugging
