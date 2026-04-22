-- Implement PostgreSQL custom types (domains) for baseball-specific data
-- Research-backed: Domains enforce data integrity and business rules
-- Use Cases: Pitch types, event types, hand types, league types

-- Create pitch type domain
CREATE DOMAIN pitch_type AS TEXT
CHECK (VALUE IN ('FF', 'SL', 'CH', 'CU', 'FC', 'FS', 'SI', 'KN', 'EP', 'UN'));

COMMENT ON DOMAIN pitch_type IS 'Valid pitch types: Four-seam Fastball (FF), Slider (SL), Changeup (CH), Curveball (CU), Cutter (FC), Splitter (FS), Sinker (SI), Knuckleball (KN), Eephus (EP), Unknown (UN)';

-- Create event type domain
CREATE DOMAIN event_type AS TEXT
CHECK (VALUE IN ('single', 'double', 'triple', 'home_run', 'walk', 'strikeout', 'ground_out', 'fly_out', 'line_out', 'pop_out', 'field_out', 'hit_by_pitch', 'sac_bunt', 'sac_fly', 'double_play', 'triple_play', 'error', 'fielders_choice', 'intentional_walk', 'catcher_interf'));

COMMENT ON DOMAIN event_type IS 'Valid event types for plate appearance outcomes';

-- Create hand domain
CREATE DOMAIN hand_type AS TEXT
CHECK (VALUE IN ('L', 'R', 'B', 'U'));

COMMENT ON DOMAIN hand_type IS 'Valid hand types: Left (L), Right (R), Both (B), Unknown (U)';

-- Create league domain
CREATE DOMAIN league_type AS TEXT
CHECK (VALUE IN ('AL', 'NL', 'MLB'));

COMMENT ON DOMAIN league_type IS 'Valid league types: American League (AL), National League (NL), MLB (combined)';

-- Create division domain
CREATE DOMAIN division_type AS TEXT
CHECK (VALUE IN ('E', 'W', 'C'));

COMMENT ON DOMAIN division_type IS 'Valid division types: East (E), West (W), Central (C)';

-- Test domain constraints
-- This should succeed
SELECT 'FF'::pitch_type;
SELECT 'single'::event_type;
SELECT 'L'::hand_type;
SELECT 'AL'::league_type;
SELECT 'E'::division_type;

-- This should fail (uncomment to test)
-- SELECT 'INVALID'::pitch_type;

-- Apply domains to existing columns (example)
-- ALTER TABLE features.plate_appearance_examples
-- ALTER COLUMN pitch_type TYPE pitch_type USING pitch_type::pitch_type;

-- ALTER TABLE features.plate_appearance_examples
-- ALTER COLUMN batter_hand TYPE hand_type USING batter_hand::hand_type;

-- ALTER TABLE features.plate_appearance_examples
-- ALTER COLUMN pitcher_hand TYPE hand_type USING pitcher_hand::hand_type;
