-- File: sql/features/099_phase3_final_enhanced_view.sql
-- Purpose: Add matchup stats and stadium physics to feature set
-- Author: Agent Cascade
-- Date: 2026-04-24
CREATE OR REPLACE VIEW features.plate_appearance_final_features AS
SELECT
    pa.*,
    -- Phase 3 Matchup features
    match.matchup_hit_rate,
    match.matchup_strikeout_rate,
    match.matchup_walk_rate,
    match.matchup_home_run_rate,
    match.matchup_avg_launch_speed,
    match.matchup_avg_launch_angle,
    match.matchup_expected_ba,
    -- Phase 3 Stadium features
    stadium.park_run_factor,
    stadium.park_hitter_friendly,
    stadium.park_pitcher_friendly,
    stadium.park_extreme_hitter
FROM features.plate_appearance_phase2_features AS pa
LEFT JOIN features.batter_pitcher_matchup_features AS match
    ON
        pa.batter_id::bigint = match.batter_id
        AND pa.pitcher_id::bigint = match.pitcher_id
        AND pa.season = match.feature_season
LEFT JOIN features.stadium_physics_features AS stadium
    ON
        pa.park_id = stadium.park_id
        AND pa.season = stadium.feature_season;

