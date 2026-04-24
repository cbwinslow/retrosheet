-- File: sql/eda/030_gis_pitch_views.sql
-- Purpose: GIS views classifying pitch locations relative to strike zone
-- Author: Agent Cascade
-- Date: 2026-04-24
CREATE OR REPLACE VIEW eda.pitch_zone_classification AS
SELECT
    id,
    game_year,
    game_pk,
    batter_id,
    pitcher_id,
    pitch_type,
    plate_x,
    plate_z,
    sz_top,
    sz_bot,
    location,
    -- Strike zone boundaries (inches from center)
    -- Standard zone: -8.5 to +8.5 inches wide, sz_bot to sz_top height
    pitch_result,
    -- More granular zone breakdown
    balls,
    -- Distance from zone center
    strikes,
    inning,
    inning_topbot,
    CASE
        WHEN
            plate_x BETWEEN -8.5 AND 8.5
            AND plate_z BETWEEN sz_bot AND sz_top THEN 'in_zone'
        WHEN
            plate_x BETWEEN -13.5 AND 13.5
            AND plate_z BETWEEN (sz_bot - 2) AND (sz_top + 2) THEN 'edge'
        ELSE 'way_outside'
    END AS zone_classification,
    CASE
        WHEN plate_x BETWEEN -8.5 AND 8.5 AND plate_z BETWEEN sz_bot AND sz_top THEN 'heart'
        WHEN plate_x BETWEEN -13.5 AND -8.5 OR plate_x BETWEEN 8.5 AND 13.5 THEN 'edge_horizontal'
        WHEN plate_z BETWEEN (sz_bot - 2) AND sz_bot OR plate_z BETWEEN sz_top AND (sz_top + 2) THEN 'edge_vertical'
        WHEN plate_x < -13.5 OR plate_x > 13.5 THEN 'far_horizontal'
        WHEN plate_z < (sz_bot - 2) THEN 'low'
        WHEN plate_z > (sz_top + 2) THEN 'high'
        ELSE 'other'
    END AS zone_detail,
    SQRT(POWER(plate_x, 2) + POWER(plate_z - ((sz_top + sz_bot) / 2), 2)) AS distance_from_center
FROM features_pitch.locations
WHERE
    plate_x IS NOT NULL
    AND plate_z IS NOT NULL
    AND sz_top IS NOT NULL
    AND sz_bot IS NOT NULL;

-- View 2: Pitcher Location Heatmap (binned for heatmap visualization)
CREATE OR REPLACE VIEW eda.pitcher_location_heatmap AS
SELECT
    pitcher_id,
    game_year,
    pitch_type,
    -- 3-inch bins for heatmap
    ROUND(plate_x / 3.0) * 3 AS bin_x,
    ROUND(plate_z / 3.0) * 3 AS bin_z,
    COUNT(*) AS pitch_count,
    AVG(launch_speed) AS avg_launch_speed,
    AVG(start_speed) AS avg_start_speed,
    -- Calculate percentage of pitches in zone
    SUM(CASE WHEN plate_x BETWEEN -8.5 AND 8.5 AND plate_z BETWEEN sz_bot AND sz_top THEN 1 ELSE 0 END)::float / COUNT(*) AS in_zone_pct,
    -- Swing rate in this location
    SUM(CASE WHEN pitch_result ILIKE '%swing%' OR pitch_result ILIKE '%foul%' THEN 1 ELSE 0 END)::float / NULLIF(COUNT(*), 0) AS swing_rate,
    -- Whiff rate in this location  
    SUM(CASE WHEN pitch_result ILIKE '%swinging strike%' THEN 1 ELSE 0 END)::float / NULLIF(SUM(CASE WHEN pitch_result ILIKE '%swing%' OR pitch_result ILIKE '%foul%' THEN 1 ELSE 0 END), 0) AS whiff_rate
FROM features_pitch.locations
WHERE plate_x IS NOT NULL AND plate_z IS NOT NULL
GROUP BY
    pitcher_id, game_year, pitch_type,
    ROUND(plate_x / 3.0) * 3, ROUND(plate_z / 3.0) * 3;

-- View 3: Batter Zone Performance
-- How batters perform by pitch location
CREATE OR REPLACE VIEW eda.batter_zone_performance AS
SELECT
    batter_id,
    game_year,
    pitch_type,
    -- Simplified zones for batter analysis
    CASE
        WHEN plate_x < -8.5 AND plate_z BETWEEN sz_bot AND sz_top THEN 'inside_strike'
        WHEN plate_x > 8.5 AND plate_z BETWEEN sz_bot AND sz_top THEN 'outside_strike'
        WHEN plate_x BETWEEN -8.5 AND 8.5 AND plate_z > sz_top THEN 'high_strike'
        WHEN plate_x BETWEEN -8.5 AND 8.5 AND plate_z < sz_bot THEN 'low_strike'
        WHEN plate_x BETWEEN -8.5 AND 8.5 AND plate_z BETWEEN sz_bot AND sz_top THEN 'heart'
        WHEN plate_x < -13.5 THEN 'far_inside'
        WHEN plate_x > 13.5 THEN 'far_outside'
        WHEN plate_z > (sz_top + 3) THEN 'way_high'
        WHEN plate_z < (sz_bot - 3) THEN 'way_low'
        ELSE 'edge'
    END AS location_zone,
    COUNT(*) AS total_pitches,
    -- Swing decisions
    SUM(CASE WHEN pitch_result ILIKE '%swing%' OR pitch_result ILIKE '%foul%' THEN 1 ELSE 0 END) AS swings,
    SUM(CASE WHEN pitch_result ILIKE '%called strike%' OR pitch_result ILIKE '%swinging strike%' THEN 1 ELSE 0 END) AS strikes,
    SUM(CASE WHEN pitch_result ILIKE '%ball%' THEN 1 ELSE 0 END) AS balls,
    -- Contact outcomes
    SUM(CASE WHEN pitch_result ILIKE '%hit%' OR pitch_result ILIKE '%single%' OR pitch_result ILIKE '%double%' OR pitch_result ILIKE '%triple%' OR pitch_result ILIKE '%home%' THEN 1 ELSE 0 END) AS hits,
    SUM(CASE WHEN pitch_result ILIKE '%out%' OR pitch_result ILIKE '%groundout%' OR pitch_result ILIKE '%flyout%' OR pitch_result ILIKE '%lineout%' THEN 1 ELSE 0 END) AS outs,
    AVG(launch_speed) AS avg_exit_velocity,
    AVG(launch_angle) AS avg_launch_angle,
    AVG(hit_distance) AS avg_hit_distance
FROM features_pitch.locations
WHERE plate_x IS NOT NULL AND plate_z IS NOT NULL
GROUP BY batter_id, game_year, pitch_type, location_zone;

-- View 4: Pitch Movement Analysis (pfx_x, pfx_z)
CREATE OR REPLACE VIEW eda.pitch_movement_analysis AS
SELECT
    pitcher_id,
    game_year,
    pitch_type,
    -- Movement classification
    CASE
        WHEN pfx_x < -5 THEN 'heavy_break_left'
        WHEN pfx_x BETWEEN -5 AND -2 THEN 'moderate_break_left'
        WHEN pfx_x BETWEEN -2 AND 2 THEN 'straight'
        WHEN pfx_x BETWEEN 2 AND 5 THEN 'moderate_break_right'
        WHEN pfx_x > 5 THEN 'heavy_break_right'
    END AS horizontal_movement,
    CASE
        WHEN pfx_z < -5 THEN 'heavy_drop'
        WHEN pfx_z BETWEEN -5 AND -2 THEN 'moderate_drop'
        WHEN pfx_z BETWEEN -2 AND 2 THEN 'flat'
        WHEN pfx_z BETWEEN 2 AND 5 THEN 'moderate_rise'
        WHEN pfx_z > 5 THEN 'heavy_rise'
    END AS vertical_movement,
    AVG(pfx_x) AS avg_pfx_x,
    AVG(pfx_z) AS avg_pfx_z,
    AVG(start_speed) AS avg_velocity,
    STDDEV(start_speed) AS velocity_stddev,
    COUNT(*) AS pitch_count,
    -- Outcomes by movement type
    SUM(CASE WHEN pitch_result ILIKE '%swinging strike%' THEN 1 ELSE 0 END)::float / NULLIF(COUNT(*), 0) AS whiff_rate,
    SUM(CASE WHEN pitch_result ILIKE '%hit%' OR pitch_result ILIKE '%single%' OR pitch_result ILIKE '%double%' OR pitch_result ILIKE '%triple%' OR pitch_result ILIKE '%home%' THEN 1 ELSE 0 END)::float / NULLIF(COUNT(*), 0) AS hit_rate
FROM features_pitch.locations
WHERE pfx_x IS NOT NULL AND pfx_z IS NOT NULL
GROUP BY pitcher_id, game_year, pitch_type, horizontal_movement, vertical_movement;

-- View 5: Spatial Strike Zone Density (for GIS heatmaps)
CREATE OR REPLACE VIEW eda.strike_zone_density AS
WITH binned_pitches AS (
    SELECT
        game_year,
        pitch_type,
        plate_x,
        plate_z,
        sz_bot,
        sz_top,
        pitch_result,
        -- 1-inch bins for detailed heatmap
        ROUND(plate_x)::int AS x_inch,
        ROUND(plate_z)::int AS z_inch
    FROM features_pitch.locations
    WHERE plate_x IS NOT NULL AND plate_z IS NOT NULL
)

SELECT
    game_year,
    pitch_type,
    x_inch,
    z_inch,
    COUNT(*) AS pitch_count,
    -- Create geometry point for each bin center
    ST_SETSRID(ST_MAKEPOINT(x_inch, z_inch), 4326) AS bin_center,
    -- Percentage of pitches in this bin that were strikes
    SUM(CASE WHEN plate_x BETWEEN -8.5 AND 8.5 AND plate_z BETWEEN sz_bot AND sz_top THEN 1 ELSE 0 END)::float / NULLIF(COUNT(*), 0) AS strike_rate,
    -- Swing rate
    SUM(CASE WHEN pitch_result ILIKE '%swing%' THEN 1 ELSE 0 END)::float / NULLIF(COUNT(*), 0) AS swing_rate,
    -- Whiff rate on swings
    SUM(CASE WHEN pitch_result ILIKE '%swinging strike%' THEN 1 ELSE 0 END)::float / NULLIF(SUM(CASE WHEN pitch_result ILIKE '%swing%' THEN 1 ELSE 0 END), 0) AS whiff_rate
FROM binned_pitches
GROUP BY game_year, pitch_type, x_inch, z_inch;

-- View 6: Pitcher-Batter Matchup Location Patterns
CREATE OR REPLACE VIEW eda.matchup_location_patterns AS
SELECT
    pitcher_id,
    batter_id,
    game_year,
    COUNT(*) AS total_matchups,
    -- Average location against this batter
    AVG(plate_x) AS avg_plate_x,
    AVG(plate_z) AS avg_plate_z,
    STDDEV(plate_x) AS std_plate_x,
    STDDEV(plate_z) AS std_plate_z,
    -- Do they work inside/outside?
    AVG(CASE WHEN plate_x < 0 THEN 1 ELSE 0 END) AS inside_pct,
    AVG(CASE WHEN plate_x > 0 THEN 1 ELSE 0 END) AS outside_pct,
    -- Do they work up/down?
    AVG(CASE WHEN plate_z > 2.5 THEN 1 ELSE 0 END) AS high_pct,
    AVG(CASE WHEN plate_z < 2.0 THEN 1 ELSE 0 END) AS low_pct,
    -- Outcomes
    AVG(CASE WHEN pitch_result ILIKE '%hit%' OR pitch_result ILIKE '%single%' OR pitch_result ILIKE '%double%' OR pitch_result ILIKE '%triple%' OR pitch_result ILIKE '%home%' THEN 1 ELSE 0 END) AS hit_rate,
    AVG(CASE WHEN pitch_result ILIKE '%strike%' THEN 1 ELSE 0 END) AS strike_rate
FROM features_pitch.locations
WHERE plate_x IS NOT NULL AND plate_z IS NOT NULL
GROUP BY pitcher_id, batter_id, game_year
HAVING COUNT(*) >= 10;  -- At least 10 pitches for meaningful patterns

-- Add comments
COMMENT ON VIEW eda.pitch_zone_classification IS 'Classifies each pitch location relative to strike zone with detailed zone breakdown';
COMMENT ON VIEW eda.pitcher_location_heatmap IS '3-inch binned heatmap of pitcher locations with swing/whiff rates';
COMMENT ON VIEW eda.batter_zone_performance IS 'Batter performance by pitch location zone';
COMMENT ON VIEW eda.pitch_movement_analysis IS 'Pitch movement patterns using pfx_x/pfx_z with outcome rates';
COMMENT ON VIEW eda.strike_zone_density IS '1-inch binned strike zone density for GIS heatmaps';
COMMENT ON VIEW eda.matchup_location_patterns IS 'Pitcher-batter specific location tendencies and outcomes';

