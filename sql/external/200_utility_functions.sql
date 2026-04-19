-- Utility functions for the Retrosheet warehouse
-- These functions encapsulate common repeatable queries and maintenance tasks.

-- 1. Refresh all materialized views in the features schema
CREATE OR REPLACE FUNCTION features.refresh_all_materialized_views()
RETURNS void LANGUAGE plpgsql AS $$
DECLARE
    r RECORD;
BEGIN
    FOR r IN SELECT matviewname FROM pg_matviews WHERE schemaname = 'features'
    LOOP
        EXECUTE format('REFRESH MATERIALIZED VIEW CONCURRENTLY features.%I', r.matviewname);
    END LOOP;
END;
$$;

-- 2. Get the loaded season range from core.games
CREATE OR REPLACE FUNCTION core.season_range()
RETURNS TABLE(min_season int, max_season int) LANGUAGE sql AS $$
    SELECT MIN(season) AS min_season, MAX(season) AS max_season FROM core.games;
$$;

-- 3. Count rows in a given core table (generic helper)
CREATE OR REPLACE FUNCTION core.count_rows(p_table regclass)
RETURNS bigint LANGUAGE plpgsql AS $$
DECLARE
    result bigint;
BEGIN
    EXECUTE format('SELECT COUNT(*) FROM %s', p_table::text) INTO result;
    RETURN result;
END;
$$;

-- 4. Convenience wrapper to get basic warehouse health metrics
-- Ensure the warehouse schema exists before defining the function
CREATE SCHEMA IF NOT EXISTS warehouse;

CREATE OR REPLACE FUNCTION warehouse.health_check()
RETURNS TABLE(
    min_season int,
    max_season int,
    games_count bigint,
    events_count bigint,
    plate_appearances_count bigint
) LANGUAGE plpgsql AS $$
BEGIN
    SELECT MIN(season), MAX(season) INTO min_season, max_season FROM core.games;
    SELECT COUNT(*) INTO games_count FROM core.games;
    SELECT COUNT(*) INTO events_count FROM core.events;
    SELECT COUNT(*) INTO plate_appearances_count FROM core.plate_appearances;
    RETURN NEXT;
END;
$$;

-- Grant execute rights to the public role for convenience (adjust as needed)
GRANT EXECUTE ON FUNCTION features.refresh_all_materialized_views() TO PUBLIC;
GRANT EXECUTE ON FUNCTION core.season_range() TO PUBLIC;
GRANT EXECUTE ON FUNCTION core.count_rows(regclass) TO PUBLIC;
GRANT EXECUTE ON FUNCTION warehouse.health_check() TO PUBLIC;

-- 5. Generate SQL statements for backing up schema objects.
--    If exclude_raw is true, objects in schemas that start with 'raw_' are omitted.
CREATE OR REPLACE FUNCTION warehouse.generate_backup_sql(exclude_raw boolean DEFAULT true)
RETURNS TABLE(object_type text, object_name text, definition text) LANGUAGE plpgsql AS $$
DECLARE
    rec RECORD;
    schema_name text;
BEGIN
    FOR rec IN
        SELECT n.nspname AS schema_name,
               c.relname AS object_name,
               CASE c.relkind
                   WHEN 'r' THEN 'TABLE'
                   WHEN 'v' THEN 'VIEW'
                   WHEN 'm' THEN 'MATERIALIZED VIEW'
                   ELSE 'OTHER'
               END AS object_type
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname NOT IN ('pg_catalog', 'information_schema')
          AND (exclude_raw IS FALSE OR n.nspname NOT LIKE 'raw_%')
    LOOP
        IF rec.object_type = 'TABLE' THEN
            definition := format('CREATE TABLE IF NOT EXISTS %I.%I (LIKE %I.%I INCLUDING ALL);', rec.schema_name, rec.object_name, rec.schema_name, rec.object_name);
        ELSIF rec.object_type = 'VIEW' THEN
            definition := pg_get_viewdef(format('%I.%I', rec.schema_name, rec.object_name), true);
            definition := format('CREATE OR REPLACE VIEW %I.%I AS %s;', rec.schema_name, rec.object_name, definition);
        ELSIF rec.object_type = 'MATERIALIZED VIEW' THEN
            definition := pg_get_viewdef(format('%I.%I', rec.schema_name, rec.object_name), true);
            definition := format('CREATE MATERIALIZED VIEW %I.%I AS %s WITH DATA;', rec.schema_name, rec.object_name, definition);
        END IF;
        object_type := rec.object_type;
        object_name := rec.object_name;
        RETURN NEXT;
    END LOOP;

    -- Functions
    FOR rec IN
        SELECT n.nspname AS schema_name,
               p.proname AS object_name,
               pg_get_functiondef(p.oid) AS definition
        FROM pg_proc p
        JOIN pg_namespace n ON n.oid = p.pronamespace
        WHERE n.nspname NOT IN ('pg_catalog', 'information_schema')
          AND (exclude_raw IS FALSE OR n.nspname NOT LIKE 'raw_%')
    LOOP
        object_type := 'FUNCTION';
        object_name := rec.object_name;
        definition := rec.definition;
        RETURN NEXT;
    END LOOP;
END;
$$;

GRANT EXECUTE ON FUNCTION warehouse.generate_backup_sql(boolean) TO PUBLIC;
