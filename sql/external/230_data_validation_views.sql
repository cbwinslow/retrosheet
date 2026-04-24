-- Data Validation Views
-- Purpose: Comprehensive data quality validation across all data sources
-- Validates tables, rows, counts, columns, quality, duplicates, errors, nulls, date ranges, overlap

-- ============================================
-- Create validation schema first
-- ============================================

CREATE SCHEMA IF NOT EXISTS validation;

-- ============================================
-- Table Row Counts and Basic Stats
-- ============================================

CREATE OR REPLACE VIEW validation.table_row_counts AS
SELECT
    schemaname,
    relname AS tablename,
    n_tup_ins AS total_inserts,
    n_tup_upd AS total_updates,
    n_tup_del AS total_deletes,
    n_live_tup AS live_rows,
    n_dead_tup AS dead_rows,
    last_vacuum,
    last_autovacuum,
    last_analyze,
    last_autoanalyze
FROM pg_stat_user_tables
WHERE schemaname IN ('raw_retrosheet', 'raw_espn', 'raw_mlb', 'raw_statcast', 'bridge', 'core', 'features', 'models', 'predictions')
ORDER BY schemaname, relname;

COMMENT ON VIEW validation.table_row_counts IS 'Basic row count and maintenance statistics for all warehouse tables';

-- ============================================
-- Column Null Analysis
-- ============================================

CREATE OR REPLACE VIEW validation.column_null_analysis AS
SELECT
    schemaname,
    tablename,
    attname AS column_name,
    n_distinct AS distinct_values,
    null_frac AS null_fraction,
    avg_width AS average_width
FROM pg_stats
WHERE schemaname IN ('raw_retrosheet', 'raw_espn', 'raw_mlb', 'raw_statcast', 'bridge', 'core', 'features', 'models', 'predictions')
ORDER BY schemaname ASC, tablename ASC, null_frac DESC;

COMMENT ON VIEW validation.column_null_analysis IS 'Null fraction analysis for all columns across warehouse tables';

-- ============================================
-- Duplicate Detection
-- ============================================

CREATE OR REPLACE VIEW validation.duplicate_analysis AS
WITH duplicate_counts AS (
    SELECT
        'raw_espn.game_snapshots' AS table_name,
        game_id::text AS key_value,
        COUNT(*) AS row_count
    FROM raw_espn.game_snapshots
    GROUP BY game_id
    HAVING COUNT(*) > 1

    UNION ALL

    SELECT
        'raw_espn.plays_snapshots',
        game_id::text,
        COUNT(*)
    FROM raw_espn.plays_snapshots
    GROUP BY game_id
    HAVING COUNT(*) > 1

    UNION ALL

    SELECT
        'raw_espn.schedule_snapshots',
        date::text,
        COUNT(*)
    FROM raw_espn.schedule_snapshots
    GROUP BY date
    HAVING COUNT(*) > 1
)

SELECT
    table_name,
    COUNT(*) AS duplicate_groups,
    SUM(row_count) AS total_duplicate_rows
FROM duplicate_counts
GROUP BY table_name;

COMMENT ON VIEW validation.duplicate_analysis IS 'Duplicate row analysis for key tables';

-- ============================================
-- ESPN Data Quality Validation
-- ============================================

CREATE OR REPLACE VIEW validation.espn_data_quality AS
SELECT
    'game_snapshots' AS table_name,
    COUNT(*) AS total_rows,
    COUNT(DISTINCT game_id) AS unique_games,
    COUNT(game_date) AS rows_with_date,
    COUNT(season) AS rows_with_season,
    MIN(game_date) AS earliest_date,
    MAX(game_date) AS latest_date,
    COUNT(DISTINCT season) AS unique_seasons,
    ROUND(COUNT(game_date)::numeric / COUNT(*) * 100, 2) AS date_completeness_pct,
    ROUND(COUNT(season)::numeric / COUNT(*) * 100, 2) AS season_completeness_pct
FROM raw_espn.game_snapshots

UNION ALL

SELECT
    'plays_snapshots',
    COUNT(*),
    COUNT(DISTINCT game_id),
    COUNT(game_date),
    COUNT(season),
    MIN(game_date),
    MAX(game_date),
    COUNT(DISTINCT season),
    ROUND(COUNT(game_date)::numeric / NULLIF(COUNT(*), 0) * 100, 2),
    ROUND(COUNT(season)::numeric / NULLIF(COUNT(*), 0) * 100, 2)
FROM raw_espn.plays_snapshots

UNION ALL

SELECT
    'schedule_snapshots',
    COUNT(*),
    COUNT(DISTINCT date) AS unique_dates,
    COUNT(date),
    COUNT(season),
    MIN(date),
    MAX(date),
    COUNT(DISTINCT season),
    ROUND(COUNT(date)::numeric / COUNT(*) * 100, 2),
    ROUND(COUNT(season)::numeric / COUNT(*) * 100, 2)
FROM raw_espn.schedule_snapshots;

COMMENT ON VIEW validation.espn_data_quality IS 'Data quality metrics for ESPN tables including completeness and date ranges';

-- ============================================
-- ESPN Season Coverage
-- ============================================

CREATE OR REPLACE VIEW validation.espn_season_coverage AS
SELECT
    season,
    COUNT(*) AS games,
    MIN(game_date) AS season_start,
    MAX(game_date) AS season_end
FROM raw_espn.game_snapshots
WHERE season IS NOT NULL
GROUP BY season
ORDER BY season;

COMMENT ON VIEW validation.espn_season_coverage IS 'Season-by-season game count and date range for ESPN data';

-- ============================================
-- Retrosheet Data Quality Validation
-- ============================================

CREATE OR REPLACE VIEW validation.retrosheet_data_quality AS
SELECT
    'biofile' AS data_type,
    COUNT(*) AS rows
FROM raw_retrosheet.biofile

UNION ALL

SELECT
    'ballparks',
    COUNT(*)
FROM raw_retrosheet.ballparks_reference

UNION ALL

SELECT
    'teams',
    COUNT(*)
FROM raw_retrosheet.teams_reference;

COMMENT ON VIEW validation.retrosheet_data_quality IS 'Data quality metrics for Retrosheet reference tables';

-- ============================================
-- Statcast Data Quality Validation
-- ============================================

CREATE OR REPLACE VIEW validation.statcast_data_quality AS
SELECT
    'statcast' AS table_name,
    COUNT(*) AS total_rows,
    COUNT(DISTINCT game_pk) AS unique_games,
    COUNT(DISTINCT batter) AS unique_batters,
    COUNT(DISTINCT pitcher) AS unique_pitchers,
    MIN(game_date) AS earliest_date,
    MAX(game_date) AS latest_date,
    COUNT(DISTINCT game_year) AS unique_seasons
FROM raw_mlb.statcast;

COMMENT ON VIEW validation.statcast_data_quality IS 'Data quality metrics for Statcast pitch-level data';

-- ============================================
-- Ingest Run Tracking Validation
-- ============================================

CREATE OR REPLACE VIEW validation.ingest_run_summary AS
SELECT
    source_name,
    COUNT(*) AS total_runs,
    COUNT(*) FILTER (WHERE status = 'completed') AS completed_runs,
    COUNT(*) FILTER (WHERE status = 'failed') AS failed_runs,
    SUM(records_downloaded) AS total_downloaded,
    SUM(records_ingested) AS total_ingested,
    SUM(records_failed) AS total_failed,
    MIN(started_at) AS first_run,
    MAX(started_at) AS last_run,
    ROUND(SUM(records_failed)::numeric / NULLIF(SUM(records_downloaded), 0) * 100, 2) AS failure_rate_pct
FROM raw_retrosheet.ingest_runs
GROUP BY source_name
ORDER BY source_name;

COMMENT ON VIEW validation.ingest_run_summary IS 'Summary of ingest runs by data source including failure rates';

-- ============================================
-- Cross-Source Game ID Overlap
-- ============================================

CREATE OR REPLACE VIEW validation.game_id_overlap AS
SELECT
    'espn_statcast' AS overlap_type,
    COUNT(*) AS overlapping_games
FROM raw_espn.game_snapshots AS e
INNER JOIN raw_mlb.statcast AS s ON e.game_id = s.game_pk::text;

COMMENT ON VIEW validation.game_id_overlap IS 'Game ID overlap analysis between ESPN and Statcast';

-- ============================================
-- Comprehensive Data Quality Report
-- ============================================

CREATE OR REPLACE VIEW validation.data_quality_report AS
SELECT
    'ESPN Game Snapshots' AS data_source,
    'raw_espn.game_snapshots' AS table_name,
    (SELECT COUNT(*) FROM raw_espn.game_snapshots) AS total_rows,
    (SELECT COUNT(DISTINCT game_id) FROM raw_espn.game_snapshots) AS unique_records,
    (SELECT MIN(game_date)::text FROM raw_espn.game_snapshots) AS date_range_start,
    (SELECT MAX(game_date)::text FROM raw_espn.game_snapshots) AS date_range_end,
    (SELECT COUNT(DISTINCT season) FROM raw_espn.game_snapshots) AS seasons_covered,
    (SELECT ROUND(COUNT(game_date)::numeric / COUNT(*) * 100, 2) FROM raw_espn.game_snapshots) AS completeness_pct,
    (SELECT COUNT(*) - COUNT(DISTINCT game_id) FROM raw_espn.game_snapshots) AS duplicate_count,
    (
        SELECT SUM(records_failed) FROM raw_retrosheet.ingest_runs
        WHERE source_name = 'espn_api'
    ) AS ingest_failures

UNION ALL

SELECT
    'ESPN Plays Snapshots',
    'raw_espn.plays_snapshots',
    (SELECT COUNT(*) FROM raw_espn.plays_snapshots),
    (SELECT COUNT(DISTINCT game_id) FROM raw_espn.plays_snapshots),
    (SELECT MIN(game_date)::text FROM raw_espn.plays_snapshots),
    (SELECT MAX(game_date)::text FROM raw_espn.plays_snapshots),
    (SELECT COUNT(DISTINCT season) FROM raw_espn.plays_snapshots),
    (SELECT ROUND(COUNT(game_date)::numeric / NULLIF(COUNT(*), 0) * 100, 2) FROM raw_espn.plays_snapshots),
    (SELECT COUNT(*) - COUNT(DISTINCT game_id) FROM raw_espn.plays_snapshots),
    NULL

UNION ALL

SELECT
    'Statcast Pitch-Level',
    'raw_mlb.statcast',
    (SELECT COUNT(*) FROM raw_mlb.statcast),
    (SELECT COUNT(DISTINCT game_pk) FROM raw_mlb.statcast),
    (SELECT MIN(game_date)::text FROM raw_mlb.statcast),
    (SELECT MAX(game_date)::text FROM raw_mlb.statcast),
    (SELECT COUNT(DISTINCT game_year) FROM raw_mlb.statcast),
    100.00,
    0,
    (
        SELECT SUM(records_failed) FROM raw_retrosheet.ingest_runs
        WHERE source_name = 'statcast'
    );

COMMENT ON VIEW validation.data_quality_report IS 'Comprehensive data quality report across all major data sources';

-- ============================================
-- Materialized View for Fast Access to Quality Report
-- ============================================

CREATE MATERIALIZED VIEW IF NOT EXISTS validation.data_quality_summary AS
SELECT
    'ESPN Game Data' AS source,
    (SELECT COUNT(*) FROM raw_espn.game_snapshots) AS games,
    (SELECT COUNT(DISTINCT season) FROM raw_espn.game_snapshots) AS seasons,
    (SELECT MIN(game_date)::text FROM raw_espn.game_snapshots) AS start_date,
    (SELECT MAX(game_date)::text FROM raw_espn.game_snapshots) AS end_date,
    (SELECT ROUND(COUNT(game_date)::numeric / COUNT(*) * 100, 2) FROM raw_espn.game_snapshots) AS completeness_pct

UNION ALL

SELECT
    'Statcast Pitch-Level',
    (SELECT COUNT(DISTINCT game_pk) FROM raw_mlb.statcast),
    (SELECT COUNT(DISTINCT game_year) FROM raw_mlb.statcast),
    (SELECT MIN(game_date)::text FROM raw_mlb.statcast),
    (SELECT MAX(game_date)::text FROM raw_mlb.statcast),
    100.00;

COMMENT ON MATERIALIZED VIEW validation.data_quality_summary IS 'Materialized summary of data quality metrics for quick access';

-- Create refresh function
CREATE OR REPLACE FUNCTION validation.refresh_data_quality_summary()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW validation.data_quality_summary;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION validation.refresh_data_quality_summary IS 'Refresh the materialized data quality summary view';
