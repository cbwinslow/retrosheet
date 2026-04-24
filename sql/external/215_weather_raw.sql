-- =============================================================================
-- NOAA Weather Data Raw Table
-- =============================================================================
-- Daily weather observations for each venue (temperature, wind, precipitation).
-- =============================================================================

CREATE SCHEMA IF NOT EXISTS raw_weather;

CREATE TABLE IF NOT EXISTS raw_weather.daily (
    observation_date DATE NOT NULL,
    venue_id TEXT NOT NULL,
    temperature_c REAL,
    wind_speed_mps REAL,
    precipitation_mm REAL,
    PRIMARY KEY (observation_date, venue_id)
);
