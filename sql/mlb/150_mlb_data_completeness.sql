-- mlb_data_completeness.sql
-- Provides views to track which MLB seasons have been ingested

CREATE SCHEMA IF NOT EXISTS mlb;

-- Expected seasons (adjust range as needed)
CREATE OR REPLACE VIEW mlb.expected_seasons AS
SELECT generate_series AS season
FROM generate_series(2000, 2025);

-- Seasons present in raw_mlb.live_feed_snapshots
CREATE OR REPLACE VIEW mlb.ingested_seasons AS
SELECT DISTINCT season
FROM raw_mlb.live_feed_snapshots
WHERE season BETWEEN 2000 AND 2025;

-- Missing seasons
CREATE OR REPLACE VIEW mlb.missing_seasons AS
SELECT e.season
FROM mlb.expected_seasons AS e
LEFT JOIN mlb.ingested_seasons AS i ON e.season = i.season
WHERE i.season IS NULL
ORDER BY e.season;

-- Summary view
CREATE OR REPLACE VIEW mlb.season_completeness AS
SELECT
e.season,
NOT coalesce(i.season IS NULL, FALSE) AS has_mlb_snapshot,
CASE WHEN i.season IS NULL THEN 'MISSING' ELSE 'OK' END AS status
FROM mlb.expected_seasons AS e
LEFT JOIN mlb.ingested_seasons AS i ON e.season = i.season
ORDER BY e.season;

-- Helper function to check if all seasons are present
CREATE OR REPLACE FUNCTION mlb.all_seasons_ingested()
RETURNS BOOLEAN
LANGUAGE sql
AS $$
    SELECT NOT EXISTS (SELECT 1 FROM mlb.missing_seasons);
$$;

-- Procedure to report missing seasons (optional strict mode)
CREATE OR REPLACE PROCEDURE mlb.check_ingestion_completeness(
IN strict BOOLEAN DEFAULT FALSE
)
LANGUAGE plpgsql
AS $$
DECLARE
    _missing TEXT;
BEGIN
    SELECT string_agg(season::text, ', ') INTO _missing
    FROM   mlb.missing_seasons;

    IF _missing IS NULL THEN
        RAISE NOTICE '✅ All expected MLB seasons (2000‑2025) are present.';
    ELSE
        RAISE NOTICE '⚠️  Missing MLB seasons: %', _missing;
        IF strict THEN
            RAISE EXCEPTION 'Ingestion incomplete – missing seasons: %', _missing;
        END IF;
    END IF;
END;
$$;
