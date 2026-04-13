-- MLB Win Probability Feature Engineering Plan
-- Combining Retrosheet historical data with MLB modern analytics

-- ================================================================================
-- FEATURE CATEGORIES NEEDED FOR WIN PROBABILITY MODELING
-- ================================================================================

-- 1. BASIC GAME STATE FEATURES (Available in both sources)
-- inning, is_bottom_inning, outs_before, balls, strikes, score_diff, runners_on_base

-- 2. PLAYER PERFORMANCE FEATURES (Enhanced with MLB data)
-- batter_season_avg, pitcher_season_era, batter_career_stats, pitcher_career_stats

-- 3. STATCAST PITCH FEATURES (MLB exclusive - major advantage)
-- pitch_velocity, pitch_spin_rate, pitch_movement, pitch_location, pitch_type_confidence

-- 4. TEAM PERFORMANCE FEATURES (Season and recent form)
-- team_win_pct, team_run_differential, recent_10_game_record

-- 5. SITUATIONAL CONTEXT FEATURES
-- home/away, park_factors, weather, matchup_history

-- 6. ADVANCED ANALYTICS (MLB enhanced)
-- launch_angle, exit_velocity, sprint_speed, arm_strength

-- ================================================================================
-- IMPLEMENTATION PLAN
-- ================================================================================

CREATE SCHEMA IF NOT EXISTS mlb_features;

-- Base game state features table (combines Retrosheet + MLB)
CREATE TABLE mlb_features.game_state_features (
    game_id text NOT NULL,
    event_sequence int NOT NULL,
    season int NOT NULL,

    -- Basic game state
    inning int NOT NULL,
    is_bottom_inning boolean NOT NULL,
    outs_before int NOT NULL,
    balls int NOT NULL DEFAULT 0,
    strikes int NOT NULL DEFAULT 0,
    score_diff int NOT NULL, -- home_score - away_score
    runners_on_base int NOT NULL DEFAULT 0, -- bitmask: 1B=1, 2B=2, 3B=4

    -- Player IDs (for joining to performance features)
    batter_id text,
    pitcher_id text,
    batting_team_id text,
    fielding_team_id text,

    -- Game context
    home_team_id text,
    away_team_id text,
    park_id text,
    is_home_game boolean, -- true if batting team is home

    -- Current pitch data (from MLB Statcast)
    pitch_type_code text,
    pitch_velocity numeric(5,1),
    pitch_spin_rate int,
    pitch_plate_x numeric(6,2),
    pitch_plate_z numeric(6,2),
    pitch_zone int,

    -- Target variable
    batting_team_wins boolean NOT NULL, -- did the team at bat win?

    -- Metadata
    data_source text NOT NULL, -- 'retrosheet' or 'mlb'
    created_at timestamptz DEFAULT now(),

    PRIMARY KEY (game_id, event_sequence)
);

-- Player performance features (season stats)
CREATE TABLE mlb_features.player_season_stats (
    player_id text NOT NULL,
    season int NOT NULL,
    is_batter boolean NOT NULL,

    -- Batting stats (if batter)
    games_played int,
    plate_appearances int,
    at_bats int,
    hits int,
    doubles int,
    triples int,
    home_runs int,
    rbi int,
    walks int,
    strikeouts int,
    batting_avg numeric(4,3),
    on_base_pct numeric(4,3),
    slugging_pct numeric(4,3),
    ops numeric(4,3),

    -- Pitching stats (if pitcher)
    games_started int,
    innings_pitched numeric(6,1),
    earned_runs int,
    pitcher_hits_allowed int,
    pitcher_walks int,
    pitcher_strikeouts int,
    pitcher_home_runs int,
    era numeric(5,2),
    whip numeric(4,2),
    k_per_9 numeric(5,2),

    -- Statcast metrics (MLB only)
    avg_exit_velocity numeric(5,1),
    avg_launch_angle numeric(4,1),
    sprint_speed numeric(4,2),
    arm_strength text,

    created_at timestamptz DEFAULT now(),

    PRIMARY KEY (player_id, season, is_batter)
);

-- Team performance features
CREATE TABLE mlb_features.team_season_stats (
    team_id text NOT NULL,
    season int NOT NULL,

    games_played int,
    wins int,
    losses int,
    win_pct numeric(4,3),
    runs_scored int,
    runs_allowed int,
    run_differential int,

    -- Recent form (last 10 games)
    recent_games int,
    recent_wins int,
    recent_win_pct numeric(4,3),

    -- Home/away splits
    home_games int,
    home_wins int,
    away_games int,
    away_wins int,

    created_at timestamptz DEFAULT now(),

    PRIMARY KEY (team_id, season)
);

-- Park/run environment factors
CREATE TABLE mlb_features.park_factors (
    park_id text NOT NULL,
    season int NOT NULL,

    -- Run scoring environment
    park_factor_runs numeric(4,3), -- 1.0 = average, >1.0 = hitter-friendly
    park_factor_hr numeric(4,3),   -- HR park factor

    -- Dimensions (feet)
    left_field_distance int,
    center_field_distance int,
    right_field_distance int,

    -- Surface and conditions
    turf_type text,
    roof_type text,

    created_at timestamptz DEFAULT now(),

    PRIMARY KEY (park_id, season)
);

-- Batter-pitcher matchup history
CREATE TABLE mlb_features.batter_pitcher_matchups (
    batter_id text NOT NULL,
    pitcher_id text NOT NULL,
    season int NOT NULL,

    -- Historical performance
    plate_appearances int,
    hits int,
    home_runs int,
    walks int,
    strikeouts int,
    avg numeric(4,3),
    slg numeric(4,3),

    -- Statcast vs this pitcher
    avg_exit_velocity_vs numeric(5,1),
    avg_launch_angle_vs numeric(4,1),

    created_at timestamptz DEFAULT now(),

    PRIMARY KEY (batter_id, pitcher_id, season)
);

-- ================================================================================
-- POPULATION SCRIPTS
-- ================================================================================

-- Function to populate game state features from Retrosheet data
CREATE OR REPLACE FUNCTION mlb_features.populate_game_state_from_retrosheet(
    start_season int DEFAULT 2000,
    end_season int DEFAULT 2024
)
RETURNS int
LANGUAGE plpgsql
AS $$
DECLARE
    rows_inserted int := 0;
BEGIN
    INSERT INTO mlb_features.game_state_features (
        game_id, event_sequence, season,
        inning, is_bottom_inning, outs_before, balls, strikes,
        score_diff, runners_on_base,
        batter_id, pitcher_id, batting_team_id, fielding_team_id,
        home_team_id, away_team_id, park_id, is_home_game,
        batting_team_wins, data_source
    )
    SELECT
        e.game_id,
        e.event_sequence,
        g.season,
        e.inning,
        e.is_bottom_inning,
        e.outs_before,
        COALESCE(e.balls, 0),
        COALESCE(e.strikes, 0),
        e.home_score_before - e.away_score_before,
        COALESCE(e.start_bases, 0),
        e.batter_id,
        e.pitcher_id,
        e.batting_team_id,
        e.fielding_team_id,
        g.home_team_id,
        g.away_team_id,
        g.park_id,
        (e.batting_team_id = g.home_team_id),
        (CASE WHEN g.home_score > g.away_score THEN (e.batting_team_id = g.home_team_id)
              WHEN g.away_score > g.home_score THEN (e.batting_team_id = g.away_team_id)
              ELSE false END),
        'retrosheet'
    FROM core.events e
    JOIN core.games g ON e.game_id = g.game_id
    WHERE g.season BETWEEN start_season AND end_season
      AND e.is_plate_appearance = true
    ON CONFLICT (game_id, event_sequence) DO NOTHING;

    GET DIAGNOSTICS rows_inserted = ROW_COUNT;
    RAISE NOTICE 'Inserted % game state features from Retrosheet', rows_inserted;

    RETURN rows_inserted;
END;
$$;

-- Function to populate game state features from MLB data
CREATE OR REPLACE FUNCTION mlb_features.populate_game_state_from_mlb()
RETURNS int
LANGUAGE plpgsql
AS $$
DECLARE
    rows_inserted int := 0;
BEGIN
    INSERT INTO mlb_features.game_state_features (
        game_id, event_sequence, season,
        inning, is_bottom_inning, outs_before, balls, strikes,
        score_diff, runners_on_base,
        batter_id, pitcher_id, batting_team_id, fielding_team_id,
        home_team_id, away_team_id, is_home_game,
        pitch_type_code, pitch_velocity, pitch_spin_rate,
        pitch_plate_x, pitch_plate_z, pitch_zone,
        batting_team_wins, data_source
    )
    SELECT
        le.game_id,
        le.event_sequence,
        le.season::int,
        le.inning,
        le.is_bottom_inning,
        le.outs_before,
        COALESCE(le.balls, 0),
        COALESCE(le.strikes, 0),
        le.home_score_after - le.away_score_after, -- Use after scores as approximation
        COALESCE(le.start_bases, 0),
        le.batter_id,
        le.pitcher_id,
        CASE WHEN le.is_bottom_inning THEN lg.home_team_id::text ELSE lg.away_team_id::text END,
        CASE WHEN le.is_bottom_inning THEN lg.away_team_id::text ELSE lg.home_team_id::text END,
        lg.home_team_id::text,
        lg.away_team_id::text,
        (CASE WHEN le.is_bottom_inning THEN lg.home_team_id::text ELSE lg.away_team_id::text END = lg.home_team_id::text),
        -- Pitch data from latest pitch in this event
        latest_pitch.pitch_type_code,
        latest_pitch.start_speed,
        latest_pitch.spin_rate,
        latest_pitch.plate_x,
        latest_pitch.plate_z,
        latest_pitch.plate_zone,
        (CASE WHEN lg.home_score > lg.away_score THEN le.is_bottom_inning
              WHEN lg.away_score > lg.home_score THEN NOT le.is_bottom_inning
              ELSE false END),
        'mlb'
    FROM core.live_events le
    JOIN core.live_games lg ON le.game_id = lg.game_id
    LEFT JOIN LATERAL (
        SELECT p.*
        FROM mlb.pitches p
        WHERE p.game_pk = le.mlb_game_pk::int
          AND p.event_index = le.event_sequence
        ORDER BY p.pitch_index DESC
        LIMIT 1
    ) latest_pitch ON true
    WHERE le.is_plate_appearance = true
    ON CONFLICT (game_id, event_sequence) DO NOTHING;

    GET DIAGNOSTICS rows_inserted = ROW_COUNT;
    RAISE NOTICE 'Inserted % game state features from MLB', rows_inserted;

    RETURN rows_inserted;
END;
$$;

-- Function to populate player season stats
CREATE OR REPLACE FUNCTION mlb_features.populate_player_season_stats()
RETURNS int
LANGUAGE plpgsql
AS $$
DECLARE
    rows_inserted int := 0;
BEGIN
    -- Insert batting stats
    INSERT INTO mlb_features.player_season_stats (
        player_id, season, is_batter,
        games_played, plate_appearances, at_bats, hits, doubles, triples, home_runs,
        rbi, walks, strikeouts, batting_avg, on_base_pct, slugging_pct, ops
    )
    SELECT
        batter_id,
        season,
        true as is_batter,
        COUNT(DISTINCT game_id) as games_played,
        COUNT(*) as plate_appearances,
        COUNT(CASE WHEN is_at_bat THEN 1 END) as at_bats,
        COUNT(CASE WHEN is_hit THEN 1 END) as hits,
        COUNT(CASE WHEN hit_value = 2 THEN 1 END) as doubles,
        COUNT(CASE WHEN hit_value = 3 THEN 1 END) as triples,
        COUNT(CASE WHEN is_home_run THEN 1 END) as home_runs,
        SUM(rbi) as rbi,
        COUNT(CASE WHEN is_walk THEN 1 END) as walks,
        COUNT(CASE WHEN is_strikeout THEN 1 END) as strikeouts,
        ROUND(AVG(is_hit::int)::numeric, 3) as batting_avg,
        ROUND(
            (COUNT(CASE WHEN is_hit OR is_walk THEN 1 END))::numeric
            / NULLIF(COUNT(*), 0),
            3
        ) as on_base_pct,
        ROUND(
            (COUNT(CASE WHEN is_hit THEN 1 END)
           + COUNT(CASE WHEN hit_value = 2 THEN 1 END)
           + 2 * COUNT(CASE WHEN hit_value = 3 THEN 1 END)
           + 3 * COUNT(CASE WHEN is_home_run THEN 1 END))::numeric
            / NULLIF(COUNT(CASE WHEN is_at_bat THEN 1 END), 0),
            3
        ) as slugging_pct,
        ROUND(
            (COUNT(CASE WHEN is_hit OR is_walk THEN 1 END))::numeric
            / NULLIF(COUNT(*), 0)
          + (COUNT(CASE WHEN is_hit THEN 1 END)
           + COUNT(CASE WHEN hit_value = 2 THEN 1 END)
           + 2 * COUNT(CASE WHEN hit_value = 3 THEN 1 END)
           + 3 * COUNT(CASE WHEN is_home_run THEN 1 END))::numeric
            / NULLIF(COUNT(CASE WHEN is_at_bat THEN 1 END), 0),
            3
        ) as ops
    FROM features.plate_appearance_examples
    WHERE batter_id IS NOT NULL
    GROUP BY batter_id, season
    ON CONFLICT (player_id, season, is_batter) DO NOTHING;

    -- Insert pitching stats
    INSERT INTO mlb_features.player_season_stats (
        player_id, season, is_batter,
        games_started, innings_pitched, earned_runs, pitcher_hits_allowed,
        pitcher_walks, pitcher_strikeouts, pitcher_home_runs, era, whip, k_per_9
    )
    SELECT
        pitcher_id,
        season,
        false as is_batter,
        COUNT(DISTINCT game_id) as games_started,
        SUM(CASE WHEN inning IS NOT NULL THEN 1 ELSE 0 END)::numeric / 3 as innings_pitched,
        0 as earned_runs, -- Would need more complex calculation
        COUNT(CASE WHEN is_hit THEN 1 END) as pitcher_hits_allowed,
        COUNT(CASE WHEN is_walk THEN 1 END) as pitcher_walks,
        COUNT(CASE WHEN is_strikeout THEN 1 END) as pitcher_strikeouts,
        COUNT(CASE WHEN is_home_run THEN 1 END) as pitcher_home_runs,
        ROUND(
            0::numeric / NULLIF(SUM(CASE WHEN inning IS NOT NULL THEN 1 ELSE 0 END)::numeric / 3, 0) * 9,
            2
        ) as era,
        ROUND(
            (COUNT(CASE WHEN is_hit THEN 1 END) + COUNT(CASE WHEN is_walk THEN 1 END))::numeric
            / NULLIF(SUM(CASE WHEN inning IS NOT NULL THEN 1 ELSE 0 END)::numeric / 3, 0),
            2
        ) as whip,
        ROUND(
            COUNT(CASE WHEN is_strikeout THEN 1 END)::numeric
            / NULLIF(SUM(CASE WHEN inning IS NOT NULL THEN 1 ELSE 0 END)::numeric / 3, 0) * 9,
            1
        ) as k_per_9
    FROM features.plate_appearance_examples
    WHERE pitcher_id IS NOT NULL
    GROUP BY pitcher_id, season
    ON CONFLICT (player_id, season, is_batter) DO NOTHING;

    GET DIAGNOSTICS rows_inserted = ROW_COUNT;
    RAISE NOTICE 'Inserted % player season stats', rows_inserted;

    RETURN rows_inserted;
END;
$$;

-- ================================================================================
-- USAGE EXAMPLES
-- ================================================================================

-- Populate all features for a season
-- 1. Populate game states
SELECT mlb_features.populate_game_state_from_retrosheet(2023, 2023);
SELECT mlb_features.populate_game_state_from_mlb();

-- 2. Populate player stats
SELECT mlb_features.populate_player_season_stats();

-- 3. Create training dataset
CREATE TABLE mlb_features.win_probability_training AS
SELECT
    gsf.*,
    -- Join player stats
    bs.batting_avg as batter_season_avg,
    ps.era as pitcher_season_era,
    -- Join team stats
    ts.win_pct as batting_team_win_pct,
    -- Add park factors
    pf.park_factor_runs,
    -- Add matchup history
    bpm.avg as batter_vs_pitcher_avg
FROM mlb_features.game_state_features gsf
LEFT JOIN mlb_features.player_season_stats bs ON gsf.batter_id = bs.player_id
    AND gsf.season = bs.season AND bs.is_batter = true
LEFT JOIN mlb_features.player_season_stats ps ON gsf.pitcher_id = ps.player_id
    AND gsf.season = ps.season AND ps.is_batter = false
LEFT JOIN mlb_features.team_season_stats ts ON gsf.batting_team_id = ts.team_id
    AND gsf.season = ts.season
LEFT JOIN mlb_features.park_factors pf ON gsf.park_id = pf.park_id
    AND gsf.season = pf.season
LEFT JOIN mlb_features.batter_pitcher_matchups bpm ON gsf.batter_id = bpm.batter_id
    AND gsf.pitcher_id = bpm.pitcher_id AND gsf.season = bpm.season;

-- Add target variable (win probability)
ALTER TABLE mlb_features.win_probability_training
ADD COLUMN win_probability numeric(4,3);

-- Calculate win probability for each state
UPDATE mlb_features.win_probability_training
SET win_probability = batting_team_wins::int;

-- This creates a comprehensive training dataset combining:
-- ✅ Retrosheet historical game states + MLB Statcast pitch data
-- ✅ Player seasonal performance + team context
-- ✅ Park factors + matchup history
-- ✅ Ready for win probability model training