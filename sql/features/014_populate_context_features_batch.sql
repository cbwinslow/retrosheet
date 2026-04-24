/*
File: sql/features/014_populate_context_features_batch.sql
Purpose: Batched population of context features
Author: Agent Cascade
Date: 2026-04-24
Depends On: sql/features/013_populate_context_features.sql
Called By: Manual execution in batches

Notes:
- Processes 100k rows at a time
- Run multiple times until complete
- Includes weather, momentum, umpire, attendance, park, fatigue
*/

-- Step 1: Game context (batch of 100k)
WITH unprocessed AS (
    SELECT ef.pitch_id, g.temperature_f, g.wind_speed_mph, g.wind_direction, 
           g.game_date, g.attendance, g.park_id, g.game_pk
    FROM features_pitch.engineered_features ef
    JOIN features_pitch.base_features bf ON ef.pitch_id = bf.pitch_id
    JOIN core.games g ON bf.game_pk = g.game_pk::text
    WHERE ef.temp_extreme_flag IS NULL
    LIMIT 100000
)
UPDATE features_pitch.engineered_features ef
SET 
    temp_extreme_flag = CASE 
        WHEN u.temperature_f > 90 THEN 'hot'
        WHEN u.temperature_f < 50 THEN 'cold'
        ELSE 'normal'
    END,
    wind_effect_score = (
        COALESCE(u.wind_speed_mph, 0) / 30.0 * 
        CASE 
            WHEN u.wind_direction ILIKE '%out%' OR u.wind_direction ILIKE '%left%out%' THEN 0.8
            WHEN u.wind_direction ILIKE '%in%' OR u.wind_direction ILIKE '%right%in%' THEN -0.8
            ELSE 0.0
        END
    ),
    humidity_proxy = (
        CASE EXTRACT(MONTH FROM u.game_date)
            WHEN 6 THEN 0.70 WHEN 7 THEN 0.75 WHEN 8 THEN 0.72
            WHEN 4 THEN 0.55 WHEN 5 THEN 0.60
            WHEN 9 THEN 0.65 WHEN 10 THEN 0.60
            ELSE 0.60
        END +
        (u.temperature_f - 70) / 100.0 * 0.1
    ),
    attendance = u.attendance,
    attendance_vs_capacity_pct = (u.attendance::numeric / 40000.0) * 100,
    is_sellout = (u.attendance > 38000),
    crowd_noise_proxy = (
        CASE WHEN EXTRACT(HOUR FROM u.game_date) BETWEEN 12 AND 17 
             AND u.attendance > 30000 THEN 1.0
             WHEN EXTRACT(HOUR FROM u.game_date) BETWEEN 12 AND 17 THEN 0.7
             WHEN u.attendance > 30000 THEN 0.8
             ELSE 0.5
        END
    ),
    park_id = u.park_id,
    is_rivalry_game = FALSE  -- Simplified for batch
FROM unprocessed u
WHERE ef.pitch_id = u.pitch_id;

-- Step 2: Park factors (batch of 100k)
WITH unprocessed AS (
    SELECT ef.pitch_id, p.*
    FROM features_pitch.engineered_features ef
    JOIN core.parks p ON ef.park_id = p.park_id
    WHERE ef.park_elevation_feet IS NULL
    LIMIT 100000
)
UPDATE features_pitch.engineered_features ef
SET 
    park_elevation_feet = u.elevation_feet,
    park_left_field_distance = u.left_field_distance,
    park_center_field_distance = u.center_field_distance,
    park_right_field_distance = u.right_field_distance,
    park_grass_turf = (u.surface = 'grass'),
    park_has_retractable_roof = u.has_retractable_roof,
    park_is_dome = u.is_dome,
    park_foul_ground_sqft = u.foul_ground_sqft,
    park_hr_factor_lf = CASE 
        WHEN u.left_field_distance <= 320 THEN 1.15
        WHEN u.left_field_distance >= 340 THEN 0.85
        ELSE 1.0
    END,
    park_hr_factor_cf = CASE 
        WHEN u.center_field_distance <= 390 THEN 1.10
        WHEN u.center_field_distance >= 420 THEN 0.90
        ELSE 1.0
    END,
    park_hr_factor_rf = CASE 
        WHEN u.right_field_distance <= 320 THEN 1.15
        WHEN u.right_field_distance >= 340 THEN 0.85
        ELSE 1.0
    END,
    park_overall_hr_factor = (
        (CASE WHEN u.left_field_distance <= 320 THEN 1.15 WHEN u.left_field_distance >= 340 THEN 0.85 ELSE 1.0 END +
         CASE WHEN u.center_field_distance <= 390 THEN 1.10 WHEN u.center_field_distance >= 420 THEN 0.90 ELSE 1.0 END +
         CASE WHEN u.right_field_distance <= 320 THEN 1.15 WHEN u.right_field_distance >= 340 THEN 0.85 ELSE 1.0 END) / 3.0
    ) * CASE WHEN u.elevation_feet > 3000 THEN 1.2 ELSE 1.0 END,
    altitude_factor = 1.0 + (COALESCE(u.elevation_feet, 0) / 5280.0 * 0.2)
FROM unprocessed u
WHERE ef.pitch_id = u.pitch_id;

-- Step 3: Umpire assignments (batch of 100k)
WITH unprocessed AS (
    SELECT ef.pitch_id, u.umpire_id
    FROM features_pitch.engineered_features ef
    JOIN features_pitch.base_features bf ON ef.pitch_id = bf.pitch_id
    JOIN core.umpires u ON bf.game_pk = u.game_id AND u.position = 'home'
    WHERE ef.home_plate_umpire_id IS NULL
    LIMIT 100000
)
UPDATE features_pitch.engineered_features ef
SET 
    home_plate_umpire_id = u.umpire_id,
    umpire_strike_zone_size = 'normal',
    umpire_strike_calls_pct = 0.31,
    umpire_ball_calls_pct = 0.35,
    umpire_k_friendly = FALSE,
    umpire_walk_friendly = FALSE,
    umpire_hitter_favored = FALSE,
    umpire_pitcher_favored = FALSE,
    umpire_consistency_score = 0.75,
    umpire_experience_estimate = 5
FROM unprocessed u
WHERE ef.pitch_id = u.pitch_id;

-- Step 4: Team momentum - batting (batch of 50k for performance)
WITH team_games AS (
    SELECT game_id, season, game_date, home_team_id AS team_id, home_win AS won FROM core.games
    UNION ALL
    SELECT game_id, season, game_date, away_team_id, NOT home_win FROM core.games
),
rolling AS (
    SELECT game_id, team_id,
        AVG(won::integer) OVER (PARTITION BY team_id ORDER BY game_date ROWS BETWEEN 5 PRECEDING AND 1 PRECEDING) as last_5,
        AVG(won::integer) OVER (PARTITION BY team_id ORDER BY game_date ROWS BETWEEN 10 PRECEDING AND 1 PRECEDING) as last_10,
        AVG(won::integer) OVER (PARTITION BY team_id ORDER BY game_date ROWS BETWEEN 30 PRECEDING AND 1 PRECEDING) as last_30
    FROM team_games
),
unprocessed AS (
    SELECT ef.pitch_id, ef.game_pk, bf.batting_team
    FROM features_pitch.engineered_features ef
    JOIN features_pitch.base_features bf ON ef.pitch_id = bf.pitch_id
    WHERE ef.batting_team_last_5_win_rate IS NULL
    LIMIT 50000
)
UPDATE features_pitch.engineered_features ef
SET 
    batting_team_last_5_win_rate = r.last_5,
    batting_team_last_10_win_rate = r.last_10,
    batting_team_momentum_delta = r.last_5 - r.last_30
FROM unprocessed u
JOIN rolling r ON u.game_pk::text = r.game_id AND u.batting_team = r.team_id
WHERE ef.pitch_id = u.pitch_id;

-- Step 5: Fielding team momentum (batch of 50k)
WITH team_games AS (
    SELECT game_id, season, game_date, home_team_id AS team_id, home_win AS won FROM core.games
    UNION ALL
    SELECT game_id, season, game_date, away_team_id, NOT home_win FROM core.games
),
rolling AS (
    SELECT game_id, team_id,
        AVG(won::integer) OVER (PARTITION BY team_id ORDER BY game_date ROWS BETWEEN 5 PRECEDING AND 1 PRECEDING) as last_5,
        AVG(won::integer) OVER (PARTITION BY team_id ORDER BY game_date ROWS BETWEEN 10 PRECEDING AND 1 PRECEDING) as last_10,
        AVG(won::integer) OVER (PARTITION BY team_id ORDER BY game_date ROWS BETWEEN 30 PRECEDING AND 1 PRECEDING) as last_30
    FROM team_games
),
unprocessed AS (
    SELECT ef.pitch_id, ef.game_pk, bf.fielding_team
    FROM features_pitch.engineered_features ef
    JOIN features_pitch.base_features bf ON ef.pitch_id = bf.pitch_id
    WHERE ef.fielding_team_last_5_win_rate IS NULL
    LIMIT 50000
)
UPDATE features_pitch.engineered_features ef
SET 
    fielding_team_last_5_win_rate = r.last_5,
    fielding_team_last_10_win_rate = r.last_10,
    fielding_team_momentum_delta = r.last_5 - r.last_30
FROM unprocessed u
JOIN rolling r ON u.game_pk::text = r.game_id AND u.fielding_team = r.team_id
WHERE ef.pitch_id = u.pitch_id;

-- Step 6: Pitcher fatigue and rest (batch of 100k)
WITH unprocessed AS (
    SELECT ef.pitch_id, bf.game_pk, bf.pitcher_id, bf.game_date
    FROM features_pitch.engineered_features ef
    JOIN features_pitch.base_features bf ON ef.pitch_id = bf.pitch_id
    WHERE ef.pitcher_days_rest IS NULL
    LIMIT 100000
),
pitcher_prev AS (
    SELECT DISTINCT
        u.pitcher_id,
        u.game_date,
        MAX(pa.game_date) FILTER (WHERE pa.game_date < u.game_date) OVER (
            PARTITION BY u.pitcher_id
        ) as prev_date,
        COUNT(*) FILTER (WHERE pa.game_date >= DATE_TRUNC('month', u.game_date)) OVER (
            PARTITION BY u.pitcher_id, DATE_TRUNC('month', u.game_date)
        ) as month_count
    FROM unprocessed u
    JOIN features_pitch.base_features pa ON u.pitcher_id = pa.pitcher_id
)
UPDATE features_pitch.engineered_features ef
SET 
    pitcher_days_rest = CASE 
        WHEN pp.prev_date IS NOT NULL THEN (bf.game_date - pp.prev_date)::integer
        ELSE 99
    END,
    is_short_rest_start = (pp.prev_date IS NOT NULL AND (bf.game_date - pp.prev_date) < 4),
    pitcher_season_workload = pp.month_count
FROM unprocessed u
JOIN pitcher_prev pp ON u.pitcher_id = pp.pitcher_id AND u.game_date = pp.game_date
JOIN features_pitch.base_features bf ON ef.pitch_id = bf.pitch_id
WHERE ef.pitch_id = u.pitch_id;

-- Step 7: Home field advantage score (batch of 100k)
WITH unprocessed AS (
    SELECT pitch_id
    FROM features_pitch.engineered_features
    WHERE home_field_advantage_score IS NULL
      AND attendance_vs_capacity_pct IS NOT NULL
    LIMIT 100000
)
UPDATE features_pitch.engineered_features ef
SET home_field_advantage_score = (
    COALESCE(ef.attendance_vs_capacity_pct / 100.0, 0.5) * 0.4 +
    COALESCE(ef.park_overall_hr_factor - 1.0, 0) * 0.3 +
    COALESCE(ef.batting_team_last_5_win_rate, 0.5) * 0.3
)
FROM unprocessed u
WHERE ef.pitch_id = u.pitch_id;

-- Step 8: Shadow games (batch of 100k)
WITH unprocessed AS (
    SELECT ef.pitch_id, bf.game_date
    FROM features_pitch.engineered_features ef
    JOIN features_pitch.base_features bf ON ef.pitch_id = bf.pitch_id
    WHERE ef.is_shadow_game IS NULL
      AND ef.is_day_game IS NOT NULL
    LIMIT 100000
)
UPDATE features_pitch.engineered_features ef
SET is_shadow_game = (
    EXTRACT(HOUR FROM u.game_date) BETWEEN 16 AND 18
    AND ef.is_day_game = TRUE
)
FROM unprocessed u
WHERE ef.pitch_id = u.pitch_id;

-- Progress report
SELECT 
    'Context batch progress' as status,
    COUNT(*) as total_rows,
    COUNT(temp_extreme_flag) as with_weather,
    COUNT(batting_team_last_5_win_rate) as with_momentum,
    COUNT(umpire_strike_zone_size) as with_umpire,
    COUNT(attendance) as with_attendance,
    COUNT(park_elevation_feet) as with_park,
    COUNT(pitcher_days_rest) as with_fatigue,
    ROUND(COUNT(temp_extreme_flag)::numeric / COUNT(*) * 100, 2) as pct_complete
FROM features_pitch.engineered_features;
