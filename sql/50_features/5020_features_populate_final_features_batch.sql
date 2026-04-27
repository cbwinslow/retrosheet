/*
File: sql/features/017_populate_final_features_batch.sql
Purpose: Batched population of final features
Author: Agent Cascade
Date: 2026-04-24
Depends On: sql/features/016_populate_final_features.sql
Called By: Manual execution in batches

Notes:
- Processes 100k rows at a time
- Run multiple times until complete
- Includes Markov chains, matchups, sequence patterns
*/

-- Step 1: Postseason context (batch of 100k)
WITH unprocessed AS (
    SELECT ef.pitch_id, bf.game_date
    FROM features_pitch.engineered_features ef
    JOIN features_pitch.base_features bf ON ef.pitch_id = bf.pitch_id
    WHERE ef.is_postseason IS NULL
    LIMIT 100000
)
UPDATE features_pitch.engineered_features ef
SET 
    is_postseason = (EXTRACT(MONTH FROM u.game_date) = 10 AND EXTRACT(DAY FROM u.game_date) > 1),
    month_of_season = EXTRACT(MONTH FROM u.game_date)::integer,
    is_season_opener = (EXTRACT(MONTH FROM u.game_date) = 3 OR 
                       (EXTRACT(MONTH FROM u.game_date) = 4 AND EXTRACT(DAY FROM u.game_date) = 1)),
    is_getaway_day = FALSE,
    is_elimination_game = FALSE
FROM unprocessed u
WHERE ef.pitch_id = u.pitch_id;

-- Step 2: Markov chain features (batch of 100k)
WITH unprocessed AS (
    SELECT pitch_id, balls, strikes
    FROM features_pitch.engineered_features
    WHERE strike_accumulation_rate IS NULL
    LIMIT 100000
)
UPDATE features_pitch.engineered_features ef
SET 
    strike_accumulation_rate = CASE 
        WHEN u.balls = 0 AND u.strikes = 0 THEN 0.45
        WHEN u.balls = 0 AND u.strikes = 1 THEN 0.55
        WHEN u.balls = 0 AND u.strikes = 2 THEN 0.60
        WHEN u.balls = 1 AND u.strikes = 0 THEN 0.40
        WHEN u.balls = 1 AND u.strikes = 1 THEN 0.48
        WHEN u.balls = 1 AND u.strikes = 2 THEN 0.58
        WHEN u.balls = 2 AND u.strikes = 0 THEN 0.35
        WHEN u.balls = 2 AND u.strikes = 1 THEN 0.42
        WHEN u.balls = 2 AND u.strikes = 2 THEN 0.55
        WHEN u.balls = 3 AND u.strikes = 0 THEN 0.25
        WHEN u.balls = 3 AND u.strikes = 1 THEN 0.38
        WHEN u.balls = 3 AND u.strikes = 2 THEN 0.52
        ELSE 0.45
    END,
    ball_accumulation_rate = CASE 
        WHEN u.balls = 0 AND u.strikes = 0 THEN 0.38
        WHEN u.balls = 0 AND u.strikes = 1 THEN 0.30
        WHEN u.balls = 0 AND u.strikes = 2 THEN 0.22
        WHEN u.balls = 1 AND u.strikes = 0 THEN 0.42
        WHEN u.balls = 1 AND u.strikes = 1 THEN 0.35
        WHEN u.balls = 1 AND u.strikes = 2 THEN 0.25
        WHEN u.balls = 2 AND u.strikes = 0 THEN 0.48
        WHEN u.balls = 2 AND u.strikes = 1 THEN 0.40
        WHEN u.balls = 2 AND u.strikes = 2 THEN 0.32
        WHEN u.balls = 3 AND u.strikes = 0 THEN 0.60
        WHEN u.balls = 3 AND u.strikes = 1 THEN 0.45
        WHEN u.balls = 3 AND u.strikes = 2 THEN 0.35
        ELSE 0.38
    END,
    is_absorbing_state = (u.strikes = 2 OR u.balls = 3),
    expected_pitches_remaining = CASE 
        WHEN u.balls = 0 AND u.strikes = 0 THEN 3.3
        WHEN u.balls = 0 AND u.strikes = 1 THEN 2.8
        WHEN u.balls = 0 AND u.strikes = 2 THEN 2.1
        WHEN u.balls = 1 AND u.strikes = 0 THEN 3.0
        WHEN u.balls = 1 AND u.strikes = 1 THEN 2.6
        WHEN u.balls = 1 AND u.strikes = 2 THEN 2.0
        WHEN u.balls = 2 AND u.strikes = 0 THEN 2.5
        WHEN u.balls = 2 AND u.strikes = 1 THEN 2.3
        WHEN u.balls = 2 AND u.strikes = 2 THEN 1.8
        WHEN u.balls = 3 AND u.strikes = 0 THEN 1.5
        WHEN u.balls = 3 AND u.strikes = 1 THEN 1.8
        WHEN u.balls = 3 AND u.strikes = 2 THEN 1.5
        ELSE 3.0
    END,
    is_favorable_hitter_count = (u.balls > u.strikes),
    is_favorable_pitcher_count = (u.strikes > u.balls OR u.strikes = 2),
    count_pressure_index = CASE 
        WHEN u.balls = 3 AND u.strikes = 2 THEN 1.0
        WHEN u.strikes = 2 AND u.balls < 3 THEN 0.8
        WHEN u.balls = 3 AND u.strikes < 2 THEN 0.7
        WHEN u.balls = 2 AND u.strikes = 2 THEN 0.6
        ELSE 0.4
    END
FROM unprocessed u
WHERE ef.pitch_id = u.pitch_id;

-- Step 3: Matchup history (batch of 50k - expensive query)
WITH unprocessed AS (
    SELECT ef.pitch_id, bf.batter_id, bf.pitcher_id, bf.game_date
    FROM features_pitch.engineered_features ef
    JOIN features_pitch.base_features bf ON ef.pitch_id = bf.pitch_id
    WHERE ef.matchup_prior_pa_count IS NULL
    LIMIT 50000
),
prior_matchups AS (
    SELECT 
        u.pitch_id,
        COUNT(bf2.pitch_id) FILTER (WHERE bf2.pitch_number = 1) as prior_pas,
        SUM(CASE WHEN bf2.events = 'home_run' THEN 1 ELSE 0 END) as prior_hrs,
        SUM(CASE WHEN bf2.events LIKE 'strikeout%' THEN 1 ELSE 0 END) as prior_ks
    FROM unprocessed u
    LEFT JOIN features_pitch.base_features bf2 
        ON u.batter_id = bf2.batter_id 
        AND u.pitcher_id = bf2.pitcher_id
        AND bf2.game_date < u.game_date
        AND bf2.pitch_number = 1
    GROUP BY u.pitch_id
)
UPDATE features_pitch.engineered_features ef
SET 
    matchup_prior_pa_count = COALESCE(pm.prior_pas, 0),
    matchup_prior_hr_count = COALESCE(pm.prior_hrs, 0),
    matchup_prior_strikeout_count = COALESCE(pm.prior_ks, 0),
    matchup_first_time_facing = (COALESCE(pm.prior_pas, 0) = 0)
FROM prior_matchups pm
WHERE ef.pitch_id = pm.pitch_id;

-- Step 4: Sequence patterns (batch of 100k)
WITH unprocessed AS (
    SELECT ef.pitch_id, bf.game_pk, bf.at_bat_number, bf.pitch_number, bf.pitch_type
    FROM features_pitch.engineered_features ef
    JOIN features_pitch.base_features bf ON ef.pitch_id = bf.pitch_id
    WHERE ef.prev_2_pitch_types IS NULL
    LIMIT 100000
),
sequences AS (
    SELECT 
        u.pitch_id,
        u.pitch_type,
        LAG(u.pitch_type, 1) OVER (PARTITION BY u.game_pk, u.at_bat_number ORDER BY u.pitch_number) as prev_1,
        LAG(u.pitch_type, 2) OVER (PARTITION BY u.game_pk, u.at_bat_number ORDER BY u.pitch_number) as prev_2
    FROM unprocessed u
)
UPDATE features_pitch.engineered_features ef
SET 
    prev_2_pitch_types = CASE WHEN s.prev_2 IS NOT NULL THEN s.prev_2 || '-' || s.prev_1 ELSE NULL END,
    is_repeated_pitch = (s.prev_1 = s.pitch_type AND s.prev_1 IS NOT NULL),
    is_alternating_pattern = (s.prev_2 = s.pitch_type AND s.prev_1 != s.pitch_type),
    pitch_sequence_category = CASE 
        WHEN s.pitch_type IN ('FF', 'FT', 'FC', 'SI') AND s.prev_1 IN ('FF', 'FT', 'FC', 'SI') THEN 'fastball_cluster'
        WHEN s.pitch_type IN ('SL', 'CU', 'KC', 'ST') AND s.prev_1 IN ('SL', 'CU', 'KC', 'ST') THEN 'breaking_cluster'
        WHEN s.pitch_type IN ('CH', 'FS', 'FO') AND s.prev_1 IN ('CH', 'FS', 'FO') THEN 'offspeed_cluster'
        ELSE 'mixed'
    END
FROM sequences s
WHERE ef.pitch_id = s.pitch_id;

-- Step 5: Platoon advantage (batch of 100k)
WITH unprocessed AS (
    SELECT ef.pitch_id, bf.stand, bf.p_throws
    FROM features_pitch.engineered_features ef
    JOIN features_pitch.base_features bf ON ef.pitch_id = bf.pitch_id
    WHERE ef.is_platoon_advantage_batter IS NULL
    LIMIT 100000
)
UPDATE features_pitch.engineered_features ef
SET 
    is_platoon_advantage_batter = (
        (u.stand = 'L' AND u.p_throws = 'R') OR (u.stand = 'R' AND u.p_throws = 'L')
    ),
    is_platoon_disadvantage_batter = (
        (u.stand = 'L' AND u.p_throws = 'L') OR (u.stand = 'R' AND u.p_throws = 'R')
    ),
    platoon_advantage_direction = CASE 
        WHEN (u.stand = 'L' AND u.p_throws = 'R') OR (u.stand = 'R' AND u.p_throws = 'L') THEN 'batter'
        WHEN (u.stand = 'L' AND u.p_throws = 'L') OR (u.stand = 'R' AND u.p_throws = 'R') THEN 'pitcher'
        ELSE 'neutral'
    END
FROM unprocessed u
WHERE ef.pitch_id = u.pitch_id;

-- Step 6: Experience levels (batch of 100k)
WITH unprocessed AS (
    SELECT ef.pitch_id, bf.batter_id, bf.pitcher_id
    FROM features_pitch.engineered_features ef
    JOIN features_pitch.base_features bf ON ef.pitch_id = bf.pitch_id
    WHERE ef.is_rookie_batter IS NULL
    LIMIT 100000
),
batter_exp AS (
    SELECT batter_id, COUNT(*) as pa_count
    FROM features_pitch.base_features
    WHERE pitch_number = 1
    GROUP BY batter_id
),
pitcher_exp AS (
    SELECT pitcher_id, COUNT(*) as pa_count
    FROM features_pitch.base_features
    WHERE pitch_number = 1
    GROUP BY pitcher_id
)
UPDATE features_pitch.engineered_features ef
SET 
    is_rookie_batter = (b.pa_count < 130),
    is_veteran_batter = (b.pa_count > 3000),
    batter_experience_level = CASE 
        WHEN b.pa_count < 130 THEN 'rookie'
        WHEN b.pa_count < 500 THEN 'young'
        WHEN b.pa_count < 3000 THEN 'prime'
        ELSE 'veteran'
    END,
    batter_career_pa_estimate = b.pa_count,
    is_rookie_pitcher = (p.pa_count < 150),
    is_veteran_pitcher = (p.pa_count > 1500),
    pitcher_experience_level = CASE 
        WHEN p.pa_count < 150 THEN 'rookie'
        WHEN p.pa_count < 500 THEN 'young'
        WHEN p.pa_count < 1500 THEN 'prime'
        ELSE 'veteran'
    END,
    pitcher_career_ip_estimate = p.pa_count
FROM unprocessed u
LEFT JOIN batter_exp b ON u.batter_id = b.batter_id
LEFT JOIN pitcher_exp p ON u.pitcher_id = p.pitcher_id
WHERE ef.pitch_id = u.pitch_id;

-- Progress report
SELECT 
    'Final batch progress' as status,
    COUNT(*) as total_rows,
    COUNT(is_postseason) as with_postseason,
    COUNT(strike_accumulation_rate) as with_markov,
    COUNT(matchup_prior_pa_count) as with_matchup,
    COUNT(is_rookie_batter) as with_rookie,
    COUNT(prev_2_pitch_types) as with_sequence,
    COUNT(is_platoon_advantage_batter) as with_platoon,
    ROUND(COUNT(strike_accumulation_rate)::numeric / COUNT(*) * 100, 2) as pct_complete
FROM features_pitch.engineered_features;
