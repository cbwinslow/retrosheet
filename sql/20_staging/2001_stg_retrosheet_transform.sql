/*
File: sql/20_staging/2001_stg_retrosheet_transform.sql
Purpose: Transform and load data from raw to staging
Author: Agent Cascade
Date: 2026-04-28
Depends On: sql/20_staging/2000_staging_schema.sql
Called By: scripts/staging/load_retrosheet_to_staging.sh

Functions:
- staging.transform_chadwick_event(): Transforms single row from chadwick_event_raw
- staging.load_events_for_season(): Batch load events for a season
- staging.validate_staged_events(): Validation rules for staged data

Notes:
- Uses Chadwick cwevent field mappings (RETROSHEET_ID, INN_CT, etc.)
- All text columns cast to appropriate types
- Validation errors collected but don't block loading
- Duplicate detection based on (season, game_id, event_id)
*/

-- Function to validate a staged event record
CREATE OR REPLACE FUNCTION staging.validate_event_record()
RETURNS TRIGGER AS $$
DECLARE
    errors text[] := '{}';
BEGIN
    -- Required fields
    IF NEW.game_id IS NULL THEN
        errors := array_append(errors, 'game_id is null');
    END IF;
    
    IF NEW.event_id IS NULL THEN
        errors := array_append(errors, 'event_id is null');
    END IF;
    
    -- Value ranges
    IF NEW.inning IS NOT NULL AND (NEW.inning < 1 OR NEW.inning > 50) THEN
        errors := array_append(errors, 'inning out of range: ' || NEW.inning);
    END IF;
    
    IF NEW.outs IS NOT NULL AND (NEW.outs < 0 OR NEW.outs > 3) THEN
        errors := array_append(errors, 'outs out of range: ' || NEW.outs);
    END IF;
    
    IF NEW.balls IS NOT NULL AND (NEW.balls < 0 OR NEW.balls > 4) THEN
        errors := array_append(errors, 'balls out of range: ' || NEW.balls);
    END IF;
    
    IF NEW.strikes IS NOT NULL AND (NEW.strikes < 0 OR NEW.strikes > 3) THEN
        errors := array_append(errors, 'strikes out of range: ' || NEW.strikes);
    END IF;
    
    -- Update validation status
    IF array_length(errors, 1) > 0 THEN
        NEW.is_valid := false;
        NEW.validation_errors := errors;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION staging.validate_event_record() IS 'Trigger function to validate staged event records';

-- Apply validation trigger
CREATE OR REPLACE TRIGGER trg_validate_stg_events
    BEFORE INSERT OR UPDATE ON staging.stg_retrosheet_events
    FOR EACH ROW
    EXECUTE FUNCTION staging.validate_event_record();

-- Function to load events from chadwick_event_raw for a season
CREATE OR REPLACE FUNCTION staging.load_events_for_season(
    p_season integer,
    p_ingest_run_id bigint DEFAULT NULL
)
RETURNS TABLE(
    rows_loaded bigint,
    rows_invalid bigint,
    errors_caught bigint
) AS $$
DECLARE
    v_rows_loaded bigint := 0;
    v_rows_invalid bigint := 0;
    v_errors_caught bigint := 0;
BEGIN
    -- Insert transformed events
    INSERT INTO staging.stg_retrosheet_events (
        source_row_id,
        ingest_run_id,
        season,
        game_id,
        event_id,
        source_type,
        inning,
        batting_team,
        outs,
        balls,
        strikes,
        pitch_sequence,
        runner_1b,
        runner_2b,
        runner_3b,
        event_type,
        event_description,
        hit_location,
        batted_ball_type,
        ab_flag,
        sf_flag,
        sh_flag,
        pitcher_id,
        pitcher_hand,
        batter_id,
        batter_hand,
        pos_1, pos_2, pos_3, pos_4, pos_5, pos_6, pos_7, pos_8, pos_9,
        runs_scored,
        rbi
    )
    SELECT
        r.row_number,
        COALESCE(p_ingest_run_id, r.ingest_run_id),
        r.season,
        r.c001,  -- game_id
        r.c002::integer,  -- event_id
        r.source_type,
        r.c004::integer,  -- inning
        r.c005,  -- batting_team
        r.c006::integer,  -- outs
        r.c007::integer,  -- balls
        r.c008::integer,  -- strikes
        r.c009,  -- pitch_sequence
        r.c010,  -- runner_1b
        r.c011,  -- runner_2b
        r.c012,  -- runner_3b
        r.c013::integer,  -- event_type
        r.c014,  -- event_description
        r.c015::integer,  -- hit_location
        r.c016,  -- batted_ball_type
        r.c017 = 'T',  -- ab_flag
        r.c018 = 'T',  -- sf_flag
        r.c019 = 'T',  -- sh_flag
        r.c020,  -- pitcher_id
        r.c021,  -- pitcher_hand
        r.c022,  -- batter_id
        r.c023,  -- batter_hand
        r.c024, r.c025, r.c026, r.c027, r.c028,  -- pos_1-5
        r.c029, r.c030, r.c031, r.c032,  -- pos_6-9
        r.c033::integer,  -- runs_scored
        r.c034::integer   -- rbi
    FROM raw_retrosheet.chadwick_event_raw r
    WHERE r.season = p_season
      AND NOT EXISTS (
          SELECT 1 FROM staging.stg_retrosheet_events s
          WHERE s.season = r.season
            AND s.game_id = r.c001
            AND s.event_id = r.c002::integer
      )
    ON CONFLICT (season, game_id, event_id) DO NOTHING;
    
    GET DIAGNOSTICS v_rows_loaded = ROW_COUNT;
    
    -- Count invalid rows
    SELECT COUNT(*) INTO v_rows_invalid
    FROM staging.stg_retrosheet_events
    WHERE season = p_season AND is_valid = false;
    
    -- Count total validation errors
    SELECT COALESCE(SUM(array_length(validation_errors, 1)), 0)
    INTO v_errors_caught
    FROM staging.stg_retrosheet_events
    WHERE season = p_season AND is_valid = false;
    
    RETURN QUERY SELECT v_rows_loaded, v_rows_invalid, v_errors_caught;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION staging.load_events_for_season(integer, bigint) IS 
    'Transforms and loads events from chadwick_event_raw to staging for a given season';

-- View to show validation summary by season
CREATE OR REPLACE VIEW staging.v_event_validation_summary AS
SELECT
    season,
    COUNT(*) as total_events,
    COUNT(*) FILTER (WHERE is_valid) as valid_events,
    COUNT(*) FILTER (WHERE NOT is_valid) as invalid_events,
    ROUND(100.0 * COUNT(*) FILTER (WHERE NOT is_valid) / NULLIF(COUNT(*), 0), 2) as invalid_pct
FROM staging.stg_retrosheet_events
GROUP BY season
ORDER BY season;

COMMENT ON VIEW staging.v_event_validation_summary IS 'Summary of validation status by season';
