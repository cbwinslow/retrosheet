-- Universal Data Dictionary Table
-- Central registry of all tables, columns, and descriptions for AI agents

CREATE SCHEMA IF NOT EXISTS metadata;

CREATE TABLE IF NOT EXISTS metadata.table_dictionary (
    table_id bigserial PRIMARY KEY,
    schemaname text NOT NULL,
    tablename text NOT NULL,
    table_description text NOT NULL,
    row_count bigint DEFAULT 0,
    last_analyzed timestamptz,
    is_active boolean DEFAULT true,
    priority_level integer DEFAULT 3,
    ai_hints text[],
    created_at timestamptz NOT NULL DEFAULT NOW(),
    updated_at timestamptz NOT NULL DEFAULT NOW(),
    UNIQUE(schemaname, tablename)
);

CREATE TABLE IF NOT EXISTS metadata.column_dictionary (
    column_id bigserial PRIMARY KEY,
    table_id bigint REFERENCES metadata.table_dictionary(table_id) ON DELETE CASCADE,
    column_name text NOT NULL,
    column_description text NOT NULL,
    data_type text NOT NULL,
    is_nullable boolean DEFAULT true,
    is_primary_key boolean DEFAULT false,
    is_foreign_key boolean DEFAULT false,
    ai_hints text[],
    created_at timestamptz NOT NULL DEFAULT NOW(),
    updated_at timestamptz NOT NULL DEFAULT NOW(),
    UNIQUE(table_id, column_name)
);

CREATE OR REPLACE FUNCTION metadata.refresh_data_dictionary()
RETURNS integer AS $$
DECLARE
    r record;
    c record;
    t_id bigint;
    count integer := 0;
BEGIN
    -- Refresh table entries
    FOR r IN
        SELECT
            schemaname,
            tablename,
            COALESCE(obj_description(('"' || schemaname || '".' || tablename)::regclass), '') as description,
            (xpath('/row/cnt/text()', query_to_xml(format('SELECT COUNT(*) as cnt FROM %I.%I', schemaname, tablename), false, true, '')))[1]::text::bigint as row_count
        FROM pg_tables
        WHERE schemaname NOT IN ('pg_catalog', 'information_schema', 'cron')
        AND tableowner = 'cbwinslow'
    LOOP
        INSERT INTO metadata.table_dictionary (schemaname, tablename, table_description, row_count, last_analyzed)
        VALUES (r.schemaname, r.tablename, r.description, r.row_count, NOW())
        ON CONFLICT (schemaname, tablename) DO UPDATE
        SET table_description = EXCLUDED.table_description,
            row_count = EXCLUDED.row_count,
            last_analyzed = NOW(),
            updated_at = NOW()
        RETURNING table_id INTO t_id;

        -- Refresh column entries
        FOR c IN
            SELECT
                column_name,
                data_type,
                is_nullable = 'YES' as is_nullable
            FROM information_schema.columns
            WHERE table_schema = r.schemaname
            AND table_name = r.tablename
        LOOP
            INSERT INTO metadata.column_dictionary (table_id, column_name, column_description, data_type, is_nullable)
            VALUES (t_id, c.column_name, '', c.data_type, c.is_nullable)
            ON CONFLICT (table_id, column_name) DO UPDATE
            SET data_type = EXCLUDED.data_type,
                is_nullable = EXCLUDED.is_nullable,
                updated_at = NOW();
        END LOOP;

        count := count + 1;
    END LOOP;

    RETURN count;
END;
$$ LANGUAGE plpgsql;

-- Initial load
SELECT metadata.refresh_data_dictionary();

-- Schedule daily refresh
SELECT cron.schedule('data-dictionary-refresh', '0 1 * * *', $$ SELECT metadata.refresh_data_dictionary(); $$);
