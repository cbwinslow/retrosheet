# MLB Historical Data Model

## Overview

This document describes the complete data model for MLB historical data ingestion, providing a structured schema that complements Retrosheet data with modern MLB API granularity.

## Schema Architecture

```
raw_mlb.* (Source Data)
├── schedule_snapshots - API responses for game schedules
└── live_feed_snapshots - API responses for live game feeds

mlb.* (Normalized Historical Data)
├── games - Game metadata and results
├── play_events - Play-by-play events
├── pitches - Individual pitch measurements
├── players - Player biographical data
├── teams - Team information
└── venues - Ballpark details

analysis.* (Combined Views)
├── combined_games - Retrosheet + MLB games
├── combined_events - Unified play-by-play
└── combined_plate_appearances - Unified PA data
```

## Table Specifications

### Raw Data Tables (`raw_mlb.*`)

#### `schedule_snapshots`
**Purpose**: Store raw MLB schedule API responses
```sql
CREATE TABLE raw_mlb.schedule_snapshots (
    snapshot_id bigserial PRIMARY KEY,
    snapshot_date date NOT NULL,           -- Date this schedule covers
    fetched_at timestamptz NOT NULL DEFAULT now(),
    endpoint text NOT NULL,                -- API endpoint called
    payload jsonb NOT NULL,               -- Full JSON response
    request_params jsonb,                 -- Parameters sent
    http_status integer,                  -- HTTP response code
    response_time_ms integer,             -- Response time
    error_text text,                      -- Error messages
    UNIQUE(snapshot_date, fetched_at)
);
```

#### `live_feed_snapshots`
**Purpose**: Store raw MLB live feed API responses
```sql
CREATE TABLE raw_mlb.live_feed_snapshots (
    snapshot_id bigserial PRIMARY KEY,
    game_pk integer NOT NULL,
    fetched_at timestamptz NOT NULL DEFAULT now(),
    endpoint text NOT NULL,
    payload jsonb NOT NULL,
    request_params jsonb,
    http_status integer,
    response_time_ms integer,
    error_text text,
    game_date date,                       -- Extracted for indexing
    season integer,                       -- Extracted for indexing
    UNIQUE(game_pk, fetched_at)
);
```

### Normalized Historical Tables (`mlb.*`)

#### `games`
**Purpose**: Complete game metadata and results
**Primary Key**: `game_pk` (MLB's game identifier)
**Relationships**: References `mlb.teams`, `mlb.venues`
```sql
CREATE TABLE mlb.games (
    game_pk integer PRIMARY KEY,
    game_date date NOT NULL,
    season integer NOT NULL,
    -- Game identification
    game_type text,                       -- R=Regular, P=Postseason
    game_number integer,
    day_night text,
    scheduled_innings integer DEFAULT 9,
    -- Teams and venue
    home_team_id integer NOT NULL,
    away_team_id integer NOT NULL,
    home_team_name text,
    away_team_name text,
    venue_id integer,
    venue_name text,
    -- Weather conditions
    field_condition text,
    precipitation text,
    sky_condition text,
    temperature_f integer,
    wind_speed_mph integer,
    wind_direction integer,
    -- Game status and results
    status_code text,
    status_description text,
    status_abstract text,                 -- Live, Final, Scheduled
    status_detailed text,
    home_score integer DEFAULT 0,
    away_score integer DEFAULT 0,
    home_hits integer,
    away_hits integer,
    home_errors integer,
    away_errors integer,
    home_lob integer,
    away_lob integer,
    winning_team_id integer,
    losing_team_id integer,
    -- Timing
    game_start_time timestamptz,
    game_end_time timestamptz,
    game_duration_minutes integer,
    -- Officials
    home_plate_umpire_id integer,
    first_base_umpire_id integer,
    second_base_umpire_id integer,
    third_base_umpire_id integer,
    -- Metadata
    api_source text DEFAULT 'mlb_api',
    data_quality_score numeric(3,2),
    last_updated timestamptz DEFAULT now(),
    created_at timestamptz DEFAULT now()
);
```

#### `play_events`
**Purpose**: Play-by-play events with complete game state
**Primary Key**: `(game_pk, event_index)`
**Relationships**: References `mlb.games`
```sql
CREATE TABLE mlb.play_events (
    game_pk integer NOT NULL,
    event_index integer NOT NULL,
    -- Event metadata
    event_type text,                      -- pitch, action, pickoff
    event_description text,
    inning integer NOT NULL,
    is_bottom_inning boolean NOT NULL,
    -- Count state
    balls_before integer DEFAULT 0,
    strikes_before integer DEFAULT 0,
    outs_before integer DEFAULT 0,
    -- Players involved
    batter_id integer,
    pitcher_id integer,
    on_deck_batter_id integer,
    in_hole_batter_id integer,
    -- Base runners
    runner_on_1b_id integer,
    runner_on_2b_id integer,
    runner_on_3b_id integer,
    -- Event result
    event_code text,                      -- MLB event code
    event_result text,                    -- single, double, home_run, etc.
    is_scoring_play boolean DEFAULT false,
    runs_batted_in integer DEFAULT 0,
    -- Game state after
    balls_after integer,
    strikes_after integer,
    outs_after integer,
    home_score_after integer,
    away_score_after integer,
    game_pa_count integer,
    half_inning_pa_count integer,
    -- Event classification
    is_plate_appearance boolean,
    is_at_bat boolean,
    is_new_plate_appearance boolean DEFAULT true,
    is_inning_start boolean DEFAULT false,
    is_inning_end boolean DEFAULT false,
    is_game_end boolean DEFAULT false,
    -- MLB-specific data
    mlb_game_pk integer,
    mlb_event_index integer,
    mlb_event_type text,
    event_type_description text,
    trajectory text,
    raw_play jsonb,
    -- Metadata
    api_source text DEFAULT 'mlb_api',
    data_quality_score numeric(3,2),
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now(),
    PRIMARY KEY (game_pk, event_index)
);
```

#### `pitches`
**Purpose**: Individual pitch measurements with physics data
**Primary Key**: `(game_pk, event_index, pitch_index)`
**Relationships**: References `mlb.play_events`
```sql
CREATE TABLE mlb.pitches (
    game_pk integer NOT NULL,
    event_index integer NOT NULL,
    pitch_index integer NOT NULL,
    pitch_number integer NOT NULL,
    -- Pitch identification
    play_id text,
    pitch_uid text UNIQUE,
    -- Pitch type classification
    pitch_type_code text,                 -- FF, SL, CU, etc.
    pitch_type_description text,
    pitch_type_confidence numeric(4,3),
    -- Pitch result
    pitch_call_code text,                 -- B, S, F, X, etc.
    pitch_call_description text,
    pitch_call_confidence numeric(4,3),
    -- Pitch location (plate coordinates)
    plate_x numeric(6,2),                 -- Horizontal (-2 to 2 ft)
    plate_z numeric(6,2),                 -- Vertical (0 to 4 ft)
    plate_zone integer,                   -- Strike zone zone (1-14)
    -- Pitch trajectory
    start_speed numeric(5,1),             -- Initial velocity (mph)
    end_speed numeric(5,1),               -- Final velocity (mph)
    extension numeric(5,3),               -- Release extension (ft)
    -- Pitch physics (Statcast)
    spin_rate integer,                    -- RPM
    spin_direction integer,               -- Degrees
    break_angle numeric(4,1),             -- Degrees
    break_length numeric(4,1),            -- Feet
    break_vertical numeric(5,1),          -- Inches
    break_horizontal numeric(5,1),        -- Inches
    pfx_x numeric(5,2),                   -- Horizontal movement (ft)
    pfx_z numeric(5,2),                   -- Vertical movement (ft)
    -- Pitch timing
    plate_time numeric(6,4),              -- Time to plate (seconds)
    reaction_time numeric(6,4),           -- Batter reaction time
    -- Contextual data
    batter_id integer,
    pitcher_id integer,
    balls_before integer,
    strikes_before integer,
    outs_before integer,
    inning integer,
    is_top_inning boolean,
    -- Game situation
    runner_on_1b boolean DEFAULT false,
    runner_on_2b boolean DEFAULT false,
    runner_on_3b boolean DEFAULT false,
    home_score integer,
    away_score integer,
    -- Metadata
    api_source text DEFAULT 'mlb_api',
    data_quality_score numeric(3,2),
    pitch_system text DEFAULT 'statcast',
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now(),
    PRIMARY KEY (game_pk, event_index, pitch_index)
);
```

#### `players`
**Purpose**: Comprehensive player biographical and performance data
**Primary Key**: `mlb_id` (MLB's player identifier)
```sql
CREATE TABLE mlb.players (
    mlb_id integer PRIMARY KEY,
    retrosheet_id text,
    -- Biographical
    full_name text NOT NULL,
    first_name text,
    last_name text,
    primary_number text,
    birth_date date,
    birth_city text,
    birth_state_province text,
    birth_country text,
    height text,                          -- "6' 2\""
    weight integer,                       -- lbs
    -- Physical attributes
    bat_side text,                        -- L, R, S
    pitch_hand text,                      -- L, R
    -- MLB career
    mlb_debut_date date,
    last_game_date date,
    active boolean DEFAULT true,
    -- Current status
    current_team_id integer,
    position_code text,
    position_name text,
    position_type text,
    -- Advanced metrics
    bat_speed numeric(6,1),               -- mph
    swing_speed numeric(6,1),             -- mph
    sprint_speed numeric(5,2),            -- seconds for 60ft
    arm_strength text,                    -- above/below average
    -- Metadata
    api_source text DEFAULT 'mlb_api',
    data_quality_score numeric(3,2),
    last_updated timestamptz DEFAULT now(),
    created_at timestamptz DEFAULT now()
);
```

#### `teams`
**Purpose**: Team information and organization
**Primary Key**: `mlb_id` (MLB's team identifier)
```sql
CREATE TABLE mlb.teams (
    mlb_id integer PRIMARY KEY,
    retrosheet_id text,
    team_name text NOT NULL,
    team_code text,                       -- BOS, NYY, etc.
    location_name text,
    league_id integer,
    league_name text,
    division_id integer,
    division_name text,
    venue_id integer,
    venue_name text,
    active boolean DEFAULT true,
    first_year integer,
    last_year integer,
    api_source text DEFAULT 'mlb_api',
    last_updated timestamptz DEFAULT now(),
    created_at timestamptz DEFAULT now()
);
```

#### `venues`
**Purpose**: Ballpark information and field dimensions
**Primary Key**: `mlb_id` (MLB's venue identifier)
```sql
CREATE TABLE mlb.venues (
    mlb_id integer PRIMARY KEY,
    retrosheet_id text,
    name text NOT NULL,
    location text,
    time_zone text,
    -- Field dimensions
    left_field_distance integer,
    center_field_distance integer,
    right_field_distance integer,
    left_center_distance integer,
    right_center_distance integer,
    -- Field surface
    turf_type text,
    roof_type text,
    active boolean DEFAULT true,
    api_source text DEFAULT 'mlb_api',
    last_updated timestamptz DEFAULT now(),
    created_at timestamptz DEFAULT now()
);
```

## Index Strategy

### Primary Indexes
```sql
-- Game lookups
CREATE INDEX games_season_date_idx ON mlb.games (season, game_date);
CREATE INDEX games_home_team_idx ON mlb.games (home_team_id);
CREATE INDEX games_away_team_idx ON mlb.games (away_team_id);
CREATE INDEX games_venue_idx ON mlb.games (venue_id);
CREATE INDEX games_status_idx ON mlb.games (status_abstract);

-- Event lookups
CREATE INDEX play_events_game_idx ON mlb.play_events (game_pk);
CREATE INDEX play_events_season_idx ON mlb.play_events (season);
CREATE INDEX play_events_batter_idx ON mlb.play_events (batter_id);
CREATE INDEX play_events_pitcher_idx ON mlb.play_events (pitcher_id);
CREATE INDEX play_events_event_type_idx ON mlb.play_events (event_type);

-- Pitch lookups
CREATE INDEX pitches_game_event_idx ON mlb.pitches (game_pk, event_index);
CREATE INDEX pitches_batter_idx ON mlb.pitches (batter_id);
CREATE INDEX pitches_pitcher_idx ON mlb.pitches (pitcher_id);
CREATE INDEX pitches_pitch_type_idx ON mlb.pitches (pitch_type_code);
CREATE INDEX pitches_season_idx ON mlb.pitches (season);

-- Reference data
CREATE INDEX players_retrosheet_idx ON mlb.players (retrosheet_id);
CREATE INDEX players_team_idx ON mlb.players (current_team_id);
CREATE INDEX teams_retrosheet_idx ON mlb.teams (retrosheet_id);
CREATE INDEX venues_retrosheet_idx ON mlb.venues (retrosheet_id);
```

### Composite Indexes for Common Queries
```sql
-- Multi-season player performance
CREATE INDEX play_events_season_batter_idx ON mlb.play_events (season, batter_id);
CREATE INDEX pitches_season_pitcher_idx ON mlb.pitches (season, pitcher_id);

-- Game-specific event sequences
CREATE INDEX play_events_game_sequence_idx ON mlb.play_events (game_pk, event_sequence);
CREATE INDEX pitches_game_sequence_idx ON mlb.pitches (game_pk, pitch_number);
```

## Data Quality & Constraints

### Check Constraints
```sql
-- Games
ALTER TABLE mlb.games ADD CONSTRAINT games_scores_positive
    CHECK (home_score >= 0 AND away_score >= 0);
ALTER TABLE mlb.games ADD CONSTRAINT games_season_valid
    CHECK (season >= 2000 AND season <= 2030);

-- Events
ALTER TABLE mlb.play_events ADD CONSTRAINT events_inning_valid
    CHECK (inning >= 1 AND inning <= 25);
ALTER TABLE mlb.play_events ADD CONSTRAINT events_count_valid
    CHECK (balls_before >= 0 AND balls_before <= 3
           AND strikes_before >= 0 AND strikes_before <= 2
           AND outs_before >= 0 AND outs_before <= 2);

-- Pitches
ALTER TABLE mlb.pitches ADD CONSTRAINT pitches_speed_valid
    CHECK (start_speed > 0 AND start_speed < 105);
ALTER TABLE mlb.pitches ADD CONSTRAINT pitches_plate_coords_valid
    CHECK (plate_x BETWEEN -4 AND 4 AND plate_z BETWEEN -2 AND 6);
```

### Data Quality Scoring
```sql
-- Quality score calculation
CREATE OR REPLACE FUNCTION mlb.calculate_data_quality(
    has_pitch_data boolean,
    has_weather_data boolean,
    has_official_data boolean,
    api_response_time integer
) RETURNS numeric(3,2) AS $$
BEGIN
    -- Base quality score
    score := 0.5;

    -- Add points for data completeness
    IF has_pitch_data THEN score := score + 0.2; END IF;
    IF has_weather_data THEN score := score + 0.1; END IF;
    IF has_official_data THEN score := score + 0.1; END IF;

    -- Penalize slow responses
    IF api_response_time > 5000 THEN score := score - 0.1; END IF;

    RETURN GREATEST(0.0, LEAST(1.0, score));
END;
$$ LANGUAGE plpgsql;
```

## Relationships & Foreign Keys

### Core Relationships
```sql
-- Games reference teams and venues
ALTER TABLE mlb.games ADD CONSTRAINT games_home_team_fk
    FOREIGN KEY (home_team_id) REFERENCES mlb.teams(mlb_id);
ALTER TABLE mlb.games ADD CONSTRAINT games_away_team_fk
    FOREIGN KEY (away_team_id) REFERENCES mlb.teams(mlb_id);
ALTER TABLE mlb.games ADD CONSTRAINT games_venue_fk
    FOREIGN KEY (venue_id) REFERENCES mlb.venues(mlb_id);

-- Events reference games
ALTER TABLE mlb.play_events ADD CONSTRAINT play_events_game_fk
    FOREIGN KEY (game_pk) REFERENCES mlb.games(game_pk);

-- Pitches reference events
ALTER TABLE mlb.pitches ADD CONSTRAINT pitches_event_fk
    FOREIGN KEY (game_pk, event_index) REFERENCES mlb.play_events(game_pk, event_index);

-- Players reference teams
ALTER TABLE mlb.players ADD CONSTRAINT players_team_fk
    FOREIGN KEY (current_team_id) REFERENCES mlb.teams(mlb_id);

-- Teams reference venues
ALTER TABLE mlb.teams ADD CONSTRAINT teams_venue_fk
    FOREIGN KEY (venue_id) REFERENCES mlb.venues(mlb_id);
```

## Integration with Retrosheet

### Bridge Table Relationships
```sql
-- Players: MLB ID ↔ Retrosheet ID
ALTER TABLE mlb.players ADD CONSTRAINT players_retrosheet_bridge_fk
    FOREIGN KEY (retrosheet_id) REFERENCES core.players(retrosheet_player_id);

-- Teams: MLB ID ↔ Retrosheet ID
ALTER TABLE mlb.teams ADD CONSTRAINT teams_retrosheet_bridge_fk
    FOREIGN KEY (retrosheet_id) REFERENCES core.teams(retrosheet_team_id);

-- Venues: MLB ID ↔ Retrosheet ID
ALTER TABLE mlb.venues ADD CONSTRAINT venues_retrosheet_bridge_fk
    FOREIGN KEY (retrosheet_id) REFERENCES core.parks(retrosheet_park_id);
```

### Combined Analysis Views
```sql
-- Unified game view
CREATE OR REPLACE VIEW analysis.combined_games AS
SELECT * FROM core.games
UNION ALL
SELECT
    game_pk, season, source_type, game_date::text, game_number,
    day_of_week, start_time, doubleheader_flag, day_night,
    -- Map MLB team IDs to Retrosheet via bridge tables
    COALESCE(rt_home.retrosheet_team_id, home_team_id::text),
    COALESCE(rt_away.retrosheet_team_id, away_team_id::text),
    -- ... map other fields
FROM mlb.games mg
LEFT JOIN bridge.team_xref rt_home ON mg.home_team_id = rt_home.mlb_team_id
LEFT JOIN bridge.team_xref rt_away ON mg.away_team_id = rt_away.mlb_team_id;
```

## Data Volume Estimates

### Target Dataset Size (2000-2025)
- **Games**: ~68,000 (regular season + postseason)
- **Play Events**: ~6.2M plate appearances
- **Pitches**: ~15M+ individual pitch measurements (2015+)
- **Players**: ~15K+ MLB players
- **Teams**: ~150 MLB franchises
- **Venues**: ~60 MLB ballparks

### Storage Requirements
- **Raw JSON**: ~500GB (compressed)
- **Normalized Tables**: ~200GB
- **Indexes**: ~50GB
- **Total**: ~750GB for complete historical dataset

## Backup & Recovery

### Schema Versioning
```sql
-- Schema version tracking
CREATE TABLE mlb.schema_versions (
    version_id serial PRIMARY KEY,
    version_tag text NOT NULL,
    applied_at timestamptz DEFAULT now(),
    description text,
    UNIQUE(version_tag)
);

-- Record schema deployments
INSERT INTO mlb.schema_versions (version_tag, description)
VALUES ('v1.0.0', 'Initial MLB historical schema deployment');
```

### Data Partitioning Strategy
```sql
-- Partition large tables by season
CREATE TABLE mlb.games_y2020 PARTITION OF mlb.games
    FOR VALUES FROM (2020) TO (2021);
CREATE TABLE mlb.games_y2021 PARTITION OF mlb.games
    FOR VALUES FROM (2021) TO (2022);
-- etc.

-- Partition events by season for performance
CREATE TABLE mlb.play_events_y2020 PARTITION OF mlb.play_events
    FOR VALUES FROM (2020) TO (2021);
```

This comprehensive data model provides a solid foundation for MLB historical data storage, analysis, and integration with existing Retrosheet data.