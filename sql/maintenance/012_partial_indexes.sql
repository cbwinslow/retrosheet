-- Implement PostgreSQL partial indexes for conditional queries
-- Research-backed: Partial indexes improve performance and reduce storage
-- Use Cases: Recent games, active players, high-leverage situations

-- Partial index on recent games (2023 and later)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_recent_games 
ON core.games (game_date) 
WHERE season >= 2023;

-- Partial index on active players
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_active_players 
ON core.people (retrosheet_player_id) 
WHERE debut_year >= 2020 OR final_year IS NULL;

-- Partial index on high-leverage plate appearances
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_high_leverage_pa 
ON features.plate_appearance_examples (game_id, inning) 
WHERE leverage_index > 2.0;

-- Partial index on complete games (for pitchers)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_complete_games 
ON core.games (game_date, home_team_id, away_team_id) 
WHERE scheduled_innings = 9 AND game_type = 'R';

-- Partial index on Statcast data with launch speed
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_statcast_launch_speed 
ON raw_mlb.statcast (launch_speed) 
WHERE launch_speed IS NOT NULL;

-- Validate partial indexes
-- Check if index is used for recent games query
EXPLAIN ANALYZE
SELECT * FROM core.games 
WHERE season >= 2023 
ORDER BY game_date 
LIMIT 10;

-- Check if index is used for active players query
EXPLAIN ANALYZE
SELECT * FROM core.people 
WHERE debut_year >= 2020 OR final_year IS NULL
LIMIT 10;

-- Check index sizes
SELECT 
    schemaname,
    tablename,
    indexname,
    pg_size_pretty(pg_relation_size(indexname::regclass)) as index_size
FROM pg_indexes
WHERE tablename IN ('games', 'people', 'plate_appearance_examples', 'statcast')
ORDER BY pg_relation_size(indexname::regclass) DESC;
