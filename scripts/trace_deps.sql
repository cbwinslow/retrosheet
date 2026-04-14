-- trace_deps.sql
-- Utility script to list objects that depend on a given relation (table, view, materialized view).
-- Usage: psql -v ON_ERROR_STOP=1 -d retrosheet -f scripts/trace_deps.sql -v target='features.game_outcome_examples'

\set ON_ERROR_STOP on

-- Resolve the target relation OID
WITH target_oid AS (
    SELECT c.oid
    FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname || '.' || c.relname = :'target'
)
SELECT
    n.nspname AS schema,
    c.relname AS object_name,
    CASE c.relkind
        WHEN 'r' THEN 'table'
        WHEN 'v' THEN 'view'
        WHEN 'm' THEN 'materialized view'
        WHEN 'i' THEN 'index'
        ELSE c.relkind::text
    END AS object_type
FROM pg_depend d
JOIN pg_class c ON c.oid = d.refobjid
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE d.objid = (SELECT oid FROM target_oid)
ORDER BY object_type, schema, object_name;

-- End of script
