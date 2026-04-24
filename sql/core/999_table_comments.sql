/*
File: sql/core/999_table_comments.sql
Purpose: Add COMMENT ON statements for tables missing documentation
Author: Agent Cascade
Date: 2026-04-24
Depends On: All core tables must exist
Called By: Manual execution after warehouse rebuild

Tables Documented:
- core.games, core.events, core.plate_appearances
- core.players, core.teams, core.parks, core.mlb_pbp
- features.play_snapshot
- models.model_registry
- predictions.* (9 tables)
- raw_mlb.boxscore_snapshots, raw_mlb.gameday_xml
*/

-- Core tables
COMMENT ON TABLE core.games IS 'Canonical game-level records (62,598 historical games 1898-2025)';
COMMENT ON TABLE core.events IS 'Play-by-play event records (~4.9M events with game-state tracking)';
COMMENT ON TABLE core.plate_appearances IS 'Plate appearance-level outcomes for PA outcome modeling';
COMMENT ON TABLE core.players IS 'Player reference data (15,000+ players with batting/throwing hands)';
COMMENT ON TABLE core.teams IS 'Team reference data (35 teams with league/division assignments)';
COMMENT ON TABLE core.parks IS 'Park/venue reference data (60 parks with location info)';
COMMENT ON TABLE core.mlb_pbp IS 'MLB play-by-play data from API for live games';

-- Features
COMMENT ON TABLE features.play_snapshot IS 'Snapshot of play state for real-time prediction features';

-- Models
COMMENT ON TABLE models.model_registry IS 'Trained model metadata with hyperparameters and artifact paths';

-- Predictions
COMMENT ON TABLE predictions.prediction_targets IS 'Taxonomy of prediction targets (game, pa, pitch outcomes)';
COMMENT ON TABLE predictions.target_outcomes IS 'Possible outcomes for each prediction target';
COMMENT ON TABLE predictions.prediction_runs IS 'Batch prediction job tracking and metadata';
COMMENT ON TABLE predictions.target_probabilities IS 'Individual prediction outputs with probability distributions';
COMMENT ON TABLE predictions.live_pa_predictions IS 'Real-time plate appearance predictions during live games';
COMMENT ON TABLE predictions.win_probabilities IS 'Game win probability predictions by state';
COMMENT ON TABLE predictions.api_prediction_requests IS 'External API prediction request log';
COMMENT ON TABLE predictions.simulation_runs IS 'Monte Carlo simulation batch runs';
COMMENT ON TABLE predictions.bootstrap_reports IS 'Bootstrap confidence interval reports';
COMMENT ON TABLE predictions.calibration_reports IS 'Model calibration assessment reports';

-- Raw MLB
COMMENT ON TABLE raw_mlb.boxscore_snapshots IS 'Source-preserved MLB boxscore JSON snapshots';
COMMENT ON TABLE raw_mlb.gameday_xml IS 'Legacy Gameday XML data source-preserved';
