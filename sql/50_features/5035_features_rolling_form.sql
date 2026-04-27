/*
File: sql/503_features_rolling_form.sql
Purpose: Rolling form features - recent performance metrics
Author: Agent cbwinslow/retrosheet
Date: 2026-04-26
Depends On: raw_gumbo.plays, features.player_ids
Called By: scripts/features/build_rolling_form_features.sh

Tables Created:
- features.batter_rolling_form: Recent batter performance
- features.pitcher_rolling_form: Recent pitcher performance
- features.rolling_form_features: Current form at game time
*/

-- Ensure features schema exists
CREATE SCHEMA IF NOT EXISTS features;

-- =============================================
-- BATTER ROLLING FORM TABLE
-- =============================================

CREATE TABLE IF NOT EXISTS features.batter_rolling_form (
    form_id SERIAL PRIMARY KEY,
    player_id INTEGER NOT NULL,
    season INTEGER NOT NULL,
    
    -- As of date (calculated up to this date)
    as_of_date DATE NOT NULL,
    
    -- Last 7 days
    l7_games INTEGER DEFAULT 0,
    l7_pa INTEGER DEFAULT 0,
    l7_avg NUMERIC(4,3),
    l7_obp NUMERIC(4,3),
    l7_slg NUMERIC(4,3),
    l7_ops NUMERIC(4,3),
    l7_iso NUMERIC(4,3),
    l7_hr INTEGER DEFAULT 0,
    l7_bb INTEGER DEFAULT 0,
    l7_so INTEGER DEFAULT 0,
    l7_hard_hit_rate NUMERIC(4,3),  -- If Statcast available
    
    -- Last 14 days
    l14_games INTEGER DEFAULT 0,
    l14_pa INTEGER DEFAULT 0,
    l14_avg NUMERIC(4,3),
    l14_obp NUMERIC(4,3),
    l14_slg NUMERIC(4,3),
    l14_ops NUMERIC(4,3),
    l14_iso NUMERIC(4,3),
    l14_hr INTEGER DEFAULT 0,
    l14_bb INTEGER DEFAULT 0,
    l14_so INTEGER DEFAULT 0,
    
    -- Last 30 days
    l30_games INTEGER DEFAULT 0,
    l30_pa INTEGER DEFAULT 0,
    l30_avg NUMERIC(4,3),
    l30_obp NUMERIC(4,3),
    l30_slg NUMERIC(4,3),
    l30_ops NUMERIC(4,3),
    l30_iso NUMERIC(4,3),
    l30_hr INTEGER DEFAULT 0,
    l30_bb INTEGER DEFAULT 0,
    l30_so INTEGER DEFAULT 0,
    l30_k_rate NUMERIC(4,3),
    l30_bb_rate NUMERIC(4,3),
    
    -- Hot/Cold indicators (vs season average)
    l7_hot_cold NUMERIC(4,3),  -- Positive = hot
    l14_hot_cold NUMERIC(4,3),
    l30_hot_cold NUMERIC(4,3),
    
    -- Trend direction (improving/declining)
    trend_direction VARCHAR(10) CHECK (trend_direction IN ('improving', 'declining', 'stable', 'unknown')),
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(player_id, season, as_of_date)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_batter_rolling_player ON features.batter_rolling_form(player_id);
CREATE INDEX IF NOT EXISTS idx_batter_rolling_date ON features.batter_rolling_form(as_of_date);
CREATE INDEX IF NOT EXISTS idx_batter_rolling_l7 ON features.batter_rolling_form(l7_pa) WHERE l7_pa > 0;
CREATE INDEX IF NOT EXISTS idx_batter_rolling_trend ON features.batter_rolling_form(trend_direction);

-- Comments
COMMENT ON TABLE features.batter_rolling_form IS 'Rolling performance metrics for batters (7/14/30 day windows)';
COMMENT ON COLUMN features.batter_rolling_form.l7_hot_cold IS 'OPS difference from season average (positive = hot)';
COMMENT ON COLUMN features.batter_rolling_form.trend_direction IS 'Performance trend based on 7 vs 30 day comparison';

-- =============================================
-- PITCHER ROLLING FORM TABLE
-- =============================================

CREATE TABLE IF NOT EXISTS features.pitcher_rolling_form (
    form_id SERIAL PRIMARY KEY,
    player_id INTEGER NOT NULL,
    season INTEGER NOT NULL,
    
    -- As of date
    as_of_date DATE NOT NULL,
    
    -- Last 7 days
    l7_games INTEGER DEFAULT 0,
    l7_ip NUMERIC(4,1) DEFAULT 0,
    l7_era NUMERIC(5,2),
    l7_whip NUMERIC(4,2),
    l7_k_9 NUMERIC(4,1),
    l7_bb_9 NUMERIC(4,1),
    l7_k_bb_ratio NUMERIC(4,2),
    l7_hr_9 NUMERIC(4,2),
    l7_babip NUMERIC(4,3),
    l7_hits INTEGER DEFAULT 0,
    l7_bb INTEGER DEFAULT 0,
    l7_so INTEGER DEFAULT 0,
    l7_hr INTEGER DEFAULT 0,
    
    -- Last 14 days
    l14_games INTEGER DEFAULT 0,
    l14_ip NUMERIC(4,1) DEFAULT 0,
    l14_era NUMERIC(5,2),
    l14_whip NUMERIC(4,2),
    l14_k_9 NUMERIC(4,1),
    l14_bb_9 NUMERIC(4,1),
    
    -- Last 30 days
    l30_games INTEGER DEFAULT 0,
    l30_ip NUMERIC(4,1) DEFAULT 0,
    l30_era NUMERIC(5,2),
    l30_whip NUMERIC(4,2),
    l30_k_9 NUMERIC(4,1),
    l30_bb_9 NUMERIC(4,1),
    l30_k_bb_ratio NUMERIC(4,2),
    l30_hr_9 NUMERIC(4,2),
    l30_babip NUMERIC(4,3),
    l30_fip NUMERIC(5,2),  -- Fielding Independent Pitching
    l30_siera NUMERIC(5,2), -- Skill-Interactive ERA (if available)
    
    -- Pitch type distribution (last 30 days)
    l30_fastball_pct NUMERIC(4,3),
    l30_breaking_pct NUMERIC(4,3),
    l30_offspeed_pct NUMERIC(4,3),
    
    -- Velocity trends
    l30_avg_velocity NUMERIC(4,1),
    velocity_trend VARCHAR(10) CHECK (velocity_trend IN ('increasing', 'decreasing', 'stable', 'unknown')),
    
    -- Hot/Cold indicators
    l7_hot_cold NUMERIC(4,2),  -- ERA difference (negative = good, pitcher)
    l14_hot_cold NUMERIC(4,2),
    l30_hot_cold NUMERIC(4,2),
    
    -- Consistency score (lower = more consistent)
    consistency_score NUMERIC(4,3),
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(player_id, season, as_of_date)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_pitcher_rolling_player ON features.pitcher_rolling_form(player_id);
CREATE INDEX IF NOT EXISTS idx_pitcher_rolling_date ON features.pitcher_rolling_form(as_of_date);
CREATE INDEX IF NOT EXISTS idx_pitcher_rolling_l7 ON features.pitcher_rolling_form(l7_ip) WHERE l7_ip > 0;
CREATE INDEX IF NOT EXISTS idx_pitcher_rolling_era ON features.pitcher_rolling_form(l30_era);

-- Comments
COMMENT ON TABLE features.pitcher_rolling_form IS 'Rolling performance metrics for pitchers (7/14/30 day windows)';
COMMENT ON COLUMN features.pitcher_rolling_form.l7_hot_cold IS 'ERA difference from season average (negative = good for pitcher)';
COMMENT ON COLUMN features.pitcher_rolling_form.consistency_score IS 'Standard deviation of game scores (lower = more consistent)';

-- =============================================
-- CURRENT FORM FEATURES (For Live Games)
-- =============================================

CREATE TABLE IF NOT EXISTS features.rolling_form_features (
    feature_id SERIAL PRIMARY KEY,
    game_pk INTEGER NOT NULL,
    season INTEGER NOT NULL,
    
    -- Batter form
    batter_id INTEGER NOT NULL,
    batter_l7_ops NUMERIC(4,3),
    batter_l14_ops NUMERIC(4,3),
    batter_l30_ops NUMERIC(4,3),
    batter_trend VARCHAR(10),
    batter_is_hot BOOLEAN DEFAULT FALSE,
    batter_is_cold BOOLEAN DEFAULT FALSE,
    batter_l7_pa INTEGER DEFAULT 0,
    batter_l30_pa INTEGER DEFAULT 0,
    
    -- Pitcher form
    pitcher_id INTEGER NOT NULL,
    pitcher_l7_era NUMERIC(5,2),
    pitcher_l14_era NUMERIC(5,2),
    pitcher_l30_era NUMERIC(5,2),
    pitcher_l7_whip NUMERIC(4,2),
    pitcher_l30_whip NUMERIC(4,2),
    pitcher_l30_k_9 NUMERIC(4,1),
    pitcher_l30_bb_9 NUMERIC(4,1),
    pitcher_trend VARCHAR(10),
    pitcher_is_hot BOOLEAN DEFAULT FALSE,
    pitcher_is_cold BOOLEAN DEFAULT FALSE,
    pitcher_l7_ip NUMERIC(4,1) DEFAULT 0,
    pitcher_l30_ip NUMERIC(4,1) DEFAULT 0,
    
    -- Form advantage (who has momentum)
    form_advantage VARCHAR(10) CHECK (form_advantage IN ('batter', 'pitcher', 'neutral')),
    form_score NUMERIC(3,2),  -- 0-1, higher = advantage to batter
    
    -- Metadata
    computed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(game_pk, batter_id, pitcher_id)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_form_features_game ON features.rolling_form_features(game_pk);
CREATE INDEX IF NOT EXISTS idx_form_features_batter ON features.rolling_form_features(batter_id);
CREATE INDEX IF NOT EXISTS idx_form_features_pitcher ON features.rolling_form_features(pitcher_id);
CREATE INDEX IF NOT EXISTS idx_form_features_advantage ON features.rolling_form_features(form_advantage);

-- Comments
COMMENT ON TABLE features.rolling_form_features IS 'Pre-computed rolling form features for game matchups';
COMMENT ON COLUMN features.rolling_form_features.form_advantage IS 'Which player has better recent form';
COMMENT ON COLUMN features.rolling_form_features.form_score IS 'Composite 0-1 score (higher = better for batter)';

-- =============================================
-- FUNCTIONS
-- =============================================

-- Function: Calculate batter rolling form
CREATE OR REPLACE FUNCTION features.calculate_batter_rolling_form(
    p_player_id INTEGER,
    p_season INTEGER,
    p_as_of_date DATE
) RETURNS TABLE (
    l7_ops NUMERIC,
    l14_ops NUMERIC,
    l30_ops NUMERIC,
    trend VARCHAR(10)
) AS $$
BEGIN
    SELECT 
        brf.l7_ops,
        brf.l14_ops,
        brf.l30_ops,
        brf.trend_direction
    INTO l7_ops, l14_ops, l30_ops, trend
    FROM features.batter_rolling_form brf
    WHERE brf.player_id = p_player_id
      AND brf.season = p_season
      AND brf.as_of_date <= p_as_of_date
    ORDER BY brf.as_of_date DESC
    LIMIT 1;
    
    RETURN NEXT;
END;
$$ LANGUAGE plpgsql;

-- Function: Calculate pitcher rolling form
CREATE OR REPLACE FUNCTION features.calculate_pitcher_rolling_form(
    p_player_id INTEGER,
    p_season INTEGER,
    p_as_of_date DATE
) RETURNS TABLE (
    l7_era NUMERIC,
    l14_era NUMERIC,
    l30_era NUMERIC,
    l30_k_9 NUMERIC,
    trend VARCHAR(10)
) AS $$
BEGIN
    SELECT 
        prf.l7_era,
        prf.l14_era,
        prf.l30_era,
        prf.l30_k_9,
        prf.trend_direction
    INTO l7_era, l14_era, l30_era, l30_k_9, trend
    FROM features.pitcher_rolling_form prf
    WHERE prf.player_id = p_player_id
      AND prf.season = p_season
      AND prf.as_of_date <= p_as_of_date
    ORDER BY prf.as_of_date DESC
    LIMIT 1;
    
    RETURN NEXT;
END;
$$ LANGUAGE plpgsql;

-- Function: Determine form advantage
CREATE OR REPLACE FUNCTION features.calculate_form_advantage(
    p_batter_id INTEGER,
    p_pitcher_id INTEGER,
    p_season INTEGER,
    p_as_of_date DATE
) RETURNS TABLE (
    advantage VARCHAR(10),
    form_score NUMERIC,
    batter_hot BOOLEAN,
    pitcher_hot BOOLEAN
) AS $$
DECLARE
    v_batter_ops NUMERIC;
    v_pitcher_era NUMERIC;
    v_season_avg_ops NUMERIC := 0.720;  -- League average
    v_season_avg_era NUMERIC := 4.20;     -- League average
BEGIN
    -- Get batter L14 OPS
    SELECT l14_ops INTO v_batter_ops
    FROM features.batter_rolling_form
    WHERE player_id = p_batter_id 
      AND season = p_season
      AND as_of_date <= p_as_of_date
    ORDER BY as_of_date DESC
    LIMIT 1;
    
    -- Get pitcher L14 ERA
    SELECT l14_era INTO v_pitcher_era
    FROM features.pitcher_rolling_form
    WHERE player_id = p_pitcher_id 
      AND season = p_season
      AND as_of_date <= p_as_of_date
    ORDER BY as_of_date DESC
    LIMIT 1;
    
    -- Determine hot/cold
    batter_hot := (v_batter_ops > v_season_avg_ops + 0.100);
    pitcher_hot := (v_pitcher_era < v_season_avg_era - 0.50);
    
    -- Calculate advantage
    IF batter_hot AND NOT pitcher_hot THEN
        advantage := 'batter';
        form_score := 0.7;
    ELSIF pitcher_hot AND NOT batter_hot THEN
        advantage := 'pitcher';
        form_score := 0.3;
    ELSIF batter_hot AND pitcher_hot THEN
        advantage := 'neutral';
        form_score := 0.5;
    ELSE
        advantage := 'neutral';
        form_score := 0.5;
    END IF;
    
    RETURN NEXT;
END;
$$ LANGUAGE plpgsql;

-- Function: Populate form features for a game
CREATE OR REPLACE FUNCTION features.populate_game_form_features(
    p_game_pk INTEGER,
    p_season INTEGER,
    p_game_date DATE
) RETURNS INTEGER AS $$
DECLARE
    v_count INTEGER := 0;
BEGIN
    INSERT INTO features.rolling_form_features (
        game_pk, season,
        batter_id, pitcher_id,
        batter_l7_ops, batter_l14_ops, batter_l30_ops,
        batter_trend, batter_is_hot, batter_is_cold,
        batter_l7_pa, batter_l30_pa,
        pitcher_l7_era, pitcher_l14_era, pitcher_l30_era,
        pitcher_l7_whip, pitcher_l30_whip,
        pitcher_l30_k_9, pitcher_l30_bb_9,
        pitcher_trend, pitcher_is_hot, pitcher_is_cold,
        pitcher_l7_ip, pitcher_l30_ip,
        form_advantage, form_score
    )
    SELECT 
        p_game_pk,
        p_season,
        p.batter_id,
        p.pitcher_id,
        brf.l7_ops,
        brf.l14_ops,
        brf.l30_ops,
        brf.trend_direction,
        brf.l14_ops > 0.850,  -- Hot threshold
        brf.l14_ops < 0.600,  -- Cold threshold
        brf.l7_pa,
        brf.l30_pa,
        prf.l7_era,
        prf.l14_era,
        prf.l30_era,
        prf.l7_whip,
        prf.l30_whip,
        prf.l30_k_9,
        prf.l30_bb_9,
        prf.trend_direction,
        prf.l14_era < 3.00,   -- Hot pitcher
        prf.l14_era > 5.00,   -- Cold pitcher
        prf.l7_ip,
        prf.l30_ip,
        CASE 
            WHEN (brf.l14_ops > 0.850 AND prf.l14_era > 4.50) THEN 'batter'
            WHEN (prf.l14_era < 3.00 AND brf.l14_ops < 0.700) THEN 'pitcher'
            ELSE 'neutral'
        END,
        CASE 
            WHEN (brf.l14_ops > 0.850 AND prf.l14_era > 4.50) THEN 0.7
            WHEN (prf.l14_era < 3.00 AND brf.l14_ops < 0.700) THEN 0.3
            ELSE 0.5
        END
    FROM raw_gumbo.plays p
    LEFT JOIN features.batter_rolling_form brf 
        ON brf.player_id = p.batter_id 
        AND brf.season = p_season
        AND brf.as_of_date = p_game_date
    LEFT JOIN features.pitcher_rolling_form prf 
        ON prf.player_id = p.pitcher_id 
        AND prf.season = p_season
        AND prf.as_of_date = p_game_date
    WHERE p.game_pk = p_game_pk
      AND p.season = p_season
    ON CONFLICT (game_pk, batter_id, pitcher_id) DO UPDATE SET
        batter_l7_ops = EXCLUDED.batter_l7_ops,
        batter_l14_ops = EXCLUDED.batter_l14_ops,
        pitcher_l7_era = EXCLUDED.pitcher_l7_era,
        pitcher_l14_era = EXCLUDED.pitcher_l14_era,
        form_advantage = EXCLUDED.form_advantage,
        form_score = EXCLUDED.form_score,
        computed_at = NOW();
    
    GET DIAGNOSTICS v_count = ROW_COUNT;
    RETURN v_count;
END;
$$ LANGUAGE plpgsql;

-- =============================================
-- VIEWS
-- =============================================

-- View: Hot batters (L14)
CREATE OR REPLACE VIEW features.hot_batters AS
SELECT 
    player_id,
    season,
    as_of_date,
    l14_games,
    l14_pa,
    l14_ops,
    l14_hot_cold,
    trend_direction
FROM features.batter_rolling_form
WHERE l14_pa >= 20
  AND l14_ops > 0.900
  AND trend_direction IN ('improving', 'stable')
ORDER BY l14_ops DESC;

-- View: Cold batters (L14)
CREATE OR REPLACE VIEW features.cold_batters AS
SELECT 
    player_id,
    season,
    as_of_date,
    l14_games,
    l14_pa,
    l14_ops,
    l14_hot_cold,
    trend_direction
FROM features.batter_rolling_form
WHERE l14_pa >= 20
  AND l14_ops < 0.600
ORDER BY l14_ops ASC;

-- View: Hot pitchers (L14)
CREATE OR REPLACE VIEW features.hot_pitchers AS
SELECT 
    player_id,
    season,
    as_of_date,
    l14_games,
    l14_ip,
    l14_era,
    l14_whip,
    l14_k_9,
    l14_hot_cold,
    trend_direction
FROM features.pitcher_rolling_form
WHERE l14_ip >= 10
  AND l14_era < 2.50
  AND trend_direction IN ('improving', 'stable')
ORDER BY l14_era ASC;

-- View: Cold pitchers (L14)
CREATE OR REPLACE VIEW features.cold_pitchers AS
SELECT 
    player_id,
    season,
    as_of_date,
    l14_games,
    l14_ip,
    l14_era,
    l14_whip,
    l14_hot_cold,
    trend_direction
FROM features.pitcher_rolling_form
WHERE l14_ip >= 10
  AND l14_era > 6.00
ORDER BY l14_era DESC;

-- View: Current game form summary
CREATE OR REPLACE VIEW features.current_game_form AS
SELECT 
    rf.game_pk,
    rf.batter_id,
    rf.pitcher_id,
    rf.batter_l14_ops,
    rf.batter_is_hot,
    rf.pitcher_l14_era,
    rf.pitcher_is_hot,
    rf.form_advantage,
    rf.form_score,
    CASE 
        WHEN rf.batter_is_hot AND rf.pitcher_is_hot THEN 'Fire vs Fire'
        WHEN rf.batter_is_hot AND rf.pitcher_is_cold THEN 'Batter advantage'
        WHEN rf.batter_is_cold AND rf.pitcher_is_hot THEN 'Pitcher advantage'
        WHEN rf.batter_is_cold AND rf.pitcher_is_cold THEN 'Cold matchup'
        ELSE 'Normal matchup'
    END as matchup_narrative
FROM features.rolling_form_features rf
WHERE rf.computed_at > NOW() - INTERVAL '24 hours';

COMMENT ON VIEW features.hot_batters IS 'Batters with OPS > 0.900 over last 14 days (min 20 PA)';
COMMENT ON VIEW features.cold_batters IS 'Batters with OPS < 0.600 over last 14 days (min 20 PA)';
COMMENT ON VIEW features.hot_pitchers IS 'Pitchers with ERA < 2.50 over last 14 days (min 10 IP)';
COMMENT ON VIEW features.cold_pitchers IS 'Pitchers with ERA > 6.00 over last 14 days (min 10 IP)';
COMMENT ON VIEW features.current_game_form IS 'Form features for recent games with narrative';
