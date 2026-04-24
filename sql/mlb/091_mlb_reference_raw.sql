CREATE SCHEMA IF NOT EXISTS raw_mlb;

CREATE TABLE IF NOT EXISTS raw_mlb.reference_snapshots (
    snapshot_id BIGSERIAL PRIMARY KEY,
    endpoint_family TEXT NOT NULL,
    resource_key TEXT,
    season INTEGER,
    endpoint TEXT NOT NULL,
    payload JSONB NOT NULL,
    fetched_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    request_params JSONB,
    http_status INTEGER,
    response_time_ms INTEGER,
    error_text TEXT,
    payload_checksum TEXT
);

CREATE INDEX IF NOT EXISTS reference_snapshots_family_idx
ON raw_mlb.reference_snapshots (endpoint_family);

CREATE INDEX IF NOT EXISTS reference_snapshots_resource_idx
ON raw_mlb.reference_snapshots (resource_key);

CREATE INDEX IF NOT EXISTS reference_snapshots_season_idx
ON raw_mlb.reference_snapshots (season);

CREATE INDEX IF NOT EXISTS reference_snapshots_fetched_at_idx
ON raw_mlb.reference_snapshots (fetched_at);

CREATE INDEX IF NOT EXISTS reference_snapshots_checksum_idx
ON raw_mlb.reference_snapshots (payload_checksum);

COMMENT ON TABLE raw_mlb.reference_snapshots IS 'Source-preserved MLB Stats API reference endpoint snapshots such as teams, rosters, people, venues, and standings';
COMMENT ON COLUMN raw_mlb.reference_snapshots.endpoint_family IS 'Logical endpoint family, such as teams, rosters, people, venues, or standings';
COMMENT ON COLUMN raw_mlb.reference_snapshots.resource_key IS 'Natural resource identifier for the fetched object or batch, such as season, team, venue, or people batch';
COMMENT ON COLUMN raw_mlb.reference_snapshots.season IS 'Season associated with the snapshot when applicable';
COMMENT ON COLUMN raw_mlb.reference_snapshots.endpoint IS 'API endpoint used to fetch the payload';
COMMENT ON COLUMN raw_mlb.reference_snapshots.payload IS 'Full JSON response from the MLB Stats API';
COMMENT ON COLUMN raw_mlb.reference_snapshots.request_params IS 'Normalized request parameters used for the fetch';
COMMENT ON COLUMN raw_mlb.reference_snapshots.http_status IS 'HTTP status code returned by the MLB API';
COMMENT ON COLUMN raw_mlb.reference_snapshots.error_text IS 'Error captured during fetch when a request fails or returns unexpected content';
COMMENT ON COLUMN raw_mlb.reference_snapshots.payload_checksum IS 'Checksum for payload-level deduping and replay audit';
