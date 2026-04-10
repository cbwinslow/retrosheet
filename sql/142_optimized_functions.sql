-- Optimized Query Functions for Common Analytics

-- Fast player season stats function
CREATE OR REPLACE FUNCTION analysis.get_player_season_stats(
    player_id text,
    target_season text
)
RETURNS TABLE (
    plate_appearances bigint,
    hits bigint,
    home_runs bigint,
    rbi bigint,
    walks bigint,
    strikeouts bigint,
    batting_avg numeric
)
LANGUAGE sql
STABLE
AS $$
    SELECT
        COUNT(*) as plate_appearances,
        COUNT(*) FILTER (WHERE is_hit) as hits,
        COUNT(*) FILTER (WHERE is_home_run) as home_runs,
        SUM(rbi) as rbi,
        COUNT(*) FILTER (WHERE is_walk) as walks,
        COUNT(*) FILTER (WHERE is_strikeout) as strikeouts,
        ROUND(AVG(is_hit::numeric), 3) as batting_avg
    FROM analysis.combined_plate_appearances
    WHERE batter_id = $1 AND season = $2 AND is_plate_appearance = true;
$$;

-- Fast game lookup by date range
CREATE OR REPLACE FUNCTION analysis.get_games_in_date_range(
    start_date text,
    end_date text DEFAULT CURRENT_DATE::text,
    source_filter text DEFAULT NULL
)
RETURNS TABLE (
    game_id text,
    game_date text,
    season text,
    source_type text,
    home_team_id text,
    away_team_id text,
    home_score integer,
    away_score integer,
    home_win boolean
)
LANGUAGE sql
STABLE
AS $$
    SELECT
        cg.game_id,
        cg.game_date,
        cg.season,
        cg.source_type,
        cg.home_team_id,
        cg.away_team_id,
        cg.home_score,
        cg.away_score,
        cg.home_win
    FROM analysis.combined_games cg
    WHERE cg.game_date >= $1 AND cg.game_date <= $2
    AND ($3 IS NULL OR cg.source_type = $3)
    ORDER BY cg.game_date DESC, cg.game_id;
$$;

-- Team performance summary
CREATE OR REPLACE FUNCTION analysis.get_team_season_summary(
    team_id text,
    target_season text
)
RETURNS TABLE (
    games_played bigint,
    wins bigint,
    losses bigint,
    win_percentage numeric,
    runs_scored bigint,
    runs_allowed bigint
)
LANGUAGE sql
STABLE
AS $$
    SELECT
        COUNT(*) as games_played,
        COUNT(*) FILTER (WHERE home_team_id = $1 AND home_win OR away_team_id = $1 AND NOT home_win) as wins,
        COUNT(*) FILTER (WHERE home_team_id = $1 AND NOT home_win OR away_team_id = $1 AND home_win) as losses,
        ROUND(AVG(CASE WHEN home_team_id = $1 THEN home_win::integer ELSE (NOT home_win)::integer END), 3) as win_percentage,
        SUM(CASE WHEN home_team_id = $1 THEN home_score ELSE away_score END) as runs_scored,
        SUM(CASE WHEN home_team_id = $1 THEN away_score ELSE home_score END) as runs_allowed
    FROM analysis.combined_games
    WHERE (home_team_id = $1 OR away_team_id = $1) AND season = $2;
$$;