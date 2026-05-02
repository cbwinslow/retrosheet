-- File: sql/external/215_weather_raw.sql
-- Purpose: COMPLETE weather raw tables - ALL fields from weather APIs
-- Author: Agent Cascade
-- Date: 2026-04-24
-- Updated: 2026-05-01 - Expanded to capture ALL available weather fields
-- =============================================================================
-- Weather Data - COMPLETE FIELD COVERAGE
-- =============================================================================
-- Weather APIs provide comprehensive meteorological data including:
-- - Temperature (multiple metrics: current, feels like, min, max, dew point)
-- - Wind (speed, direction, gusts)
-- - Precipitation (rain, snow, probability)
-- - Atmospheric (pressure, humidity, visibility, UV index)
-- - Clouds, weather conditions, timestamps
-- =============================================================================

CREATE SCHEMA IF NOT EXISTS raw_weather;

-- ============================================================================
-- HOURLY WEATHER - Complete field coverage from OpenWeatherMap / VisualCrossing
-- ============================================================================
DROP TABLE IF EXISTS raw_weather.hourly CASCADE;
CREATE TABLE raw_weather.hourly (
    -- Identity
    observation_id BIGSERIAL PRIMARY KEY,
    observation_datetime TIMESTAMPTZ NOT NULL,
    venue_id TEXT NOT NULL,
    
    -- Location
    venue_lat REAL,
    venue_lon REAL,
    venue_city TEXT,
    
    -- Temperature (multiple metrics)
    temp_c REAL,
    temp_f REAL,
    feels_like_c REAL,
    feels_like_f REAL,
    temp_min_c REAL,
    temp_max_c REAL,
    temp_min_f REAL,
    temp_max_f REAL,
    dew_point_c REAL,
    
    -- Wind
    wind_speed_mps REAL,
    wind_speed_mph REAL,
    wind_direction_deg INT,
    wind_direction_cardinal TEXT,
    wind_gust_mps REAL,
    wind_gust_mph REAL,
    
    -- Precipitation
    precipitation_mm REAL,
    precipitation_in REAL,
    rain_mm REAL,
    rain_in REAL,
    snow_mm REAL,
    snow_in REAL,
    precipitation_probability REAL,
    
    -- Atmospheric
    pressure_hpa REAL,
    pressure_in REAL,
    humidity_percent INT,
    visibility_m INT,
    visibility_mi REAL,
    cloud_cover_percent INT,
    uv_index REAL,
    
    -- Weather condition
    weather_condition_id INT,
    weather_main TEXT,
    weather_description TEXT,
    weather_icon TEXT,
    
    -- Sun times (if available)
    sunrise TIMESTAMPTZ,
    sunset TIMESTAMPTZ,
    
    -- Metadata
    data_source TEXT,
    api_response JSONB,
    ingested_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Unique constraint
    CONSTRAINT unique_hourly_observation UNIQUE (observation_datetime, venue_id)
);

-- ============================================================================
-- DAILY WEATHER AGGREGATE - Complete field coverage
-- ============================================================================
DROP TABLE IF EXISTS raw_weather.daily CASCADE;
CREATE TABLE raw_weather.daily (
    -- Identity
    observation_date DATE NOT NULL,
    venue_id TEXT NOT NULL,
    
    -- Temperature aggregates
    temp_avg_c REAL,
    temp_min_c REAL,
    temp_max_c REAL,
    temp_avg_f REAL,
    temp_min_f REAL,
    temp_max_f REAL,
    feels_like_avg_c REAL,
    feels_like_min_c REAL,
    feels_like_max_c REAL,
    dew_point_avg_c REAL,
    
    -- Wind aggregates
    wind_speed_avg_mps REAL,
    wind_speed_max_mps REAL,
    wind_direction_deg INT,
    wind_direction_cardinal TEXT,
    wind_gust_max_mps REAL,
    
    -- Precipitation totals
    precipitation_mm REAL,
    precipitation_in REAL,
    rain_mm REAL,
    rain_in REAL,
    snow_mm REAL,
    snow_in REAL,
    precipitation_hours REAL,
    
    -- Atmospheric aggregates
    pressure_avg_hpa REAL,
    humidity_avg_percent INT,
    humidity_max_percent INT,
    visibility_avg_m INT,
    cloud_cover_avg_percent INT,
    uv_index_max REAL,
    
    -- Weather summary
    weather_condition_id INT,
    weather_main TEXT,
    weather_description TEXT,
    
    -- Daylight
    sunrise TIME,
    sunset TIME,
    daylight_hours REAL,
    
    -- Metadata
    data_source TEXT,
    observation_count INT,
    ingested_at TIMESTAMPTZ DEFAULT NOW(),
    
    PRIMARY KEY (observation_date, venue_id)
);

-- ============================================================================
-- GAME WEATHER - Weather joined to specific games
-- ============================================================================
DROP TABLE IF EXISTS raw_weather.game_weather CASCADE;
CREATE TABLE raw_weather.game_weather (
    game_pk BIGINT NOT NULL,
    game_datetime TIMESTAMPTZ,
    venue_id TEXT NOT NULL,
    
    -- Pre-game weather (closest observation before game start)
    temp_at_game_c REAL,
    wind_speed_at_game_mps REAL,
    wind_direction_at_game TEXT,
    humidity_at_game_percent INT,
    precipitation_probability REAL,
    weather_condition TEXT,
    
    -- In-game weather (average conditions during game)
    temp_avg_c REAL,
    wind_speed_avg_mps REAL,
    humidity_avg_percent INT,
    
    -- Weather API metadata
    hourly_observation_id BIGINT REFERENCES raw_weather.hourly(observation_id),
    data_source TEXT,
    
    -- Cross-reference
    ingested_at TIMESTAMPTZ DEFAULT NOW(),
    
    PRIMARY KEY (game_pk)
);

-- ============================================================================
-- Indexes
-- ============================================================================
CREATE INDEX idx_weather_hourly_datetime ON raw_weather.hourly(observation_datetime);
CREATE INDEX idx_weather_hourly_venue ON raw_weather.hourly(venue_id);
CREATE INDEX idx_weather_daily_date ON raw_weather.daily(observation_date);
CREATE INDEX idx_weather_daily_venue ON raw_weather.daily(venue_id);
CREATE INDEX idx_weather_game_gamepk ON raw_weather.game_weather(game_pk);
CREATE INDEX idx_weather_game_venue ON raw_weather.game_weather(venue_id);

-- ============================================================================
-- Comments
-- ============================================================================
COMMENT ON TABLE raw_weather.hourly IS 'COMPLETE hourly weather observations with ALL meteorological fields';
COMMENT ON TABLE raw_weather.daily IS 'COMPLETE daily weather aggregates with ALL meteorological fields';
COMMENT ON TABLE raw_weather.game_weather IS 'Weather conditions for specific MLB games';
