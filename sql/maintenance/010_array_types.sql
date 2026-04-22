-- Implement PostgreSQL array types for multi-value features
-- Research-backed: Arrays are efficient for storing sequences and multi-value data
-- Use Cases: Pitch sequences, player rosters, injury history, recent performance

-- Add pitch sequence array to plate appearance examples
-- This stores the sequence of pitch types in an at-bat
ALTER TABLE features.plate_appearance_examples 
ADD COLUMN IF NOT EXISTS pitch_sequence TEXT[];

-- Add example of array operations
-- Insert a pitch sequence
UPDATE features.plate_appearance_examples
SET pitch_sequence = ARRAY['FF', 'FF', 'SL', 'CH']
WHERE pitch_sequence IS NULL
LIMIT 1;

-- Query array elements
SELECT pitch_sequence, pitch_sequence[1], array_length(pitch_sequence, 1)
FROM features.plate_appearance_examples
WHERE pitch_sequence IS NOT NULL
LIMIT 5;

-- Add recent performance array to player season stats
-- This stores the last 10 game performances
ALTER TABLE features.player_season_stats
ADD COLUMN IF NOT EXISTS recent_game_results INTEGER[];

-- Add injury history array to player bio
ALTER TABLE core.people
ADD COLUMN IF NOT EXISTS injury_history TEXT[];

-- Validate array operations
-- Check array contains specific value
SELECT * FROM features.plate_appearance_examples
WHERE 'FF' = ANY(pitch_sequence)
LIMIT 5;

-- Get array length
SELECT pitch_sequence, array_length(pitch_sequence, 1)
FROM features.plate_appearance_examples
WHERE pitch_sequence IS NOT NULL
LIMIT 5;
