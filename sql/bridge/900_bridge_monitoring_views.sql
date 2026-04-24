-- File: sql/bridge/900_bridge_monitoring_views.sql
-- Purpose: Monitoring views for bridge table counts, coverage, quality, duplicates
-- Author: Agent Cascade
-- Date: 2026-04-24
CREATE OR REPLACE VIEW bridge.bridge_table_counts AS
SELECT 
    'player_xref' as table_name,
    COUNT(*) as total_rows,
    COUNT(DISTINCT retrosheet_id) as retrosheet_ids,
    COUNT(DISTINCT mlb_id) as mlb_ids,
    COUNT(DISTINCT baseball_reference_id) as bref_ids
FROM bridge.player_xref
UNION ALL
SELECT 
    'team_xref' as table_name,
    COUNT(*) as total_rows,
    COUNT(DISTINCT retrosheet_team_id) as retrosheet_ids,
    COUNT(DISTINCT mlb_team_id) as mlb_ids,
    0 as bref_ids
FROM bridge.team_xref
UNION ALL
SELECT 
    'park_xref' as table_name,
    COUNT(*) as total_rows,
    COUNT(DISTINCT retrosheet_park_id) as retrosheet_ids,
    COUNT(DISTINCT mlb_venue_id) as mlb_ids,
    0 as bref_ids
FROM bridge.park_xref
UNION ALL
SELECT 
    'game_xref' as table_name,
    COUNT(*) as total_rows,
    COUNT(DISTINCT retrosheet_game_id) as retrosheet_ids,
    COUNT(DISTINCT mlb_game_pk) as mlb_ids,
    0 as bref_ids
FROM bridge.game_xref
UNION ALL
SELECT 
    'external_player_xref' as table_name,
    COUNT(*) as total_rows,
    COUNT(DISTINCT retrosheet_player_id) as retrosheet_ids,
    0 as mlb_ids,
    0 as bref_ids
FROM bridge.external_player_xref
UNION ALL
SELECT 
    'coach_xref' as table_name,
    COUNT(*) as total_rows,
    COUNT(DISTINCT retrosheet_coach_id) as retrosheet_ids,
    COUNT(DISTINCT mlb_coach_id) as mlb_ids,
    0 as bref_ids
FROM bridge.coach_xref
UNION ALL
SELECT 
    'umpire_xref' as table_name,
    COUNT(*) as total_rows,
    COUNT(DISTINCT retrosheet_umpire_id) as retrosheet_ids,
    COUNT(DISTINCT mlb_umpire_id) as mlb_ids,
    0 as bref_ids
FROM bridge.umpire_xref;

COMMENT ON VIEW bridge.bridge_table_counts IS 'Row counts and ID coverage statistics for all bridge tables';

-- View: External player ID coverage by source
CREATE OR REPLACE VIEW bridge.external_player_coverage AS
SELECT 
    external_source,
    COUNT(*) as total_mappings,
    COUNT(DISTINCT retrosheet_player_id) as unique_retrosheet_players,
    COUNT(DISTINCT external_player_id) as unique_external_ids
FROM bridge.external_player_xref
GROUP BY external_source
ORDER BY total_mappings DESC;

COMMENT ON VIEW bridge.external_player_coverage IS 'Coverage statistics for external player ID mappings by source';

-- View: Unmapped IDs (players without certain ID mappings)
CREATE OR REPLACE VIEW bridge.unmapped_player_ids AS
SELECT 
    'mlb_id_missing' as missing_type,
    COUNT(*) as count
FROM bridge.player_xref
WHERE retrosheet_id IS NOT NULL AND mlb_id IS NULL
UNION ALL
SELECT 
    'bref_id_missing' as missing_type,
    COUNT(*) as count
FROM bridge.player_xref
WHERE retrosheet_id IS NOT NULL AND baseball_reference_id IS NULL
UNION ALL
SELECT 
    'retrosheet_id_missing' as missing_type,
    COUNT(*) as count
FROM bridge.player_xref
WHERE retrosheet_id IS NULL AND mlb_id IS NOT NULL;

COMMENT ON VIEW bridge.unmapped_player_ids IS 'Counts of players missing specific ID mappings';

-- View: Team season coverage
CREATE OR REPLACE VIEW bridge.team_season_coverage AS
SELECT 
    retrosheet_team_id,
    abbreviation,
    name,
    valid_from_season,
    valid_to_season,
    CASE 
        WHEN valid_to_season IS NULL THEN 'Active'
        ELSE 'Historical'
    END as status
FROM bridge.team_xref
WHERE valid_from_season IS NOT NULL
ORDER BY 
    CASE WHEN valid_to_season IS NULL THEN 0 ELSE 1 END,
    retrosheet_team_id;

COMMENT ON VIEW bridge.team_season_coverage IS 'Team coverage with season ranges and active/historical status';

-- View: Bridge data quality checks
CREATE OR REPLACE VIEW bridge.bridge_data_quality AS
SELECT 
    'player_xref_null_retrosheet' as check_name,
    COUNT(*) as issue_count
FROM bridge.player_xref
WHERE retrosheet_id IS NULL AND (mlb_id IS NOT NULL OR baseball_reference_id IS NOT NULL)
UNION ALL
SELECT 
    'team_xref_null_mlb' as check_name,
    COUNT(*) as issue_count
FROM bridge.team_xref
WHERE retrosheet_team_id IS NOT NULL AND mlb_team_id IS NULL
UNION ALL
SELECT 
    'external_player_null_retrosheet' as check_name,
    COUNT(*) as issue_count
FROM bridge.external_player_xref
WHERE retrosheet_player_id IS NULL OR retrosheet_player_id = '0'
UNION ALL
SELECT 
    'game_xref_date_mismatch' as check_name,
    COUNT(*) as issue_count
FROM bridge.game_xref
WHERE retrosheet_game_id IS NOT NULL 
AND mlb_game_pk IS NOT NULL 
AND game_date IS NULL;

COMMENT ON VIEW bridge.bridge_data_quality IS 'Data quality checks for bridge tables identifying potential issues';

-- View: Cross-source player mapping summary
CREATE OR REPLACE VIEW bridge.player_mapping_summary AS
SELECT 
    px.retrosheet_id,
    px.name_first,
    px.name_last,
    px.mlb_id,
    px.baseball_reference_id,
    ep.statcast_external_id,
    ep.lahman_external_id,
    ep.bref_external_id
FROM bridge.player_xref px
LEFT JOIN (
    SELECT 
        retrosheet_player_id,
        MAX(CASE WHEN external_source = 'statcast' THEN external_player_id END) as statcast_external_id,
        MAX(CASE WHEN external_source = 'lahman' THEN external_player_id END) as lahman_external_id,
        MAX(CASE WHEN external_source = 'baseball_reference' THEN external_player_id END) as bref_external_id
    FROM bridge.external_player_xref
    GROUP BY retrosheet_player_id
) ep ON px.retrosheet_id = ep.retrosheet_player_id
WHERE px.retrosheet_id IS NOT NULL
ORDER BY px.name_last, px.name_first;

COMMENT ON VIEW bridge.player_mapping_summary IS 'Summary of all ID mappings for each player across all sources';

-- View: Duplicate ID detection
CREATE OR REPLACE VIEW bridge.duplicate_id_detection AS
SELECT 
    'player_xref_duplicate_mlb' as check_name,
    mlb_id as duplicate_id,
    COUNT(*) as occurrence_count
FROM bridge.player_xref
WHERE mlb_id IS NOT NULL
GROUP BY mlb_id
HAVING COUNT(*) > 1
UNION ALL
SELECT 
    'player_xref_duplicate_bref' as check_name,
    baseball_reference_id as duplicate_id,
    COUNT(*) as occurrence_count
FROM bridge.player_xref
WHERE baseball_reference_id IS NOT NULL
GROUP BY baseball_reference_id
HAVING COUNT(*) > 1
UNION ALL
SELECT 
    'team_xref_duplicate_mlb' as check_name,
    mlb_team_id::text as duplicate_id,
    COUNT(*) as occurrence_count
FROM bridge.team_xref
WHERE mlb_team_id IS NOT NULL
GROUP BY mlb_team_id
HAVING COUNT(*) > 1
UNION ALL
SELECT 
    'external_player_duplicate_source_id' as check_name,
    external_source || ':' || external_player_id as duplicate_id,
    COUNT(*) as occurrence_count
FROM bridge.external_player_xref
GROUP BY external_source, external_player_id
HAVING COUNT(*) > 1;

COMMENT ON VIEW bridge.duplicate_id_detection IS 'Detects duplicate ID entries across bridge tables';

-- View: Orphaned external IDs (IDs in external tables not in main bridge tables)
CREATE OR REPLACE VIEW bridge.orphaned_external_ids AS
SELECT 
    'statcast_mlb_not_in_player_xref' as check_name,
    COUNT(*) as orphan_count
FROM (
    SELECT DISTINCT batter::text as mlb_id FROM raw_mlb.statcast WHERE batter IS NOT NULL
    UNION
    SELECT DISTINCT pitcher::text as mlb_id FROM raw_mlb.statcast WHERE pitcher IS NOT NULL
) s
WHERE s.mlb_id NOT IN (
    SELECT mlb_id::text FROM bridge.player_xref WHERE mlb_id IS NOT NULL
)
UNION ALL
SELECT 
    'external_player_retrosheet_not_in_player_xref' as check_name,
    COUNT(*) as orphan_count
FROM bridge.external_player_xref
WHERE retrosheet_player_id IS NOT NULL
AND retrosheet_player_id != ''
AND retrosheet_player_id NOT IN (
    SELECT retrosheet_id FROM bridge.player_xref WHERE retrosheet_id IS NOT NULL
);

COMMENT ON VIEW bridge.orphaned_external_ids IS 'Detects external IDs that reference non-existent Retrosheet IDs';

-- View: Cross-reference consistency checks
CREATE OR REPLACE VIEW bridge.cross_reference_consistency AS
SELECT 
    'external_player_mlb_in_player_xref' as check_name,
    COUNT(*) as consistent_count,
    COUNT(*) - COUNT(px.mlb_id) as inconsistent_count
FROM bridge.external_player_xref ep
LEFT JOIN bridge.player_xref px ON ep.retrosheet_player_id = px.retrosheet_id
WHERE ep.external_source = 'statcast'
AND ep.retrosheet_player_id IS NOT NULL
UNION ALL
SELECT 
    'external_player_bref_in_player_xref' as check_name,
    COUNT(*) as consistent_count,
    COUNT(*) - COUNT(px.baseball_reference_id) as inconsistent_count
FROM bridge.external_player_xref ep
LEFT JOIN bridge.player_xref px ON ep.retrosheet_player_id = px.retrosheet_id
WHERE ep.external_source = 'baseball_reference'
AND ep.retrosheet_player_id IS NOT NULL
UNION ALL
SELECT 
    'game_xref_teams_in_team_xref' as check_name,
    COUNT(*) as consistent_count,
    COUNT(*) - COUNT(txh.mlb_team_id) - COUNT(txa.mlb_team_id) as inconsistent_count
FROM bridge.game_xref gx
LEFT JOIN bridge.team_xref txh ON gx.mlb_home_team_id = txh.mlb_team_id
LEFT JOIN bridge.team_xref txa ON gx.mlb_away_team_id = txa.mlb_team_id
WHERE gx.mlb_home_team_id IS NOT NULL OR gx.mlb_away_team_id IS NOT NULL;

COMMENT ON VIEW bridge.cross_reference_consistency IS 'Checks consistency between bridge table references';

-- View: Season coverage gaps
CREATE OR REPLACE VIEW bridge.season_coverage_gaps AS
SELECT 
    'team_season_gaps' as gap_type,
    retrosheet_team_id,
    abbreviation,
    valid_from_season,
    valid_to_season,
    CASE 
        WHEN valid_to_season IS NULL THEN 'No end season'
        WHEN valid_from_season IS NULL THEN 'No start season'
        WHEN valid_to_season < valid_from_season THEN 'Invalid range'
        ELSE 'Valid range'
    END as status
FROM bridge.team_xref
WHERE valid_from_season IS NULL 
   OR valid_to_season IS NULL
   OR valid_to_season < valid_from_season
ORDER BY retrosheet_team_id;

COMMENT ON VIEW bridge.season_coverage_gaps AS 'Identifies teams with incomplete or invalid season ranges';

-- View: Mapping completeness by entity type
CREATE OR REPLACE VIEW bridge.mapping_completeness AS
SELECT 
    'players' as entity_type,
    COUNT(*) as total_entities,
    COUNT(mlb_id) as with_mlb_id,
    COUNT(baseball_reference_id) as with_bref_id,
    ROUND(100.0 * COUNT(mlb_id) / NULLIF(COUNT(*), 0), 2) as mlb_coverage_pct,
    ROUND(100.0 * COUNT(baseball_reference_id) / NULLIF(COUNT(*), 0), 2) as bref_coverage_pct
FROM bridge.player_xref
WHERE retrosheet_id IS NOT NULL
UNION ALL
SELECT 
    'teams' as entity_type,
    COUNT(*) as total_entities,
    COUNT(mlb_team_id) as with_mlb_id,
    0 as with_bref_id,
    ROUND(100.0 * COUNT(mlb_team_id) / NULLIF(COUNT(*), 0), 2) as mlb_coverage_pct,
    0 as bref_coverage_pct
FROM bridge.team_xref
WHERE retrosheet_team_id IS NOT NULL
UNION ALL
SELECT 
    'parks' as entity_type,
    COUNT(*) as total_entities,
    COUNT(mlb_venue_id) as with_mlb_id,
    0 as with_bref_id,
    ROUND(100.0 * COUNT(mlb_venue_id) / NULLIF(COUNT(*), 0), 2) as mlb_coverage_pct,
    0 as bref_coverage_pct
FROM bridge.park_xref
WHERE retrosheet_park_id IS NOT NULL;

COMMENT ON VIEW bridge.mapping_completeness IS 'Overall mapping completeness statistics by entity type';

