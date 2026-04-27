/*
File: sql/502_features_matchup.sql
Purpose: Matchup features for batter vs pitcher predictions
Author: Agent cbwinslow/retrosheet
Date: 2026-04-26
Depends On: raw_gumbo.plays, features.player_ids
Called By: scripts/features/build_matchup_features.sh

Tables Created:
- features.batter_vs_pitcher_matchups: H2H history
- features.platoon_splits: Lefty/righty performance
- features.matchup_features: Current game matchup features
*/

-- Ensure features schema exists
CREATE SCHEMA IF NOT EXISTS features;

-- =============================================
-- MATCHUP HISTORY TABLE
-- =============================================

CREATE TABLE IF NOT EXISTS features.batter_vs_pitcher_matchups (
    matchup_id SERIAL PRIMARY KEY,
    batter_id INTEGER NOT NULL,
    pitcher_id INTEGER NOT NULL,
    season INTEGER NOT NULL,
    
    -- Career totals vs this pitcher
    career_pa INTEGER DEFAULT 0,
    career_ab INTEGER DEFAULT 0,
    career_h INTEGER DEFAULT 0,
    career_2b INTEGER DEFAULT 0,
    career_3b INTEGER DEFAULT 0,
    career_hr INTEGER DEFAULT 0,
    career_bb INTEGER DEFAULT 0,
    career_so INTEGER DEFAULT 0,
    career_rbi INTEGER DEFAULT 0,
    
    -- Career calculated stats
    career_avg NUMERIC(4,3) GENERATED ALWAYS AS (
        CASE WHEN career_ab > 0 THEN career_h::NUMERIC / career_ab ELSE 0 END
    ) STORED,
    career_obp NUMERIC(4,3) GENERATED ALWAYS AS (
        CASE WHEN (career_ab + career_bb) > 0 
            THEN (career_h + career_bb)::NUMERIC / (career_ab + career_bb) 
            ELSE 0 END
    ) STORED,
    career_slg NUMERIC(4,3) GENERATED ALWAYS AS (
        CASE WHEN career_ab > 0 
            THEN (career_h + career_2b + 2*career_3b + 3*career_hr)::NUMERIC / career_ab 
            ELSE 0 END
    ) STORED,
    career_ops NUMERIC(4,3) GENERATED ALWAYS AS (
        career_obp + career_slg
    ) STORED,
    
    -- Recent matchups (last 2 seasons)
    recent_pa INTEGER DEFAULT 0,
    recent_avg NUMERIC(4,3),
    recent_hr INTEGER DEFAULT 0,
    
    -- First matchup date
    first_matchup_date DATE,
    last_matchup_date DATE,
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Unique constraint
    UNIQUE(batter_id, pitcher_id, season)
);

-- Indexes for matchup lookups
CREATE INDEX IF NOT EXISTS idx_matchups_batter ON features.batter_vs_pitcher_matchups(batter_id);
CREATE INDEX IF NOT EXISTS idx_matchups_pitcher ON features.batter_vs_pitcher_matchups(pitcher_id);
CREATE INDEX IF NOT EXISTS idx_matchups_season ON features.batter_vs_pitcher_matchups(season);
CREATE INDEX IF NOT EXISTS idx_matchups_career_pa ON features.batter_vs_pitcher_matchups(career_pa) WHERE career_pa > 0;

-- Comments
COMMENT ON TABLE features.batter_vs_pitcher_matchups IS 'Batter vs pitcher head-to-head statistics by season';
COMMENT ON COLUMN features.batter_vs_pitcher_matchups.career_pa IS 'Career plate appearances vs this pitcher';
COMMENT ON COLUMN features.batter_vs_pitcher_matchups.recent_pa IS 'Plate appearances in last 2 seasons';

-- =============================================
-- PLATOON SPLITS TABLE
-- =============================================

CREATE TABLE IF NOT EXISTS features.platoon_splits (
    split_id SERIAL PRIMARY KEY,
    player_id INTEGER NOT NULL,
    player_type VARCHAR(10) NOT NULL CHECK (player_type IN ('batter', 'pitcher')),
    season INTEGER NOT NULL,
    
    -- Handedness
    throws VARCHAR(1),  -- For pitchers: L/R
    bats VARCHAR(1),    -- For batters: L/R/S
    
    -- vs Left-handed
    vs_l_pa INTEGER DEFAULT 0,
    vs_l_avg NUMERIC(4,3),
    vs_l_obp NUMERIC(4,3),
    vs_l_slg NUMERIC(4,3),
    vs_l_ops NUMERIC(4,3),
    vs_l_iso NUMERIC(4,3),
    vs_l_bb_rate NUMERIC(4,3),
    vs_l_so_rate NUMERIC(4,3),
    vs_l_babip NUMERIC(4,3),
    
    -- vs Right-handed
    vs_r_pa INTEGER DEFAULT 0,
    vs_r_avg NUMERIC(4,3),
    vs_r_obp NUMERIC(4,3),
    vs_r_slg NUMERIC(4,3),
    vs_r_ops NUMERIC(4,3),
    vs_r_iso NUMERIC(4,3),
    vs_r_bb_rate NUMERIC(4,3),
    vs_r_so_rate NUMERIC(4,3),
    vs_r_babip NUMERIC(4,3),
    
    -- Platoon advantage (for batters: OPS vs L - OPS vs R)
    -- For lefty batters, positive = good vs RHP
    platoon_advantage NUMERIC(4,3),
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(player_id, player_type, season)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_platoon_player ON features.platoon_splits(player_id);
CREATE INDEX IF NOT EXISTS idx_platoon_season ON features.platoon_splits(season);
CREATE INDEX IF NOT EXISTS idx_platoon_advantage ON features.platoon_splits(platoon_advantage);

-- Comments
COMMENT ON TABLE features.platoon_splits IS 'Platoon splits for batters and pitchers (vs LHP/RHP)';
COMMENT ON COLUMN features.platoon_splits.platoon_advantage IS 'OPS difference indicating platoon strength (batters: positive = better vs RHP)';

-- =============================================
-- CURRENT MATCHUP FEATURES (Live Games)
-- =============================================

CREATE TABLE IF NOT EXISTS features.matchup_features (
    feature_id SERIAL PRIMARY KEY,
    game_pk INTEGER NOT NULL,
    at_bat_index INTEGER NOT NULL,
    season INTEGER NOT NULL,
    
    -- Players
    batter_id INTEGER NOT NULL,
    pitcher_id INTEGER NOT NULL,
    
    -- Career matchup history
    career_matchup_pa INTEGER DEFAULT 0,
    career_matchup_avg NUMERIC(4,3),
    career_matchup_ops NUMERIC(4,3),
    career_matchup_hr INTEGER DEFAULT 0,
    has_matchup_history BOOLEAN DEFAULT FALSE,
    
    -- Recent matchup (last 30 days)
    recent_matchup_pa INTEGER DEFAULT 0,
    recent_matchup_success BOOLEAN,  -- Got a hit or BB
    
    -- Platoon context
    batter_handedness VARCHAR(1),
    pitcher_throws VARCHAR(1),
    is_platoon_advantage BOOLEAN,  -- LHB vs RHP or RHB vs LHP
    
    -- Batter platoon performance
    batter_season_vs_hand_pa INTEGER,
    batter_season_vs_hand_avg NUMERIC(4,3),
    batter_season_vs_hand_ops NUMERIC(4,3),
    
    -- Pitcher platoon performance
    pitcher_season_vs_hand_pa INTEGER,
    pitcher_season_vs_hand_avg NUMERIC(4,3),
    pitcher_season_vs_hand_ops NUMERIC(4,3),
    
    -- Combined matchup score (0-1, higher = better for batter)
    matchup_score NUMERIC(3,2),
    
    -- Metadata
    computed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(game_pk, at_bat_index)
);

-- Indexes for live lookups
CREATE INDEX IF NOT EXISTS idx_matchup_features_game ON features.matchup_features(game_pk);
CREATE INDEX IF NOT EXISTS idx_matchup_features_batter ON features.matchup_features(batter_id);
CREATE INDEX IF NOT EXISTS idx_matchup_features_pitcher ON features.matchup_features(pitcher_id);
CREATE INDEX IF NOT EXISTS idx_matchup_features_score ON features.matchup_features(matchup_score);

-- Comments
COMMENT ON TABLE features.matchup_features IS 'Pre-computed matchup features for each plate appearance';
COMMENT ON COLUMN features.matchup_features.matchup_score IS 'Composite score (0-1) favoring batter based on platoon/history';

-- =============================================
-- FUNCTIONS
-- =============================================

-- Function: Get or compute matchup features
CREATE OR REPLACE FUNCTION features.get_matchup_features(
    p_game_pk INTEGER,
    p_at_bat_index INTEGER,
    p_batter_id INTEGER,
    p_pitcher_id INTEGER,
    p_season INTEGER
) RETURNS TABLE (
    career_pa INTEGER,
    career_avg NUMERIC,
    is_platoon_advantage BOOLEAN,
    matchup_score NUMERIC
) AS $$
BEGIN
    -- First check if already computed
    SELECT mf.career_matchup_pa, mf.career_matchup_avg, 
           mf.is_platoon_advantage, mf.matchup_score
    INTO career_pa, career_avg, is_platoon_advantage, matchup_score
    FROM features.matchup_features mf
    WHERE mf.game_pk = p_game_pk 
      AND mf.at_bat_index = p_at_bat_index;
    
    -- If not found, compute on the fly
    IF NOT FOUND THEN
        SELECT 
            COALESCE(bvpm.career_pa, 0),
            COALESCE(bvpm.career_avg, 0),
            -- Platoon advantage: LHB vs RHP or RHB vs LHP
            CASE 
                WHEN (bats.bats = 'L' AND throws.throws = 'R') OR 
                     (bats.bats = 'R' AND throws.throws = 'L') 
                THEN TRUE
                ELSE FALSE
            END,
            -- Simple matchup score
            CASE 
                WHEN bvpm.career_pa >= 10 THEN 
                    LEAST(1.0, GREATEST(0.0, 0.3 + (bvpm.career_avg - 0.250) * 2))
                ELSE 0.5  -- Unknown matchup
            END
        INTO career_pa, career_avg, is_platoon_advantage, matchup_score
        FROM features.batter_vs_pitcher_matchups bvpm
        LEFT JOIN (
            SELECT DISTINCT player_id, bats 
            FROM features.platoon_splits 
            WHERE player_type = 'batter'
        ) bats ON bats.player_id = p_batter_id
        LEFT JOIN (
            SELECT DISTINCT player_id, throws 
            FROM features.platoon_splits 
            WHERE player_type = 'pitcher'
        ) throws ON throws.player_id = p_pitcher_id
        WHERE bvpm.batter_id = p_batter_id 
          AND bvpm.pitcher_id = p_pitcher_id
          AND bvpm.season = p_season;
        
        IF NOT FOUND THEN
            career_pa := 0;
            career_avg := 0;
            is_platoon_advantage := NULL;
            matchup_score := 0.5;
        END IF;
    END IF;
    
    RETURN NEXT;
END;
$$ LANGUAGE plpgsql;

-- Function: Calculate platoon advantage
CREATE OR REPLACE FUNCTION features.calculate_platoon_advantage(
    p_batter_id INTEGER,
    p_pitcher_id INTEGER
) RETURNS BOOLEAN AS $$
DECLARE
    v_batter_handedness VARCHAR(1);
    v_pitcher_throws VARCHAR(1);
BEGIN
    -- Get batter handedness
    SELECT bats INTO v_batter_handedness
    FROM features.platoon_splits
    WHERE player_id = p_batter_id 
      AND player_type = 'batter'
    ORDER BY season DESC
    LIMIT 1;
    
    -- Get pitcher throwing hand
    SELECT throws INTO v_pitcher_throws
    FROM features.platoon_splits
    WHERE player_id = p_pitcher_id 
      AND player_type = 'pitcher'
    ORDER BY season DESC
    LIMIT 1;
    
    -- Switch hitters: assume they take advantage
    IF v_batter_handedness = 'S' THEN
        RETURN TRUE;
    END IF;
    
    -- LHB vs RHP = advantage, RHB vs LHP = advantage
    RETURN (v_batter_handedness = 'L' AND v_pitcher_throws = 'R') OR
           (v_batter_handedness = 'R' AND v_pitcher_throws = 'L');
END;
$$ LANGUAGE plpgsql;

-- Function: Populate matchup features for a game
CREATE OR REPLACE FUNCTION features.populate_game_matchups(
    p_game_pk INTEGER,
    p_season INTEGER
) RETURNS INTEGER AS $$
DECLARE
    v_count INTEGER := 0;
BEGIN
    INSERT INTO features.matchup_features (
        game_pk, at_bat_index, season,
        batter_id, pitcher_id,
        career_matchup_pa, career_matchup_avg, career_matchup_ops,
        has_matchup_history,
        batter_handedness, pitcher_throws,
        is_platoon_advantage,
        matchup_score
    )
    SELECT 
        p.game_pk,
        p.at_bat_index,
        p.season,
        p.batter_id,
        p.pitcher_id,
        COALESCE(bvpm.career_pa, 0),
        COALESCE(bvpm.career_avg, 0),
        COALESCE(bvpm.career_ops, 0),
        bvpm.career_pa > 0,
        bats.bats,
        throws.throws,
        features.calculate_platoon_advantage(p.batter_id, p.pitcher_id),
        CASE 
            WHEN bvpm.career_pa >= 10 THEN 
                LEAST(1.0, GREATEST(0.0, 0.3 + (bvpm.career_avg - 0.250) * 2))
            ELSE 0.5
        END
    FROM raw_gumbo.plays p
    LEFT JOIN features.batter_vs_pitcher_matchups bvpm 
        ON bvpm.batter_id = p.batter_id 
        AND bvpm.pitcher_id = p.pitcher_id 
        AND bvpm.season = p.season
    LEFT JOIN (
        SELECT DISTINCT player_id, bats 
        FROM features.platoon_splits 
        WHERE player_type = 'batter'
    ) bats ON bats.player_id = p.batter_id
    LEFT JOIN (
        SELECT DISTINCT player_id, throws 
        FROM features.platoon_splits 
        WHERE player_type = 'pitcher'
    ) throws ON throws.player_id = p.pitcher_id
    WHERE p.game_pk = p_game_pk
      AND p.season = p_season
    ON CONFLICT (game_pk, at_bat_index) DO UPDATE SET
        career_matchup_pa = EXCLUDED.career_matchup_pa,
        career_matchup_avg = EXCLUDED.career_matchup_avg,
        matchup_score = EXCLUDED.matchup_score,
        computed_at = NOW();
    
    GET DIAGNOSTICS v_count = ROW_COUNT;
    RETURN v_count;
END;
$$ LANGUAGE plpgsql;

-- =============================================
-- VIEWS
-- =============================================

-- View: Career matchup leaders
CREATE OR REPLACE VIEW features.career_matchup_leaders AS
SELECT 
    batter_id,
    pitcher_id,
    SUM(career_pa) as total_pa,
    ROUND(SUM(career_h)::NUMERIC / NULLIF(SUM(career_ab), 0), 3) as career_avg,
    ROUND(SUM(career_h + 2*career_2b + 3*career_3b + 4*career_hr)::NUMERIC / NULLIF(SUM(career_ab), 0), 3) as career_slg,
    SUM(career_hr) as total_hr,
    MAX(last_matchup_date) as last_met
FROM features.batter_vs_pitcher_matchups
WHERE career_pa >= 20
GROUP BY batter_id, pitcher_id
HAVING SUM(career_pa) >= 20
ORDER BY total_pa DESC;

-- View: Platoon advantage batters
CREATE OR REPLACE VIEW features.platoon_advantage_batters AS
SELECT 
    player_id,
    season,
    bats,
    platoon_advantage,
    vs_l_ops,
    vs_r_ops,
    vs_l_pa,
    vs_r_pa
FROM features.platoon_splits
WHERE player_type = 'batter'
  AND vs_l_pa >= 50
  AND vs_r_pa >= 100
ORDER BY ABS(platoon_advantage) DESC;

-- View: Current game matchups summary
CREATE OR REPLACE VIEW features.current_game_matchups AS
SELECT 
    mf.game_pk,
    mf.batter_id,
    mf.pitcher_id,
    mf.career_matchup_pa,
    mf.career_matchup_avg,
    mf.is_platoon_advantage,
    mf.matchup_score,
    CASE 
        WHEN mf.career_matchup_pa >= 20 THEN 'Familiar'
        WHEN mf.career_matchup_pa >= 5 THEN 'Some history'
        ELSE 'First meeting'
    END as matchup_familiarity
FROM features.matchup_features mf
WHERE mf.computed_at > NOW() - INTERVAL '24 hours';

COMMENT ON VIEW features.career_matchup_leaders IS 'Batters with most PA against specific pitchers (career)';
COMMENT ON VIEW features.platoon_advantage_batters IS 'Batters with significant platoon splits';
COMMENT ON VIEW features.current_game_matchups IS 'Matchup features for recent games';
