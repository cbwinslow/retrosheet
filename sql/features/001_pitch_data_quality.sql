-- Pitch Data Quality Layer
-- Handles outliers and creates clean datasets for analysis

-- Add quality classification column (if not exists)
ALTER TABLE features_pitch.locations
ADD COLUMN IF NOT EXISTS quality_flag TEXT DEFAULT 'normal';

-- Classify all pitches by quality
UPDATE features_pitch.locations
SET quality_flag = CASE
    -- Extreme outliers (clear tracking errors)
    WHEN plate_z < -5 THEN 'extreme_outlier_low'
    WHEN plate_z > 6 THEN 'high_passed_ball'  -- Valid but unusual
    WHEN plate_x < -20 OR plate_x > 20 THEN 'wide_wild_pitch'  -- Valid but unusual
    WHEN plate_x IS NULL OR plate_z IS NULL THEN 'missing_location'
    WHEN start_speed IS NULL OR start_speed < 30 OR start_speed > 110 THEN 'velocity_outlier'
    ELSE 'normal'
END;

-- Create clean view for modeling/analysis (excludes only extreme outliers)
CREATE OR REPLACE VIEW features_pitch.locations_clean AS
SELECT *
FROM features_pitch.locations
WHERE
    quality_flag = 'normal'
    OR quality_flag = 'high_passed_ball'
    OR quality_flag = 'wide_wild_pitch';

-- Create strict clean view (only perfect tracking data)
CREATE OR REPLACE VIEW features_pitch.locations_strict AS
SELECT *
FROM features_pitch.locations
WHERE quality_flag = 'normal';

-- Quality summary view
CREATE OR REPLACE VIEW features_pitch.data_quality_summary AS
SELECT
    quality_flag,
    COUNT(*) AS pitch_count,
    ROUND(COUNT(*)::NUMERIC / (SELECT COUNT(*) FROM features_pitch.locations) * 100, 4) AS pct_of_total,
    ROUND(COUNT(*)::NUMERIC / (SELECT COUNT(*) FROM features_pitch.locations) * 1000000, 2) AS per_million
FROM features_pitch.locations
GROUP BY quality_flag
ORDER BY pitch_count DESC;

-- Indexes for quality filtering
CREATE INDEX IF NOT EXISTS idx_pitch_quality_flag
ON features_pitch.locations (quality_flag);

-- Documentation comments
COMMENT ON COLUMN features_pitch.locations.quality_flag IS
'Data quality classification: normal, high_passed_ball, wide_wild_pitch, extreme_outlier_low, missing_location, velocity_outlier';

COMMENT ON VIEW features_pitch.locations_clean IS
'Pitch data excluding only extreme outliers (plate_z < -5). Includes normal pitches and reasonable wild pitches.';

COMMENT ON VIEW features_pitch.locations_strict IS
'Pitch data with only normal tracking (no outliers of any kind). Use for strict analysis.';

-- Show final quality breakdown
SELECT * FROM features_pitch.data_quality_summary;
