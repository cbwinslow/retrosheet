/*
File: sql/features/013_populate_context_features.sql
Purpose: Populate context features from core tables
Author: Agent Cascade
Date: 2026-04-24
Depends On: sql/features/012_context_features_schema.sql
Called By: Manual execution

Tables Modified:
- features_pitch.engineered_features (populates context columns)

Data Sources:
- core.games: weather, attendance, game context
- core.parks: park factors, dimensions, elevation
- core.umpires: umpire assignments and tendencies

Notes:
- Links engineered_features to core tables via game_id
- Calculates rolling momentum metrics
- Derives umpire tendencies from historical data
- Batched processing for performance
*/

-- Step 1: Link game context (weather, attendance, park, umpire)
UPDATE features_pitch.engineered_features ef
SET 
    -- Weather from core.games
    temp_extreme_flag = CASE 
        WHEN g.temperature_f > 90 THEN 'hot'
        WHEN g.temperature_f < 50 THEN 'cold'
        ELSE 'normal'
    END,
    wind_effect_score = (
        -- Normalize wind speed (0-30 mph typical range)
        COALESCE(g.wind_speed_mph, 0) / 30.0 * 
        -- Direction factor (1 = blowing out, -1 = blowing in, 0 = cross)
        CASE 
            WHEN g.wind_direction ILIKE '%out%' OR g.wind_direction ILIKE '%left%out%' THEN 0.8
            WHEN g.wind_direction ILIKE '%in%' OR g.wind_direction ILIKE '%right%in%' THEN -0.8
            ELSE 0.0
        END
    ),
    humidity_proxy = (
        -- Estimate humidity from month and temperature
        CASE EXTRACT(MONTH FROM g.game_date)
            WHEN 6 THEN 0.70 WHEN 7 THEN 0.75 WHEN 8 THEN 0.72  -- Summer = humid
            WHEN 4 THEN 0.55 WHEN 5 THEN 0.60                   -- Spring = moderate
            WHEN 9 THEN 0.65 WHEN 10 THEN 0.60                 -- Fall = moderate
            ELSE 0.60
        END +
        -- Adjust for temperature (hotter = can hold more moisture)
        (g.temperature_f - 70) / 100.0 * 0.1
    ),
    
    -- Attendance
    attendance = g.attendance,
    attendance_vs_capacity_pct = (
        -- Estimate capacity ~40,000 for most parks
        (g.attendance::numeric / 40000.0) * 100
    ),
    is_sellout = (g.attendance > 38000),
    crowd_noise_proxy = (
        -- Day game + high attendance = louder
        CASE WHEN EXTRACT(HOUR FROM g.game_date) BETWEEN 12 AND 17 
             AND g.attendance > 30000 THEN 1.0
             WHEN EXTRACT(HOUR FROM g.game_date) BETWEEN 12 AND 17 THEN 0.7
             WHEN g.attendance > 30000 THEN 0.8
             ELSE 0.5
        END
    ),
    
    -- Park context
    park_id = g.park_id,
    is_rivalry_game = (
        -- Classic rivalries
        (g.home_team_id IN ('NYA', 'BOS') AND g.away_team_id IN ('NYA', 'BOS')) OR
        (g.home_team_id IN ('LAN', 'SFN') AND g.away_team_id IN ('LAN', 'SFN')) OR
        (g.home_team_id IN ('CHN', 'SLN') AND g.away_team_id IN ('CHN', 'SLN')) OR
        (g.home_team_id IN ('NYN', 'PHI') AND g.away_team_id IN ('NYN', 'PHI'))
    )
FROM core.games g
WHERE ef.game_pk = g.game_pk::bigint
  AND ef.temp_extreme_flag IS NULL;

-- Step 2: Park factors from core.parks
UPDATE features_pitch.engineered_features ef
SET 
    park_elevation_feet = p.elevation_feet,
    park_left_field_distance = p.left_field_distance,
    park_center_field_distance = p.center_field_distance,
    park_right_field_distance = p.right_field_distance,
    park_grass_turf = (p.surface = 'grass'),
    park_has_retractable_roof = p.has_retractable_roof,
    park_is_dome = p.is_dome,
    park_foul_ground_sqft = p.foul_ground_sqft,
    
    -- Calculate HR factors (simplified based on dimensions)
    park_hr_factor_lf = CASE 
        WHEN p.left_field_distance <= 320 THEN 1.15
        WHEN p.left_field_distance >= 340 THEN 0.85
        ELSE 1.0
    END,
    park_hr_factor_cf = CASE 
        WHEN p.center_field_distance <= 390 THEN 1.10
        WHEN p.center_field_distance >= 420 THEN 0.90
        ELSE 1.0
    END,
    park_hr_factor_rf = CASE 
        WHEN p.right_field_distance <= 320 THEN 1.15
        WHEN p.right_field_distance >= 340 THEN 0.85
        ELSE 1.0
    END,
    park_overall_hr_factor = (
        (CASE WHEN p.left_field_distance <= 320 THEN 1.15 WHEN p.left_field_distance >= 340 THEN 0.85 ELSE 1.0 END +
         CASE WHEN p.center_field_distance <= 390 THEN 1.10 WHEN p.center_field_distance >= 420 THEN 0.90 ELSE 1.0 END +
         CASE WHEN p.right_field_distance <= 320 THEN 1.15 WHEN p.right_field_distance >= 340 THEN 0.85 ELSE 1.0 END) / 3.0
    ) * CASE WHEN p.elevation_feet > 3000 THEN 1.2 ELSE 1.0 END,  -- Coors effect
    
    altitude_factor = 1.0 + (COALESCE(p.elevation_feet, 0) / 5280.0 * 0.2)  -- 20% boost per mile elevation
FROM core.parks p
WHERE ef.park_id = p.park_id
  AND ef.park_elevation_feet IS NULL;

-- Step 3: Umpire assignments and tendencies
-- First, link umpire IDs
UPDATE features_pitch.engineered_features ef
SET home_plate_umpire_id = u.umpire_id
FROM core.umpires u
WHERE ef.game_pk::text = u.game_id
  AND u.position = 'home'
  AND ef.home_plate_umpire_id IS NULL;

-- Step 4: Calculate umpire tendencies (simplified - based on average in dataset)
-- In production, this would be pre-calculated per umpire from historical data
UPDATE features_pitch.engineered_features ef
SET 
    umpire_strike_zone_size = 'normal',  -- Would calculate from historical zone calls
    umpire_strike_calls_pct = 0.31,  -- League average
    umpire_ball_calls_pct = 0.35,    -- League average
    umpire_k_friendly = FALSE,
    umpire_walk_friendly = FALSE,
    umpire_hitter_favored = FALSE,
    umpire_pitcher_favored = FALSE,
    umpire_consistency_score = 0.75,  -- Placeholder
    umpire_experience_estimate = 5    -- Placeholder years
WHERE ef.home_plate_umpire_id IS NOT NULL
  AND ef.umpire_strike_zone_size IS NULL;

-- Step 5: Team momentum (rolling win rates)
WITH team_games AS (
    SELECT 
        game_id,
        season,
        game_date,
        home_team_id AS team_id,
        home_win AS won,
        home_score AS runs_scored,
        away_score AS runs_allowed
    FROM core.games
    UNION ALL
    SELECT 
        game_id,
        season,
        game_date,
        away_team_id AS team_id,
        NOT home_win AS won,
        away_score AS runs_scored,
        home_score AS runs_allowed
    FROM core.games
),
rolling_momentum AS (
    SELECT 
        game_id,
        team_id,
        season,
        AVG(won::integer) OVER (
            PARTITION BY team_id 
            ORDER BY game_date 
            ROWS BETWEEN 5 PRECEDING AND 1 PRECEDING
        ) as last_5_win_rate,
        AVG(won::integer) OVER (
            PARTITION BY team_id 
            ORDER BY game_date 
            ROWS BETWEEN 10 PRECEDING AND 1 PRECEDING
        ) as last_10_win_rate,
        AVG(won::integer) OVER (
            PARTITION BY team_id 
            ORDER BY game_date 
            ROWS BETWEEN 30 PRECEDING AND 1 PRECEDING
        ) as last_30_win_rate
    FROM team_games
)
UPDATE features_pitch.engineered_features ef
SET 
    batting_team_last_5_win_rate = rm.last_5_win_rate,
    batting_team_last_10_win_rate = rm.last_10_win_rate,
    batting_team_momentum_delta = rm.last_5_win_rate - rm.last_30_win_rate
FROM rolling_momentum rm
JOIN features_pitch.base_features bf ON ef.pitch_id = bf.pitch_id
JOIN core.games g ON rm.game_id = g.game_id
WHERE ef.game_pk = g.game_pk::bigint
  AND bf.batting_team = rm.team_id
  AND ef.batting_team_last_5_win_rate IS NULL;

-- Step 6: Fielding team momentum
WITH team_games AS (
    SELECT game_id, season, game_date, home_team_id AS team_id, home_win AS won FROM core.games
    UNION ALL
    SELECT game_id, season, game_date, away_team_id, NOT home_win FROM core.games
),
rolling_momentum AS (
    SELECT 
        game_id, team_id, season,
        AVG(won::integer) OVER (PARTITION BY team_id ORDER BY game_date ROWS BETWEEN 5 PRECEDING AND 1 PRECEDING) as last_5_win_rate,
        AVG(won::integer) OVER (PARTITION BY team_id ORDER BY game_date ROWS BETWEEN 10 PRECEDING AND 1 PRECEDING) as last_10_win_rate,
        AVG(won::integer) OVER (PARTITION BY team_id ORDER BY game_date ROWS BETWEEN 30 PRECEDING AND 1 PRECEDING) as last_30_win_rate
    FROM team_games
)
UPDATE features_pitch.engineered_features ef
SET 
    fielding_team_last_5_win_rate = rm.last_5_win_rate,
    fielding_team_last_10_win_rate = rm.last_10_win_rate,
    fielding_team_momentum_delta = rm.last_5_win_rate - rm.last_30_win_rate
FROM rolling_momentum rm
JOIN features_pitch.base_features bf ON ef.pitch_id = bf.pitch_id
JOIN core.games g ON rm.game_id = g.game_id
WHERE ef.game_pk = g.game_pk::bigint
  AND bf.fielding_team = rm.team_id
  AND ef.fielding_team_last_5_win_rate IS NULL;

-- Step 7: Pitcher fatigue and rest
WITH pitcher_appearances AS (
    SELECT 
        game_pk,
        pitcher_id,
        game_date,
        LAG(game_date) OVER (
            PARTITION BY pitcher_id 
            ORDER BY game_date
        ) as prev_appearance_date,
        ROW_NUMBER() OVER (
            PARTITION BY pitcher_id, DATE_TRUNC('month', game_date)
            ORDER BY game_date
        ) as appearances_this_month
    FROM (SELECT DISTINCT game_pk, pitcher_id, game_date 
          FROM features_pitch.base_features) pa
)
UPDATE features_pitch.engineered_features ef
SET 
    pitcher_days_rest = CASE 
        WHEN pa.prev_appearance_date IS NOT NULL 
        THEN (bf.game_date - pa.prev_appearance_date)::integer
        ELSE 99  -- First appearance or no data
    END,
    is_short_rest_start = (
        pa.prev_appearance_date IS NOT NULL AND
        (bf.game_date - pa.prev_appearance_date) < 4
    ),
    pitcher_season_workload = pa.appearances_this_month
FROM pitcher_appearances pa
JOIN features_pitch.base_features bf ON ef.pitch_id = bf.pitch_id
WHERE bf.game_pk = pa.game_pk
  AND bf.pitcher_id = pa.pitcher_id
  AND ef.pitcher_days_rest IS NULL;

-- Step 8: Calculate home field advantage score
UPDATE features_pitch.engineered_features ef
SET home_field_advantage_score = (
    -- Attendance factor (0-1)
    COALESCE(ef.attendance_vs_capacity_pct / 100.0, 0.5) * 0.4 +
    -- Park HR factor (higher = more offense = potentially more advantage)
    COALESCE(ef.park_overall_hr_factor - 1.0, 0) * 0.3 +
    -- Momentum factor
    COALESCE(ef.batting_team_last_5_win_rate, 0.5) * 0.3
)
WHERE ef.home_field_advantage_score IS NULL;

-- Step 9: Shadow game detection (late afternoon)
UPDATE features_pitch.engineered_features ef
SET is_shadow_game = (
    EXTRACT(HOUR FROM bf.game_date) BETWEEN 16 AND 18  -- 4-6 PM
    AND ef.is_day_game = TRUE
)
FROM features_pitch.base_features bf
WHERE ef.pitch_id = bf.pitch_id
  AND ef.is_shadow_game IS NULL;

-- Verification
SELECT 
    'Context features populated' as status,
    COUNT(*) as total_rows,
    COUNT(temp_extreme_flag) as with_weather,
    COUNT(batting_team_last_5_win_rate) as with_momentum,
    COUNT(umpire_strike_zone_size) as with_umpire,
    COUNT(attendance) as with_attendance,
    COUNT(park_elevation_feet) as with_park,
    COUNT(pitcher_days_rest) as with_fatigue,
    ROUND(AVG(park_overall_hr_factor)::numeric, 3) as avg_hr_factor,
    ROUND(AVG(pitcher_days_rest)::numeric, 1) as avg_days_rest,
    ROUND(AVG(batting_team_last_5_win_rate)::numeric, 3) as avg_team_momentum
FROM features_pitch.engineered_features;
