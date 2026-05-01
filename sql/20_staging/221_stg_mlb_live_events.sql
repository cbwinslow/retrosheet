/*
File: sql/20_staging/221_stg_mlb_live_events.sql
Purpose: Staging table for MLB live feed events with flattened structure
Author: Agent Cascade
Date: 2026-04-29
Depends On: sql/10_raw/1020_raw_mlb_live_feed.sql, sql/20_staging/2000_staging_schema.sql
Called By: baseball/sources/mlb.py ingest pipeline, transform scripts

Table: staging.stg_mlb_live_events
- Flattened event data from raw_mlb.live_feed_snapshots
- Preserves complete event structure from MLB API
- Deterministic uniqueness on (game_pk, event_id, snapshot_id)
- Links to core tables via bridge lookups

Notes:
- ALL fields from MLB API are preserved (no field reduction)
- JSONB extraction with explicit column mapping
- Validation flags for data quality checks
- Lineage tracking to raw snapshots
*/

-- Staging table for MLB live events
CREATE TABLE IF NOT EXISTS staging.stg_mlb_live_events (
    -- Primary key and lineage
    staging_event_id bigserial PRIMARY KEY,
    snapshot_id bigint NOT NULL REFERENCES raw_mlb.live_feed_snapshots(snapshot_id),
    ingest_run_id bigint REFERENCES raw_retrosheet.ingest_runs(ingest_run_id),
    
    -- Game identification
    game_pk integer NOT NULL,
    game_date date,
    season integer,
    
    -- Event identification
    event_id integer NOT NULL,              -- Sequence number within game
    event_type varchar(20) NOT NULL,          -- 'PA', 'PITCH', 'GAME_STATE', 'SUB'
    event_timestamp timestamptz,
    
    -- Game state at time of event
    inning smallint NOT NULL,
    is_top_inning boolean NOT NULL,
    outs smallint NOT NULL,
    balls smallint,
    strikes smallint,
    
    -- Base state
    runner_on_first boolean DEFAULT FALSE,
    runner_on_second boolean DEFAULT FALSE,
    runner_on_third boolean DEFAULT FALSE,
    bases_occupied varchar(3),              -- '000', '100', '111', etc.
    
    -- Score state
    home_score integer DEFAULT 0,
    away_score integer DEFAULT 0,
    score_differential integer GENERATED ALWAYS AS (home_score - away_score) STORED,
    
    -- Matchup
    batter_id varchar(20),                  -- Retrosheet ID (from bridge)
    batter_mlb_id integer,                 -- Original MLB ID
    batter_name varchar(100),
    batter_hand char(1),                    -- 'L', 'R', 'S'
    
    pitcher_id varchar(20),                 -- Retrosheet ID (from bridge)
    pitcher_mlb_id integer,                -- Original MLB ID
    pitcher_name varchar(100),
    pitcher_hand char(1),                   -- 'L', 'R', 'S'
    
    -- Plate appearance details (if event_type = 'PA')
    pa_result varchar(50),                  -- 'Single', 'Home Run', 'Walk', etc.
    pa_result_code varchar(10),             -- '1B', 'HR', 'BB', 'K', etc.
    exit_velocity decimal(5,2),             -- Statcast exit velocity (mph)
    launch_angle decimal(5,2),              -- Statcast launch angle (degrees)
    hit_distance integer,                   -- Estimated hit distance (feet)
    hit_location smallint,                  -- 1-9 fielding position
    
    -- Pitch details (if event_type = 'PITCH')
    pitch_number smallint,                  -- Pitch number within PA
    pitch_type varchar(10),                 -- 'FF', 'SL', 'CH', etc.
    pitch_type_description varchar(50),     -- 'Four-Seam Fastball'
    pitch_speed decimal(4,1),               -- MPH
    pitch_result varchar(50),               -- 'Ball', 'Called Strike', 'Swinging Strike', etc.
    pitch_result_code varchar(10),          -- 'B', 'C', 'S', 'F', 'X', etc.
    zone smallint,                          -- 1-9 strike zone (null = out of zone)
    
    -- Run expectancy context
    re24_state varchar(10),                 -- Runners-outs state (e.g., '1_2_3_2')
    re24_value decimal(6,4),                -- Change in run expectancy
    win_exp_before decimal(5,4),            -- Win probability before event
    win_exp_after decimal(5,4),             -- Win probability after event
    
    -- Inning/win probability context
    inning_half varchar(10),                -- 'top_1', 'bot_9', etc.
    leverage_index decimal(4,2),            -- Current leverage index
    
    -- Validation and metadata
    is_valid boolean DEFAULT true,
    validation_errors text[],
    loaded_at timestamptz NOT NULL DEFAULT NOW(),
    
    -- Unique constraint per game/snapshot/event
    UNIQUE(game_pk, snapshot_id, event_id)
);

COMMENT ON TABLE staging.stg_mlb_live_events IS 
    'Flattened MLB live feed events with complete field preservation and bridge ID resolution';

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_stg_mlb_live_game ON staging.stg_mlb_live_events(game_pk);
CREATE INDEX IF NOT EXISTS idx_stg_mlb_live_snapshot ON staging.stg_mlb_live_events(snapshot_id);
CREATE INDEX IF NOT EXISTS idx_stg_mlb_live_type ON staging.stg_mlb_live_events(event_type);
CREATE INDEX IF NOT EXISTS idx_stg_mlb_live_batter ON staging.stg_mlb_live_events(batter_id) WHERE batter_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_stg_mlb_live_pitcher ON staging.stg_mlb_live_events(pitcher_id) WHERE pitcher_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_stg_mlb_live_loaded ON staging.stg_mlb_live_events(loaded_at DESC);

-- Composite index for model training queries
CREATE INDEX IF NOT EXISTS idx_stg_mlb_live_features ON staging.stg_mlb_live_events(
    inning, is_top_inning, outs, bases_occupied, score_differential
) WHERE event_type = 'PA';

-- Function to insert staging events from raw snapshot
CREATE OR REPLACE FUNCTION staging.insert_mlb_live_events(
    p_snapshot_id bigint,
    p_game_pk integer,
    p_payload jsonb
)
RETURNS integer AS $$
DECLARE
    v_count integer;
BEGIN
    -- Extract events from JSONB payload and insert into staging
    INSERT INTO staging.stg_mlb_live_events (
        snapshot_id,
        game_pk,
        game_date,
        season,
        event_id,
        event_type,
        event_timestamp,
        inning,
        is_top_inning,
        outs,
        balls,
        strikes,
        runner_on_first,
        runner_on_second,
        runner_on_third,
        bases_occupied,
        home_score,
        away_score,
        batter_mlb_id,
        batter_name,
        batter_hand,
        pitcher_mlb_id,
        pitcher_name,
        pitcher_hand,
        pa_result,
        pa_result_code,
        exit_velocity,
        launch_angle,
        hit_distance,
        hit_location,
        pitch_number,
        pitch_type,
        pitch_type_description,
        pitch_speed,
        pitch_result,
        pitch_result_code,
        zone,
        re24_state,
        re24_value,
        win_exp_before,
        win_exp_after,
        inning_half,
        leverage_index,
        loaded_at
    )
    SELECT 
        p_snapshot_id,
        p_game_pk,
        (p_payload->>'gameDate')::date,
        (p_payload->>'season')::integer,
        (e->>'event_id')::integer,
        e->>'event_type',
        (e->>'event_timestamp')::timestamptz,
        (e->>'inning')::smallint,
        (e->>'is_top_inning')::boolean,
        (e->>'outs')::smallint,
        (e->>'balls')::smallint,
        (e->>'strikes')::smallint,
        (e->>'runner_on_first')::boolean,
        (e->>'runner_on_second')::boolean,
        (e->>'runner_on_third')::boolean,
        e->>'bases_occupied',
        (e->>'home_score')::integer,
        (e->>'away_score')::integer,
        (e->>'batter_mlb_id')::integer,
        e->>'batter_name',
        e->>'batter_hand',
        (e->>'pitcher_mlb_id')::integer,
        e->>'pitcher_name',
        e->>'pitcher_hand',
        e->>'pa_result',
        e->>'pa_result_code',
        (e->>'exit_velocity')::decimal(5,2),
        (e->>'launch_angle')::decimal(5,2),
        (e->>'hit_distance')::integer,
        (e->>'hit_location')::smallint,
        (e->>'pitch_number')::smallint,
        e->>'pitch_type',
        e->>'pitch_type_description',
        (e->>'pitch_speed')::decimal(4,1),
        e->>'pitch_result',
        e->>'pitch_result_code',
        (e->>'zone')::smallint,
        e->>'re24_state',
        (e->>'re24_value')::decimal(6,4),
        (e->>'win_exp_before')::decimal(5,4),
        (e->>'win_exp_after')::decimal(5,4),
        e->>'inning_half',
        (e->>'leverage_index')::decimal(4,2),
        NOW()
    FROM jsonb_array_elements(p_payload->'events') e
    ON CONFLICT (game_pk, snapshot_id, event_id) DO NOTHING;
    
    GET DIAGNOSTICS v_count = ROW_COUNT;
    RETURN v_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION staging.insert_mlb_live_events IS 
    'Extract and insert events from raw MLB live feed snapshot into staging table';
