-- Phase 3 Final Enhanced Feature View
-- Complete combined feature set including all Phase 1, 2, and 3 features

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
FROM features.plate_appearance_phase2_features pa
LEFT JOIN features.batter_pitcher_matchup_features match
    ON pa.batter_id::bigint = match.batter_id
    AND pa.pitcher_id::bigint = match.pitcher_id
    AND pa.season = match.feature_season
LEFT JOIN features.stadium_physics_features stadium
    ON pa.park_id = stadium.park_id
    AND pa.season = stadium.feature_season;
