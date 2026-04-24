-- File: sql/external/215_weather_raw.sql
-- Purpose: Create weather raw table for daily conditions by venue
-- Author: Agent Cascade
-- Date: 2026-04-24
CREATE SCHEMA IF NOT EXISTS raw_weather;

CREATE TABLE IF NOT EXISTS raw_weather.daily (
    observation_date DATE NOT NULL,
    venue_id TEXT NOT NULL,
    temperature_c REAL,
    wind_speed_mps REAL,
    precipitation_mm REAL,
    PRIMARY KEY (observation_date, venue_id)
);

-- Table comments
COMMENT ON TABLE raw_weather.daily IS 'Daily weather conditions by venue';
