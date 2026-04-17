-- Pitch Count Statistics Feature Mart
-- ====================================
-- 
-- Purpose: Create batter-pitcher pitch statistics grouped by count state
-- for next-pitch prediction modeling.
--
-- Research basis:
-- - SABR study "Study of 'The Count' Yields Fascinating Data" (1986 analysis)
-- - Baseball Savant pitch arsenal stats methodology
-- - Strike zone control and pitch sequencing research
--
-- Count states tracked:
-- - All 12 possible counts: 0-0, 0-1, 0-2, 1-0, 1-1, 1-2, 2-0, 2-1, 2-2, 3-0, 3-1, 3-2
-- - Binned into hitter-friendly (3-0, 3-1, 2-0, 2-1) vs pitcher-friendly (0-2, 1-2)
-- - Leverage index proxy for high-stakes counts (2-2, 3-2, 0-2 with RISP)
--
-- Tables created:
-- - features.batter_pitch_count_stats: Batter performance by count
-- - features.pitcher_pitch_count_stats: Pitcher behavior by count  
-- - features.pitch_archetypes: Pitch type distribution profiles
-- - features.count_state_expectations: League baselines by count

-- =============================================================================
-- Part 1: Count State Expectations (League Baselines)
-- =============================================================================

CREATE TABLE IF NOT EXISTS features.count_state_expectations (
    id SERIAL PRIMARY KEY,
    balls_before INTEGER NOT NULL,
    strikes_before INTEGER NOT NULL,
    count_key VARCHAR(5) NOT NULL,  -- e.g., "1-2", "3-0"
    count_category VARCHAR(20),     -- hitter_friendly, pitcher_friendly, neutral, full
    pa_count INTEGER,               -- number of PAs reaching this count
    
    -- Pitch outcome rates (league average)
    called_strike_rate NUMERIC(6,4),
    swinging_strike_rate NUMERIC(6,4),
    foul_rate NUMERIC(6,4),
    ball_rate NUMERIC(6,4),
    in_play_rate NUMERIC(6,4),
    
    -- When ball in play
    hit_rate NUMERIC(6,4),          -- any hit
    out_rate NUMERIC(6,4),          -- any out
    
    -- Strikeout/walk context
    so_imminent BOOLEAN,            -- 2 strikes
    bb_imminent BOOLEAN,            -- 3 balls
    two_strikes BOOLEAN,
    three_balls BOOLEAN,
    
    -- Pitch characteristics (averages when available)
    avg_release_speed NUMERIC(5,2),
    avg_spin_rate NUMERIC(7,2),
    avg_plate_x NUMERIC(5,2),
    avg_plate_z NUMERIC(5,2),
    
    -- Most common pitch types
    top_pitch_type_1 VARCHAR(10),
    top_pitch_type_1_rate NUMERIC(6,4),
    top_pitch_type_2 VARCHAR(10),
    top_pitch_type_2_rate NUMERIC(6,4),
    
    -- Metadata
    sample_seasons INTEGER[],       -- which seasons in sample
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now(),
    
    UNIQUE(count_key)
);

COMMENT ON TABLE features.count_state_expectations IS 
'League-average pitch outcome rates by count state for baseline comparisons in prediction models';

-- =============================================================================
-- Part 2: Batter Pitch Count Statistics
-- =============================================================================

CREATE TABLE IF NOT EXISTS features.batter_pitch_count_stats (
    id SERIAL PRIMARY KEY,
    batter_id INTEGER NOT NULL,          -- MLB player ID
    season INTEGER NOT NULL,
    balls_before INTEGER NOT NULL,
    strikes_before INTEGER NOT NULL,
    count_key VARCHAR(5) NOT NULL,       -- e.g., "1-2"
    
    -- Sample size
    pitches_seen INTEGER,
    plate_appearances INTEGER,          -- PAs that reached this count
    
    -- Swing behavior
    swing_rate NUMERIC(6,4),              -- % of pitches swung at
    contact_rate NUMERIC(6,4),            -- % of swings making contact
    whiff_rate NUMERIC(6,4),              -- % of swings missing
    foul_contact_rate NUMERIC(6,4),       -- % of contact that is foul
    
    -- Outcome rates
    called_strike_rate NUMERIC(6,4),
    swinging_strike_rate NUMERIC(6,4),
    ball_rate NUMERIC(6,4),
    in_play_rate NUMERIC(6,4),
    
    -- When in play
    hit_rate NUMERIC(6,4),
    hard_hit_rate NUMERIC(6,4),           -- based on launch speed if available
    
    -- Pitch type handling (what they see and how they do)
    fastball_seen_rate NUMERIC(6,4),      -- % of fastballs seen
    breaking_seen_rate NUMERIC(6,4),      -- % of breaking balls seen
    offspeed_seen_rate NUMERIC(6,4),      -- % of offspeed seen
    
    -- Performance vs pitch types
    wOBA_vs_fastball NUMERIC(5,3),
    wOBA_vs_breaking NUMERIC(5,3),
    wOBA_vs_offspeed NUMERIC(5,3),
    
    -- Zone control (when available)
    chase_rate NUMERIC(6,4),              -- swings outside zone
    zone_contact_rate NUMERIC(6,4),         -- contact on pitches in zone
    
    -- Relative to league (percentiles or deltas)
    swing_rate_vs_league NUMERIC(5,2),    -- percentage points above/below league
    contact_rate_vs_league NUMERIC(5,2),
    
    -- Career vs recent (for trend detection)
    is_career_stat BOOLEAN DEFAULT false, -- if this is career-to-date vs single season
    
    -- Metadata
    first_game_date DATE,
    last_game_date DATE,
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now(),
    
    UNIQUE(batter_id, season, count_key, is_career_stat)
);

CREATE INDEX IF NOT EXISTS idx_batter_pitch_stats_lookup 
ON features.batter_pitch_count_stats(batter_id, season, count_key);

CREATE INDEX IF NOT EXISTS idx_batter_pitch_stats_season 
ON features.batter_pitch_count_stats(season, count_key, is_career_stat);

COMMENT ON TABLE features.batter_pitch_count_stats IS 
'Batter performance and swing behavior statistics by count state for pitch-level prediction models';

-- =============================================================================
-- Part 3: Pitcher Pitch Count Statistics
-- =============================================================================

CREATE TABLE IF NOT EXISTS features.pitcher_pitch_count_stats (
    id SERIAL PRIMARY KEY,
    pitcher_id INTEGER NOT NULL,         -- MLB player ID
    season INTEGER NOT NULL,
    balls_before INTEGER NOT NULL,
    strikes_before INTEGER NOT NULL,
    count_key VARCHAR(5) NOT NULL,       -- e.g., "1-2"
    
    -- Sample size
    pitches_thrown INTEGER,
    batters_faced INTEGER,               -- batters reached this count
    
    -- Pitch selection
    fastball_pct NUMERIC(6,4),           -- % fastballs
    breaking_pct NUMERIC(6,4),           -- % breaking balls
    offspeed_pct NUMERIC(6,4),           -- % offspeed
    changeup_pct NUMERIC(6,4),           -- % changeups
    slider_pct NUMERIC(6,4),
    curveball_pct NUMERIC(6,4),
    
    -- Arsenal depth (how many pitch types used regularly)
    arsenal_size INTEGER,                -- count of pitch types >5% usage
    
    -- Location tendencies
    zone_rate NUMERIC(6,4),              -- % pitches in strike zone
    heart_rate NUMERIC(6,4),             -- % in heart of zone
    edge_rate NUMERIC(6,4),              -- % on edges
    chase_induced_rate NUMERIC(6,4),     -- % resulting in swings outside zone
    
    -- Outcome rates
    called_strike_rate NUMERIC(6,4),
    swinging_strike_rate NUMERIC(6,4),
    whiff_rate NUMERIC(6,4),             -- swinging strikes / total swings
    foul_rate NUMERIC(6,4),
    ball_rate NUMERIC(6,4),
    in_play_rate NUMERIC(6,4),
    
    -- When in play
    hit_allowed_rate NUMERIC(6,4),
    hard_hit_allowed_rate NUMERIC(6,4),
    
    -- Pitch quality (when available)
    avg_release_speed NUMERIC(5,2),
    avg_spin_rate NUMERIC(7,2),
    avg_break_x NUMERIC(5,2),
    avg_break_z NUMERIC(5,2),
    avg_plate_x NUMERIC(5,2),
    avg_plate_z NUMERIC(5,2),
    avg_nasty_factor NUMERIC(5,2),
    
    -- Velocity variance (tells us about effort level)
    speed_variance NUMERIC(5,2),
    
    -- First pitch specifics (for 0-0)
    first_pitch_strike_rate NUMERIC(6,4),
    
    -- Two-strike approach
    waste_pitch_rate NUMERIC(6,4),       -- pitches clearly out of zone with 2 strikes
    put_away_pitch_type VARCHAR(10),     -- most common pitch for strikeout
    
    -- Three-ball approach  
    pitching_around_rate NUMERIC(6,4),   -- with 3 balls, how often pitching around
    
    -- Relative to league
    zone_rate_vs_league NUMERIC(5,2),
    whiff_rate_vs_league NUMERIC(5,2),
    
    -- Career vs recent
    is_career_stat BOOLEAN DEFAULT false,
    
    -- Metadata
    first_game_date DATE,
    last_game_date DATE,
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now(),
    
    UNIQUE(pitcher_id, season, count_key, is_career_stat)
);

CREATE INDEX IF NOT EXISTS idx_pitcher_pitch_stats_lookup 
ON features.pitcher_pitch_count_stats(pitcher_id, season, count_key);

CREATE INDEX IF NOT EXISTS idx_pitcher_pitch_stats_season 
ON features.pitcher_pitch_count_stats(season, count_key, is_career_stat);

COMMENT ON TABLE features.pitcher_pitch_count_stats IS 
'Pitcher pitch selection and outcome statistics by count state for pitch-level prediction models';

-- =============================================================================
-- Part 4: Pitch Archetypes (Classification of Batter/Pitcher Pitch Type Usage)
-- =============================================================================

CREATE TABLE IF NOT EXISTS features.pitch_archetypes (
    id SERIAL PRIMARY KEY,
    player_id INTEGER NOT NULL,
    player_type VARCHAR(10) NOT NULL,     -- 'batter' or 'pitcher'
    season INTEGER NOT NULL,
    
    -- Overall pitch mix faced (batters) or thrown (pitchers)
    total_pitches INTEGER,
    
    -- Primary classification
    archetype VARCHAR(30),                -- e.g., "fastball_hunter", "breaking_ball_seeing",
                                          -- "sinker_slider_pitcher", "four_seam_dominant"
    
    -- Pitch mix breakdown
    four_seam_pct NUMERIC(6,4),
    sinker_pct NUMERIC(6,4),
    cutter_pct NUMERIC(6,4),
    curve_pct NUMERIC(6,4),
    slider_pct NUMERIC(6,4),
    changeup_pct NUMERIC(6,4),
    split_pct NUMERIC(6,4),
    knuckle_pct NUMERIC(6,4),
    other_pct NUMERIC(6,4),
    
    -- Performance by pitch type (batters only)
    wOBA_vs_four_seam NUMERIC(5,3),
    wOBA_vs_sinker NUMERIC(5,3),
    wOBA_vs_breaking NUMERIC(5,3),
    wOBA_vs_offspeed NUMERIC(5,3),
    
    -- Arsenal depth (pitchers only)
    arsenal_size INTEGER,
    arsenal_description VARCHAR(100),      -- e.g., "4-seam, slider, change"
    
    -- Platoon-specific archetype
    vs_right_archetype VARCHAR(30),       -- specific archetype vs RHP/RHH
    vs_left_archetype VARCHAR(30),        -- specific archetype vs LHP/LHH
    
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now(),
    
    UNIQUE(player_id, player_type, season)
);

COMMENT ON TABLE features.pitch_archetypes IS 
'Pitch type classification and mix profiles for batters and pitchers';

-- =============================================================================
-- Part 5: Build Functions for Feature Generation
-- =============================================================================

CREATE OR REPLACE FUNCTION features.get_batter_count_stats(
    p_batter_id INTEGER,
    p_season INTEGER,
    p_count_key VARCHAR(5)
) RETURNS TABLE (
    swing_rate NUMERIC,
    contact_rate NUMERIC,
    whiff_rate NUMERIC,
    fastball_seen_rate NUMERIC,
    pitches_seen INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        b.swing_rate,
        b.contact_rate,
        b.whiff_rate,
        b.fastball_seen_rate,
        b.pitches_seen
    FROM features.batter_pitch_count_stats b
    WHERE b.batter_id = p_batter_id
      AND b.season = p_season
      AND b.count_key = p_count_key
      AND b.is_career_stat = false
    LIMIT 1;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION features.get_pitcher_count_stats(
    p_pitcher_id INTEGER,
    p_season INTEGER,
    p_count_key VARCHAR(5)
) RETURNS TABLE (
    fastball_pct NUMERIC,
    zone_rate NUMERIC,
    whiff_rate NUMERIC,
    avg_release_speed NUMERIC,
    pitches_thrown INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        p.fastball_pct,
        p.zone_rate,
        p.whiff_rate,
        p.avg_release_speed,
        p.pitches_thrown
    FROM features.pitcher_pitch_count_stats p
    WHERE p.pitcher_id = p_pitcher_id
      AND p.season = p_season
      AND p.count_key = p_count_key
      AND p.is_career_stat = false
    LIMIT 1;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION features.get_count_key(
    p_balls INTEGER,
    p_strikes INTEGER
) RETURNS VARCHAR(5) AS $$
BEGIN
    RETURN p_balls || '-' || p_strikes;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

CREATE OR REPLACE FUNCTION features.get_count_category(
    p_balls INTEGER,
    p_strikes INTEGER
) RETURNS VARCHAR(20) AS $$
DECLARE
    count_key VARCHAR(5);
BEGIN
    count_key := p_balls || '-' || p_strikes;
    
    -- Hitter-friendly counts
    IF count_key IN ('3-0', '3-1', '2-0', '2-1', '1-0') THEN
        RETURN 'hitter_friendly';
    -- Pitcher-friendly counts
    ELSIF count_key IN ('0-2', '1-2', '0-1') THEN
        RETURN 'pitcher_friendly';
    -- Full counts
    ELSIF count_key = '3-2' THEN
        RETURN 'full_count';
    -- Neutral
    ELSE
        RETURN 'neutral';
    END IF;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- =============================================================================
-- Part 6: Analysis Views
-- =============================================================================

-- View: Count state transitions
CREATE OR REPLACE VIEW features.count_state_transitions AS
SELECT 
    p1.balls_before || '-' || p1.strikes_before as from_count,
    CASE 
        WHEN p2.is_strike THEN p1.balls_before || '-' || LEAST(p1.strikes_before + 1, 2)
        WHEN p2.is_ball THEN LEAST(p1.balls_before + 1, 3) || '-' || p1.strikes_before
        ELSE p1.balls_before || '-' || p1.strikes_before  -- in play or other
    END as to_count,
    COUNT(*) as transition_count,
    AVG(p1.release_speed) as avg_pitch_speed,
    MODE() WITHIN GROUP (ORDER BY p1.pitch_type_code) as most_common_pitch
FROM mlb.pitches p1
LEFT JOIN mlb.pitches p2 ON 
    p1.game_pk = p2.game_pk 
    AND p1.at_bat_number = p2.at_bat_number 
    AND p1.pitch_number + 1 = p2.pitch_number
WHERE p1.pitch_number = 1  -- First pitch of PA
GROUP BY 1, 2;

-- View: Batter hot/cold zones by count
CREATE OR REPLACE VIEW features.batter_zone_heatmaps AS
SELECT 
    batter_id,
    season,
    balls_before || '-' || strikes_before as count_key,
    CASE 
        WHEN plate_x < -0.5 THEN 'left'
        WHEN plate_x > 0.5 THEN 'right'
        ELSE 'center'
    END as horizontal_zone,
    CASE 
        WHEN plate_z < 1.5 THEN 'low'
        WHEN plate_z > 3.0 THEN 'high'
        ELSE 'middle'
    END as vertical_zone,
    COUNT(*) as pitches,
    AVG(CASE WHEN is_in_play THEN 1 ELSE 0 END) as in_play_rate,
    AVG(CASE WHEN hit_rate > 0 THEN 1 ELSE 0 END) as hit_rate  -- placeholder
FROM mlb.pitches
WHERE release_speed IS NOT NULL
GROUP BY 1, 2, 3, 4, 5;

-- =============================================================================
-- Part 7: Refresh Function
-- =============================================================================

CREATE OR REPLACE FUNCTION features.refresh_pitch_count_stats(
    p_season INTEGER
) RETURNS VOID AS $$
BEGIN
    -- This would populate the feature tables from mlb.pitches
    -- Implementation depends on having pitch-level data in mlb.pitches
    
    RAISE NOTICE 'Pitch count stats refresh not yet implemented - requires pitch-level data in mlb.pitches';
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- Documentation
-- =============================================================================

COMMENT ON FUNCTION features.get_batter_count_stats IS 
'Returns batter statistics for a specific count state. Use for pitch-level model features.';

COMMENT ON FUNCTION features.get_pitcher_count_stats IS 
'Returns pitcher statistics for a specific count state. Use for pitch-level model features.';

COMMENT ON FUNCTION features.get_count_key IS 
'Converts balls and strikes to standard count key format (e.g., 1-2)';

COMMENT ON FUNCTION features.get_count_category IS 
'Classifies count as hitter_friendly, pitcher_friendly, full_count, or neutral';
