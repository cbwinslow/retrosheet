-- File: sql/external/213_park_factors_raw.sql
-- Purpose: Create park factors raw table from Baseball Savant
-- Author: Agent Cascade
-- Date: 2026-04-24
 st-- =============================================================================
-- MLB Park Factors (Statcast) Raw Table
-- =============================================================================
-- Public CSV from Baseball‑Savant: https://baseballsavant.mlb.com/park-factors
-- =============================================================================

CREATE SCHEMA IF NOT EXISTS raw_park_factors;

CREATE TABLE IF NOT EXISTS raw_park_factors.factors (
    season          INT,
    park_id         TEXT,
    park_name       TEXT,
    runs_factor     REAL,
    home_runs_factor REAL,
    slugging_factor REAL,
    PRIMARY KEY (season, park_id)
);

-- Table comments
COMMENT ON TABLE raw_park_factors.factors IS 'Park factors from Baseball Savant by season and park';
