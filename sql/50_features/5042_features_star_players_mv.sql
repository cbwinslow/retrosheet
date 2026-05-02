/*
File: sql/50_features/5042_features_star_players_mv.sql
Purpose: Materialized views for star player predictions (fast lookups)
Author: Agent Cascade
Date: 2026-05-02
Depends On: sql/50_features/5041_features_player_context.sql
Called By: baseball/features/star_players.py, live prediction pipeline

Materialized Views:
- features.star_batters: Pre-computed star batter profiles
- features.star_pitchers: Pre-computed star pitcher profiles
- features.active_roster: Today's active players by team

Notes:
- Refreshed every 15 minutes during season
- Covers ~500 star players (top by WAR, recent performance)
- Includes 7-day, 30-day, season stats for fast access
*/

CREATE SCHEMA IF NOT EXISTS features;

-- Star batters materialized view
CREATE MATERIALIZED VIEW IF NOT EXISTS features.star_batters AS
WITH player_war AS (
    -- Get estimated WAR from recent performance
    SELECT 
        batter_id as player_id,
        AVG(avg_30d) as avg_30d,
        AVG(k_rate_30d) as k_rate_30d,
        AVG(bb_rate_30d) as bb_rate_30d,
        AVG(hr_rate_30d) as hr_rate_30d,
        AVG(pa_30d) as pa_30d,
        SUM(pa_30d) as total_pa_30d
    FROM features.player_batter_30day
    WHERE context_date >= CURRENT_DATE - INTERVAL '7 days'
    GROUP BY batter_id
    HAVING SUM(pa_30d) >= 20  -- Minimum playing time
),
ranked_batters AS (
    SELECT 
        player_id,
        avg_30d,
        k_rate_30d,
        bb_rate_30d,
        hr_rate_30d,
        pa_30d,
        -- Simple WAR estimate: (AVG * 200 + HR% * 50 - K% * 10)
        (avg_30d * 200 + hr_rate_30d * 0.5 - k_rate_30d * 0.1) as war_estimate,
        ROW_NUMBER() OVER (ORDER BY (avg_30d * 200 + hr_rate_30d * 0.5 - k_rate_30d * 0.1) DESC) as rank
    FROM player_war
)
SELECT 
    rb.player_id,
    rb.rank as star_rank,
    rb.war_estimate,
    rb.avg_30d,
    rb.k_rate_30d,
    rb.bb_rate_30d,
    rb.hr_rate_30d,
    rb.pa_30d,
    NOW() as computed_at
FROM ranked_batters rb
WHERE rb.rank <= 250;  -- Top 250 batters

CREATE UNIQUE INDEX IF NOT EXISTS idx_star_batters_player 
ON features.star_batters (player_id);

CREATE INDEX IF NOT EXISTS idx_star_batters_rank 
ON features.star_batters (star_rank);

-- Star pitchers materialized view
CREATE MATERIALIZED VIEW IF NOT EXISTS features.star_pitchers AS
WITH pitcher_war AS (
    SELECT 
        pitcher_id as player_id,
        AVG(k_rate_30d) as k_rate_30d,
        AVG(bb_rate_30d) as bb_rate_30d,
        AVG(hr_rate_30d) as hr_rate_30d,
        AVG(avg_velo_30d) as avg_velo_30d,
        AVG(arsenal_depth) as arsenal_depth,
        SUM(bf_30d) as total_bf_30d
    FROM features.player_pitcher_30day
    WHERE context_date >= CURRENT_DATE - INTERVAL '7 days'
    GROUP BY pitcher_id
    HAVING SUM(bf_30d) >= 30  -- Minimum playing time
),
ranked_pitchers AS (
    SELECT 
        player_id,
        k_rate_30d,
        bb_rate_30d,
        hr_rate_30d,
        avg_velo_30d,
        arsenal_depth,
        total_bf_30d,
        -- Simple WAR estimate: (K% * 2 - BB% * 1.5 - HR% * 5 + Velo/10)
        (k_rate_30d * 2 - bb_rate_30d * 1.5 - hr_rate_30d * 5 + avg_velo_30d / 10) as war_estimate,
        ROW_NUMBER() OVER (ORDER BY (k_rate_30d * 2 - bb_rate_30d * 1.5 - hr_rate_30d * 5 + avg_velo_30d / 10) DESC) as rank
    FROM pitcher_war
)
SELECT 
    rp.player_id,
    rp.rank as star_rank,
    rp.war_estimate,
    rp.k_rate_30d,
    rp.bb_rate_30d,
    rp.hr_rate_30d,
    rp.avg_velo_30d,
    rp.arsenal_depth,
    rp.total_bf_30d,
    NOW() as computed_at
FROM ranked_pitchers rp
WHERE rp.rank <= 250;  -- Top 250 pitchers

CREATE UNIQUE INDEX IF NOT EXISTS idx_star_pitchers_player 
ON features.star_pitchers (player_id);

CREATE INDEX IF NOT EXISTS idx_star_pitchers_rank 
ON features.star_pitchers (star_rank);

-- Active roster view (players with games today)
CREATE MATERIALIZED VIEW IF NOT EXISTS features.active_roster AS
SELECT DISTINCT
    csp.player_id,
    csp.player_full_name as player_name,
    csp.position,
    csp.team_id,
    t.team_name,
    t.team_abbreviation,
    CASE 
        WHEN sb.player_id IS NOT NULL THEN 'batter'
        WHEN sp.player_id IS NOT NULL THEN 'pitcher'
        ELSE 'unknown'
    END as player_type,
    sb.star_rank as batter_rank,
    sp.star_rank as pitcher_rank,
    NOW() as computed_at
FROM core.current_season_players csp
LEFT JOIN features.star_batters sb ON csp.player_id = sb.player_id
LEFT JOIN features.star_pitchers sp ON csp.player_id = sp.player_id
LEFT JOIN core.teams t ON csp.team_id = t.team_id
WHERE csp.is_active = TRUE
  AND (sb.player_id IS NOT NULL OR sp.player_id IS NOT NULL);

CREATE INDEX IF NOT EXISTS idx_active_roster_team 
ON features.active_roster (team_id);

CREATE INDEX IF NOT EXISTS idx_active_roster_player 
ON features.active_roster (player_id);

-- Star matchups (pre-computed head-to-head for star players)
CREATE MATERIALIZED VIEW IF NOT EXISTS features.star_matchups AS
SELECT 
    pmh.pitcher_id,
    pmh.batter_id,
    sp.star_rank as pitcher_rank,
    sb.star_rank as batter_rank,
    pmh.total_pas,
    pmh.matchup_avg,
    pmh.matchup_k_rate,
    pmh.last_matchup_date,
    -- Calculate matchup advantage (-1 to +1, positive favors pitcher)
    CASE 
        WHEN pmh.total_pas >= 10 THEN
            (pmh.matchup_k_rate / 100.0 * 0.5 + 
             (1 - pmh.matchup_avg) * 0.5 - 
             0.25)
        ELSE NULL
    END as matchup_advantage,
    NOW() as computed_at
FROM features.player_matchup_history pmh
JOIN features.star_pitchers sp ON pmh.pitcher_id = sp.player_id
JOIN features.star_batters sb ON pmh.batter_id = sb.player_id
WHERE pmh.total_pas >= 5  -- At least 5 PAs
ORDER BY pmh.total_pas DESC;

CREATE INDEX IF NOT EXISTS idx_star_matchups_pitcher 
ON features.star_matchups (pitcher_id);

CREATE INDEX IF NOT EXISTS idx_star_matchups_batter 
ON features.star_matchups (batter_id);

-- Comments
COMMENT ON MATERIALIZED VIEW features.star_batters IS 
'Top 250 batters by WAR estimate. Refreshed every 15 minutes. Used for fast player lookups in live predictions.';

COMMENT ON MATERIALIZED VIEW features.star_pitchers IS 
'Top 250 pitchers by WAR estimate. Refreshed every 15 minutes. Used for fast player lookups in live predictions.';

COMMENT ON MATERIALIZED VIEW features.active_roster IS 
'Active players with star rankings. Refreshed hourly during season.';

COMMENT ON MATERIALIZED VIEW features.star_matchups IS 
'Pre-computed matchups between star players. Refreshed daily.';
