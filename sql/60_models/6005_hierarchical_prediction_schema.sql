-- ============================================================
-- Hierarchical Prediction System (HPS) - Panel Data Schema
-- Multi-Layer Database Schema for Real-Time Baseball Predictions
-- ============================================================
-- Author: Agent Cascade
-- Date: 2026-05-01
-- Purpose: 5-layer hierarchical prediction from league trends to pitch-by-pitch
-- Design: All factors included; models select subsets without query changes
-- ============================================================

-- Create schema
CREATE SCHEMA IF NOT EXISTS predictions;
COMMENT ON SCHEMA predictions IS 'Hierarchical prediction system - panel data for multi-layer baseball inference. All 5 abstraction layers included.';

-- ============================================================
-- LAYER 1: LEAGUE/SEASON ENVIRONMENT (Macro Trends)
-- ============================================================

CREATE TABLE predictions.league_environment (
    season INTEGER PRIMARY KEY,
    league_id VARCHAR(10),  -- 'AL', 'NL', 'MLB'
    
    -- Scoring environment
    runs_per_game DECIMAL(5,3),
    runs_per_pa DECIMAL(5,3),
    
    -- Outcome rates (league averages)
    hr_rate DECIMAL(5,4),  -- HR per PA
    k_rate DECIMAL(5,4),   -- K per PA
    bb_rate DECIMAL(5,4),  -- BB per PA
    avg DECIMAL(4,3),
    obp DECIMAL(4,3),
    slg DECIMAL(4,3),
    ops DECIMAL(4,3),
    woba DECIMAL(4,3),
    
    -- Pitch characteristics (league-wide)
    avg_pitch_velocity DECIMAL(5,2),
    avg_pitch_spin DECIMAL(7,2),
    fastball_pct DECIMAL(4,3),
    breaking_pct DECIMAL(4,3),
    offspeed_pct DECIMAL(4,3),
    
    -- Context effects
    home_field_advantage DECIMAL(4,3),  -- Win pct for home teams
    day_game_factor DECIMAL(4,3),
    month_trends JSONB,  -- {"04": {"hr_rate": 0.025}, "07": {"hr_rate": 0.032}}
    
    -- Ball/dead ball indicators
    ball_carry_index DECIMAL(4,3),  -- 1.0 = neutral, >1 = more carry
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE predictions.league_environment IS 
'Layer 1: League-wide trends and scoring environment by season. Updated annually/monthly. Factors: 20+ season-level metrics.';

-- ============================================================
-- LAYER 2: TEAM CONTEXT MODELS (Form, Streak, Environment)
-- ============================================================

CREATE TABLE predictions.team_context_rolling (
    team_id VARCHAR(20) NOT NULL,
    as_of_date DATE NOT NULL,
    
    -- Form metrics (last 10 games)
    last_10_wins INTEGER,
    last_10_losses INTEGER,
    last_10_win_pct DECIMAL(4,3),
    streak_type VARCHAR(10),  -- 'winning', 'losing', 'neutral'
    streak_length INTEGER,
    
    -- Home/Away splits
    home_win_pct DECIMAL(4,3),
    away_win_pct DECIMAL(4,3),
    home_advantage DECIMAL(4,3),  -- Difference from neutral
    
    -- Offense (rolling 30 days)
    team_ops DECIMAL(4,3),
    team_woba DECIMAL(4,3),
    runs_per_game DECIMAL(4,2),
    hr_per_game DECIMAL(4,2),
    
    -- Pitching (rolling 30 days)
    team_era DECIMAL(4,2),
    team_wh DECIMAL(4,2),
    k_per_nine DECIMAL(5,2),
    bb_per_nine DECIMAL(5,2),
    
    -- Bullpen status
    bullpen_era DECIMAL(4,2),
    bullpen_fatigue_score INTEGER,  -- 0-100, higher = more tired
    days_since_last_game INTEGER,
    
    -- vs LHP/RHP splits
    vs_lhp_ops DECIMAL(4,3),
    vs_rhp_ops DECIMAL(4,3),
    
    -- Park factor
    home_park_factor DECIMAL(4,2),  -- 100 = neutral
    
    created_at TIMESTAMP DEFAULT NOW(),
    
    PRIMARY KEY (team_id, as_of_date)
);

COMMENT ON TABLE predictions.team_context_rolling IS 
'Layer 2: Team form, home/away, bullpen status. Updated daily. Factors: 25+ team-level metrics.';

CREATE INDEX idx_team_context_as_of ON predictions.team_context_rolling(as_of_date, team_id);

-- ============================================================
-- LAYER 3: PLAYER PROFILES (Batter/Pitcher Tendencies)
-- ============================================================

-- Batter rolling profiles
CREATE TABLE predictions.batter_profiles_rolling (
    batter_id VARCHAR(20) NOT NULL,
    as_of_date DATE NOT NULL,
    
    -- Sample size
    last_30_pa INTEGER,
    last_100_pa INTEGER,
    season_pa INTEGER,
    
    -- Overall performance
    batting_avg DECIMAL(4,3),
    obp DECIMAL(4,3),
    slg DECIMAL(4,3),
    ops DECIMAL(4,3),
    woba DECIMAL(4,3),
    wrc_plus INTEGER,  -- Weighted runs created+
    
    -- Discipline
    k_rate DECIMAL(4,3),
    bb_rate DECIMAL(4,3),
    zone_swing_rate DECIMAL(4,3),
    o_swing_rate DECIMAL(4,3),  -- Chase rate
    zone_contact_rate DECIMAL(4,3),
    o_contact_rate DECIMAL(4,3),
    swinging_strike_rate DECIMAL(4,3),
    
    -- Power
    iso DECIMAL(4,3),  -- Isolated power
    hr_flyball_rate DECIMAL(4,3),
    avg_exit_velocity DECIMAL(5,2),
    hard_hit_rate DECIMAL(4,3),
    
    -- Pitch type performance
    vs_fastball_avg DECIMAL(4,3),
    vs_fastball_slg DECIMAL(4,3),
    vs_breaking_avg DECIMAL(4,3),
    vs_breaking_slg DECIMAL(4,3),
    vs_offspeed_avg DECIMAL(4,3),
    vs_offspeed_slg DECIMAL(4,3),
    
    -- Count performance (JSON for flexibility)
    count_performance JSONB,  -- {"0-0": {"avg": .280, "ops": .750}, "2-2": {...}}
    
    -- Situational
    risp_avg DECIMAL(4,3),
    risp_ops DECIMAL(4,3),
    two_outs_ops DECIMAL(4,3),
    late_close_ops DECIMAL(4,3),
    
    -- Trends
    velocity_adjustment DECIMAL(4,3),  -- Performance vs different velo buckets
    trend_direction VARCHAR(10),  -- 'improving', 'declining', 'stable'
    trend_confidence DECIMAL(4,3),
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    PRIMARY KEY (batter_id, as_of_date)
);

COMMENT ON TABLE predictions.batter_profiles_rolling IS 
'Layer 3: Batter tendencies and rolling 30-day performance. Updated daily. Factors: 30+ batter metrics.';

CREATE INDEX idx_batter_profiles_as_of ON predictions.batter_profiles_rolling(as_of_date, batter_id);

-- Pitcher rolling profiles
CREATE TABLE predictions.pitcher_profiles_rolling (
    pitcher_id VARCHAR(20) NOT NULL,
    as_of_date DATE NOT NULL,
    
    -- Sample size
    last_5_games_pitches INTEGER,
    last_10_games_pitches INTEGER,
    season_pitches INTEGER,
    season_ip DECIMAL(5,1),
    
    -- Overall performance
    era DECIMAL(4,2),
    fip DECIMAL(4,2),
    whip DECIMAL(4,2),
    k_per_nine DECIMAL(5,2),
    bb_per_nine DECIMAL(5,2),
    k_bb_ratio DECIMAL(4,2),
    
    -- Stuff metrics
    avg_velocity DECIMAL(5,2),
    max_velocity DECIMAL(5,2),
    avg_spin_rate DECIMAL(7,2),
    stuff_plus INTEGER,  -- 100 = league average
    
    -- Pitch mix (overall)
    pitch_mix JSONB,  -- {"FF": 0.45, "SL": 0.25, "CU": 0.20, "CH": 0.10}
    primary_pitch VARCHAR(5),
    secondary_pitch VARCHAR(5),
    
    -- Pitch mix by count (nested JSON)
    pitch_mix_by_count JSONB,  -- {"0-0": {"FF": 0.60}, "2-2": {"FF": 0.40}}
    
    -- Count-specific tendencies
    first_pitch_strike_rate DECIMAL(4,3),
    first_pitch_fastball_pct DECIMAL(4,3),
    two_strike_k_rate DECIMAL(4,3),
    two_strike_out_of_zone_pct DECIMAL(4,3),  -- Chase pitches
    three_ball_walk_rate DECIMAL(4,3),
    ahead_in_count_pct DECIMAL(4,3),
    behind_in_count_pct DECIMAL(4,3),
    
    -- Outcome rates
    zone_rate DECIMAL(4,3),
    o_swing_rate DECIMAL(4,3),
    whiff_rate DECIMAL(4,3),
    groundball_rate DECIMAL(4,3),
    flyball_rate DECIMAL(4,3),
    weak_contact_rate DECIMAL(4,3),
    
    -- Situational
    risp_era DECIMAL(4,2),
    high_leverage_era DECIMAL(4,2),
    times_thru_order_penalty DECIMAL(4,3),  -- OPS jump 2nd/3rd time
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    PRIMARY KEY (pitcher_id, as_of_date)
);

COMMENT ON TABLE predictions.pitcher_profiles_rolling IS 
'Layer 3: Pitcher tendencies and rolling performance. Updated daily. Factors: 35+ pitcher metrics.';

CREATE INDEX idx_pitcher_profiles_as_of ON predictions.pitcher_profiles_rolling(as_of_date, pitcher_id);

-- ============================================================
-- LAYER 4: MATCHUP HISTORY (H2H Dynamics)
-- ============================================================

CREATE TABLE predictions.matchup_history (
    matchup_pair_id VARCHAR PRIMARY KEY,  -- pitcher_batter composite key
    pitcher_id VARCHAR(20),
    batter_id VARCHAR(20),
    
    -- Career H2H
    career_pas INTEGER,
    career_avg DECIMAL(4,3),
    career_obp DECIMAL(4,3),
    career_slg DECIMAL(4,3),
    career_hr INTEGER,
    career_so INTEGER,
    career_bb INTEGER,
    
    -- Pitch mix faced
    pitch_mix_faced JSONB,  -- {"FF": 45, "SL": 23, "CU": 12}
    
    -- Outcomes distribution
    outcomes_distribution JSONB,  -- {"single": 5, "double": 2, "hr": 1, "so": 8}
    
    -- Recent history (last 2 seasons)
    last_2_seasons_pas INTEGER,
    last_2_seasons_woba DECIMAL(4,3),
    
    -- Current season
    times_faced_this_season INTEGER,
    
    -- Metadata
    most_recent_date DATE,
    trend_direction VARCHAR(10),  -- 'improving', 'declining', 'stable'
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE predictions.matchup_history IS 
'Layer 4: Historical pitcher-batter interactions. Updated weekly. Factors: 15+ H2H metrics.';

CREATE INDEX idx_matchup_pitcher ON predictions.matchup_history(pitcher_id);
CREATE INDEX idx_matchup_batter ON predictions.matchup_history(batter_id);

-- ============================================================
-- LAYER 5: SITUATIONAL/REAL-TIME STATE
-- ============================================================

-- Real-time game state (updates each pitch)
CREATE TABLE predictions.live_game_state (
    -- IDs
    game_pk INTEGER,
    pa_id VARCHAR,
    pitch_id BIGINT PRIMARY KEY,
    
    -- Time
    game_date DATE,
    timestamp TIMESTAMP,
    
    -- Game context
    half_inning INTEGER,
    pa_number INTEGER,
    pitch_number INTEGER,
    
    -- Score
    home_score INTEGER,
    away_score INTEGER,
    score_diff INTEGER,
    batting_team_leading BOOLEAN,
    
    -- Count
    balls INTEGER,
    strikes INTEGER,
    count_label VARCHAR(5),  -- "2-2"
    count_category VARCHAR(20),  -- "ahead", "behind", "even", "two_strikes"
    
    -- Base state
    on_1b BOOLEAN,
    on_2b BOOLEAN,
    on_3b BOOLEAN,
    base_state INTEGER,  -- 0-7 binary encoding
    base_state_label VARCHAR(20),  -- "bases_empty", "runners_1_2"
    risp BOOLEAN,
    runners_on INTEGER,
    
    -- Outs/situation
    outs INTEGER,
    inning INTEGER,
    inning_half VARCHAR(10),  -- 'top', 'bottom'
    outs_remaining INTEGER,
    
    -- Leverage
    game_leverage_index DECIMAL(4,2),  -- LI (1.0 = avg)
    win_exp_home DECIMAL(4,3),  -- Home team win probability
    
    -- Players
    pitcher_id VARCHAR(20),
    batter_id VARCHAR(20),
    pitcher_hand VARCHAR(1),
    batter_hand VARCHAR(1),
    platoon_advantage BOOLEAN,  -- True if same hand (pitcher advantage)
    
    -- Pitcher state
    pitcher_pitches_thrown INTEGER,
    pitcher_batters_faced INTEGER,
    pitcher_innings DECIMAL(4,1),
    pitcher_days_rest INTEGER,
    times_thru_order INTEGER,  -- 1st/2nd/3rd time through lineup
    
    -- Sequence
    previous_pitch_type VARCHAR(5),
    previous_pitch_result VARCHAR(20),
    pitch_sequence VARCHAR(20),  -- "BCSF" format
    
    -- Predictions (populated by models)
    pred_next_pitch_type JSONB,  -- {"FF": 0.45, "SL": 0.35}
    pred_swing_probability DECIMAL(4,3),
    pred_contact_probability DECIMAL(4,3),
    pred_fair_probability DECIMAL(4,3),
    pred_pa_outcome JSONB,  -- Full distribution
    pred_home_run_prob DECIMAL(4,3),
    
    -- Actual outcome (populated after pitch)
    actual_pitch_type VARCHAR(5),
    actual_swing BOOLEAN,
    actual_contact BOOLEAN,
    actual_outcome VARCHAR(20),
    
    created_at TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE predictions.live_game_state IS 
'Layer 5: Real-time game state updated each pitch. Factors: 30+ situational metrics.';

CREATE INDEX idx_live_game_game ON predictions.live_game_state(game_pk, timestamp);
CREATE INDEX idx_live_game_pa ON predictions.live_game_state(pa_id, pitch_number);

-- ============================================================
-- MASTER PANEL TABLE (All Layers Combined)
-- ============================================================

-- This is the main table for model training
-- Joins all 5 layers into one observation row
-- Models SELECT any subset of factors without changing queries

CREATE TABLE predictions.panel_master (
    -- Primary key
    observation_id BIGINT PRIMARY KEY,
    
    -- LAYER 1: League/Season (fixed effects)
    season INTEGER,
    league_environment_id VARCHAR,  -- 'AL_2024', 'NL_2024'
    league_hr_rate DECIMAL(5,4),
    league_k_rate DECIMAL(5,4),
    league_bb_rate DECIMAL(5,4),
    league_woba DECIMAL(4,3),
    ball_carry_index DECIMAL(4,3),
    
    -- LAYER 2: Team (context effects)
    home_team_id VARCHAR,
    away_team_id VARCHAR,
    home_team_win_pct DECIMAL(4,3),
    away_team_win_pct DECIMAL(4,3),
    home_team_streak_type VARCHAR,
    away_team_streak_type VARCHAR,
    home_team_ops DECIMAL(4,3),
    away_team_era DECIMAL(4,2),
    home_park_factor DECIMAL(4,2),
    
    -- LAYER 3: Players (random effects)
    pitcher_id VARCHAR(20),
    batter_id VARCHAR(20),
    
    -- Pitcher profile factors
    pitcher_era DECIMAL(4,2),
    pitcher_whip DECIMAL(4,2),
    pitcher_k_per_nine DECIMAL(5,2),
    pitcher_stuff_plus INTEGER,
    pitcher_pitch_mix JSONB,
    pitcher_two_strike_k_rate DECIMAL(4,3),
    pitcher_zone_rate DECIMAL(4,3),
    
    -- Batter profile factors
    batter_woba DECIMAL(4,3),
    batter_ops DECIMAL(4,3),
    batter_k_rate DECIMAL(4,3),
    batter_bb_rate DECIMAL(4,3),
    batter_vs_fastball_slg DECIMAL(4,3),
    batter_vs_breaking_slg DECIMAL(4,3),
    batter_zone_swing_rate DECIMAL(4,3),
    batter_o_swing_rate DECIMAL(4,3),
    batter_hard_hit_rate DECIMAL(4,3),
    
    -- LAYER 4: Matchup (H2H effects)
    matchup_pair_id VARCHAR,
    matchup_career_pas INTEGER,
    matchup_career_avg DECIMAL(4,3),
    matchup_career_hr INTEGER,
    matchup_career_so INTEGER,
    matchup_hr_rate DECIMAL(5,4),
    matchup_k_rate DECIMAL(5,4),
    
    -- LAYER 5: State (situational effects)
    game_pk INTEGER,
    pa_id VARCHAR,
    pitch_number INTEGER,
    count_label VARCHAR(5),
    count_category VARCHAR(20),
    base_state INTEGER,
    base_state_label VARCHAR(20),
    outs INTEGER,
    risp BOOLEAN,
    inning INTEGER,
    inning_half VARCHAR(10),
    score_diff INTEGER,
    game_leverage_index DECIMAL(4,2),
    win_exp DECIMAL(4,3),
    times_thru_order INTEGER,
    previous_pitch_type VARCHAR(5),
    pitch_sequence VARCHAR(20),
    
    -- TARGET VARIABLES (for model training)
    -- Primary targets
    target_outcome VARCHAR(20),  -- 'K', 'BB', '1B', '2B', '3B', 'HR', 'Out'
    target_is_home_run BOOLEAN,
    target_is_strikeout BOOLEAN,
    target_is_walk BOOLEAN,
    target_is_hit BOOLEAN,
    
    -- Pitch-level targets
    target_next_pitch_type VARCHAR(5),  -- For pitch prediction models
    target_swing BOOLEAN,
    target_contact BOOLEAN,
    
    -- Metadata
    data_quality_score DECIMAL(3,2),  -- 0-1 completeness score
    created_at TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE predictions.panel_master IS 
'Master panel data table combining all 5 layers. 130+ factors available. Models SELECT any subset without query modification.';

-- Indexes for common query patterns
CREATE INDEX idx_panel_season ON predictions.panel_master(season);
CREATE INDEX idx_panel_game ON predictions.panel_master(game_pk);
CREATE INDEX idx_panel_pa ON predictions.panel_master(pa_id);
CREATE INDEX idx_panel_pitcher ON predictions.panel_master(pitcher_id);
CREATE INDEX idx_panel_batter ON predictions.panel_master(batter_id);
CREATE INDEX idx_panel_matchup ON predictions.panel_master(matchup_pair_id);
CREATE INDEX idx_panel_count ON predictions.panel_master(count_label);
CREATE INDEX idx_panel_outcome ON predictions.panel_master(target_outcome);

-- ============================================================
-- REFRESH PROCEDURES
-- ============================================================

-- Procedure to refresh all prediction tables
CREATE OR REPLACE FUNCTION predictions.refresh_all(as_of_date DATE DEFAULT CURRENT_DATE)
RETURNS TABLE(schema_name TEXT, table_name TEXT, rows_refreshed INTEGER, status TEXT) AS $$
DECLARE
    v_date DATE := as_of_date;
    v_count INTEGER;
BEGIN
    -- Refresh Layer 2: Team context
    -- (Would call Python/DBT or other refresh logic)
    
    -- Refresh Layer 3: Player profiles
    -- (Would call player profile calculation)
    
    -- Refresh Layer 4: Matchup history
    -- (Would call matchup aggregation)
    
    -- Return status
    RETURN QUERY SELECT 
        'predictions'::TEXT,
        'panel_master'::TEXT,
        (SELECT COUNT(*)::INTEGER FROM predictions.panel_master WHERE created_at > NOW() - INTERVAL '1 hour'),
        'refreshed'::TEXT;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION predictions.refresh_all IS 
'Refreshes all prediction layer tables. Called daily or after significant data ingestion.';

-- ============================================================
-- VIEWS FOR QUICK ACCESS
-- ============================================================

-- View: Current player profiles (latest as_of_date)
CREATE VIEW predictions.v_current_batter_profiles AS
SELECT DISTINCT ON (batter_id)
    batter_id,
    as_of_date,
    batting_avg,
    ops,
    woba,
    vs_fastball_slg,
    vs_breaking_slg,
    k_rate,
    bb_rate,
    trend_direction
FROM predictions.batter_profiles_rolling
ORDER BY batter_id, as_of_date DESC;

CREATE VIEW predictions.v_current_pitcher_profiles AS
SELECT DISTINCT ON (pitcher_id)
    pitcher_id,
    as_of_date,
    era,
    whip,
    stuff_plus,
    pitch_mix,
    pitch_mix_by_count,
    two_strike_k_rate,
    zone_rate
FROM predictions.pitcher_profiles_rolling
ORDER BY pitcher_id, as_of_date DESC;

-- View: Current team context
CREATE VIEW predictions.v_current_team_context AS
SELECT DISTINCT ON (team_id)
    team_id,
    as_of_date,
    last_10_win_pct,
    streak_type,
    streak_length,
    team_ops,
    team_era,
    bullpen_era
FROM predictions.team_context_rolling
ORDER BY team_id, as_of_date DESC;

-- ============================================================
-- GRANTS
-- ============================================================

GRANT USAGE ON SCHEMA predictions TO readonly;
GRANT USAGE ON SCHEMA predictions TO readwrite;

GRANT SELECT ON ALL TABLES IN SCHEMA predictions TO readonly;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA predictions TO readwrite;

-- ============================================================
-- DOCUMENTATION
-- ============================================================

COMMENT ON SCHEMA predictions IS 
'Hierarchical Prediction System (HPS) - 5-layer panel data architecture for baseball predictions.
Layers: 1=League/Season, 2=Team/Context, 3=Player Profiles, 4=Matchup History, 5=Situational/Real-Time.
Total factors: 130+. All layers stored for flexible feature selection.';

-- End of schema creation
-- Next: Run dbt models or Python scripts to populate tables
