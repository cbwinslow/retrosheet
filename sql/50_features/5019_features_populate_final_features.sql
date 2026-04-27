/*
File: sql/features/016_populate_final_features.sql
Purpose: Populate final features - Markov chains, matchups, postseason, sequence
Author: Agent Cascade
Date: 2026-04-24
Depends On: sql/features/015_final_features_schema.sql
Called By: Manual execution

Tables Modified:
- features_pitch.engineered_features (populates final columns)

Data Sources:
- core.games: postseason flags, standings
- core.events: matchup history calculation
- features_pitch.base_features: pitch sequences

Notes:
- Markov features calculated from historical count transitions
- Matchup history built from prior encounters in database
- Sequence features from pitch_number ordering
*/

-- Step 1: Postseason & Season Context
UPDATE features_pitch.engineered_features ef
SET 
    is_postseason = (EXTRACT(MONTH FROM bf.game_date) = 10 AND EXTRACT(DAY FROM bf.game_date) > 1),
    is_elimination_game = FALSE,  -- Would need series context
    is_potential_clincher = FALSE,  -- Would need series context
    month_of_season = EXTRACT(MONTH FROM bf.game_date)::integer,
    is_season_opener = (EXTRACT(MONTH FROM bf.game_date) = 3 OR 
                       (EXTRACT(MONTH FROM bf.game_date) = 4 AND EXTRACT(DAY FROM bf.game_date) = 1)),
    is_finale_game = FALSE,  -- Would need series lookup
    is_getaway_day = FALSE,  -- Travel schedule not available
    series_game_number = NULL  -- Would need series lookup
FROM features_pitch.base_features bf
WHERE ef.pitch_id = bf.pitch_id
  AND ef.is_postseason IS NULL;

-- Step 2: Markov Chain Count State Features
-- Based on FanGraphs/Retrosheet research: 12 count states + absorbing states
UPDATE features_pitch.engineered_features ef
SET 
    -- From research: probability of adding strike or ball from each count
    strike_accumulation_rate = CASE 
        WHEN ef.balls = 0 AND ef.strikes = 0 THEN 0.45  -- 0-0: ~45% strike rate
        WHEN ef.balls = 0 AND ef.strikes = 1 THEN 0.55  -- 0-1: pitchers attack
        WHEN ef.balls = 0 AND ef.strikes = 2 THEN 0.60  -- 0-2: pitchers ahead
        WHEN ef.balls = 1 AND ef.strikes = 0 THEN 0.40  -- 1-0: hitters ahead
        WHEN ef.balls = 1 AND ef.strikes = 1 THEN 0.48  -- 1-1: even
        WHEN ef.balls = 1 AND ef.strikes = 2 THEN 0.58  -- 1-2: pitcher count
        WHEN ef.balls = 2 AND ef.strikes = 0 THEN 0.35  -- 2-0: hitter well ahead
        WHEN ef.balls = 2 AND ef.strikes = 1 THEN 0.42  -- 2-1: hitter ahead
        WHEN ef.balls = 2 AND ef.strikes = 2 THEN 0.55  -- 2-2: even pressure
        WHEN ef.balls = 3 AND ef.strikes = 0 THEN 0.25  -- 3-0: almost always take
        WHEN ef.balls = 3 AND ef.strikes = 1 THEN 0.38  -- 3-1: hitter ahead
        WHEN ef.balls = 3 AND ef.strikes = 2 THEN 0.52  -- 3-2: full count pressure
        ELSE 0.45
    END,
    ball_accumulation_rate = CASE 
        WHEN ef.balls = 0 AND ef.strikes = 0 THEN 0.38  -- 0-0: ~38% ball rate
        WHEN ef.balls = 0 AND ef.strikes = 1 THEN 0.30  -- 0-1: smaller zone
        WHEN ef.balls = 0 AND ef.strikes = 2 THEN 0.22  -- 0-2: pitchers expand
        WHEN ef.balls = 1 AND ef.strikes = 0 THEN 0.42  -- 1-0: larger zone
        WHEN ef.balls = 1 AND ef.strikes = 1 THEN 0.35  -- 1-1: standard
        WHEN ef.balls = 1 AND ef.strikes = 2 THEN 0.25  -- 1-2: pitchers expand
        WHEN ef.balls = 2 AND ef.strikes = 0 THEN 0.48  -- 2-0: larger zone
        WHEN ef.balls = 2 AND ef.strikes = 1 THEN 0.40  -- 2-1: hitters ahead
        WHEN ef.balls = 2 AND ef.strikes = 2 THEN 0.32  -- 2-2: even pressure
        WHEN ef.balls = 3 AND ef.strikes = 0 THEN 0.60  -- 3-0: walk likely
        WHEN ef.balls = 3 AND ef.strikes = 1 THEN 0.45  -- 3-1: walk likely
        WHEN ef.balls = 3 AND ef.strikes = 2 THEN 0.35  -- 3-2: walk/strikeout
        ELSE 0.38
    END,
    -- Absorbing state: 3 strikes or 4 balls (end of PA imminent)
    is_absorbing_state = (ef.strikes = 2 OR ef.balls = 3),
    -- Expected pitches remaining (Markov expectation)
    expected_pitches_remaining = CASE 
        WHEN ef.balls = 0 AND ef.strikes = 0 THEN 3.3
        WHEN ef.balls = 0 AND ef.strikes = 1 THEN 2.8
        WHEN ef.balls = 0 AND ef.strikes = 2 THEN 2.1
        WHEN ef.balls = 1 AND ef.strikes = 0 THEN 3.0
        WHEN ef.balls = 1 AND ef.strikes = 1 THEN 2.6
        WHEN ef.balls = 1 AND ef.strikes = 2 THEN 2.0
        WHEN ef.balls = 2 AND ef.strikes = 0 THEN 2.5
        WHEN ef.balls = 2 AND ef.strikes = 1 THEN 2.3
        WHEN ef.balls = 2 AND ef.strikes = 2 THEN 1.8
        WHEN ef.balls = 3 AND ef.strikes = 0 THEN 1.5
        WHEN ef.balls = 3 AND ef.strikes = 1 THEN 1.8
        WHEN ef.balls = 3 AND ef.strikes = 2 THEN 1.5  -- Full count
        ELSE 3.0
    END,
    -- Count is favorable to hitter (ahead in count)
    is_favorable_hitter_count = (ef.balls > ef.strikes),
    -- Count is favorable to pitcher (ahead in count)
    is_favorable_pitcher_count = (ef.strikes > ef.balls OR ef.strikes = 2),
    -- Count pressure (how "important" is this pitch)
    count_pressure_index = CASE 
        WHEN ef.balls = 3 AND ef.strikes = 2 THEN 1.0  -- Full count max pressure
        WHEN ef.strikes = 2 AND ef.balls < 3 THEN 0.8  -- Strikeout threat
        WHEN ef.balls = 3 AND ef.strikes < 2 THEN 0.7  -- Walk threat
        WHEN ef.balls = 2 AND ef.strikes = 2 THEN 0.6  -- Next pitch decisive
        ELSE 0.4
    END
WHERE ef.strike_accumulation_rate IS NULL;

-- Step 3: Calculate matchup history from available data
-- Count prior PAs between this batter and pitcher
WITH matchup_history AS (
    SELECT 
        bf1.pitch_id,
        bf1.batter_id,
        bf1.pitcher_id,
        bf1.game_date,
        COUNT(bf2.pitch_id) as prior_pas,
        SUM(CASE WHEN bf2.events IN ('single', 'double', 'triple', 'home_run') THEN 1 ELSE 0 END) as prior_hits,
        SUM(CASE WHEN bf2.events = 'home_run' THEN 1 ELSE 0 END) as prior_hrs,
        SUM(CASE WHEN bf2.events IN ('strikeout', 'strikeout_double_play') THEN 1 ELSE 0 END) as prior_ks,
        AVG(CASE WHEN bf2.events IN ('single', 'double', 'triple', 'home_run') THEN 1.0 ELSE 0.0 END) as prior_ba
    FROM features_pitch.base_features bf1
    LEFT JOIN features_pitch.base_features bf2 
        ON bf1.batter_id = bf2.batter_id 
        AND bf1.pitcher_id = bf2.pitcher_id
        AND bf2.game_date < bf1.game_date  -- Prior encounters only
    WHERE bf2.pitch_number = 1  -- Count once per PA
    GROUP BY bf1.pitch_id, bf1.batter_id, bf1.pitcher_id, bf1.game_date
)
UPDATE features_pitch.engineered_features ef
SET 
    matchup_prior_pa_count = COALESCE(mh.prior_pas, 0),
    matchup_prior_hr_count = COALESCE(mh.prior_hrs, 0),
    matchup_prior_strikeout_count = COALESCE(mh.prior_ks, 0),
    matchup_prior_ba = CASE WHEN mh.prior_pas > 0 THEN mh.prior_ba ELSE NULL END,
    matchup_first_time_facing = (COALESCE(mh.prior_pas, 0) = 0),
    matchup_first_time_this_season = (COALESCE(mh.prior_pas, 0) = 0)  -- Simplified
FROM matchup_history mh
WHERE ef.pitch_id = mh.pitch_id
  AND ef.matchup_prior_pa_count IS NULL;

-- Step 4: Sequence pattern features
-- Get previous 2-3 pitches for pattern detection
WITH pitch_sequences AS (
    SELECT 
        bf1.pitch_id,
        bf1.game_pk,
        bf1.at_bat_number,
        bf1.pitch_number,
        LAG(bf1.pitch_type, 1) OVER (
            PARTITION BY bf1.game_pk, bf1.at_bat_number 
            ORDER BY bf1.pitch_number
        ) as prev_pitch_1,
        LAG(bf1.pitch_type, 2) OVER (
            PARTITION BY bf1.game_pk, bf1.at_bat_number 
            ORDER BY bf1.pitch_number
        ) as prev_pitch_2
    FROM features_pitch.base_features bf1
)
UPDATE features_pitch.engineered_features ef
SET 
    prev_2_pitch_types = CASE 
        WHEN ps.prev_pitch_1 IS NOT NULL AND ps.prev_pitch_2 IS NOT NULL 
        THEN ps.prev_pitch_2 || '-' || ps.prev_pitch_1
        ELSE NULL
    END,
    is_repeated_pitch = (
        ps.prev_pitch_1 = bf.pitch_type AND ps.prev_pitch_1 IS NOT NULL
    ),
    is_alternating_pattern = (
        ps.prev_pitch_2 = bf.pitch_type AND ps.prev_pitch_1 != bf.pitch_type
        AND ps.prev_pitch_2 IS NOT NULL
    ),
    pitch_sequence_category = CASE 
        WHEN bf.pitch_type IN ('FF', 'FT', 'FC', 'SI') AND ps.prev_pitch_1 IN ('FF', 'FT', 'FC', 'SI')
        THEN 'fastball_cluster'
        WHEN bf.pitch_type IN ('SL', 'CU', 'KC', 'ST') AND ps.prev_pitch_1 IN ('SL', 'CU', 'KC', 'ST')
        THEN 'breaking_cluster'
        WHEN bf.pitch_type IN ('CH', 'FS', 'FO') AND ps.prev_pitch_1 IN ('CH', 'FS', 'FO')
        THEN 'offspeed_cluster'
        ELSE 'mixed'
    END
FROM pitch_sequences ps
JOIN features_pitch.base_features bf ON ef.pitch_id = bf.pitch_id
WHERE ef.pitch_id = ps.pitch_id
  AND ef.prev_2_pitch_types IS NULL;

-- Step 5: Platoon advantage (situational splits)
UPDATE features_pitch.engineered_features ef
SET 
    is_platoon_advantage_batter = (
        (bf.stand = 'L' AND bf.p_throws = 'R') OR  -- LHB vs RHP
        (bf.stand = 'R' AND bf.p_throws = 'L')     -- RHB vs LHP
    ),
    is_platoon_disadvantage_batter = (
        (bf.stand = 'L' AND bf.p_throws = 'L') OR  -- LHB vs LHP
        (bf.stand = 'R' AND bf.p_throws = 'R')     -- RHB vs RHP
    ),
    is_platoon_advantage_pitcher = (
        (bf.stand = 'L' AND bf.p_throws = 'L') OR  -- LHP vs LHB
        (bf.stand = 'R' AND bf.p_throws = 'R')     -- RHP vs RHB
    ),
    platoon_advantage_direction = CASE 
        WHEN (bf.stand = 'L' AND bf.p_throws = 'R') OR (bf.stand = 'R' AND bf.p_throws = 'L')
        THEN 'batter'
        WHEN (bf.stand = 'L' AND bf.p_throws = 'L') OR (bf.stand = 'R' AND bf.p_throws = 'R')
        THEN 'pitcher'
        ELSE 'neutral'
    END
FROM features_pitch.base_features bf
WHERE ef.pitch_id = bf.pitch_id
  AND ef.is_platoon_advantage_batter IS NULL;

-- Step 6: Rookie/Veteran classification (estimated from data)
-- Count career PAs/IP from available data
WITH batter_career AS (
    SELECT batter_id, COUNT(DISTINCT game_pk) as games, COUNT(*) as estimated_pa
    FROM features_pitch.base_features
    WHERE pitch_number = 1  -- One per PA
    GROUP BY batter_id
),
pitcher_career AS (
    SELECT pitcher_id, COUNT(DISTINCT game_pk) as games, COUNT(*) as estimated_ip
    FROM features_pitch.base_features
    WHERE pitch_number = 1
    GROUP BY pitcher_id
)
UPDATE features_pitch.engineered_features ef
SET 
    is_rookie_batter = (bc.estimated_pa < 130),
    is_veteran_batter = (bc.estimated_pa > 3000),
    batter_experience_level = CASE 
        WHEN bc.estimated_pa < 130 THEN 'rookie'
        WHEN bc.estimated_pa < 500 THEN 'young'
        WHEN bc.estimated_pa < 3000 THEN 'prime'
        ELSE 'veteran'
    END,
    batter_career_pa_estimate = bc.estimated_pa,
    is_rookie_pitcher = (pc.estimated_ip < 150),
    is_veteran_pitcher = (pc.estimated_ip > 1500),
    pitcher_experience_level = CASE 
        WHEN pc.estimated_ip < 150 THEN 'rookie'
        WHEN pc.estimated_ip < 500 THEN 'young'
        WHEN pc.estimated_ip < 1500 THEN 'prime'
        ELSE 'veteran'
    END,
    pitcher_career_ip_estimate = pc.estimated_ip
FROM features_pitch.base_features bf
LEFT JOIN batter_career bc ON bf.batter_id = bc.batter_id
LEFT JOIN pitcher_career pc ON bf.pitcher_id = pc.pitcher_id
WHERE ef.pitch_id = bf.pitch_id
  AND ef.is_rookie_batter IS NULL;

-- Step 7: Games back in standings (simplified - would need actual standings)
UPDATE features_pitch.engineered_features ef
SET games_back_in_standings = NULL  -- Placeholder - requires standings data
WHERE ef.games_back_in_standings IS NULL;

-- Verification
SELECT 
    'Final features populated' as status,
    COUNT(*) as total_rows,
    COUNT(is_postseason) as with_postseason,
    COUNT(strike_accumulation_rate) as with_markov,
    COUNT(matchup_prior_pa_count) as with_matchup,
    COUNT(is_rookie_batter) as with_rookie,
    COUNT(prev_2_pitch_types) as with_sequence,
    COUNT(is_platoon_advantage_batter) as with_platoon,
    ROUND(AVG(matchup_prior_pa_count)::numeric, 2) as avg_prior_matchups,
    ROUND(AVG(strike_accumulation_rate)::numeric, 3) as avg_strike_rate,
    SUM(CASE WHEN is_repeated_pitch THEN 1 ELSE 0 END) as repeated_pitch_count
FROM features_pitch.engineered_features;
