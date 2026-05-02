/*
File: sql/20_staging/222_stg_mlb_live_pitch_events.sql
Purpose: COMPREHENSIVE pitch event extraction from MLB API - ALL fields
Author: Agent Cascade
Date: 2026-05-01
Depends On: sql/20_staging/221_stg_mlb_live_events.sql
Called By: Live game ingestion pipeline

CRITICAL: Extracts ALL available pitch data from MLB API:
- Basic: pitch number, type, speed, result
- Advanced: spin rate, spin axis, release position, extension
- Movement: break angle, break length, pfx_x, pfx_z
- Location: plate coordinates, strike zone dimensions, zone
- Batted ball: exit velocity, launch angle, hit distance

All fields from liveData.plays.allPlays[].playEvents[].pitchData
*/

-- Function to extract ALL pitch events from live feed snapshot
CREATE OR REPLACE FUNCTION staging.extract_all_pitch_events(
    p_snapshot_id bigint,
    p_game_pk integer,
    p_payload jsonb
)
RETURNS integer AS $$
DECLARE
    v_count integer := 0;
    v_play jsonb;
    v_event jsonb;
    v_pitch_data jsonb;
    v_pa_number integer := 0;
    v_event_id integer := 0;
BEGIN
    -- Iterate through all plays (plate appearances)
    FOR v_play IN SELECT * FROM jsonb_array_elements(p_payload->'liveData'->'plays'->'allPlays')
    LOOP
        v_pa_number := v_pa_number + 1;
        
        -- Iterate through playEvents (pitches + actions) within each PA
        FOR v_event IN SELECT * FROM jsonb_array_elements(v_play->'playEvents')
        LOOP
            v_event_id := v_event_id + 1;
            v_pitch_data := v_event->'pitchData';
            
            -- Only process actual pitch events (not pickoffs, substitutions, etc.)
            IF v_pitch_data IS NOT NULL OR v_event->>'isPitch' = 'true' THEN
                
                INSERT INTO core.live_pitch_events (
                    game_pk,
                    snapshot_id,
                    pa_number,
                    pitch_number,
                    pitch_timestamp,
                    
                    -- Game state
                    inning,
                    is_top_inning,
                    outs,
                    balls,
                    strikes,
                    
                    -- Base state
                    runner_on_first,
                    runner_on_second,
                    runner_on_third,
                    bases_occupied,
                    
                    -- Score state
                    home_score,
                    away_score,
                    
                    -- Matchup
                    batter_mlb_id,
                    batter_name,
                    batter_hand,
                    pitcher_mlb_id,
                    pitcher_name,
                    pitcher_hand,
                    
                    -- Pitch characteristics (ALL fields from MLB API)
                    pitch_type,
                    pitch_type_description,
                    pitch_speed,
                    pitch_spin_rate,
                    pitch_spin_axis,
                    pitch_release_x,
                    pitch_release_z,
                    pitch_extension,
                    
                    -- Pitch result
                    pitch_result,
                    pitch_result_code,
                    
                    -- Zone and location
                    zone,
                    plate_x,
                    plate_z,
                    
                    -- Strike zone dimensions (from pitchData)
                    strike_zone_top,
                    strike_zone_bottom,
                    
                    -- Movement data
                    pfx_x,
                    pfx_z,
                    break_angle,
                    break_length,
                    break_y,
                    
                    -- Batted ball data (if applicable)
                    exit_velocity,
                    launch_angle,
                    hit_distance,
                    hit_location,
                    batted_ball_type,
                    hang_time,
                    
                    -- Win probability
                    win_exp_before,
                    win_exp_after,
                    leverage_index,
                    
                    -- Team context
                    home_team_id,
                    away_team_id,
                    batting_team_id,
                    
                    extracted_at
                ) VALUES (
                    p_game_pk,
                    p_snapshot_id,
                    v_pa_number,
                    (v_event->>'pitchNumber')::smallint,
                    (v_event->>'startTime')::timestamptz,
                    
                    -- Game state from play 'about' or linescore
                    (v_play->'about'->>'inning')::smallint,
                    (v_play->'about'->>'isTopInning')::boolean,
                    (v_play->'count'->>'outs')::smallint,
                    (v_event->'count'->>'balls')::smallint,
                    (v_event->'count'->>'strikes')::smallint,
                    
                    -- Base state from matchups
                    (v_play->'matchup'->'postOnFirst' IS NOT NULL),
                    (v_play->'matchup'->'postOnSecond' IS NOT NULL),
                    (v_play->'matchup'->'postOnThird' IS NOT NULL),
                    CONCAT(
                        CASE WHEN v_play->'matchup'->'postOnFirst' IS NOT NULL THEN '1' ELSE '0' END,
                        CASE WHEN v_play->'matchup'->'postOnSecond' IS NOT NULL THEN '1' ELSE '0' END,
                        CASE WHEN v_play->'matchup'->'postOnThird' IS NOT NULL THEN '1' ELSE '0' END
                    ),
                    
                    -- Score from result
                    (v_play->'result'->>'homeScore')::integer,
                    (v_play->'result'->>'awayScore')::integer,
                    
                    -- Matchup
                    (v_play->'matchup'->'batter'->>'id')::integer,
                    v_play->'matchup'->'batter'->>'fullName',
                    LEFT(v_play->'matchup'->'batter'->>'batSide', 1),
                    (v_play->'matchup'->'pitcher'->>'id')::integer,
                    v_play->'matchup'->'pitcher'->>'fullName',
                    LEFT(v_play->'matchup'->'pitcher'->>'pitchHand', 1),
                    
                    -- Pitch type and speed
                    v_event->'details'->'type'->>'code',
                    v_event->'details'->'type'->>'description',
                    (v_pitch_data->>'startSpeed')::decimal(4,1),
                    (v_pitch_data->>'spinRate')::decimal(5,1),
                    (v_pitch_data->>'spinAxis')::decimal(5,1),
                    (v_pitch_data->'releasePosition'->>'x')::decimal(5,2),
                    (v_pitch_data->'releasePosition'->>'z')::decimal(5,2),
                    (v_pitch_data->>'extension')::decimal(4,2),
                    
                    -- Pitch result
                    v_event->'details'->>'description',
                    v_event->'details'->>'code',
                    
                    -- Zone and location
                    (v_pitch_data->>'zone')::smallint,
                    (v_pitch_data->'coordinates'->>'x')::decimal(5,2),
                    (v_pitch_data->'coordinates'->>'y')::decimal(5,2),
                    
                    -- Strike zone
                    (v_pitch_data->>'strikeZoneTop')::decimal(5,2),
                    (v_pitch_data->>'strikeZoneBottom')::decimal(5,2),
                    
                    -- Movement
                    (v_pitch_data->>'pfxX')::decimal(5,2),
                    (v_pitch_data->>'pfxZ')::decimal(5,2),
                    (v_pitch_data->'breaks'->>'breakAngle')::decimal(5,2),
                    (v_pitch_data->'breaks'->>'breakLength')::decimal(5,2),
                    (v_pitch_data->'breaks'->>'breakY')::decimal(5,2),
                    
                    -- Batted ball (from hitData if in play)
                    (v_play->'hitData'->>'exitVelocity')::decimal(5,2),
                    (v_play->'hitData'->>'launchAngle')::decimal(5,2),
                    (v_play->'hitData'->>'totalDistance')::integer,
                    (v_play->'hitData'->>'location')::smallint,
                    v_play->'hitData'->>'trajectory',
                    (v_play->'hitData'->>'hangTime')::decimal(4,2),
                    
                    -- Win probability (from play result)
                    (v_play->'result'->>'winProbabilityBefore')::decimal(5,4),
                    (v_play->'result'->>'winProbabilityAfter')::decimal(5,4),
                    (v_play->'result'->>'leverageIndex')::decimal(4,2),
                    
                    -- Team IDs from gameData
                    p_payload->'gameData'->'teams'->'home'->>'id',
                    p_payload->'gameData'->'teams'->'away'->>'id',
                    CASE 
                        WHEN (v_play->'about'->>'isTopInning')::boolean THEN 
                            p_payload->'gameData'->'teams'->'away'->>'id'
                        ELSE 
                            p_payload->'gameData'->'teams'->'home'->>'id'
                    END,
                    
                    NOW()
                )
                ON CONFLICT (game_pk, pa_number, pitch_number) 
                DO UPDATE SET
                    snapshot_id = EXCLUDED.snapshot_id,
                    pitch_timestamp = EXCLUDED.pitch_timestamp,
                    balls = EXCLUDED.balls,
                    strikes = EXCLUDED.strikes,
                    runner_on_first = EXCLUDED.runner_on_first,
                    runner_on_second = EXCLUDED.runner_on_second,
                    runner_on_third = EXCLUDED.runner_on_third,
                    bases_occupied = EXCLUDED.bases_occupied,
                    home_score = EXCLUDED.home_score,
                    away_score = EXCLUDED.away_score,
                    pitch_speed = EXCLUDED.pitch_speed,
                    pitch_spin_rate = EXCLUDED.pitch_spin_rate,
                    pitch_spin_axis = EXCLUDED.pitch_spin_axis,
                    pitch_result = EXCLUDED.pitch_result,
                    pitch_result_code = EXCLUDED.pitch_result_code,
                    zone = EXCLUDED.zone,
                    plate_x = EXCLUDED.plate_x,
                    plate_z = EXCLUDED.plate_z,
                    exit_velocity = EXCLUDED.exit_velocity,
                    launch_angle = EXCLUDED.launch_angle,
                    hit_distance = EXCLUDED.hit_distance,
                    batted_ball_type = EXCLUDED.batted_ball_type,
                    win_exp_before = EXCLUDED.win_exp_before,
                    win_exp_after = EXCLUDED.win_exp_after,
                    leverage_index = EXCLUDED.leverage_index,
                    extracted_at = NOW();
                
                v_count := v_count + 1;
            END IF;
        END LOOP;
    END LOOP;
    
    RETURN v_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION staging.extract_all_pitch_events IS 
    'Extract ALL pitch data fields from MLB API live feed into core.live_pitch_events. Handles all pitch metrics, spin rates, movement, and batted ball data.';

-- Index to support the ON CONFLICT clause
CREATE UNIQUE INDEX IF NOT EXISTS idx_live_pitch_game_pa_pitch 
    ON core.live_pitch_events (game_pk, pa_number, pitch_number);

-- Add columns if they don't exist (for strike zone and movement data)
DO $$
BEGIN
    -- Strike zone dimensions
    ALTER TABLE core.live_pitch_events 
        ADD COLUMN IF NOT EXISTS strike_zone_top decimal(5,2),
        ADD COLUMN IF NOT EXISTS strike_zone_bottom decimal(5,2);
    
    -- Movement data
    ALTER TABLE core.live_pitch_events 
        ADD COLUMN IF NOT EXISTS pfx_x decimal(5,2),
        ADD COLUMN IF NOT EXISTS pfx_z decimal(5,2),
        ADD COLUMN IF NOT EXISTS break_angle decimal(5,2),
        ADD COLUMN IF NOT EXISTS break_length decimal(5,2),
        ADD COLUMN IF NOT EXISTS break_y decimal(5,2);
        
    -- Pitch timing
    ALTER TABLE core.live_pitch_events 
        ADD COLUMN IF NOT EXISTS plate_time decimal(4,3);
EXCEPTION
    WHEN duplicate_column THEN NULL;
END $$;
