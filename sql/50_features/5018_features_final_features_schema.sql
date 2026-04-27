/*
File: sql/features/015_final_features_schema.sql
Purpose: Final feature schema - Coaching, Postseason, Markov chains, Matchup history
Author: Agent Cascade
Date: 2026-04-24
Depends On: sql/features/014_populate_context_features_batch.sql
Called By: Manual execution

Tables Modified:
- features_pitch.engineered_features (adds final columns)

New Features (50+):

## Coaching Effects (Category 5) - LIMITED
- manager_aggressiveness_score: Sac bunt, steal, pinch-hit tendencies
- team_shift_percentage: Defensive shift usage
- bullpen_usage_pattern: Quick hook vs patient

## Postseason & Clutch (Category 6)
- is_postseason: Playoff game flag
- is_elimination_game: Win or go home
- is_potential_clincher: Can clinch series/division
- games_back_in_standings: Division race pressure
- month_of_season: April through October effect
- is_season_opener: Opening day flag
- is_finale_game: Final game of series

## Markov Chain Features (Research-backed)
Based on FanGraphs/Retrosheet Markov research:
- count_transition_probability: P(next state | current state)
- strike_accumulation_rate: P(add strike | current count)
- ball_accumulation_rate: P(add ball | current count)
- is_absorbing_state: 3 strikes or 4 balls (end state)
- expected_pitches_remaining: Mean pitches to PA end from this count
- count_leverage_index: How "important" is this pitch in the count

## Batter-Pitcher Matchup History
- matchup_prior_pa_count: Times faced before this game
- matchup_prior_ba: Batting average in prior matchups
- matchup_prior_obp: OBP in prior matchups
- matchup_prior_slg: SLG in prior matchups
- matchup_prior_hr_count: HRs hit vs this pitcher
- matchup_prior_strikeout_rate: K% in prior matchups
- matchup_prior_whiff_rate: Swing-and-miss rate
- matchup_chase_rate: Chase rate vs this pitcher
- matchup_first_time_facing: First PA ever vs this pitcher
- matchup_first_time_this_season: First PA this season

## Player Career History (Context)
- batter_career_avg: Career batting average
- batter_career_obp: Career on-base
- batter_career_slg: Career slugging
- batter_career_iso: Career isolated power
- batter_career_k_rate: Career strikeout rate
- batter_career_bb_rate: Career walk rate
- pitcher_career_era: Career ERA
- pitcher_career_whip: Career WHIP
- pitcher_career_k_per_9: Career strikeouts per 9
- pitcher_career_bb_per_9: Career walks per 9
- pitcher_career_fip: Career FIP
- is_rookie_batter: < 130 career AB
- is_rookie_pitcher: < 50 career IP
- is_veteran_batter: > 3000 career PA
- is_veteran_pitcher: > 1000 career IP

## Situational Performance History
- batter_vs_pitcher_type_split: Performance vs RHP/LHP
- pitcher_vs_batter_type_split: Performance vs RHB/LHB
- batter_home_away_split: Home/road differential
- pitcher_home_away_split: Home/road ERA split
- batter_day_night_split: Day vs night performance
- pitcher_day_night_split: Day vs night ERA

## Sequence Pattern Features
- prev_2_pitch_types: Last 2 pitch types
- prev_3_pitch_types: Last 3 pitch types
- is_repeated_pitch: Same as previous
- is_alternating_pattern: FB-CB-FB pattern
- pitch_sequence_category: Fastball cluster, offspeed cluster, mixed

Notes:
- Coaching effects limited due to external data requirements
- Markov features calculated from historical count transitions
- Matchup history from core.events + features_pitch data
- Career stats would need external source or calculated from available data
*/

-- Coaching & Strategy (limited - external data needed)
ALTER TABLE features_pitch.engineered_features
    ADD COLUMN IF NOT EXISTS manager_aggressiveness_score NUMERIC,
    ADD COLUMN IF NOT EXISTS team_shift_percentage NUMERIC,
    ADD COLUMN IF NOT EXISTS bullpen_usage_pattern TEXT;

-- Postseason & Season Context
ALTER TABLE features_pitch.engineered_features
    ADD COLUMN IF NOT EXISTS is_postseason BOOLEAN,
    ADD COLUMN IF NOT EXISTS is_elimination_game BOOLEAN,
    ADD COLUMN IF NOT EXISTS is_potential_clincher BOOLEAN,
    ADD COLUMN IF NOT EXISTS games_back_in_standings NUMERIC,
    ADD COLUMN IF NOT EXISTS month_of_season INTEGER,
    ADD COLUMN IF NOT EXISTS is_season_opener BOOLEAN,
    ADD COLUMN IF NOT EXISTS is_finale_game BOOLEAN,
    ADD COLUMN IF NOT EXISTS is_getaway_day BOOLEAN,
    ADD COLUMN IF NOT EXISTS series_game_number INTEGER,
    ADD COLUMN IF NOT EXISTS team_is_in_pennyrace BOOLEAN;

-- Markov Chain / Count State Features
ALTER TABLE features_pitch.engineered_features
    ADD COLUMN IF NOT EXISTS count_transition_probability NUMERIC,
    ADD COLUMN IF NOT EXISTS strike_accumulation_rate NUMERIC,
    ADD COLUMN IF NOT EXISTS ball_accumulation_rate NUMERIC,
    ADD COLUMN IF NOT EXISTS is_absorbing_state BOOLEAN,
    ADD COLUMN IF NOT EXISTS expected_pitches_remaining NUMERIC,
    ADD COLUMN IF NOT EXISTS count_absorption_probability NUMERIC,
    ADD COLUMN IF NOT EXISTS is_favorable_hitter_count BOOLEAN,
    ADD COLUMN IF NOT EXISTS is_favorable_pitcher_count BOOLEAN,
    ADD COLUMN IF NOT EXISTS count_pressure_index NUMERIC;

-- Batter-Pitcher Matchup History
ALTER TABLE features_pitch.engineered_features
    ADD COLUMN IF NOT EXISTS matchup_prior_pa_count INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS matchup_prior_ba NUMERIC,
    ADD COLUMN IF NOT EXISTS matchup_prior_obp NUMERIC,
    ADD COLUMN IF NOT EXISTS matchup_prior_slg NUMERIC,
    ADD COLUMN IF NOT EXISTS matchup_prior_ops NUMERIC,
    ADD COLUMN IF NOT EXISTS matchup_prior_hr_count INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS matchup_prior_strikeout_count INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS matchup_prior_strikeout_rate NUMERIC,
    ADD COLUMN IF NOT EXISTS matchup_prior_whiff_rate NUMERIC,
    ADD COLUMN IF NOT EXISTS matchup_prior_chase_rate NUMERIC,
    ADD COLUMN IF NOT EXISTS matchup_first_time_facing BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS matchup_first_time_this_season BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS matchup_success_trend TEXT; -- improving/declining/stable

-- Player Career History (placeholder - would need external data or long calc)
ALTER TABLE features_pitch.engineered_features
    ADD COLUMN IF NOT EXISTS is_rookie_batter BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS is_rookie_pitcher BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS is_veteran_batter BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS is_veteran_pitcher BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS batter_experience_level TEXT, -- rookie/young/prime/veteran
    ADD COLUMN IF NOT EXISTS pitcher_experience_level TEXT,
    ADD COLUMN IF NOT EXISTS batter_career_pa_estimate INTEGER,
    ADD COLUMN IF NOT EXISTS pitcher_career_ip_estimate INTEGER;

-- Situational Splits (from available data)
ALTER TABLE features_pitch.engineered_features
    ADD COLUMN IF NOT EXISTS is_platoon_advantage_batter BOOLEAN,
    ADD COLUMN IF NOT EXISTS is_platoon_disadvantage_batter BOOLEAN,
    ADD COLUMN IF NOT EXISTS is_platoon_advantage_pitcher BOOLEAN,
    ADD COLUMN IF NOT EXISTS is_platoon_disadvantage_pitcher BOOLEAN,
    ADD COLUMN IF NOT EXISTS platoon_advantage_direction TEXT; -- pitcher/batter/neutral

-- Sequence Pattern Features
ALTER TABLE features_pitch.engineered_features
    ADD COLUMN IF NOT EXISTS prev_2_pitch_types TEXT,
    ADD COLUMN IF NOT EXISTS prev_3_pitch_types TEXT,
    ADD COLUMN IF NOT EXISTS is_repeated_pitch BOOLEAN,
    ADD COLUMN IF NOT EXISTS is_alternating_pattern BOOLEAN,
    ADD COLUMN IF NOT EXISTS pitch_sequence_category TEXT, -- fastball_cluster/breaking_cluster/mixed
    ADD COLUMN IF NOT EXISTS sequence_predictability_score NUMERIC; -- How predictable is pitcher

-- Comments
COMMENT ON COLUMN features_pitch.engineered_features.count_transition_probability IS 
    'Markov chain: P(next count state | current count state) from historical data';
COMMENT ON COLUMN features_pitch.engineered_features.strike_accumulation_rate IS 
    'Markov: P(add strike | current count) - likelihood of moving toward strikeout';
COMMENT ON COLUMN features_pitch.engineered_features.expected_pitches_remaining IS 
    'Markov expected value: mean pitches remaining in PA from current count';
COMMENT ON COLUMN features_pitch.engineered_features.matchup_prior_pa_count IS 
    'Career PAs between this batter and pitcher before this game';
COMMENT ON COLUMN features_pitch.engineered_features.matchup_first_time_facing IS 
    'True if first career PA vs this pitcher (debut effect)';
COMMENT ON COLUMN features_pitch.engineered_features.is_postseason IS 
    'True if playoff game (different dynamics, higher leverage)';
COMMENT ON COLUMN features_pitch.engineered_features.month_of_season IS 
    'April=4 through October=10 - seasonal progression/fatigue effect';
COMMENT ON COLUMN features_pitch.engineered_features.games_back_in_standings IS 
    'Division race pressure: 0 = leading, >5 = out of race';

-- Verification
SELECT 
    'Final features schema added' as status,
    COUNT(*) as total_rows,
    COUNT(is_postseason) as with_postseason,
    COUNT(count_transition_probability) as with_markov,
    COUNT(matchup_prior_pa_count) as with_matchup,
    COUNT(is_rookie_batter) as with_rookie,
    COUNT(prev_2_pitch_types) as with_sequence
FROM features_pitch.engineered_features;
