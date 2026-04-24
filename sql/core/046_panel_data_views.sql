-- Panel Data Materialized Views
-- Creates materialized views for player-season, pitcher-season, and player-game panel data
-- Related to GitHub Issue #46

-- Player-season batting panel
DROP MATERIALIZED VIEW IF EXISTS features.player_season_batting CASCADE;
CREATE MATERIALIZED VIEW features.player_season_batting AS
SELECT
    p.batter_id,
    p.season,
    p.home_team_id,
    COUNT(DISTINCT p.game_id) AS games_played,
    SUM(p.ab) AS at_bats,
    SUM(p.h) AS hits,
    SUM(p."2b") AS doubles,
    SUM(p."3b") AS triples,
    SUM(p.hr) AS home_runs,
    SUM(p.rbi) AS rbi,
    SUM(p.bb) AS walks,
    SUM(p.so) AS strikeouts,
    SUM(p.sb) AS stolen_bases,
    SUM(p.cs) AS caught_stealing,
    ROUND(SUM(p.h)::NUMERIC / NULLIF(SUM(p.ab), 0), 3) AS batting_avg,
    ROUND((SUM(p.h) + SUM(p.bb) + SUM(p.hbp))::NUMERIC / NULLIF(SUM(p.ab) + SUM(p.bb) + SUM(p.hbp), 0), 3) AS on_base_pct,
    ROUND((SUM(p.h - p."2b" - p."3b" - p.hr) + 2 * SUM(p."2b") + 3 * SUM(p."3b") + 4 * SUM(p.hr))::NUMERIC / NULLIF(SUM(p.ab), 0), 3) AS slugging_pct,
    ROUND((SUM(p.h) + SUM(p.bb) + SUM(p.hbp))::NUMERIC / NULLIF(SUM(p.ab) + SUM(p.bb) + SUM(p.hbp), 0) + (SUM(p.h - p."2b" - p."3b" - p.hr) + 2 * SUM(p."2b") + 3 * SUM(p."3b") + 4 * SUM(p.hr))::NUMERIC / NULLIF(SUM(p.ab), 0), 3) AS ops
FROM core.plate_appearances AS p
GROUP BY p.batter_id, p.season, p.home_team_id
WITH DATA;

CREATE INDEX idx_player_season_batting_player_season ON features.player_season_batting (player_id, season);
CREATE INDEX idx_player_season_batting_team ON features.player_season_batting (team_id);

-- Player-season pitching panel
DROP MATERIALIZED VIEW IF EXISTS features.player_season_pitching CASCADE;
CREATE MATERIALIZED VIEW features.player_season_pitching AS
SELECT
    p.player_id,
    p.season,
    p.team_id,
    COUNT(DISTINCT p.game_id) AS games_played,
    COUNT(DISTINCT CASE WHEN p.pitching_appearance THEN p.game_id END) AS games_pitched,
    SUM(p.outs_played) AS outs_recorded,
    SUM(p.outs_played)::NUMERIC / 3 AS innings_pitched,
    SUM(p.h) AS hits_allowed,
    SUM(p.r) AS runs_allowed,
    SUM(p.er) AS earned_runs,
    SUM(p.hr) AS home_runs_allowed,
    SUM(p.bb) AS walks_allowed,
    SUM(p.so) AS strikeouts,
    SUM(p.hbp) AS hit_batters,
    ROUND(SUM(p.er) * 9.0::NUMERIC / NULLIF(SUM(p.outs_played), 0), 2) AS era,
    ROUND(SUM(p.bb + p.h)::NUMERIC / NULLIF(SUM(p.outs_played), 0), 3) AS whip
FROM core.plate_appearances AS p
WHERE p.pitching_appearance = true
GROUP BY p.player_id, p.season, p.team_id
WITH DATA;

CREATE INDEX idx_player_season_pitching_player_season ON features.player_season_pitching (player_id, season);
CREATE INDEX idx_player_season_pitching_team ON features.player_season_pitching (team_id);

-- Player-game panel
DROP MATERIALIZED VIEW IF EXISTS features.player_game_panel CASCADE;
CREATE MATERIALIZED VIEW features.player_game_panel AS
SELECT
    p.game_id,
    p.player_id,
    p.season,
    p.team_id,
    p.ab,
    p.h,
    p."2b",
    p."3b",
    p.hr,
    p.rbi,
    p.bb,
    p.so,
    p.sb,
    p.cs,
    p.outs_played,
    ROUND(p.h::NUMERIC / NULLIF(p.ab, 0), 3) AS batting_avg,
    COALESCE(p.pitching_appearance, FALSE) AS pitching_appearance,
    ROUND(p.outs_played::NUMERIC / 3, 1) AS innings_pitched
FROM core.plate_appearances AS p
GROUP BY p.game_id, p.player_id, p.season, p.team_id, p.ab, p.h, p."2b", p."3b", p.hr, p.rbi, p.bb, p.so, p.sb, p.cs, p.pitching_appearance, p.outs_played
WITH DATA;

CREATE INDEX idx_player_game_panel_game ON features.player_game_panel (game_id);
CREATE INDEX idx_player_game_panel_player ON features.player_game_panel (batter_id);
CREATE INDEX idx_player_game_panel_season ON features.player_game_panel (season);

COMMENT ON MATERIALIZED VIEW features.player_season_batting IS 'Player-season aggregated batting statistics for panel data analysis';
COMMENT ON MATERIALIZED VIEW features.player_season_pitching IS 'Player-season aggregated pitching statistics for panel data analysis';
COMMENT ON MATERIALIZED VIEW features.player_game_panel IS 'Player-game level panel data for detailed analysis';
