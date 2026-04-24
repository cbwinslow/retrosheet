-- Phase 2 Enhanced Feature View
-- Combines Phase 2 features into the training set

CREATE OR REPLACE VIEW features.plate_appearance_phase2_features AS
SELECT
    pa.*,
    -- Team momentum features
    home_team.team_last_5_win_rate AS home_team_last_5_win_rate,
    home_team.team_last_10_win_rate AS home_team_last_10_win_rate,
    home_team.team_last_3_runs_scored_avg AS home_team_last_3_runs_scored_avg,
    home_team.team_momentum_delta AS home_team_momentum_delta,
    away_team.team_last_5_win_rate AS away_team_last_5_win_rate,
    away_team.team_last_10_win_rate AS away_team_last_10_win_rate,
    away_team.team_last_3_runs_scored_avg AS away_team_last_3_runs_scored_avg,
    away_team.team_momentum_delta AS away_team_momentum_delta,
    -- Postseason clutch features
    post.is_postseason,
    post.is_high_leverage_situation,
    post.is_weekend_game,
    post.is_doubleheader
FROM features.plate_appearance_enhanced_examples AS pa
LEFT JOIN features.team_momentum_features AS home_team
    ON
        pa.game_id = home_team.game_id
        AND pa.home_team_id = home_team.team_id
LEFT JOIN features.team_momentum_features AS away_team
    ON
        pa.game_id = away_team.game_id
        AND pa.away_team_id = away_team.team_id
LEFT JOIN features.postseason_clutch_features AS post
    ON pa.game_id = post.game_id;
