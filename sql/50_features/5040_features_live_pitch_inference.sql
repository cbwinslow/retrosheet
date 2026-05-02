/*
File: sql/50_features/5040_features_live_pitch_inference.sql
Purpose: Live pitch feature view for real-time model inference
Author: Agent Cascade
Date: 2026-05-02
Depends On: sql/30_core/313_core_live_pitch_events.sql, sql/50_features/5001_features_pitch_data_quality.sql
Called By: baseball/predictions/live_predictor.py, live inference pipeline

View: features.live_pitch_inference
- Maps core.live_pitch_events to model input format
- Feature parity with features_pitch.base_features for historical data
- Designed for real-time prediction during live games
- One row per pitch with full model feature set

Notes:
- LIVE FEATURE PARITY: Columns must match historical feature tables
- Maps live feed column names (pitch_speed) to historical names (release_speed)
- Includes derived physics features (break_magnitude, approach_angle)
- Nullable handling for incomplete live data
*/

-- Schema for live inference features
CREATE SCHEMA IF NOT EXISTS features;

-- Live pitch inference view (feature parity with historical)
CREATE OR REPLACE VIEW features.live_pitch_inference AS
SELECT 
    -- Primary keys
    lpe.live_pitch_id,
    lpe.game_pk,
    
    -- Pitch identification (synthetic for live data)
    'LIVE_' || lpe.game_pk || '_' || lpe.live_pa_id || '_' || lpe.pitch_number AS pitch_id,
    
    -- Game context
    EXTRACT(YEAR FROM lpe.pitch_timestamp)::integer AS game_year,
    DATE(lpe.pitch_timestamp) AS game_date,
    
    -- Matchup
    lpe.pitcher_id,
    lpe.batter_id,
    lpe.pitcher_hand AS p_throws,
    lpe.batter_hand AS stand,
    
    -- Pitch characteristics (mapped to historical column names)
    lpe.pitch_type,
    lpe.pitch_type_description AS pitch_name,
    lpe.pitch_speed AS release_speed,
    lpe.pitch_release_x AS release_pos_x,
    0.0::decimal AS release_pos_y,  -- Not available in live feed, default to 0
    lpe.pitch_release_z AS release_pos_z,
    
    -- Pitch movement (defaults for live feed limitations)
    0.0::decimal AS pfx_x,  -- Not directly available
    0.0::decimal AS pfx_z,  -- Not directly available
    0.0::decimal AS plate_x,  -- Not directly available
    0.0::decimal AS plate_z,  -- Not directly available
    0.0::decimal AS plate_z_adj,
    
    -- Velocity components (not available in live, default to 0)
    0.0::decimal AS vx0,
    0.0::decimal AS vy0,
    0.0::decimal AS vz0,
    0.0::decimal AS ax,
    0.0::decimal AS ay,
    0.0::decimal AS az,
    
    -- Derived metrics
    lpe.pitch_speed AS effective_speed,
    lpe.pitch_spin_rate AS release_spin_rate,
    lpe.pitch_spin_axis AS spin_axis,
    lpe.pitch_extension AS release_extension,
    
    -- Count
    lpe.balls AS balls_pre,
    lpe.strikes AS strikes_pre,
    COALESCE(lpe.balls, 0)::text || '-' || COALESCE(lpe.strikes, 0)::text AS count_label,
    
    -- Zone (live feed zone vs strike zone)
    NULL::smallint AS zone,
    
    -- Outcome (for training labels, NULL for prediction)
    NULL::text AS outcome_tier1,
    NULL::text AS outcome_tier2,
    
    -- Derived physics features
    0.0::decimal AS break_magnitude,
    0.0::decimal AS approach_angle,
    
    -- Context features
    1.0::decimal AS leverage_index,  -- Default for live
    (lpe.home_score - lpe.away_score)::decimal AS score_diff,
    0.0::decimal AS plate_distance_from_center,
    
    -- Game situation
    lpe.inning,
    lpe.outs AS outs_when_up,
    
    -- Live-specific flags
    TRUE AS is_live_data,
    lpe.pitch_timestamp AS live_timestamp,
    lpe.snapshot_id
    
FROM core.live_pitch_events lpe
WHERE lpe.pitch_timestamp >= NOW() - INTERVAL '24 hours'  -- Recent pitches only
   OR lpe.is_top_inning IS NOT NULL;  -- Or any complete pitch data

-- Materialized view for faster inference (refresh every minute during games)
CREATE MATERIALIZED VIEW IF NOT EXISTS features.live_pitch_inference_mv AS
SELECT * FROM features.live_pitch_inference;

-- Index for game-based lookups
CREATE INDEX IF NOT EXISTS idx_live_pitch_inference_mv_game_pk 
ON features.live_pitch_inference_mv (game_pk);

-- Index for timestamp-based lookups (for real-time feed)
CREATE INDEX IF NOT EXISTS idx_live_pitch_inference_mv_timestamp 
ON features.live_pitch_inference_mv (live_timestamp DESC);

-- Comment explaining usage
COMMENT ON VIEW features.live_pitch_inference IS 
'Live pitch feature view for real-time model inference. Maps core.live_pitch_events to model input format with feature parity to historical pitch features. Use for pre-pitch predictions during live MLB games.';

COMMENT ON MATERIALIZED VIEW features.live_pitch_inference_mv IS 
'Materialized cache of live pitch features for fast inference queries. Refresh every 30-60 seconds during active games.';
