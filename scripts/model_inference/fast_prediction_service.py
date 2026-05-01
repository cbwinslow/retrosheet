#!/usr/bin/env python3
"""
High-Performance Prediction Service

Optimized for simulation workloads with:
- Model caching in memory
- Batch prediction support
- Minimal database queries
- Fast feature lookups
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from psycopg2.pool import SimpleConnectionPool


ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = ROOT / 'data' / 'models'


class PredictionService:
    """High-performance prediction service with model caching."""

    def __init__(self, max_connections: int = 10):
        self.models: dict[str, tuple[Any, dict]] = {}  # target_id -> (model, feature_spec)
        self.db_pool = SimpleConnectionPool(
            minconn=1,
            maxconn=max_connections,
            **self._database_kwargs(),
        )
        self.executor = ThreadPoolExecutor(max_workers=max_connections)
        self._load_active_models()

    def _database_kwargs(self) -> dict[str, str]:
        return {
            'host': os.environ.get('PGHOST', 'localhost'),
            'port': os.environ.get('PGPORT', '5432'),
            'dbname': os.environ.get('PGDATABASE', 'retrosheet'),
            'user': os.environ.get('PGUSER', 'postgres'),
            'password': os.environ.get('PGPASSWORD', ''),
        }

    def _database_url(self) -> str:
        kwargs = self._database_kwargs()
        return f'postgresql+psycopg2://{kwargs["user"]}:{kwargs["password"]}@{kwargs["host"]}:{kwargs["port"]}/{kwargs["dbname"]}'

    def _load_active_models(self) -> None:
        """Load all active models into memory."""
        conn = self.db_pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT target_id, model_name, artifact_uri, feature_spec
                    FROM models.model_registry
                    WHERE is_active = true
                    ORDER BY target_id, model_name
                    """,
                )
                rows = cur.fetchall()

                for row in rows:
                    target_id, model_name, artifact_uri, feature_spec = row
                    model_path = ROOT / artifact_uri

                    if model_path.exists():
                        model = joblib.load(model_path)
                        self.models[target_id] = (model, feature_spec)
                        print(f'Loaded model: {target_id} ({model_name})')
                    else:
                        print(f'Warning: Model file not found: {model_path}')

        finally:
            self.db_pool.putconn(conn)

    def get_features_from_db(self, game_id: str, plate_appearance_id: int) -> dict | None:
        """Get pre-computed features from optimized inference view."""
        conn = self.db_pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT * FROM inference.plate_appearance_features
                    WHERE game_id = %s AND plate_appearance_id = %s
                    """,
                    (game_id, plate_appearance_id),
                )
                row = cur.fetchone()
                if row:
                    # Convert to dict (simplified - would need column names)
                    return dict(zip([desc[0] for desc in cur.description], row, strict=False))
                return None
        finally:
            self.db_pool.putconn(conn)

    def get_features_from_state(self, game_state: dict) -> pd.DataFrame:
        """Compute features from game state parameters."""
        # Use database function to get enriched features
        conn = self.db_pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT * FROM inference.get_plate_appearance_features(
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    """,
                    (
                        game_state.get('season', 2023),
                        game_state.get('inning', 1),
                        game_state.get('is_bottom_inning', False),
                        game_state.get('outs_before', 0),
                        game_state.get('start_bases', 0),
                        game_state.get('balls', 0),
                        game_state.get('strikes', 0),
                        game_state.get('home_score_diff', 0),
                        game_state.get('batter_hand', 'R'),
                        game_state.get('pitcher_hand', 'R'),
                        game_state.get('batter_id'),
                        game_state.get('pitcher_id'),
                        game_state.get('batting_team_id'),
                        game_state.get('fielding_team_id'),
                    ),
                )
                row = cur.fetchone()
                if row:
                    # Create feature vector
                    features = dict(zip([desc[0] for desc in cur.description], row, strict=False))

                    # Create base features
                    base_features = {
                        'inning': game_state.get('inning', 1),
                        'is_bottom_inning': int(game_state.get('is_bottom_inning', False)),
                        'outs_before': game_state.get('outs_before', 0),
                        'start_bases': game_state.get('start_bases', 0),
                        'balls': game_state.get('balls', 0),
                        'strikes': game_state.get('strikes', 0),
                        'home_score_diff': game_state.get('home_score_diff', 0),
                        'batter_hand': game_state.get('batter_hand', 'R'),
                        'pitcher_hand': game_state.get('pitcher_hand', 'R'),
                    }

                    # Add enriched features
                    base_features.update(features)

                    return pd.DataFrame([base_features])
                return pd.DataFrame()
        finally:
            self.db_pool.putconn(conn)

    def predict_single(self, target_id: str, features: pd.DataFrame) -> float:
        """Make a single prediction."""
        if target_id not in self.models:
            msg = f'No active model found for {target_id}'
            raise ValueError(msg)

        model, feature_spec = self.models[target_id]
        numeric_features = feature_spec['numeric_features']
        categorical_features = feature_spec['categorical_features']
        feature_cols = numeric_features + categorical_features

        # Ensure all required features are present
        missing_features = set(feature_cols) - set(features.columns)
        if missing_features:
            # Fill missing features with defaults
            for feat in missing_features:
                if feat in ['batter_prior_pa', 'pitcher_prior_batters_faced']:
                    features[feat] = 0
                elif 'rate' in feat or 'win_rate' in feat:
                    features[feat] = 0.25  # Neutral rate
                else:
                    features[feat] = 0

        feature_data = features[feature_cols]
        probabilities = model.predict_proba(feature_data)
        return float(probabilities[0][1])

    def predict_batch(self, predictions: list[dict]) -> list[dict]:
        """Make batch predictions efficiently."""
        results = []

        for pred_request in predictions:
            target_id = pred_request['target_id']
            game_state = pred_request['game_state']

            # Get features
            features = self.get_features_from_state(game_state)

            if features.empty:
                results.append(
                    {
                        'target_id': target_id,
                        'probability': 0.5,  # Default fallback
                        'error': 'Could not compute features',
                    },
                )
                continue

            # Make prediction
            try:
                probability = self.predict_single(target_id, features)
                results.append({'target_id': target_id, 'probability': probability})
            except Exception as e:
                results.append({'target_id': target_id, 'probability': 0.5, 'error': str(e)})

        return results

    def predict_plate_appearance(self, game_id: str, plate_appearance_id: int) -> dict:
        """Predict all outcomes for a specific plate appearance."""
        features = self.get_features_from_db(game_id, plate_appearance_id)
        if not features:
            return {'error': 'Plate appearance not found'}

        # Convert to DataFrame
        features_df = pd.DataFrame([features])

        predictions = {}
        for target_id in self.models:
            try:
                prob = self.predict_single(target_id, features_df)
                predictions[target_id] = prob
            except Exception as e:
                predictions[target_id] = {'error': str(e)}

        return {
            'game_id': game_id,
            'plate_appearance_id': plate_appearance_id,
            'predictions': predictions,
            'features_used': list(features_df.columns),
        }

    def simulate_half_inning_fast(self, game_state: dict, num_simulations: int = 100) -> dict:
        """Fast half-inning simulation using cached models."""
        # This is a simplified simulation - in practice you'd want more sophisticated
        # base-running and game-state logic

        results = []

        for _ in range(num_simulations):
            sim_state = game_state.copy()
            runs_scored = 0
            outs = 0
            pa_count = 0

            while outs < 3 and pa_count < 12:  # Safety limit
                # Create feature vector for current state
                current_features = self.get_features_from_state(sim_state)

                if current_features.empty:
                    break

                # Predict outcomes for this plate appearance
                predictions = {}
                for target_id in [
                    'pa_batter_hit',
                    'pa_batter_walk',
                    'pa_batter_strikeout',
                ]:
                    try:
                        prob = self.predict_single(target_id, current_features)
                        predictions[target_id] = prob
                    except:
                        predictions[target_id] = 0.5

                # Sample outcomes
                outcomes = {}
                for target, prob in predictions.items():
                    outcomes[target] = np.random.random() < prob

                # Update game state based on outcomes
                if outcomes.get('pa_batter_strikeout', False):
                    outs += 1
                elif outcomes.get('pa_batter_walk', False) or outcomes.get('pa_batter_hit', False):
                    # Simplified: batter reaches base
                    # In reality, this would involve base-running logic
                    pass  # For now, just continue
                else:
                    outs += 1

                pa_count += 1

                # Reset count for next PA
                sim_state['balls'] = 0
                sim_state['strikes'] = 0

            results.append({'runs': runs_scored, 'outs': outs, 'plate_appearances': pa_count})

        # Aggregate results
        runs_dist = [r['runs'] for r in results]
        any_run_prob = sum(1 for r in results if r['runs'] > 0) / len(results)

        return {
            'num_simulations': num_simulations,
            'any_run_probability': any_run_prob,
            'average_runs': np.mean(runs_dist),
            'runs_distribution': {
                '0': runs_dist.count(0),
                '1': runs_dist.count(1),
                '2': runs_dist.count(2),
                '3+': sum(1 for r in runs_dist if r >= 3),
            },
        }


class AsyncPredictionService:
    """Async wrapper for the prediction service."""

    def __init__(self, service: PredictionService):
        self.service = service
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()

    def _run_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    async def predict_batch_async(self, predictions: list[dict]) -> list[dict]:
        """Async batch prediction."""
        return await asyncio.get_event_loop().run_in_executor(
            None,
            self.service.predict_batch,
            predictions,
        )

    async def simulate_half_inning_async(
        self,
        game_state: dict,
        num_simulations: int = 100,
    ) -> dict:
        """Async half-inning simulation."""
        return await asyncio.get_event_loop().run_in_executor(
            None,
            self.service.simulate_half_inning_fast,
            game_state,
            num_simulations,
        )


def main():
    parser = argparse.ArgumentParser(description='High-performance prediction service')
    parser.add_argument('--port', type=int, default=8080, help='Port to run service on')
    parser.add_argument('--workers', type=int, default=4, help='Number of worker threads')

    args = parser.parse_args()

    # Initialize service
    service = PredictionService(max_connections=args.workers)
    AsyncPredictionService(service)

    print(f'Prediction service started with {len(service.models)} cached models')
    print(f'Available targets: {list(service.models.keys())}')

    # Simple CLI interface for testing
    while True:
        try:
            cmd = input('Enter command (predict/simulate/quit): ').strip().lower()

            if cmd == 'quit':
                break
            if cmd == 'predict':
                game_id = input('Game ID: ').strip()
                pa_id = int(input('Plate appearance ID: ').strip())
                result = service.predict_plate_appearance(game_id, pa_id)
                print(json.dumps(result, indent=2))
            elif cmd == 'simulate':
                # Simple simulation test
                game_state = {
                    'season': 2023,
                    'inning': 1,
                    'is_bottom_inning': False,
                    'outs_before': 0,
                    'start_bases': 0,
                    'balls': 0,
                    'strikes': 0,
                    'home_score_diff': 0,
                    'batter_hand': 'R',
                    'pitcher_hand': 'R',
                }
                start_time = time.time()
                result = service.simulate_half_inning_fast(game_state, 50)
                time.time() - start_time
                print('.2f')
                print(json.dumps(result, indent=2))
            else:
                print('Unknown command. Use: predict, simulate, or quit')

        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f'Error: {e}')


if __name__ == '__main__':
    main()
