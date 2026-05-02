/*
File: sql/50_features/5041_features_player_context.sql
Purpose: Player context features with 30-day rolling averages
Author: Agent Cascade
Date: 2026-05-02
Depends On: sql/30_core/313_core_live_pitch_events.sql, features_pitch.base_features
Called By: baseball/features/player_context.py, model training pipeline

Tables:
- features.player_batter_30day: Batter performance last 30 days
- features.player_pitcher_30day: Pitcher performance last 30 days
- features.player_matchup_history: Head-to-head matchup stats

Notes:
- Rolling windows: 7-day, 14-day, 30-day for different contexts
- Updated via materialized view refresh (not real-time)
- Used for model features and live prediction context
*/

CREATE SCHEMA IF NOT EXISTS features;

-- Batter performance (last 30 days)
CREATE MATERIALIZED VIEW IF NOT EXISTS features.player_batter_30day AS
WITH batter_stats AS (
    SELECT 
        bf.batter_id,
        DATE(bf.game_date) as stat_date,
        COUNT(*) as pa_count,
        SUM(CASE WHEN bf.outcome_tier1 = 'BallInPlay' THEN 1 ELSE 0 END) as bip_count,
        SUM(CASE WHEN bf.outcome_tier2 IN ('Single', 'Double', 'Triple', 'HR') THEN 1 ELSE 0 END) as hit_count,
        SUM(CASE WHEN bf.outcome_tier2 = 'Single' THEN 1 ELSE 0 END) as single_count,
        SUM(CASE WHEN bf.outcome_tier2 = 'Double' THEN 1 ELSE 0 END) as double_count,
        SUM(CASE WHEN bf.outcome_tier2 = 'Triple' THEN 1 ELSE 0 END) as triple_count,
        SUM(CASE WHEN bf.outcome_tier2 = 'HR' THEN 1 ELSE 0 END) as hr_count,
        SUM(CASE WHEN bf.outcome_tier2 = 'Walk' THEN 1 ELSE 0 END) as walk_count,
        SUM(CASE WHEN bf.outcome_tier2 = 'K' THEN 1 ELSE 0 END) as k_count,
        SUM(CASE WHEN bf.outcome_tier2 = 'Out' THEN 1 ELSE 0 END) as out_count,
        AVG(CASE WHEN bf.outcome_tier1 = 'BallInPlay' THEN bf.launch_speed ELSE NULL END) as avg_ev,
        AVG(CASE WHEN bf.outcome_tier1 = 'BallInPlay' THEN bf.launch_angle ELSE NULL END) as avg_la
    FROM features_pitch.base_features bf
    WHERE bf.game_date >= CURRENT_DATE - INTERVAL '30 days'
    GROUP BY bf.batter_id, DATE(bf.game_date)
),
rolling_7day AS (
    SELECT 
        batter_id,
        stat_date,
        SUM(pa_count) OVER (PARTITION BY batter_id ORDER BY stat_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) as pa_7d,
        SUM(hit_count) OVER (PARTITION BY batter_id ORDER BY stat_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) as hits_7d,
        ROUND(100.0 * SUM(k_count) OVER (PARTITION BY batter_id ORDER BY stat_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) / 
            NULLIF(SUM(pa_count) OVER (PARTITION BY batter_id ORDER BY stat_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW), 0), 1) as k_rate_7d,
        ROUND(100.0 * SUM(walk_count) OVER (PARTITION BY batter_id ORDER BY stat_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) / 
            NULLIF(SUM(pa_count) OVER (PARTITION BY batter_id ORDER BY stat_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW), 0), 1) as bb_rate_7d
    FROM batter_stats
),
rolling_30day AS (
    SELECT 
        batter_id,
        stat_date,
        SUM(pa_count) OVER (PARTITION BY batter_id ORDER BY stat_date ROWS BETWEEN 29 PRECEDING AND CURRENT ROW) as pa_30d,
        SUM(hit_count) OVER (PARTITION BY batter_id ORDER BY stat_date ROWS BETWEEN 29 PRECEDING AND CURRENT ROW) as hits_30d,
        SUM(bip_count) OVER (PARTITION BY batter_id ORDER BY stat_date ROWS BETWEEN 29 PRECEDING AND CURRENT ROW) as bip_30d,
        SUM(hr_count) OVER (PARTITION BY batter_id ORDER BY stat_date ROWS BETWEEN 29 PRECEDING AND CURRENT ROW) as hr_30d,
        ROUND(100.0 * SUM(hit_count) OVER (PARTITION BY batter_id ORDER BY stat_date ROWS BETWEEN 29 PRECEDING AND CURRENT ROW) / 
            NULLIF(SUM(pa_count) OVER (PARTITION BY batter_id ORDER BY stat_date ROWS BETWEEN 29 PRECEDING AND CURRENT ROW), 0), 3) as avg_30d,
        ROUND(100.0 * SUM(k_count) OVER (PARTITION BY batter_id ORDER BY stat_date ROWS BETWEEN 29 PRECEDING AND CURRENT ROW) / 
            NULLIF(SUM(pa_count) OVER (PARTITION BY batter_id ORDER BY stat_date ROWS BETWEEN 29 PRECEDING AND CURRENT ROW), 0), 1) as k_rate_30d,
        ROUND(100.0 * SUM(walk_count) OVER (PARTITION BY batter_id ORDER BY stat_date ROWS BETWEEN 29 PRECEDING AND CURRENT ROW) / 
            NULLIF(SUM(pa_count) OVER (PARTITION BY batter_id ORDER BY stat_date ROWS BETWEEN 29 PRECEDING AND CURRENT ROW), 0), 1) as bb_rate_30d,
        ROUND(100.0 * SUM(hr_count) OVER (PARTITION BY batter_id ORDER BY stat_date ROWS BETWEEN 29 PRECEDING AND CURRENT ROW) / 
            NULLIF(SUM(bip_count) OVER (PARTITION BY batter_id ORDER BY stat_date ROWS BETWEEN 29 PRECEDING AND CURRENT ROW), 0), 1) as hr_rate_30d,
        AVG(avg_ev) OVER (PARTITION BY batter_id ORDER BY stat_date ROWS BETWEEN 29 PRECEDING AND CURRENT ROW) as avg_ev_30d
    FROM batter_stats
)
SELECT 
    r30.batter_id,
    r30.stat_date as context_date,
    r7.pa_7d,
    r7.k_rate_7d,
    r7.bb_rate_7d,
    r30.pa_30d,
    r30.avg_30d,
    r30.k_rate_30d,
    r30.bb_rate_30d,
    r30.hr_rate_30d,
    r30.avg_ev_30d,
    r30.hits_30d,
    r30.hr_30d,
    NOW() as computed_at
FROM rolling_30day r30
JOIN rolling_7day r7 ON r30.batter_id = r7.batter_id AND r30.stat_date = r7.stat_date
WHERE r30.pa_30d >= 10;  -- Minimum sample size

CREATE UNIQUE INDEX IF NOT EXISTS idx_player_batter_30day_pk 
ON features.player_batter_30day (batter_id, context_date);

-- Pitcher performance (last 30 days)
CREATE MATERIALIZED VIEW IF NOT EXISTS features.player_pitcher_30day AS
WITH pitcher_stats AS (
    SELECT 
        bf.pitcher_id,
        DATE(bf.game_date) as stat_date,
        COUNT(*) as bf_count,  -- Batters faced
        SUM(CASE WHEN bf.outcome_tier1 = 'Strike' THEN 1 ELSE 0 END) as strike_count,
        SUM(CASE WHEN bf.outcome_tier1 = 'Ball' THEN 1 ELSE 0 END) as ball_count,
        SUM(CASE WHEN bf.outcome_tier1 = 'BallInPlay' THEN 1 ELSE 0 END) as bip_count,
        SUM(CASE WHEN bf.outcome_tier2 IN ('Out') THEN 1 ELSE 0 END) as out_count,
        SUM(CASE WHEN bf.outcome_tier2 IN ('Single', 'Double', 'Triple', 'HR') THEN 1 ELSE 0 END) as hit_count,
        SUM(CASE WHEN bf.outcome_tier2 = 'HR' THEN 1 ELSE 0 END) as hr_count,
        SUM(CASE WHEN bf.outcome_tier2 = 'K' THEN 1 ELSE 0 END) as k_count,
        SUM(CASE WHEN bf.outcome_tier2 = 'Walk' THEN 1 ELSE 0 END) as bb_count,
        AVG(bf.release_speed) as avg_velo,
        AVG(bf.spin_axis) as avg_spin_axis,
        COUNT(DISTINCT bf.pitch_type) as pitch_type_count
    FROM features_pitch.base_features bf
    WHERE bf.game_date >= CURRENT_DATE - INTERVAL '30 days'
    GROUP BY bf.pitcher_id, DATE(bf.game_date)
),
rolling_30day AS (
    SELECT 
        pitcher_id,
        stat_date,
        SUM(bf_count) OVER (PARTITION BY pitcher_id ORDER BY stat_date ROWS BETWEEN 29 PRECEDING AND CURRENT ROW) as bf_30d,
        SUM(k_count) OVER (PARTITION BY pitcher_id ORDER BY stat_date ROWS BETWEEN 29 PRECEDING AND CURRENT ROW) as k_30d,
        SUM(bb_count) OVER (PARTITION BY pitcher_id ORDER BY stat_date ROWS BETWEEN 29 PRECEDING AND CURRENT ROW) as bb_30d,
        SUM(hr_count) OVER (PARTITION BY pitcher_id ORDER BY stat_date ROWS BETWEEN 29 PRECEDING AND CURRENT ROW) as hr_30d,
        SUM(hit_count) OVER (PARTITION BY pitcher_id ORDER BY stat_date ROWS BETWEEN 29 PRECEDING AND CURRENT ROW) as hits_30d,
        ROUND(100.0 * SUM(k_count) OVER (PARTITION BY pitcher_id ORDER BY stat_date ROWS BETWEEN 29 PRECEDING AND CURRENT ROW) / 
            NULLIF(SUM(bf_count) OVER (PARTITION BY pitcher_id ORDER BY stat_date ROWS BETWEEN 29 PRECEDING AND CURRENT ROW), 0), 1) as k_rate_30d,
        ROUND(100.0 * SUM(bb_count) OVER (PARTITION BY pitcher_id ORDER BY stat_date ROWS BETWEEN 29 PRECEDING AND CURRENT ROW) / 
            NULLIF(SUM(bf_count) OVER (PARTITION BY pitcher_id ORDER BY stat_date ROWS BETWEEN 29 PRECEDING AND CURRENT ROW), 0), 1) as bb_rate_30d,
        ROUND(100.0 * SUM(hr_count) OVER (PARTITION BY pitcher_id ORDER BY stat_date ROWS BETWEEN 29 PRECEDING AND CURRENT ROW) / 
            NULLIF(SUM(bf_count) OVER (PARTITION BY pitcher_id ORDER BY stat_date ROWS BETWEEN 29 PRECEDING AND CURRENT ROW), 0), 1) as hr_rate_30d,
        AVG(avg_velo) OVER (PARTITION BY pitcher_id ORDER BY stat_date ROWS BETWEEN 29 PRECEDING AND CURRENT ROW) as avg_velo_30d,
        AVG(pitch_type_count) OVER (PARTITION BY pitcher_id ORDER BY stat_date ROWS BETWEEN 29 PRECEDING AND CURRENT ROW) as arsenal_depth
    FROM pitcher_stats
)
SELECT 
    pitcher_id,
    stat_date as context_date,
    bf_30d,
    k_rate_30d,
    bb_rate_30d,
    hr_rate_30d,
    k_30d,
    avg_velo_30d,
    arsenal_depth,
    NOW() as computed_at
FROM rolling_30day
WHERE bf_30d >= 20;  -- Minimum sample size

CREATE UNIQUE INDEX IF NOT EXISTS idx_player_pitcher_30day_pk 
ON features.player_pitcher_30day (pitcher_id, context_date);

-- Head-to-head matchup history
CREATE MATERIALIZED VIEW IF NOT EXISTS features.player_matchup_history AS
SELECT 
    bf.pitcher_id,
    bf.batter_id,
    COUNT(*) as total_pas,
    SUM(CASE WHEN bf.outcome_tier2 IN ('Single', 'Double', 'Triple', 'HR') THEN 1 ELSE 0 END) as hits,
    SUM(CASE WHEN bf.outcome_tier2 = 'K' THEN 1 ELSE 0 END) as strikeouts,
    SUM(CASE WHEN bf.outcome_tier2 = 'Walk' THEN 1 ELSE 0 END) as walks,
    ROUND(100.0 * SUM(CASE WHEN bf.outcome_tier2 IN ('Single', 'Double', 'Triple', 'HR') THEN 1 ELSE 0 END) / 
        NULLIF(COUNT(*), 0), 3) as matchup_avg,
    ROUND(100.0 * SUM(CASE WHEN bf.outcome_tier2 = 'K' THEN 1 ELSE 0 END) / 
        NULLIF(COUNT(*), 0), 1) as matchup_k_rate,
    MAX(bf.game_date) as last_matchup_date,
    NOW() as computed_at
FROM features_pitch.base_features bf
WHERE bf.game_date >= CURRENT_DATE - INTERVAL '3 years'  -- Last 3 seasons
GROUP BY bf.pitcher_id, bf.batter_id
HAVING COUNT(*) >= 3;  -- Minimum 3 plate appearances

CREATE UNIQUE INDEX IF NOT EXISTS idx_player_matchup_history_pk 
ON features.player_matchup_history (pitcher_id, batter_id);

-- Comments
COMMENT ON MATERIALIZED VIEW features.player_batter_30day IS 
'30-day rolling batter performance stats for model features. Includes PA count, AVG, K%, BB%, exit velocity. Refresh daily.';

COMMENT ON MATERIALIZED VIEW features.player_pitcher_30day IS 
'30-day rolling pitcher performance stats for model features. Includes BF count, K%, BB%, HR%, velocity. Refresh daily.';

COMMENT ON MATERIALIZED VIEW features.player_matchup_history IS 
'Historical head-to-head matchup stats (last 3 years). Includes matchup AVG, K rate, last encounter date. Refresh weekly.';
