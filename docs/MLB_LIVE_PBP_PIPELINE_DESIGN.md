# MLB Live Play-by-Play Data Ingestion Pipeline Design

## Executive Summary

This document outlines a comprehensive pipeline to ingest current MLB play-by-play data from the official MLB Stats API, map it to Retrosheet-compatible field definitions, and store it in separate but interoperable tables. The pipeline respects API limits, focuses on current games only, and complements annual Retrosheet releases.

## Pipeline Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          MLB LIVE PBP INGESTION PIPELINE                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │  Discovery  │───▶│  Fetch PBP │───▶│  Transform │───▶│   Store     │     │
│  │  (Current   │    │   (MLB     │    │  (Map to   │    │  (Separate  │     │
│  │   Games)    │    │   API)     │    │ Retrosheet)│    │   Tables)   │     │
│  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘     │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐     │
│  │                    INTEGRATION WITH RETROSHEET                     │     │
│  │  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐               │     │
│  │  │ Retrosheet  │───▶│  Combined  │───▶│   Models    │               │     │
│  │  │  Archive    │    │   Views    │    │  & ML      │               │     │
│  │  │  (Annual)   │    │            │    │  Training   │               │     │
│  │  └─────────────┘    └─────────────┘    └─────────────┘               │     │
│  └─────────────────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────────────────┘
```

## API Constraints & Design Principles

### MLB Stats API Limitations
- **Current Games Only**: No historical data beyond ~1-2 weeks
- **Rate Limits**: ~60 requests/minute, 429 responses trigger backoff
- **Live Data Focus**: Optimized for real-time game monitoring
- **No Bulk Downloads**: Individual game requests required

### Design Principles
1. **Non-Disruptive**: Complements, doesn't replace Retrosheet data
2. **Interoperable**: Same field mappings for seamless integration
3. **Resource Conscious**: Respects API limits, implements intelligent caching
4. **Current Focus**: Only active/recent games, no historical backfill attempts
5. **Quality Assurance**: Comprehensive validation and error handling

## Pipeline Components

### 1. Game Discovery Component

**Purpose**: Identify currently active MLB games for ingestion

**Implementation**: Enhanced `scripts/fetch_mlb_schedule.py`

**API Calls**:
```bash
# Current games only (last 24 hours)
GET /api/v1/schedule?sportId=1&startDate=2026-04-09&endDate=2026-04-10

# Filter for active games
if game["status"]["abstractGameState"] in ["Live", "In Progress"]:
    active_games.append(game)
```

**Data Stored**:
```sql
-- Temporary table for active games
CREATE TEMP TABLE active_games (
    game_pk integer PRIMARY KEY,
    game_date date,
    home_team_id integer,
    away_team_id integer,
    status text,
    discovered_at timestamptz DEFAULT now()
);
```

### 2. Play-by-Play Fetch Component

**Purpose**: Download live PBP data for active games

**Implementation**: Enhanced `scripts/fetch_mlb_live_pbp.py`

**API Calls**:
```bash
# Live feed for each active game
for game_pk in active_games:
    url = f"https://statsapi.mlb.com/api/v1.1/game/{game_pk}/feed/live"
    response = requests.get(url, timeout=30)

    # Rate limiting check
    if response.status_code == 429:
        sleep(exponential_backoff(attempt))

    # Store raw response
    store_raw_pbp(game_pk, response.json())
```

**Raw Storage Schema**:
```sql
-- Separate from raw_mlb.live_feed_snapshots for PBP-specific data
CREATE TABLE raw_mlb.live_pbp_snapshots (
    snapshot_id bigserial PRIMARY KEY,
    game_pk integer NOT NULL,
    fetched_at timestamptz NOT NULL DEFAULT now(),
    endpoint text NOT NULL,
    payload jsonb NOT NULL,
    request_params jsonb,
    http_status integer,
    response_time_ms integer,
    error_text text,
    is_live boolean DEFAULT true,
    last_play_index integer,  -- Track incremental updates
    UNIQUE(game_pk, fetched_at)
);

-- Indexes for performance
CREATE INDEX live_pbp_game_pk_idx ON raw_mlb.live_pbp_snapshots (game_pk);
CREATE INDEX live_pbp_fetched_at_idx ON raw_mlb.live_pbp_snapshots (fetched_at DESC);
CREATE INDEX live_pbp_live_idx ON raw_mlb.live_pbp_snapshots (is_live) WHERE is_live = true;
```

### 3. Data Transformation Component

**Purpose**: Map MLB API data to Retrosheet-compatible event format

**Implementation**: New `scripts/transform_mlb_to_retrosheet.py`

**Field Mapping Strategy**:

#### Game-Level Mapping (core.live_games)
```python
mlb_to_retrosheet_game_mapping = {
    # MLB API → Retrosheet Field
    "game.pk": "mlb_game_pk",
    "game.season": "season",
    "datetime.dateTime": "game_date",
    "teams.home.id": "home_team_id",  # Will be mapped to Retrosheet ID
    "teams.away.id": "away_team_id",  # Will be mapped to Retrosheet ID
    "venue.id": "park_id",            # Will be mapped to Retrosheet ID
    "weather.temp": "temperature_f",
    "weather.windSpeed": "wind_speed_mph",
    "weather.windDirection": "wind_direction",
    "weather.condition": "sky_condition",
    "linescore.teams.home.runs": "home_score",
    "linescore.teams.away.runs": "away_score",
    "status.abstractGameState": "game_status",
    "status.detailedState": "detailed_state"
}
```

#### Event-Level Mapping (core.live_events)
```python
mlb_to_retrosheet_event_mapping = {
    # MLB Play → Retrosheet Event
    "result.type": {
        "single": {"event_code": 20, "hit_value": 1, "is_hit": True},
        "double": {"event_code": 21, "hit_value": 2, "is_hit": True},
        "triple": {"event_code": 22, "hit_value": 3, "is_hit": True},
        "home_run": {"event_code": 23, "hit_value": 4, "is_hit": True, "is_home_run": True},
        "strikeout": {"event_code": 3, "is_strikeout": True},
        "walk": {"event_code": 14, "is_walk": True},
        "field_out": {"event_code": 2},
        "force_out": {"event_code": 6},
        "grounded_into_double_play": {"event_code": 8},
        "hit_by_pitch": {"event_code": 16, "is_hit_by_pitch": True},
        "catcher_interference": {"event_code": 17, "is_interference": True}
    },
    "about.atBatIndex": "event_sequence",
    "about.inning": "inning",
    "about.isTopInning": "is_top_inning",  # Convert to is_bottom_inning
    "about.halfInningOuts": "outs_before",
    "count.balls": "balls",
    "count.strikes": "strikes",
    "matchup.batter.id": "batter_id",      # Map to Retrosheet ID
    "matchup.pitcher.id": "pitcher_id",    # Map to Retrosheet ID
    "matchup.batSide.code": "batter_hand",
    "matchup.pitchHand.code": "pitcher_hand",
    "result.description": "event_text",
    "result.eventCode": "event_code",
    "result.rbi": "rbi"
}
```

**Transformation Process**:
1. Parse MLB live feed JSON
2. Extract game metadata and map to Retrosheet game fields
3. Iterate through `liveData.plays.allPlays[]`
4. Map each play to Retrosheet event format
5. Calculate derived fields (bases, outs, runs scored)
6. Apply ID mapping through bridge tables
7. Store in live Retrosheet-compatible tables

### 4. Storage Schema Design

**Separate but Compatible Tables**:

#### Live Games Table (mlb.live_games)
```sql
CREATE SCHEMA mlb;
CREATE TABLE mlb.live_games (
    -- Retrosheet-compatible game fields
    game_id text PRIMARY KEY,           -- MLB{gamePk} format
    season integer,
    game_date date,
    game_number smallint,
    day_of_week text,
    start_time text,
    doubleheader_flag text,
    day_night text,
    home_team_id text,                  -- Retrosheet team ID (mapped)
    away_team_id text,                  -- Retrosheet team ID (mapped)
    park_id text,                       -- Retrosheet park ID (mapped)
    home_starting_pitcher_id text,      -- Retrosheet player ID (mapped)
    away_starting_pitcher_id text,      -- Retrosheet player ID (mapped)
    attendance integer,
    temperature_f integer,
    wind_direction text,
    wind_speed_mph integer,
    field_condition text,
    precipitation text,
    sky_condition text,
    duration_minutes integer,
    innings integer,
    away_score integer NOT NULL,
    home_score integer NOT NULL,
    away_hits integer,
    home_hits integer,
    away_errors integer,
    home_errors integer,
    away_lob integer,
    home_lob integer,
    winning_team_id text,
    home_win boolean,
    win_pitcher_id text,
    loss_pitcher_id text,
    save_pitcher_id text,
    source_type text DEFAULT 'mlb_live',

    -- MLB-specific fields
    mlb_game_pk integer UNIQUE,
    mlb_home_team_id integer,
    mlb_away_team_id integer,
    mlb_park_id integer,
    game_status text,
    detailed_state text,
    venue_name text,
    snapshot_id integer,
    last_updated timestamptz,

    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);
```

#### Live Events Table (mlb.live_events)
```sql
CREATE TABLE mlb.live_events (
    -- Retrosheet-compatible event fields
    game_id text REFERENCES mlb.live_games(game_id),
    event_id integer,
    season integer,
    source_type text DEFAULT 'mlb_live',
    event_sequence integer,
    inning integer,
    is_bottom_inning boolean,
    outs_before integer,
    balls integer,
    strikes integer,
    away_score_before integer,
    home_score_before integer,
    batting_team_id text,
    fielding_team_id text,
    batter_id text,                     -- Retrosheet player ID (mapped)
    batter_hand text,
    pitcher_id text,                    -- Retrosheet player ID (mapped)
    pitcher_hand text,
    event_code integer,
    event_text text,
    is_plate_appearance boolean,
    is_at_bat boolean,
    hit_value integer DEFAULT 0,
    is_hit boolean DEFAULT false,
    is_walk boolean DEFAULT false,
    is_strikeout boolean DEFAULT false,
    is_home_run boolean DEFAULT false,
    outs_on_play integer DEFAULT 0,
    runs_on_play integer DEFAULT 0,
    rbi integer DEFAULT 0,
    start_bases integer DEFAULT 0,
    end_bases integer DEFAULT 0,
    away_score_after integer,
    home_score_after integer,
    game_pa_count integer,
    half_inning_pa_count integer,
    is_new_plate_appearance boolean DEFAULT true,
    is_inning_start boolean DEFAULT false,
    is_inning_end boolean DEFAULT false,
    is_game_end boolean DEFAULT false,

    -- MLB-specific fields
    mlb_game_pk integer,
    mlb_event_index integer,
    mlb_batter_id integer,
    mlb_pitcher_id integer,
    play_id text,
    play_type text,
    event_type_description text,
    trajectory text,
    raw_play jsonb,

    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),

    PRIMARY KEY (game_id, event_id)
);
```

#### Live Plate Appearances Table (mlb.live_plate_appearances)
```sql
CREATE TABLE mlb.live_plate_appearances (
    -- Complete Retrosheet-compatible PA fields (same as core.plate_appearances)
    game_id text NOT NULL,
    plate_appearance_id integer NOT NULL,
    game_pa_number integer NOT NULL,
    half_inning_pa_number integer NOT NULL,
    season integer NOT NULL,
    game_date date NOT NULL,
    source_type text NOT NULL DEFAULT 'mlb_live',
    event_sequence integer NOT NULL,
    inning integer NOT NULL,
    is_bottom_inning boolean NOT NULL,
    outs_before integer NOT NULL,
    balls integer,
    strikes integer,
    start_bases integer,
    end_bases integer,
    away_score_before integer NOT NULL,
    home_score_before integer NOT NULL,
    away_score_after integer,
    home_score_after integer,
    home_team_id text,
    away_team_id text,
    batting_team_id text,
    fielding_team_id text,
    batter_id text,
    batter_hand text,
    pitcher_id text,
    pitcher_hand text,
    event_code integer,
    event_text text,
    is_at_bat boolean,
    hit_value integer DEFAULT 0,
    is_hit boolean DEFAULT false,
    is_walk boolean DEFAULT false,
    is_strikeout boolean DEFAULT false,
    is_home_run boolean DEFAULT false,
    is_hit_by_pitch boolean DEFAULT false,
    is_interference boolean DEFAULT false,
    is_reach_base boolean,
    outs_on_play integer DEFAULT 0,
    runs_on_play integer DEFAULT 0,
    rbi integer DEFAULT 0,
    is_new_pa boolean DEFAULT true,
    pa_index integer,
    batter_is_starter boolean,
    pitcher_is_starter boolean,
    park_id text,
    park_name text,
    temperature_f integer,
    wind_speed_mph integer,
    wind_direction text,
    precipitation text,
    sky_condition text,
    game_pa_count integer,
    inning_pa_count integer,
    is_inning_start boolean DEFAULT false,
    is_inning_end boolean DEFAULT false,
    is_game_end boolean DEFAULT false,

    -- MLB-specific provenance
    mlb_game_pk integer,
    snapshot_id integer,
    raw_play jsonb,

    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),

    PRIMARY KEY (game_id, plate_appearance_id)
);
```

### 5. Integration & Interoperability

**Combined Analysis Views**:
```sql
-- Enhanced combined views to include MLB live data
CREATE OR REPLACE VIEW analysis.combined_games AS
SELECT * FROM core.games
UNION ALL
SELECT
    game_id, season, source_type, game_date::text, game_number, day_of_week,
    start_time, doubleheader_flag, day_night, away_team_id, home_team_id,
    park_id, away_starting_pitcher_id, home_starting_pitcher_id, attendance,
    temperature_f, wind_direction, wind_speed_mph, field_condition, precipitation,
    sky_condition, duration_minutes, innings, away_score, home_score, away_hits,
    home_hits, away_errors, home_errors, away_lob, home_lob, winning_team_id,
    home_win, win_pitcher_id, loss_pitcher_id, save_pitcher_id, NULL as raw_loaded_at,
    created_at, updated_at
FROM mlb.live_games;

-- Combined events view
CREATE OR REPLACE VIEW analysis.combined_events AS
SELECT * FROM core.events
UNION ALL
SELECT
    game_id, event_id, season, source_type, event_sequence, inning, is_bottom_inning,
    outs_before, balls, strikes, away_score_before, home_score_before, batting_team_id,
    fielding_team_id, batter_id, batter_hand, pitcher_id, pitcher_hand, event_code,
    event_text, is_plate_appearance, is_at_bat, hit_value, is_hit, is_walk, is_strikeout,
    is_home_run, outs_on_play, runs_on_play, rbi, start_bases, end_bases, away_score_after,
    home_score_after, game_pa_count, half_inning_pa_count, is_new_plate_appearance,
    is_inning_start, is_inning_end, is_game_end, NULL as raw_loaded_at, created_at
FROM mlb.live_events;
```

## Pipeline Execution Workflow

### Phase 1: Discovery & Scheduling
```bash
# Run every 15 minutes during game hours (12 PM - 11 PM ET)
# Discover active games from MLB schedule
python3 scripts/fetch_mlb_schedule.py --today --active-only

# Output: List of game_pks currently in progress
# Example: [715753, 715754, 715755]
```

### Phase 2: Live Data Ingestion
```bash
# Fetch live PBP for each active game (respecting rate limits)
for game_pk in active_games:
    python3 scripts/fetch_mlb_live_pbp.py --game-pk $game_pk --wait 2
    
# Rate limiting: 60 requests/minute = ~1 request/second
# With 2-second delay = 30 requests/minute (safe margin)
```

### Phase 3: Data Transformation
```bash
# Transform raw MLB data to Retrosheet-compatible format
python3 scripts/transform_mlb_to_retrosheet.py --recent --hours 24

# Process all untransformed snapshots from last 24 hours
# Map MLB fields to Retrosheet event codes
# Apply ID mapping through bridge tables
# Store in mlb.live_games, mlb.live_events, mlb.live_plate_appearances
```

### Phase 4: Quality Assurance & Integration
```bash
# Validate transformed data
python3 scripts/validate_mlb_ingestion.py --recent --hours 24

# Update combined analysis views
python3 scripts/update_analysis_views.py

# Check data completeness
SELECT * FROM analysis.get_data_source_stats();
```

## Constraints & Safeguards

### API Rate Limiting
- **Hard Limit**: 60 requests/minute per IP
- **Implementation**: Exponential backoff on 429 responses
- **Monitoring**: Track request rates and success rates
- **Fallback**: Cache recent responses to avoid redundant calls

### Data Freshness
- **Live Focus**: Only current games (no historical backfill)
- **Update Frequency**: Game state updates every 10-30 seconds
- **Storage Limits**: Automatic cleanup of games > 30 days old
- **Completeness Check**: Validate all required fields present

### Error Handling
- **Network Errors**: Retry with exponential backoff
- **Data Corruption**: Validate JSON structure before processing
- **ID Mapping Failures**: Fallback to MLB-prefixed IDs with logging
- **Database Constraints**: Transaction rollbacks on validation failures

### Resource Management
- **Memory Limits**: Process one game at a time
- **Disk Space**: Compress old raw JSON snapshots
- **CPU Usage**: Schedule during off-peak hours when possible
- **Concurrent Jobs**: Limit to 3 simultaneous game fetches

## Retrieval Mechanics

### Real-Time Game State
```sql
-- Get current state of a live game
SELECT
    lg.game_id,
    lg.home_team_name,
    lg.away_team_name,
    lg.home_score,
    lg.away_score,
    lg.inning,
    lg.is_bottom_inning,
    le.batter_id,
    le.pitcher_id,
    le.balls,
    le.strikes,
    le.outs_before,
    le.event_text as last_play
FROM mlb.live_games lg
LEFT JOIN mlb.live_events le ON lg.game_id = le.game_id
WHERE lg.mlb_game_pk = $1
  AND lg.game_status IN ('In Progress', 'Live')
ORDER BY le.event_sequence DESC
LIMIT 1;
```

### Player Performance (Live)
```sql
-- Live player stats for current season
SELECT
    le.batter_id,
    p.name_first,
    p.name_last,
    COUNT(*) FILTER (WHERE le.is_plate_appearance) as pa,
    COUNT(*) FILTER (WHERE le.is_hit) as hits,
    COUNT(*) FILTER (WHERE le.is_home_run) as hr,
    SUM(le.rbi) as rbi,
    ROUND(AVG(le.is_hit::numeric), 3) as avg
FROM mlb.live_events le
JOIN core.players p ON le.batter_id = p.retrosheet_player_id
WHERE le.season = EXTRACT(YEAR FROM CURRENT_DATE)
  AND le.is_plate_appearance = true
GROUP BY le.batter_id, p.name_first, p.name_last
HAVING COUNT(*) >= 10
ORDER BY pa DESC;
```

### Combined Historical + Live Analysis
```sql
-- Seamless analysis across data sources
SELECT
    source_type,
    COUNT(*) as games,
    AVG(home_score + away_score) as avg_total_runs,
    SUM(home_score + away_score) as total_runs
FROM analysis.combined_games
WHERE season = 2026
GROUP BY source_type;
```

## Implementation Approval Request

### Proposed Changes

1. **New Schema**: Create `mlb` schema with `live_games`, `live_events`, `live_plate_appearances` tables
2. **New Scripts**:
   - `scripts/fetch_mlb_live_pbp.py` - Live PBP fetching
   - `scripts/transform_mlb_to_retrosheet.py` - Field mapping transformation
   - `scripts/validate_mlb_ingestion.py` - Quality assurance
3. **Enhanced Views**: Update `analysis.combined_*` views to include MLB data
4. **Scheduling**: Add cron jobs for automated ingestion during game hours

### Risk Assessment

**Low Risk**:
- Separate schema prevents interference with existing data
- Read-only operations on existing Retrosheet data
- Comprehensive error handling and validation
- Rate limiting prevents API abuse

**Medium Risk**:
- API dependency (but well-established MLB Stats API)
- Data format changes (monitored with validation)
- Bridge table accuracy (regular updates from Chadwick)

### Success Metrics

- **Data Completeness**: >95% of live games successfully ingested
- **API Compliance**: Zero rate limit violations
- **Data Quality**: <1% invalid records after validation
- **Performance**: <30 second query response times
- **Integration**: Seamless analysis across data sources

### Rollback Plan

1. **Immediate**: Disable cron jobs and ingestion scripts
2. **Cleanup**: Drop `mlb` schema and related objects
3. **Verification**: Confirm no impact on existing Retrosheet data
4. **Documentation**: Update pipeline documentation

---

## Approval Request

**I am requesting approval to implement this MLB live play-by-play data ingestion pipeline.** 

The pipeline will:
- ✅ Respect all API limits and constraints
- ✅ Store data in separate, interoperable tables  
- ✅ Map MLB data to Retrosheet-compatible field definitions
- ✅ Complement (not replace) annual Retrosheet releases
- ✅ Include comprehensive error handling and monitoring
- ✅ Provide seamless integration with existing analytics

**Please approve or provide feedback on this pipeline design before I proceed with implementation.**