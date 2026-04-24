#!/usr/bin/env python3
"""
Plate Appearance Prediction Inference Script

Loads trained models and makes predictions for plate appearance outcomes.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import joblib
import pandas as pd
import psycopg2
from sqlalchemy import URL, create_engine, text


ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = ROOT / 'data' / 'models'


def database_kwargs() -> dict[str, str]:
    return {
        'host': os.environ.get('PGHOST', 'localhost'),
        'port': os.environ.get('PGPORT', '5432'),
        'dbname': os.environ.get('PGDATABASE', 'retrosheet'),
        'user': os.environ.get('PGUSER', 'postgres'),
        'password': os.environ.get('PGPASSWORD', ''),
    }


def database_url() -> str | URL:
    if os.environ.get('DATABASE_URL'):
        return os.environ['DATABASE_URL']
    kwargs = database_kwargs()
    return URL.create(
        'postgresql+psycopg2',
        username=kwargs['user'],
        password=kwargs['password'] or None,
        host=kwargs['host'],
        port=int(kwargs['port']),
        database=kwargs['dbname'],
    )


def load_model(target_id: str, model_name: str = 'hist_gradient_boosting') -> tuple:
    """Load a trained model and its feature specification."""
    conn = psycopg2.connect(**database_kwargs())
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT artifact_uri, feature_spec
                FROM models.model_registry
                WHERE target_id = %s AND model_name = %s AND is_active = true
                ORDER BY model_version DESC
                LIMIT 1
                """,
                (target_id, model_name),
            )
            row = cur.fetchone()
            if not row:
                cur.execute(
                    """
                    SELECT artifact_uri, feature_spec
                    FROM models.model_registry
                    WHERE target_id = %s AND model_name = %s
                    ORDER BY model_version DESC
                    LIMIT 1
                    """,
                    (target_id, model_name),
                )
                row = cur.fetchone()
            if not row:
                raise ValueError(f'No active model found for {target_id} with {model_name}')

            artifact_path = ROOT / row[0]
            feature_spec = row[1]

        model = joblib.load(artifact_path)
        return model, feature_spec
    finally:
        conn.close()


def predict_plate_appearance(
    game_id: str, plate_appearance_id: int, target_ids: list[str] | None = None,
) -> dict:
    """Make predictions for a specific plate appearance."""
    if target_ids is None:
        target_ids = [
            'pa_batter_hit',
            'pa_batter_walk',
            'pa_batter_strikeout',
            'pa_batter_home_run',
            'pa_batter_reach_base',
            'pa_batter_extra_base_hit',
        ]

    # Load features for this plate appearance
    engine = create_engine(database_url())
    try:
        sql = """
            SELECT
                examples.season,
                examples.inning,
                examples.is_bottom_inning::integer AS is_bottom_inning,
                examples.outs_before,
                examples.start_bases,
                examples.balls,
                examples.strikes,
                examples.home_score_diff,
                COALESCE(examples.batter_hand::text, 'U') AS batter_hand,
                COALESCE(examples.pitcher_hand::text, 'U') AS pitcher_hand,
                batter.prior_pa AS batter_prior_pa,
                batter.prior_hit_rate AS batter_prior_hit_rate,
                batter.prior_walk_rate AS batter_prior_walk_rate,
                batter.prior_strikeout_rate AS batter_prior_strikeout_rate,
                batter.prior_home_run_rate AS batter_prior_home_run_rate,
                batter.prior_reach_base_rate AS batter_prior_reach_base_rate,
                batter.prior_extra_base_hit_rate AS batter_prior_extra_base_hit_rate,
                pitcher.prior_batters_faced AS pitcher_prior_batters_faced,
                pitcher.prior_hit_allowed_rate AS pitcher_prior_hit_allowed_rate,
                pitcher.prior_walk_allowed_rate AS pitcher_prior_walk_allowed_rate,
                pitcher.prior_strikeout_rate AS pitcher_prior_strikeout_rate,
                pitcher.prior_home_run_allowed_rate AS pitcher_prior_home_run_allowed_rate,
                pitcher.prior_reach_base_allowed_rate AS pitcher_prior_reach_base_allowed_rate,
                pitcher.prior_extra_base_hit_allowed_rate AS pitcher_prior_extra_base_hit_allowed_rate,
                batting_team.prior_win_rate AS batting_team_prior_win_rate,
                batting_team.prior_runs_scored_per_game AS batting_team_prior_runs_scored_per_game,
                batting_team.prior_runs_allowed_per_game AS batting_team_prior_runs_allowed_per_game,
                fielding_team.prior_win_rate AS fielding_team_prior_win_rate,
                fielding_team.prior_runs_scored_per_game AS fielding_team_prior_runs_scored_per_game,
                fielding_team.prior_runs_allowed_per_game AS fielding_team_prior_runs_allowed_per_game,
                context.prior_pa AS context_prior_pa,
                context.prior_hit_rate AS context_prior_hit_rate,
                context.prior_walk_rate AS context_prior_walk_rate,
                context.prior_strikeout_rate AS context_prior_strikeout_rate,
                context.prior_home_run_rate AS context_prior_home_run_rate,
                context.prior_reach_base_rate AS context_prior_reach_base_rate,
                context.prior_extra_base_hit_rate AS context_prior_extra_base_hit_rate,
                context.prior_batting_team_win_rate AS context_prior_batting_team_win_rate
            FROM features.plate_appearance_examples examples
            LEFT JOIN features.batter_prior_season_pa_summary batter
              ON batter.feature_season = examples.season
             AND batter.batter_id = examples.batter_id
            LEFT JOIN features.pitcher_prior_season_pa_summary pitcher
              ON pitcher.feature_season = examples.season
             AND pitcher.pitcher_id = examples.pitcher_id
            LEFT JOIN features.team_prior_season_summary batting_team
              ON batting_team.feature_season = examples.season
             AND batting_team.team_id = examples.batting_team_id
            LEFT JOIN features.team_prior_season_summary fielding_team
              ON fielding_team.feature_season = examples.season
             AND fielding_team.team_id = examples.fielding_team_id
            LEFT JOIN features.pa_context_prior_season_rates context
              ON context.feature_season = examples.season
             AND context.batter_hand = COALESCE(examples.batter_hand::text, 'U')
             AND context.pitcher_hand = COALESCE(examples.pitcher_hand::text, 'U')
             AND context.inning = examples.inning
             AND context.is_bottom_inning = examples.is_bottom_inning
             AND context.outs_before = examples.outs_before
             AND context.start_bases = examples.start_bases
             AND context.balls = examples.balls
             AND context.strikes = examples.strikes
            WHERE examples.game_id = :game_id AND examples.plate_appearance_id = :plate_appearance_id
        """
        df = pd.read_sql_query(
            text(sql),
            engine,
            params={'game_id': game_id, 'plate_appearance_id': plate_appearance_id},
        )
        if df.empty:
            raise ValueError(f'Plate appearance {game_id}:{plate_appearance_id} not found')

        predictions = {}

        for target_id in target_ids:
            model, feature_spec = load_model(target_id)

            # Prepare features
            numeric_features = feature_spec['numeric_features']
            categorical_features = feature_spec['categorical_features']
            features = df[numeric_features + categorical_features]

            # Make prediction
            probabilities = model.predict_proba(features)[0]
            predictions[target_id] = {
                'probability': float(probabilities[1]),
                'model_version': 'latest',
            }

        return {
            'game_id': game_id,
            'plate_appearance_id': plate_appearance_id,
            'predictions': predictions,
            'input_features': df.iloc[0].to_dict(),
        }

    finally:
        engine.dispose()


def main():
    parser = argparse.ArgumentParser(description='Make plate appearance predictions')
    parser.add_argument('--game-id', required=True, help='Game ID')
    parser.add_argument(
        '--plate-appearance-id', type=int, required=True, help='Plate appearance ID',
    )
    parser.add_argument('--targets', nargs='*', help='Specific targets to predict (default: all)')

    args = parser.parse_args()

    try:
        result = predict_plate_appearance(args.game_id, args.plate_appearance_id, args.targets)
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(f'Error: {e}')
        exit(1)


if __name__ == '__main__':
    main()
