-- Player Xref Population Procedure (SQL-based)
-- This procedure expects Chadwick CSV files to be available in /tmp/chadwick_register/
-- Use the wrapper script to download files before calling this procedure

-- Create temp table schema for Chadwick data
CREATE TEMPORARY TABLE IF NOT EXISTS temp_table.chadwick_player_data (
    key_uuid TEXT,
    key_mlbam TEXT,
    key_retro TEXT,
    key_bbref TEXT,
    key_fangraphs TEXT,
    name_first TEXT,
    name_last TEXT,
    name_given TEXT,
    name_suffix TEXT,
    name_nick TEXT,
    birth_year INTEGER,
    mlb_played_first INTEGER,
    bats TEXT,
    throws TEXT
);

-- Procedure: Populate player_xref from Chadwick CSV files
CREATE OR REPLACE PROCEDURE bridge.populate_player_xref_from_chadwick(p_csv_directory TEXT DEFAULT '/tmp/chadwick_register/')
LANGUAGE plpgsql
AS $$
DECLARE
    file_pattern TEXT;
    file_count INT := 0;
    inserted_count INT := 0;
BEGIN
    -- Clear temp table
    TRUNCATE TABLE temp_table.chadwick_player_data;
    
    -- Import all Chadwick CSV files (people-0.csv through people-f.csv)
    FOR file_pattern IN SELECT 'people-' || suffix || '.csv' 
                         FROM (SELECT unnest(ARRAY['0','1','2','3','4','5','6','7','8','9','a','b','c','d','e','f']) AS suffix) t
    LOOP
        BEGIN
            EXECUTE format('COPY temp_table.chadwick_player_data FROM %L CSV HEADER', 
                          p_csv_directory || file_pattern);
            file_count := file_count + 1;
            RAISE NOTICE 'Imported file: %', file_pattern;
        EXCEPTION WHEN others THEN
            RAISE NOTICE 'Could not import file: % (may not exist)', file_pattern;
        END;
    END LOOP;
    
    RAISE NOTICE 'Imported % Chadwick CSV files', file_count;
    
    -- Insert into bridge.player_xref with all ID fields
    INSERT INTO bridge.player_xref (
        retrosheet_player_id,
        mlb_player_id,
        chadwick_register_id,
        bbref_id,
        fangraphs_id,
        first_name,
        last_name,
        bats,
        throws,
        mlb_played_first,
        birth_year,
        updated_at
    )
    SELECT 
        key_retro,
        CASE WHEN key_mlbam ~ '^[0-9]+$' THEN key_mlbam::INTEGER ELSE NULL END,
        key_uuid,
        key_bbref,
        CASE WHEN key_fangraphs ~ '^[0-9]+$' THEN key_fangraphs::INTEGER ELSE NULL END,
        name_first,
        name_last,
        SUBSTRING(UPPER(COALESCE(bats, 'U')), 1, 1),
        SUBSTRING(UPPER(COALESCE(throws, 'U')), 1, 1),
        mlb_played_first,
        birth_year,
        now()
    FROM temp_table.chadwick_player_data
    WHERE key_retro IS NOT NULL
    ON CONFLICT (retrosheet_player_id) DO UPDATE
    SET 
        mlb_player_id = EXCLUDED.mlb_player_id,
        chadwick_register_id = EXCLUDED.chadwick_register_id,
        bbref_id = EXCLUDED.bbref_id,
        fangraphs_id = EXCLUDED.fangraphs_id,
        first_name = EXCLUDED.first_name,
        last_name = EXCLUDED.last_name,
        bats = EXCLUDED.bats,
        throws = EXCLUDED.throws,
        mlb_played_first = EXCLUDED.mlb_played_first,
        birth_year = EXCLUDED.birth_year,
        updated_at = now();
    
    GET DIAGNOSTICS inserted_count = ROW_COUNT;
    RAISE NOTICE 'Inserted/updated % player mappings', inserted_count;
    
    -- Clean up temp table
    TRUNCATE TABLE temp_table.chadwick_player_data;
END;
$$;

COMMENT ON PROCEDURE bridge.populate_player_xref_from_chadwick (p_csv_directory TEXT) IS 'Populates bridge.player_xref from Chadwick Bureau Register CSV files';

-- Wrapper procedure: Download Chadwick data and populate player_xref
CREATE OR REPLACE PROCEDURE bridge.populate_player_xref_full()
LANGUAGE plpgsql
AS $$
DECLARE
    download_script TEXT;
    temp_dir TEXT := '/tmp/chadwick_register_' || to_char(now(), 'YYYYMMDD_HH24MISS');
BEGIN
    -- Create temp directory
    EXECUTE format('mkdir -p %s', temp_dir);
    RAISE NOTICE 'Created temp directory: %', temp_dir;
    
    -- Download Chadwick CSV files using shell
    FOR i IN 0..15 LOOP
        BEGIN
            EXECUTE format('curl -s -o %s/people-%x.csv https://github.com/chadwickbureau/register/raw/master/data/people-%x.csv', 
                          temp_dir, i, i);
            RAISE NOTICE 'Downloaded people-%x.csv', i;
        EXCEPTION WHEN others THEN
            RAISE NOTICE 'Could not download people-%x.csv', i;
        END;
    END LOOP;
    
    -- Call the population procedure
    CALL bridge.populate_player_xref_from_chadwick(temp_dir);
    
    -- Clean up temp directory
    EXECUTE format('rm -rf %s', temp_dir);
    RAISE NOTICE 'Cleaned up temp directory: %', temp_dir;
END;
$$;

COMMENT ON PROCEDURE bridge.populate_player_xref_full () IS 'Downloads Chadwick Bureau Register data and populates bridge.player_xref';
