-- =============================================================================
-- MLB Team Rosters & Salaries Raw JSON
-- =============================================================================
-- Free MLB Stats API endpoints (no auth required for basic roster/salary data).
-- The raw JSON payload is stored for reproducibility; a view extracts the
-- normalized columns.
-- =============================================================================

CREATE SCHEMA IF NOT EXISTS raw_mlb_rosters;

CREATE TABLE IF NOT EXISTS raw_mlb_rosters.roster_snapshots (
    snapshot_date   DATE NOT NULL,
    team_id         TEXT NOT NULL,
    json_payload    JSONB,
    PRIMARY KEY (snapshot_date, team_id)
);