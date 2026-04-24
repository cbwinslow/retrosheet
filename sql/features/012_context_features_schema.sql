/*
File: sql/features/012_context_features_schema.sql
Purpose: Create schema for context features: weather, momentum, umpire, attendance, park
Author: Agent Cascade
Date: 2026-04-24
Depends On: sql/features/011_populate_more_features_batch.sql
Called By: Manual execution

Tables Modified:
- features_pitch.engineered_features (adds context columns)

New Features (60+):

## Weather & Environmental (Category 2)
- temp_extreme_flag: Hot/cold game indicator
- wind_in_direction: Wind blowing out (LF/CF/RF)
- wind_effect_score: Combined direction + speed impact
- humidity_proxy: Estimated humidity from month/temp
- altitude_factor: Park elevation effect
- is_shadow_game: Late afternoon shadow conditions

## Momentum & Streaks (Category 3)
- team_last_5_win_rate: Recent team form (5 games)
- team_last_10_win_rate: Medium-term form (10 games)
- team_momentum_delta: Change from 30-day to 5-day
- batter_last_7_pa_count: Recent playing time
- pitcher_last_3_era: Recent ERA (last 3 starts)
- pitcher_last_3_strikeout_rate: Recent K-rate
- pitcher_last_3_walk_rate: Recent BB-rate

## Umpire Effects (Category 4)
- umpire_strike_zone_size: Small/large zone tendency
- umpire_strike_calls_pct: Called strike %
- umpire_ball_calls_pct: Called ball %
- umpire_k_friendly: Strikeout-friendly tendency
- umpire_walk_friendly: Walk-friendly tendency
- umpire_hitter_favored: Small zone = hitter advantage
- umpire_pitcher_favored: Large zone = pitcher advantage
- umpire_consistency_score: Zone call variance
- umpire_experience_years: Estimated tenure

## Attendance & Crowd (Category 8)
- attendance_vs_capacity_pct: Crowd fullness
- attendance_vs_team_avg_pct: Relative to team average
- is_sellout: 95%+ capacity
- crowd_noise_proxy: Day game + attendance interaction
- home_field_advantage_score: Combined factors

## Park Factors (Category 7)
- park_elevation_feet: Altitude (Coors effect)
- park_left_field_distance: LF wall distance
- park_center_field_distance: CF wall distance
- park_right_field_distance: RF wall distance
- park_grass_turf: Surface type
- park_has_retractable_roof: Roofed stadium
- park_is_dome: Indoor stadium
- hr_factor_lf: Home run factor left field
- hr_factor_cf: Home run factor center
- hr_factor_rf: Home run factor right field

## Fatigue Deep Dive (Category 1 extension)
- pitcher_inning_velocity_decline: Velo drop within game
- pitcher_season_workload: Season pitch count
- pitcher_back_to_back: Starts on short rest
- days_since_last_appearance: Rest days

Notes:
- All features research-backed from FEATURE_ENGINEERING_PLAN.md
- Uses existing data from core.games, core.parks, core.umpires
- Links via game_id and park_id
*/

-- Weather & Environmental features
ALTER TABLE features_pitch.engineered_features
    ADD COLUMN IF NOT EXISTS temp_extreme_flag TEXT,
    ADD COLUMN IF NOT EXISTS wind_in_direction BOOLEAN,
    ADD COLUMN IF NOT EXISTS wind_effect_score NUMERIC,
    ADD COLUMN IF NOT EXISTS humidity_proxy NUMERIC,
    ADD COLUMN IF NOT EXISTS altitude_factor NUMERIC,
    ADD COLUMN IF NOT EXISTS is_shadow_game BOOLEAN,
    ADD COLUMN IF NOT EXISTS home_run_environment_boost NUMERIC;

-- Momentum & Streaks features
ALTER TABLE features_pitch.engineered_features
    ADD COLUMN IF NOT EXISTS batting_team_last_5_win_rate NUMERIC,
    ADD COLUMN IF NOT EXISTS batting_team_last_10_win_rate NUMERIC,
    ADD COLUMN IF NOT EXISTS batting_team_momentum_delta NUMERIC,
    ADD COLUMN IF NOT EXISTS fielding_team_last_5_win_rate NUMERIC,
    ADD COLUMN IF NOT EXISTS fielding_team_last_10_win_rate NUMERIC,
    ADD COLUMN IF NOT EXISTS fielding_team_momentum_delta NUMERIC,
    ADD COLUMN IF NOT EXISTS batter_7day_pa_count INTEGER,
    ADD COLUMN IF NOT EXISTS pitcher_last_3_era NUMERIC,
    ADD COLUMN IF NOT EXISTS pitcher_last_3_strikeout_rate NUMERIC,
    ADD COLUMN IF NOT EXISTS pitcher_last_3_walk_rate NUMERIC,
    ADD COLUMN IF NOT EXISTS pitcher_last_3_ip_avg NUMERIC,
    ADD COLUMN IF NOT EXISTS pitcher_quality_starts_last_5 INTEGER;

-- Umpire features
ALTER TABLE features_pitch.engineered_features
    ADD COLUMN IF NOT EXISTS home_plate_umpire_id TEXT,
    ADD COLUMN IF NOT EXISTS umpire_strike_zone_size TEXT,
    ADD COLUMN IF NOT EXISTS umpire_strike_calls_pct NUMERIC,
    ADD COLUMN IF NOT EXISTS umpire_ball_calls_pct NUMERIC,
    ADD COLUMN IF NOT EXISTS umpire_k_friendly BOOLEAN,
    ADD COLUMN IF NOT EXISTS umpire_walk_friendly BOOLEAN,
    ADD COLUMN IF NOT EXISTS umpire_hitter_favored BOOLEAN,
    ADD COLUMN IF NOT EXISTS umpire_pitcher_favored BOOLEAN,
    ADD COLUMN IF NOT EXISTS umpire_consistency_score NUMERIC,
    ADD COLUMN IF NOT EXISTS umpire_experience_estimate INTEGER;

-- Attendance & Crowd features
ALTER TABLE features_pitch.engineered_features
    ADD COLUMN IF NOT EXISTS attendance INTEGER,
    ADD COLUMN IF NOT EXISTS attendance_vs_capacity_pct NUMERIC,
    ADD COLUMN IF NOT EXISTS attendance_vs_team_avg_pct NUMERIC,
    ADD COLUMN IF NOT EXISTS is_sellout BOOLEAN,
    ADD COLUMN IF NOT EXISTS crowd_noise_proxy NUMERIC,
    ADD COLUMN IF NOT EXISTS home_field_advantage_score NUMERIC,
    ADD COLUMN IF NOT EXISTS is_rivalry_game BOOLEAN;

-- Park factors
ALTER TABLE features_pitch.engineered_features
    ADD COLUMN IF NOT EXISTS park_id TEXT,
    ADD COLUMN IF NOT EXISTS park_elevation_feet NUMERIC,
    ADD COLUMN IF NOT EXISTS park_left_field_distance INTEGER,
    ADD COLUMN IF NOT EXISTS park_center_field_distance INTEGER,
    ADD COLUMN IF NOT EXISTS park_right_field_distance INTEGER,
    ADD COLUMN IF NOT EXISTS park_grass_turf BOOLEAN,
    ADD COLUMN IF NOT EXISTS park_has_retractable_roof BOOLEAN,
    ADD COLUMN IF NOT EXISTS park_is_dome BOOLEAN,
    ADD COLUMN IF NOT EXISTS park_hr_factor_lf NUMERIC,
    ADD COLUMN IF NOT EXISTS park_hr_factor_cf NUMERIC,
    ADD COLUMN IF NOT EXISTS park_hr_factor_rf NUMERIC,
    ADD COLUMN IF NOT EXISTS park_overall_hr_factor NUMERIC,
    ADD COLUMN IF NOT EXISTS park_foul_ground_sqft INTEGER;

-- Deep fatigue metrics
ALTER TABLE features_pitch.engineered_features
    ADD COLUMN IF NOT EXISTS pitcher_inning_velocity_decline NUMERIC,
    ADD COLUMN IF NOT EXISTS pitcher_season_workload INTEGER,
    ADD COLUMN IF NOT EXISTS pitcher_back_to_back BOOLEAN,
    ADD COLUMN IF NOT EXISTS pitcher_days_rest INTEGER,
    ADD COLUMN IF NOT EXISTS is_short_rest_start BOOLEAN;

-- Comments for documentation
COMMENT ON COLUMN features_pitch.engineered_features.temp_extreme_flag IS 
    'Weather extreme: hot (>90F), cold (<50F), or normal - affects grip and ball carry';
COMMENT ON COLUMN features_pitch.engineered_features.wind_in_direction IS 
    'Wind blowing toward LF/CF/RF (home run helper) vs blowing in';
COMMENT ON COLUMN features_pitch.engineered_features.wind_effect_score IS 
    'Combined wind direction + speed impact score (-1 to +1)';
COMMENT ON COLUMN features_pitch.engineered_features.altitude_factor IS 
    'Park elevation effect on ball flight (1.0 = sea level, 1.2 = Coors Field)';
COMMENT ON COLUMN features_pitch.engineered_features.umpire_strike_zone_size IS 
    'Umpire tendency: small, normal, or large strike zone';
COMMENT ON COLUMN features_pitch.engineered_features.umpire_k_friendly IS 
    'True if umpire has higher than average strikeout rate';
COMMENT ON COLUMN features_pitch.engineered_features.park_overall_hr_factor IS 
    'Park factor for home runs (1.0 = neutral, >1 = hitter friendly)';
COMMENT ON COLUMN features_pitch.engineered_features.pitcher_inning_velocity_decline IS 
    'Velocity drop from early innings to current inning (fatigue indicator)';
COMMENT ON COLUMN features_pitch.engineered_features.pitcher_days_rest IS 
    'Days since last appearance (5+ is normal rest)';
COMMENT ON COLUMN features_pitch.engineered_features.is_short_rest_start IS 
    'True if pitcher starting on < 4 days rest (fatigue risk)';
COMMENT ON COLUMN features_pitch.engineered_features.home_field_advantage_score IS 
    'Composite of attendance, park factors, and team home performance';

-- Verification
SELECT 
    'Context features schema added' as status,
    COUNT(*) as total_rows,
    COUNT(temp_extreme_flag) as with_weather,
    COUNT(batting_team_last_5_win_rate) as with_momentum,
    COUNT(umpire_strike_zone_size) as with_umpire,
    COUNT(attendance) as with_attendance,
    COUNT(park_elevation_feet) as with_park
FROM features_pitch.engineered_features;
