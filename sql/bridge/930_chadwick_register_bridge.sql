-- File: sql/bridge/930_chadwick_register_bridge.sql
-- Purpose: Populate bridge.player_xref from Chadwick Bureau Register data
-- Author: Agent Cascade
-- Date: 2026-04-24
-- Depends On: bridge.player_xref table, Chadwick Register CSV files
-- Called By: scripts/bridge/populate_bridge_tables.py, orchestration scripts

/*
Chadwick Bureau Register Bridge Population
==========================================

This procedure populates player ID mappings using the Chadwick Bureau Register,
the most comprehensive authority file for baseball player identities.

Data Source: https://github.com/chadwickbureau/register
Files: people-{0-9,a-f}.csv (16 files, ~20,000+ players)
Key Fields:
  - key_uuid: Chadwick's canonical UUID (primary key)
  - key_mlbam: MLBAM ID (Statcast/MLB API)
  - key_retro: Retrosheet ID
  - key_bbref: Baseball-Reference ID
  - key_fangraphs: FanGraphs ID
  - name_first, name_last: Player names
  - bats, throws: Handedness

Coverage: North American professional leagues from 19th century to present
*/

-- ============================================================================
-- STAGE 1: Create staging table for Chadwick Register data
-- ============================================================================

CREATE TABLE IF NOT EXISTS bridge._staging_chadwick_register (
    key_uuid TEXT PRIMARY KEY,
    key_mlbam TEXT,
    key_retro TEXT,
    key_bbref TEXT,
    key_fangraphs TEXT,
    key_baseball_prospectus TEXT,
    key_cbs TEXT,
    key_espn TEXT,
    key_fanduel TEXT,
    key_draftkings TEXT,
    key_yahoo TEXT,
    key_nfbc TEXT,
    key_rotowire TEXT,
    key_rotoworld TEXT,
    key_kffl TEXT,
    name_first TEXT,
    name_last TEXT,
    name_full TEXT,
    name_given TEXT,
    name_matrilineal TEXT,
    bats TEXT,
    throws TEXT,
    birth_year INTEGER,
    birth_month INTEGER,
    birth_day INTEGER,
    death_year INTEGER,
    death_month INTEGER,
    death_day INTEGER,
    birth_city TEXT,
    birth_state TEXT,
    birth_country TEXT,
    death_city TEXT,
    death_state TEXT,
    death_country TEXT,
    weight INTEGER,
    height INTEGER,
    debut DATE,
    final_game DATE,
    mlb_played_first INTEGER,
    mlb_played_last INTEGER,
    retro_played_first INTEGER,
    retro_played_last INTEGER,
    college TEXT,
    college_id INTEGER,
    high_school TEXT,
    high_school_id INTEGER,
    bats_throws_source TEXT,
    birth_source TEXT,
    death_source TEXT,
    weight_height_source TEXT,
    debut_source TEXT,
    mlb_organization TEXT,
    mlb_position TEXT,
    twitter_id TEXT,
    wikipedia_id TEXT,
    gelb_id TEXT,
    lahman_id TEXT,
    source_timestamp TIMESTAMP WITH TIME ZONE,
    loaded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE bridge._staging_chadwick_register IS 'Staging table for Chadwick Bureau Register data. Loaded from CSV files before merging to player_xref.';

-- ============================================================================
-- STAGE 2: Create procedure to upsert from staging to player_xref
-- ============================================================================

CREATE OR REPLACE PROCEDURE bridge.upsert_chadwick_to_player_xref()
LANGUAGE plpgsql
AS $$
DECLARE
    v_inserted INTEGER := 0;
    v_updated INTEGER := 0;
    v_total INTEGER := 0;
BEGIN
    -- Count total records to process
    SELECT COUNT(*) INTO v_total FROM bridge._staging_chadwick_register;
    
    RAISE NOTICE 'Processing % Chadwick Register records...', v_total;
    
    -- Insert new records (where Retrosheet ID doesn't exist)
    INSERT INTO bridge.player_xref (
        retrosheet_id,
        mlb_id,
        baseball_reference_id,
        name_first,
        name_last,
        source_notes,
        updated_at,
        confidence_score,
        confidence_source
    )
    SELECT 
        key_retro,
        key_mlbam::BIGINT,
        key_bbref,
        name_first,
        name_last,
        jsonb_build_object(
            'chadwick_key_uuid', key_uuid,
            'chadwick_key_fangraphs', key_fangraphs,
            'lahman_id', lahman_id,
            'bats', bats,
            'throws', throws,
            'birth_date', CASE 
                WHEN birth_year IS NOT NULL 
                THEN MAKE_DATE(birth_year, COALESCE(birth_month, 1), COALESCE(birth_day, 1))
                ELSE NULL 
            END,
            'death_date', CASE 
                WHEN death_year IS NOT NULL 
                THEN MAKE_DATE(death_year, COALESCE(death_month, 1), COALESCE(death_day, 1))
                ELSE NULL 
            END,
            'debut', debut,
            'final_game', final_game,
            'mlb_years', CASE 
                WHEN mlb_played_first IS NOT NULL AND mlb_played_last IS NOT NULL
                THEN ARRAY[mlb_played_first, mlb_played_last]
                ELSE NULL
            END
        ),
        NOW(),
        0.95,  -- High confidence for Chadwick Bureau
        'Chadwick Bureau Register'
    FROM bridge._staging_chadwick_register cr
    WHERE cr.key_retro IS NOT NULL
      AND cr.key_retro NOT IN (SELECT retrosheet_id FROM bridge.player_xref WHERE retrosheet_id IS NOT NULL)
      AND (cr.key_mlbam IS NULL OR cr.key_mlbam::BIGINT NOT IN (SELECT mlb_id FROM bridge.player_xref WHERE mlb_id IS NOT NULL));
    
    GET DIAGNOSTICS v_inserted = ROW_COUNT;
    RAISE NOTICE 'Inserted % new player records', v_inserted;
    
    -- Update existing records (merge additional IDs)
    UPDATE bridge.player_xref px
    SET 
        mlb_id = COALESCE(px.mlb_id, cr.key_mlbam::BIGINT),
        baseball_reference_id = COALESCE(px.baseball_reference_id, cr.key_bbref),
        source_notes = px.source_notes || jsonb_build_object(
            'chadwick_key_uuid', cr.key_uuid,
            'chadwick_key_fangraphs', cr.key_fangraphs,
            'lahman_id', cr.lahman_id,
            'merged_at', NOW()
        ),
        updated_at = NOW(),
        confidence_score = GREATEST(px.confidence_score, 0.95),
        confidence_source = CASE 
            WHEN px.confidence_score < 0.95 THEN 'Chadwick Bureau Register (merged)'
            ELSE px.confidence_source
        END
    FROM bridge._staging_chadwick_register cr
    WHERE px.retrosheet_id = cr.key_retro
      AND cr.key_retro IS NOT NULL;
    
    GET DIAGNOSTICS v_updated = ROW_COUNT;
    RAISE NOTICE 'Updated % existing player records', v_updated;
    
    -- Commit statistics
    RAISE NOTICE 'Chadwick Register sync complete: % inserted, % updated', v_inserted, v_updated;
    
    -- Log to metadata table if it exists
    BEGIN
        INSERT INTO metadata.bridge_sync_log (
            sync_type, source_system, records_processed, records_inserted, records_updated, sync_timestamp
        ) VALUES (
            'player_xref_population', 'chadwick_register', v_total, v_inserted, v_updated, NOW()
        );
    EXCEPTION WHEN undefined_table THEN
        -- metadata.bridge_sync_log doesn't exist, skip logging
        NULL;
    END;
END;
$$;

COMMENT ON PROCEDURE bridge.upsert_chadwick_to_player_xref() IS 'Merges Chadwick Register staging data into bridge.player_xref, inserting new records and updating existing ones with additional IDs.';

-- ============================================================================
-- STAGE 3: Create function to load Chadwick data from CSV
-- ============================================================================

CREATE OR REPLACE FUNCTION bridge.load_chadwick_from_csv(
    p_file_path TEXT,
    p_suffix TEXT
)
RETURNS INTEGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_count INTEGER := 0;
    v_sql TEXT;
BEGIN
    -- Use dynamic SQL with COPY command
    -- Note: This requires file access on the PostgreSQL server
    v_sql := format('COPY bridge._staging_chadwick_register (
        key_uuid, key_mlbam, key_retro, key_bbref, key_fangraphs,
        key_baseball_prospectus, key_cbs, key_espn, key_fanduel,
        key_draftkings, key_yahoo, key_nfbc, key_rotowire, key_rotoworld,
        key_kffl, name_first, name_last, name_full, name_given, name_matrilineal,
        bats, throws, birth_year, birth_month, birth_day, death_year, death_month,
        death_day, birth_city, birth_state, birth_country, death_city, death_state,
        death_country, weight, height, debut, final_game, mlb_played_first,
        mlb_played_last, retro_played_first, retro_played_last, college, college_id,
        high_school, high_school_id, bats_throws_source, birth_source, death_source,
        weight_height_source, debut_source, mlb_organization, mlb_position,
        twitter_id, wikipedia_id, gelb_id, lahman_id
    ) FROM %L WITH (FORMAT CSV, HEADER true)', p_file_path);
    
    EXECUTE v_sql;
    
    GET DIAGNOSTICS v_count = ROW_COUNT;
    
    -- Update source tracking
    UPDATE bridge._staging_chadwick_register
    SET source_timestamp = NOW()
    WHERE key_uuid IN (
        SELECT key_uuid FROM bridge._staging_chadwick_register
        ORDER BY loaded_at DESC LIMIT v_count
    );
    
    RETURN v_count;
EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE 'Error loading %: %', p_file_path, SQLERRM;
    RETURN 0;
END;
$$;

COMMENT ON FUNCTION bridge.load_chadwick_from_csv(TEXT, TEXT) IS 'Loads a Chadwick Register CSV file into the staging table. Returns number of rows loaded.';

-- ============================================================================
-- STAGE 4: Create view for Chadwick data quality monitoring
-- ============================================================================

CREATE OR REPLACE VIEW bridge.vw_chadwick_coverage AS
SELECT 
    'Chadwick Register Coverage' as metric_category,
    COUNT(*) as total_players,
    COUNT(key_mlbam) as with_mlb_id,
    COUNT(key_retro) as with_retrosheet_id,
    COUNT(key_bbref) as with_bbref_id,
    COUNT(key_fangraphs) as with_fangraphs_id,
    COUNT(lahman_id) as with_lahman_id,
    ROUND(COUNT(key_mlbam)::numeric / NULLIF(COUNT(*), 0) * 100, 2) as mlb_coverage_pct,
    ROUND(COUNT(key_retro)::numeric / NULLIF(COUNT(*), 0) * 100, 2) as retro_coverage_pct,
    ROUND(COUNT(key_bbref)::numeric / NULLIF(COUNT(*), 0) * 100, 2) as bbref_coverage_pct
FROM bridge._staging_chadwick_register
UNION ALL
SELECT 
    'Player Xref Coverage' as metric_category,
    COUNT(*) as total_players,
    COUNT(mlb_id) as with_mlb_id,
    COUNT(retrosheet_id) as with_retrosheet_id,
    COUNT(baseball_reference_id) as with_bbref_id,
    NULL::bigint as with_fangraphs_id,
    NULL::bigint as with_lahman_id,
    ROUND(COUNT(mlb_id)::numeric / NULLIF(COUNT(*), 0) * 100, 2) as mlb_coverage_pct,
    ROUND(COUNT(retrosheet_id)::numeric / NULLIF(COUNT(*), 0) * 100, 2) as retro_coverage_pct,
    ROUND(COUNT(baseball_reference_id)::numeric / NULLIF(COUNT(*), 0) * 100, 2) as bbref_coverage_pct
FROM bridge.player_xref;

COMMENT ON VIEW bridge.vw_chadwick_coverage IS 'Compares ID coverage between Chadwick Register staging and bridge.player_xref for gap analysis.';

-- ============================================================================
-- TABLE AND COLUMN COMMENTS
-- ============================================================================

COMMENT ON TABLE bridge.player_xref IS 'Cross-reference table mapping player IDs across data sources: Retrosheet (primary key), MLB, Baseball-Reference, FanGraphs, Lahman, etc.';

COMMENT ON COLUMN bridge.player_xref.retrosheet_id IS 'Primary identifier from Retrosheet event files (e.g., aardsd001)';
COMMENT ON COLUMN bridge.player_xref.mlb_id IS 'MLBAM ID from MLB Stats API and Statcast (e.g., 605151)';
COMMENT ON COLUMN bridge.player_xref.baseball_reference_id IS 'Baseball-Reference ID (e.g., aardsda01)';
COMMENT ON COLUMN bridge.player_xref.name_first IS 'Player first name';
COMMENT ON COLUMN bridge.player_xref.name_last IS 'Player last name';
COMMENT ON COLUMN bridge.player_xref.source_notes IS 'JSONB field storing additional IDs and metadata from various sources';
COMMENT ON COLUMN bridge.player_xref.confidence_score IS '0.0-1.0 confidence in ID mapping accuracy';
COMMENT ON COLUMN bridge.player_xref.confidence_source IS 'Source system for the ID mapping (Chadwick Bureau, Lahman, etc.)';
COMMENT ON COLUMN bridge.player_xref.updated_at IS 'Timestamp of last update to this record';
