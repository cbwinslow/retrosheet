-- Player Profile Mart: Rolling pitcher and batter stats from pitch-level data
-- These tables enable dynamic player-level features for PA outcome prediction

-- 1. Pitcher Arsenal Profiles
DROP TABLE IF EXISTS features_pitch.pitcher_arsenals CASCADE;
CREATE TABLE features_pitch.pitcher_arsenals (
    pitcher_id INTEGER NOT NULL,
    game_year INTEGER NOT NULL,
    pitch_type TEXT NOT NULL,
    total_pitches INTEGER,
    avg_velocity NUMERIC(5, 1),
    max_velocity NUMERIC(5, 1),
    min_velocity NUMERIC(5, 1),
    std_velocity NUMERIC(5, 2),
    avg_spin_rate NUMERIC(7, 0),
    avg_spin_axis NUMERIC(5, 1),
    avg_release_x NUMERIC(6, 3),
    avg_release_z NUMERIC(6, 3),
    avg_pfx_x NUMERIC(6, 3),
    avg_pfx_z NUMERIC(6, 3),
    zone_pct NUMERIC(4, 1),
    swing_pct NUMERIC(4, 1),
    whiff_pct NUMERIC(4, 1),
    in_play_pct NUMERIC(4, 1),
    -- Add movement signature
    movement_signature TEXT, -- computed: pfx_x/pfx_z classification
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (pitcher_id, game_year, pitch_type)
);

COMMENT ON TABLE features_pitch.pitcher_arsenals IS
'Pitcher arsenal composition by year and pitch type. Rolling statistics updated per game.';

-- 2. Batter Zone Discipline Profiles  
DROP TABLE IF EXISTS features_pitch.batter_zone_profiles CASCADE;
CREATE TABLE features_pitch.batter_zone_profiles (
    batter_id INTEGER NOT NULL,
    game_year INTEGER NOT NULL,
    zone INTEGER NOT NULL, -- 1-9 strike zone, 11-14 out of zone
    total_pitches INTEGER,
    swing_pct NUMERIC(4, 1), -- Swing rate in this zone
    contact_pct NUMERIC(4, 1), -- Contact rate when swinging
    whiff_pct NUMERIC(4, 1), -- Whiff rate
    foul_pct NUMERIC(4, 1), -- Foul ball rate
    in_play_pct NUMERIC(4, 1), -- Balls in play rate
    hard_hit_pct NUMERIC(4, 1), -- Hard hit rate (launch_speed >= 95)
    avg_launch_speed NUMERIC(5, 1),
    avg_launch_angle NUMERIC(5, 1),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (batter_id, game_year, zone)
);

COMMENT ON TABLE features_pitch.batter_zone_profiles IS
'Batter swing/contact decisions by zone and year. Enables "chase rate" and "zone coverage" analysis.';

-- 3. Batter vs Pitch Type Performance
DROP TABLE IF EXISTS features_pitch.batter_pitch_type_performance CASCADE;
CREATE TABLE features_pitch.batter_pitch_type_performance (
    batter_id INTEGER NOT NULL,
    game_year INTEGER NOT NULL,
    pitch_type TEXT NOT NULL,
    total_pitches INTEGER,
    swings INTEGER,
    whiffs INTEGER,
    contact INTEGER,
    fouls INTEGER,
    balls_in_play INTEGER,
    singles INTEGER,
    doubles INTEGER,
    triples INTEGER,
    home_runs INTEGER,
    outs INTEGER,
    avg_launch_speed NUMERIC(5, 1),
    avg_launch_angle NUMERIC(5, 1),
    slugging_pct NUMERIC(5, 3),
    babip NUMERIC(4, 3),
    iso NUMERIC(5, 3),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (batter_id, game_year, pitch_type)
);

COMMENT ON TABLE features_pitch.batter_pitch_type_performance IS
'Batter performance against specific pitch types. For matchup analysis.';

-- 4. Pitcher-Batter Matchup History
DROP TABLE IF EXISTS features_pitch.matchup_history CASCADE;
CREATE TABLE features_pitch.matchup_history (
    pitcher_id INTEGER NOT NULL,
    batter_id INTEGER NOT NULL,
    game_year INTEGER NOT NULL,
    times_faced INTEGER,
    total_pitches INTEGER,
    pa_count INTEGER,
    walk_count INTEGER,
    strikeout_count INTEGER,
    hit_count INTEGER,
    hr_count INTEGER,
    avg_launch_speed NUMERIC(5, 1),
    common_pitch_sequence TEXT, -- Most frequent pitch sequence used
    last_faced_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (pitcher_id, batter_id, game_year)
);

COMMENT ON TABLE features_pitch.matchup_history IS
'Historical head-to-head matchup data between specific pitcher-batter pairs.';

-- 5. Count Performance Profiles
DROP TABLE IF EXISTS features_pitch.count_performance CASCADE;
CREATE TABLE features_pitch.count_performance (
    player_id INTEGER NOT NULL,
    player_type TEXT NOT NULL CHECK (player_type IN ('batter', 'pitcher')),
    game_year INTEGER NOT NULL,
    balls INTEGER NOT NULL,
    strikes INTEGER NOT NULL,
    total_pas INTEGER,
    -- For batters
    avg_woba NUMERIC(5, 3),
    ops NUMERIC(5, 3),
    hr_rate NUMERIC(5, 4),
    k_rate NUMERIC(4, 3),
    bb_rate NUMERIC(4, 3),
    -- For pitchers (mirror of batter stats, from pitcher's perspective)
    avg_woba_allowed NUMERIC(5, 3),
    ops_allowed NUMERIC(5, 3),
    hr_allowed_rate NUMERIC(5, 4),
    k_induced_rate NUMERIC(4, 3),
    bb_allowed_rate NUMERIC(4, 3),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (player_id, player_type, game_year, balls, strikes)
);

COMMENT ON TABLE features_pitch.count_performance IS
'Player performance by count (0-0, 1-2, 3-1, etc.). Critical for pitch sequence modeling.';

-- Indexes for common lookups
CREATE INDEX idx_pitcher_arsenals_pitcher ON features_pitch.pitcher_arsenals (pitcher_id);
CREATE INDEX idx_batter_zone_batter ON features_pitch.batter_zone_profiles (batter_id);
CREATE INDEX idx_batter_pitch_type_batter ON features_pitch.batter_pitch_type_performance (batter_id);
CREATE INDEX idx_matchup_pitcher ON features_pitch.matchup_history (pitcher_id);
CREATE INDEX idx_matchup_batter ON features_pitch.matchup_history (batter_id);
CREATE INDEX idx_matchup_pair ON features_pitch.matchup_history (pitcher_id, batter_id);

-- Populate with initial data (example queries)
-- These would typically be run by a Python script that processes season-by-season

COMMENT ON SCHEMA features_pitch IS
'Pitch-level feature engineering schema with player-attributed rolling statistics';
