-- File: sql/optimization/141_performance_indexes.sql
-- Purpose: Performance indexes on core events, games, players, teams
-- Author: Agent Cascade
-- Date: 2026-04-24
CREATE INDEX CONCURRENTLY IF NOT EXISTS events_game_id_idx ON core.events (game_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS events_season_idx ON core.events (season);
CREATE INDEX CONCURRENTLY IF NOT EXISTS events_game_event_idx ON core.events (game_id, event_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS events_season_batter_idx ON core.events (season, batter_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS events_season_pitcher_idx ON core.events (season, pitcher_id);

-- Live events additional indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS live_events_game_id_idx ON core.live_events (game_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS live_events_season_idx ON core.live_events (season);
CREATE INDEX CONCURRENTLY IF NOT EXISTS live_events_game_event_idx ON core.live_events (game_id, event_id);

-- Plate appearances additional indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS plate_appearances_game_id_idx ON core.plate_appearances (game_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS plate_appearances_season_idx ON core.plate_appearances (season);
CREATE INDEX CONCURRENTLY IF NOT EXISTS plate_appearances_season_batter_idx ON core.plate_appearances (season, batter_id);

-- Players and teams reference indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS players_retrosheet_id_idx ON core.players (retrosheet_player_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS teams_retrosheet_id_idx ON core.teams (retrosheet_team_id);

-- Game filtering indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS games_source_type_idx ON core.games (source_type);

