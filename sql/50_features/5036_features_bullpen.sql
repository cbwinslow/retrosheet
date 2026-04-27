/*
File: sql/504_features_bullpen.sql
Purpose: Bullpen features - fatigue, effectiveness, and depth metrics
Author: Agent cbwinslow/retrosheet
Date: 2026-04-26
Depends On: raw_gumbo.plays, features.player_ids
Called By: scripts/features/build_bullpen_features.sh

Tables Created:
- features.bullpen_status: Team bullpen status by game
- features.reliever_fatigue: Individual reliever workload
- features.bullpen_features: Combined features for games
*/

-- Ensure features schema exists
CREATE SCHEMA IF NOT EXISTS features;

-- =============================================
-- BULLPEN STATUS BY GAME
-- =============================================

CREATE TABLE IF NOT EXISTS features.bullpen_status (
    status_id SERIAL PRIMARY KEY,
    team_id INTEGER NOT NULL,
    game_pk INTEGER NOT NULL,
    season INTEGER NOT NULL,
    game_date DATE NOT NULL,
    is_home_team BOOLEAN NOT NULL,
    
    -- Available relievers
    available_pitchers INTEGER DEFAULT 0,
    rested_pitchers INTEGER DEFAULT 0,  -- No pitch in last 2 days
    warm_pitchers INTEGER DEFAULT 0,    -- Pitched yesterday but not today
    tired_pitchers INTEGER DEFAULT 0,   -- Pitched 2 of last 3 days
    
    -- Bullpen quality (season aggregates)
    bullpen_era NUMERIC(5,2),
    bullpen_whip NUMERIC(4,2),
    bullpen_k_9 NUMERIC(4,1),
    bullpen_bb_9 NUMERIC(4,1),
    
    -- Recent bullpen performance (last 7 days)
    l7_bullpen_era NUMERIC(5,2),
    l7_bullpen_ip NUMERIC(5,1),
    l7_bullpen_games INTEGER DEFAULT 0,
    l7_save_opps INTEGER DEFAULT 0,
    l7_saves_converted INTEGER DEFAULT 0,
    l7_blown_saves INTEGER DEFAULT 0,
    l7_save_pct NUMERIC(4,3),
    
    -- Fatigue indicators
    days_since_last_game INTEGER,  -- For the team
    games_last_3_days INTEGER DEFAULT 0,
    games_last_5_days INTEGER DEFAULT 0,
    games_last_7_days INTEGER DEFAULT 0,
    
    -- Workload metrics
    total_bullpen_ip_season NUMERIC(6,1) DEFAULT 0,
    bullpen_starter_ratio NUMERIC(4,2),  -- Bullpen IP / Starter IP
    
    -- Depth score (0-1, higher = deeper/better)
    depth_score NUMERIC(3,2),
    
    -- Fatigue score (0-1, higher = more tired)
    fatigue_score NUMERIC(3,2),
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(team_id, game_pk)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_bullpen_status_team ON features.bullpen_status(team_id);
CREATE INDEX IF NOT EXISTS idx_bullpen_status_game ON features.bullpen_status(game_pk);
CREATE INDEX IF NOT EXISTS idx_bullpen_status_date ON features.bullpen_status(game_date);
CREATE INDEX IF NOT EXISTS idx_bullpen_fatigue ON features.bullpen_status(fatigue_score);
CREATE INDEX IF NOT EXISTS idx_bullpen_depth ON features.bullpen_status(depth_score);

-- Comments
COMMENT ON TABLE features.bullpen_status IS 'Team bullpen status and fatigue for each game';
COMMENT ON COLUMN features.bullpen_status.fatigue_score IS '0-1 score, higher = bullpen is more fatigued';
COMMENT ON COLUMN features.bullpen_status.depth_score IS '0-1 score, higher = deeper/more reliable bullpen';

-- =============================================
-- RELIEVER FATIGUE TRACKING
-- =============================================

CREATE TABLE IF NOT EXISTS features.reliever_fatigue (
    fatigue_id SERIAL PRIMARY KEY,
    player_id INTEGER NOT NULL,
    team_id INTEGER NOT NULL,
    season INTEGER NOT NULL,
    
    -- Date tracking
    as_of_date DATE NOT NULL,
    
    -- Recent workload
    pitches_last_1_day INTEGER DEFAULT 0,
    pitches_last_2_days INTEGER DEFAULT 0,
    pitches_last_3_days INTEGER DEFAULT 0,
    pitches_last_5_days INTEGER DEFAULT 0,
    pitches_last_7_days INTEGER DEFAULT 0,
    
    -- Appearance tracking
    games_last_1_day INTEGER DEFAULT 0,
    games_last_2_days INTEGER DEFAULT 0,
    games_last_3_days INTEGER DEFAULT 0,
    games_last_5_days INTEGER DEFAULT 0,
    games_last_7_days INTEGER DEFAULT 0,
    games_last_14_days INTEGER DEFAULT 0,
    
    -- Innings pitched
    ip_last_3_days NUMERIC(4,1) DEFAULT 0,
    ip_last_7_days NUMERIC(4,1) DEFAULT 0,
    ip_last_14_days NUMERIC(4,1) DEFAULT 0,
    
    -- Fatigue indicators
    back_to_back_days BOOLEAN DEFAULT FALSE,
    three_in_four_days BOOLEAN DEFAULT FALSE,
    four_in_six_days BOOLEAN DEFAULT FALSE,
    
    -- Days since last appearance
    days_rest INTEGER,
    
    -- Fatigue score (0-1, higher = more fatigued)
    fatigue_score NUMERIC(3,2),
    
    -- Availability
    availability_status VARCHAR(20) DEFAULT 'available' 
        CHECK (availability_status IN ('available', 'tired', 'rest', 'injured', 'unavailable')),
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(player_id, as_of_date)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_reliever_fatigue_player ON features.reliever_fatigue(player_id);
CREATE INDEX IF NOT EXISTS idx_reliever_fatigue_date ON features.reliever_fatigue(as_of_date);
CREATE INDEX IF NOT EXISTS idx_reliever_fatigue_team ON features.reliever_fatigue(team_id);
CREATE INDEX IF NOT EXISTS idx_reliever_availability ON features.reliever_fatigue(availability_status);
CREATE INDEX IF NOT EXISTS idx_reliever_score ON features.reliever_fatigue(fatigue_score);

-- Comments
COMMENT ON TABLE features.reliever_fatigue IS 'Individual reliever fatigue tracking';
COMMENT ON COLUMN features.reliever_fatigue.fatigue_score IS 'Calculated from pitches/appearances in recent days';
COMMENT ON COLUMN features.reliever_fatigue.availability_status IS 'Current availability for game';

-- =============================================
-- BULLPEN FEATURES FOR GAMES
-- =============================================

CREATE TABLE IF NOT EXISTS features.bullpen_features (
    feature_id SERIAL PRIMARY KEY,
    game_pk INTEGER NOT NULL,
    season INTEGER NOT NULL,
    
    -- Home team bullpen
    home_team_id INTEGER NOT NULL,
    home_bullpen_fatigue NUMERIC(3,2),
    home_bullpen_depth NUMERIC(3,2),
    home_available_pitchers INTEGER,
    home_rested_pitchers INTEGER,
    home_bullpen_era NUMERIC(5,2),
    home_bullpen_l7_era NUMERIC(5,2),
    home_bullpen_save_pct NUMERIC(4,3),
    
    -- Away team bullpen
    away_team_id INTEGER NOT NULL,
    away_bullpen_fatigue NUMERIC(3,2),
    away_bullpen_depth NUMERIC(3,2),
    away_available_pitchers INTEGER,
    away_rested_pitchers INTEGER,
    away_bullpen_era NUMERIC(5,2),
    away_bullpen_l7_era NUMERIC(5,2),
    away_bullpen_save_pct NUMERIC(4,3),
    
    -- Comparative advantage
    fatigue_advantage VARCHAR(4) CHECK (fatigue_advantage IN ('home', 'away', 'even')),
    depth_advantage VARCHAR(4) CHECK (depth_advantage IN ('home', 'away', 'even')),
    overall_bullpen_advantage VARCHAR(4) CHECK (overall_bullpen_advantage IN ('home', 'away', 'even')),
    
    -- Advantage scores (positive = home advantage, negative = away advantage)
    fatigue_advantage_score NUMERIC(4,2),
    depth_advantage_score NUMERIC(4,2),
    overall_advantage_score NUMERIC(4,2),
    
    -- Late game prediction support
    home_late_inning_strength NUMERIC(3,2),  -- 7-9 inning effectiveness
    away_late_inning_strength NUMERIC(3,2),
    
    -- Metadata
    computed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(game_pk)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_bullpen_features_game ON features.bullpen_features(game_pk);
CREATE INDEX IF NOT EXISTS idx_bullpen_features_home ON features.bullpen_features(home_team_id);
CREATE INDEX IF NOT EXISTS idx_bullpen_features_away ON features.bullpen_features(away_team_id);
CREATE INDEX IF NOT EXISTS idx_bullpen_advantage ON features.bullpen_features(overall_bullpen_advantage);

-- Comments
COMMENT ON TABLE features.bullpen_features IS 'Pre-computed bullpen features for games';
COMMENT ON COLUMN features.bullpen_features.overall_advantage_score IS 'Positive = home bullpen advantage, negative = away';

-- =============================================
-- FUNCTIONS
-- =============================================

-- Function: Calculate reliever fatigue score
CREATE OR REPLACE FUNCTION features.calculate_reliever_fatigue_score(
    p_pitches_1d INTEGER,
    p_pitches_3d INTEGER,
    p_games_3d INTEGER,
    p_back_to_back BOOLEAN,
    p_days_rest INTEGER
) RETURNS NUMERIC(3,2) AS $$
DECLARE
    v_score NUMERIC(3,2) := 0.0;
BEGIN
    -- Pitches yesterday (high impact)
    IF p_pitches_1d > 30 THEN
        v_score := v_score + 0.30;
    ELSIF p_pitches_1d > 15 THEN
        v_score := v_score + 0.20;
    ELSIF p_pitches_1d > 0 THEN
        v_score := v_score + 0.10;
    END IF;
    
    -- Total pitches in last 3 days
    IF p_pitches_3d > 60 THEN
        v_score := v_score + 0.25;
    ELSIF p_pitches_3d > 45 THEN
        v_score := v_score + 0.15;
    END IF;
    
    -- Games in last 3 days
    v_score := v_score + (p_games_3d * 0.10);
    
    -- Back to back days (major fatigue)
    IF p_back_to_back THEN
        v_score := v_score + 0.20;
    END IF;
    
    -- Rest helps (reduce score)
    IF p_days_rest >= 3 THEN
        v_score := GREATEST(0, v_score - 0.30);
    ELSIF p_days_rest >= 2 THEN
        v_score := GREATEST(0, v_score - 0.20);
    ELSIF p_days_rest >= 1 THEN
        v_score := GREATEST(0, v_score - 0.10);
    END IF;
    
    RETURN LEAST(1.0, v_score);
END;
$$ LANGUAGE plpgsql;

-- Function: Determine reliever availability
CREATE OR REPLACE FUNCTION features.get_reliever_availability(
    p_fatigue_score NUMERIC,
    p_back_to_back BOOLEAN,
    p_three_in_four BOOLEAN,
    p_days_rest INTEGER
) RETURNS VARCHAR(20) AS $$
BEGIN
    -- Injured or unavailable not tracked here (need injury data)
    
    -- Rest day required
    IF p_fatigue_score > 0.70 OR p_three_in_four THEN
        RETURN 'rest';
    END IF;
    
    -- Tired but available for emergency
    IF p_fatigue_score > 0.50 OR p_back_to_back THEN
        RETURN 'tired';
    END IF;
    
    -- Fresh and available
    RETURN 'available';
END;
$$ LANGUAGE plpgsql;

-- Function: Calculate team bullpen fatigue
CREATE OR REPLACE FUNCTION features.calculate_team_bullpen_fatigue(
    p_team_id INTEGER,
    p_game_date DATE,
    p_season INTEGER
) RETURNS TABLE (
    avg_fatigue NUMERIC,
    max_fatigue NUMERIC,
    available_count INTEGER,
    tired_count INTEGER,
    rested_count INTEGER
) AS $$
BEGIN
    SELECT 
        AVG(rf.fatigue_score),
        MAX(rf.fatigue_score),
        COUNT(*) FILTER (WHERE rf.availability_status = 'available'),
        COUNT(*) FILTER (WHERE rf.availability_status = 'tired'),
        COUNT(*) FILTER (WHERE rf.availability_status = 'available' AND rf.days_rest >= 2)
    INTO avg_fatigue, max_fatigue, available_count, tired_count, rested_count
    FROM features.reliever_fatigue rf
    WHERE rf.team_id = p_team_id
      AND rf.season = p_season
      AND rf.as_of_date = p_game_date;
    
    RETURN NEXT;
END;
$$ LANGUAGE plpgsql;

-- Function: Populate bullpen features for a game
CREATE OR REPLACE FUNCTION features.populate_game_bullpen_features(
    p_game_pk INTEGER,
    p_season INTEGER,
    p_game_date DATE,
    p_home_team_id INTEGER,
    p_away_team_id INTEGER
) RETURNS INTEGER AS $$
DECLARE
    v_home_fatigue NUMERIC;
    v_home_depth NUMERIC;
    v_away_fatigue NUMERIC;
    v_away_depth NUMERIC;
    v_fatigue_advantage VARCHAR(4);
    v_depth_advantage VARCHAR(4);
    v_overall_advantage VARCHAR(4);
    v_fatigue_score NUMERIC;
    v_depth_score NUMERIC;
    v_overall_score NUMERIC;
BEGIN
    -- Get home team bullpen status
    SELECT bs.fatigue_score, bs.depth_score
    INTO v_home_fatigue, v_home_depth
    FROM features.bullpen_status bs
    WHERE bs.team_id = p_home_team_id 
      AND bs.game_pk = p_game_pk;
    
    -- Get away team bullpen status
    SELECT bs.fatigue_score, bs.depth_score
    INTO v_away_fatigue, v_away_depth
    FROM features.bullpen_status bs
    WHERE bs.team_id = p_away_team_id 
      AND bs.game_pk = p_game_pk;
    
    -- Calculate advantages
    IF v_home_fatigue < v_away_fatigue THEN
        v_fatigue_advantage := 'home';
        v_fatigue_score := (v_away_fatigue - v_home_fatigue);
    ELSIF v_away_fatigue < v_home_fatigue THEN
        v_fatigue_advantage := 'away';
        v_fatigue_score := -(v_home_fatigue - v_away_fatigue);
    ELSE
        v_fatigue_advantage := 'even';
        v_fatigue_score := 0;
    END IF;
    
    IF v_home_depth > v_away_depth THEN
        v_depth_advantage := 'home';
        v_depth_score := (v_home_depth - v_away_depth);
    ELSIF v_away_depth > v_home_depth THEN
        v_depth_advantage := 'away';
        v_depth_score := -(v_away_depth - v_home_depth);
    ELSE
        v_depth_advantage := 'even';
        v_depth_score := 0;
    END IF;
    
    -- Overall (fatigue + depth)
    v_overall_score := v_fatigue_score + v_depth_score;
    IF v_overall_score > 0.1 THEN
        v_overall_advantage := 'home';
    ELSIF v_overall_score < -0.1 THEN
        v_overall_advantage := 'away';
    ELSE
        v_overall_advantage := 'even';
    END IF;
    
    -- Insert/Update
    INSERT INTO features.bullpen_features (
        game_pk, season,
        home_team_id, home_bullpen_fatigue, home_bullpen_depth,
        away_team_id, away_bullpen_fatigue, away_bullpen_depth,
        fatigue_advantage, depth_advantage, overall_bullpen_advantage,
        fatigue_advantage_score, depth_advantage_score, overall_advantage_score
    ) VALUES (
        p_game_pk, p_season,
        p_home_team_id, v_home_fatigue, v_home_depth,
        p_away_team_id, v_away_fatigue, v_away_depth,
        v_fatigue_advantage, v_depth_advantage, v_overall_advantage,
        v_fatigue_score, v_depth_score, v_overall_score
    )
    ON CONFLICT (game_pk) DO UPDATE SET
        home_bullpen_fatigue = EXCLUDED.home_bullpen_fatigue,
        home_bullpen_depth = EXCLUDED.home_bullpen_depth,
        away_bullpen_fatigue = EXCLUDED.away_bullpen_fatigue,
        away_bullpen_depth = EXCLUDED.away_bullpen_depth,
        fatigue_advantage = EXCLUDED.fatigue_advantage,
        depth_advantage = EXCLUDED.depth_advantage,
        overall_bullpen_advantage = EXCLUDED.overall_bullpen_advantage,
        overall_advantage_score = EXCLUDED.overall_advantage_score,
        computed_at = NOW();
    
    RETURN 1;
END;
$$ LANGUAGE plpgsql;

-- =============================================
-- VIEWS
-- =============================================

-- View: Teams with tired bullpens
CREATE OR REPLACE VIEW features.tired_bullpens AS
SELECT 
    team_id,
    season,
    game_pk,
    game_date,
    fatigue_score,
    tired_pitchers,
    available_pitchers,
    l7_bullpen_games,
    games_last_3_days
FROM features.bullpen_status
WHERE fatigue_score > 0.60
ORDER BY fatigue_score DESC;

-- View: Strong bullpens (low ERA, high depth)
CREATE OR REPLACE VIEW features.strong_bullpens AS
SELECT 
    team_id,
    season,
    game_pk,
    game_date,
    bullpen_era,
    depth_score,
    bullpen_k_9,
    l7_save_pct,
    available_pitchers
FROM features.bullpen_status
WHERE bullpen_era < 3.50
  AND depth_score > 0.70
  AND available_pitchers >= 6
ORDER BY bullpen_era ASC;

-- View: Most used relievers (high fatigue risk)
CREATE OR REPLACE VIEW features.high_workload_relievers AS
SELECT 
    player_id,
    team_id,
    season,
    as_of_date,
    games_last_7_days,
    games_last_14_days,
    pitches_last_7_days,
    back_to_back_days,
    fatigue_score,
    availability_status
FROM features.reliever_fatigue
WHERE games_last_7_days >= 5
   OR pitches_last_7_days >= 150
   OR back_to_back_days = TRUE
ORDER BY games_last_7_days DESC, pitches_last_7_days DESC;

-- View: Game bullpen advantage summary
CREATE OR REPLACE VIEW features.game_bullpen_summary AS
SELECT 
    bf.game_pk,
    bf.home_team_id,
    bf.away_team_id,
    bf.home_bullpen_fatigue,
    bf.away_bullpen_fatigue,
    bf.home_bullpen_depth,
    bf.away_bullpen_depth,
    bf.fatigue_advantage,
    bf.depth_advantage,
    bf.overall_bullpen_advantage,
    bf.overall_advantage_score,
    CASE 
        WHEN bf.overall_advantage_score > 0.2 THEN 'Home bullpen advantage'
        WHEN bf.overall_advantage_score < -0.2 THEN 'Away bullpen advantage'
        ELSE 'Bullpens even'
    END as bullpen_narrative
FROM features.bullpen_features bf
WHERE bf.computed_at > NOW() - INTERVAL '24 hours';

-- View: Relievers needing rest
CREATE OR REPLACE VIEW features.relievers_needing_rest AS
SELECT 
    player_id,
    team_id,
    season,
    as_of_date,
    games_last_3_days,
    pitches_last_3_days,
    back_to_back_days,
    three_in_four_days,
    fatigue_score,
    CASE 
        WHEN fatigue_score > 0.70 THEN 'Must rest'
        WHEN fatigue_score > 0.50 THEN 'Avoid using'
        WHEN back_to_back_days THEN 'Monitor closely'
        ELSE 'Available'
    END as recommendation
FROM features.reliever_fatigue
WHERE fatigue_score > 0.50
   OR back_to_back_days = TRUE
   OR three_in_four_days = TRUE
ORDER BY fatigue_score DESC;

COMMENT ON VIEW features.tired_bullpens IS 'Teams with fatigued bullpens (fatigue_score > 0.60)';
COMMENT ON VIEW features.strong_bullpens IS 'Teams with strong, well-rested bullpens';
COMMENT ON VIEW features.high_workload_relievers IS 'Relievers with heavy recent workloads';
COMMENT ON VIEW features.game_bullpen_summary IS 'Bullpen comparison for recent games';
COMMENT ON VIEW features.relievers_needing_rest IS 'Relievers who should rest based on workload';
