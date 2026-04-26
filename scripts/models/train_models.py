#!/usr/bin/env python3
"""Model Training Pipeline for Baseball Prediction Models.

This script trains the Next-Run Probability and PA Outcome models:
1. Populates training data from historical games
2. Computes feature vectors
3. Trains models with cross-validation
4. Evaluates and saves models
5. Generates predictions on test data

Usage:
    # Train both models for 2024-2025, test on 2026
    uv run python scripts/models/train_models.py \\
        --train-seasons 2024 2025 \\
        --test-seasons 2026 \\
        --models next_run pa_outcome

    # Train only Next-Run model
    uv run python scripts/models/train_models.py \\
        --train-seasons 2023 2024 2025 \\
        --test-seasons 2026 \\
        --models next_run

    # Quick test mode (10% sample)
    uv run python scripts/models/train_models.py \\
        --train-seasons 2025 \\
        --test-seasons 2026 \\
        --sample-rate 0.1

Author: Agent cbwinslow/retrosheet
Date: 2026-04-26
"""

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import psycopg2
from psycopg2.extensions import connection

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from baseball.models import (
    NextRunProbabilityModel,
    PAOutcomeModel,
    TrainingConfig,
    ModelConfig,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('train_models')


def get_db_connection() -> connection:
    """Get database connection from environment or defaults."""
    import os
    
    # Try DATABASE_URL first
    db_url = os.environ.get('DATABASE_URL')
    if db_url:
        return psycopg2.connect(db_url)
    
    # Fall back to individual parameters
    return psycopg2.connect(
        host=os.environ.get('PGHOST', 'localhost'),
        port=os.environ.get('PGPORT', '5432'),
        database=os.environ.get('PGDATABASE', 'retrosheet'),
        user=os.environ.get('PGUSER', 'postgres'),
        password=os.environ.get('PGPASSWORD', ''),
    )


def populate_next_run_training(
    db: connection,
    seasons: List[int],
    sample_rate: float = 1.0
) -> int:
    """Populate Next-Run training data.
    
    Args:
        db: Database connection
        seasons: Seasons to populate
        sample_rate: Fraction of data to sample (1.0 = all)
        
    Returns:
        Number of rows inserted
    """
    logger.info(f'Populating Next-Run training data for seasons: {seasons}')
    
    total_rows = 0
    with db.cursor() as cur:
        for season in seasons:
            cur.execute(
                'SELECT models.populate_next_run_training(%s, %s)',
                (season, sample_rate)
            )
            rows = cur.fetchone()[0]
            total_rows += rows
            logger.info(f'  Season {season}: {rows} rows')
    
    db.commit()
    logger.info(f'Total Next-Run training rows: {total_rows}')
    return total_rows


def populate_pa_outcome_training(
    db: connection,
    seasons: List[int],
    sample_rate: float = 1.0
) -> int:
    """Populate PA Outcome training data.
    
    Args:
        db: Database connection
        seasons: Seasons to populate
        sample_rate: Fraction of data to sample
        
    Returns:
        Number of rows inserted
    """
    logger.info(f'Populating PA Outcome training data for seasons: {seasons}')
    
    total_rows = 0
    with db.cursor() as cur:
        for season in seasons:
            cur.execute(
                'SELECT models.populate_pa_outcome_training(%s, %s)',
                (season, sample_rate)
            )
            rows = cur.fetchone()[0]
            total_rows += rows
            logger.info(f'  Season {season}: {rows} rows')
    
    db.commit()
    logger.info(f'Total PA Outcome training rows: {total_rows}')
    return total_rows


def compute_next_run_features(db: connection, seasons: List[int]) -> int:
    """Compute feature vectors for Next-Run model.
    
    Args:
        db: Database connection
        seasons: Seasons to compute
        
    Returns:
        Number of feature vectors computed
    """
    logger.info(f'Computing Next-Run features for seasons: {seasons}')
    
    with db.cursor() as cur:
        # Get training IDs that need features
        cur.execute('''
            SELECT training_id 
            FROM models.next_run_training_data
            WHERE season = ANY(%s)
              AND training_id NOT IN (
                  SELECT training_id FROM models.next_run_features
              )
            LIMIT 10000
        ''', (seasons,))
        
        training_ids = [row[0] for row in cur.fetchall()]
        
        if not training_ids:
            logger.info('No new training examples to process')
            return 0
        
        logger.info(f'Computing features for {len(training_ids)} examples')
        
        # Compute features in batches
        batch_size = 1000
        computed = 0
        
        for i in range(0, len(training_ids), batch_size):
            batch = training_ids[i:i + batch_size]
            for training_id in batch:
                cur.execute(
                    'SELECT models.compute_next_run_features(%s)',
                    (training_id,)
                )
            db.commit()
            computed += len(batch)
            logger.info(f'  Computed {computed}/{len(training_ids)}')
    
    logger.info(f'Total Next-Run features computed: {computed}')
    return computed


def compute_pa_outcome_features(db: connection, seasons: List[int]) -> int:
    """Compute feature vectors for PA Outcome model.
    
    Args:
        db: Database connection
        seasons: Seasons to compute
        
    Returns:
        Number of feature vectors computed
    """
    logger.info(f'Computing PA Outcome features for seasons: {seasons}')
    
    with db.cursor() as cur:
        # Get training IDs that need features
        cur.execute('''
            SELECT training_id 
            FROM models.pa_outcome_training_data
            WHERE season = ANY(%s)
              AND training_id NOT IN (
                  SELECT training_id FROM models.pa_outcome_features
              )
            LIMIT 10000
        ''', (seasons,))
        
        training_ids = [row[0] for row in cur.fetchall()]
        
        if not training_ids:
            logger.info('No new training examples to process')
            return 0
        
        logger.info(f'Computing features for {len(training_ids)} examples')
        
        # Compute features in batches
        batch_size = 1000
        computed = 0
        
        for i in range(0, len(training_ids), batch_size):
            batch = training_ids[i:i + batch_size]
            for training_id in batch:
                cur.execute(
                    'SELECT models.compute_pa_outcome_features(%s)',
                    (training_id,)
                )
            db.commit()
            computed += len(batch)
            logger.info(f'  Computed {computed}/{len(training_ids)}')
    
    logger.info(f'Total PA Outcome features computed: {computed}')
    return computed


def train_next_run_model(
    db: connection,
    train_config: TrainingConfig,
    model_version: str
) -> dict:
    """Train Next-Run Probability Model.
    
    Args:
        db: Database connection
        train_config: Training configuration
        model_version: Version string
        
    Returns:
        Training results dictionary
    """
    logger.info('=' * 60)
    logger.info('Training Next-Run Probability Model')
    logger.info(f'Version: {model_version}')
    logger.info(f'Train seasons: {train_config.train_seasons}')
    logger.info(f'Test seasons: {train_config.test_seasons}')
    
    # Create model
    config = ModelConfig(
        model_type='next_run_probability',
        model_name='Next-Run Probability Model',
        version=model_version,
        random_seed=42,
        hyperparameters={
            'model_type': 'xgboost',
            'max_depth': 6,
            'n_estimators': 100,
            'learning_rate': 0.1,
        }
    )
    
    model = NextRunProbabilityModel(db_connection=db, config=config)
    
    # Train
    result = model.train(train_config)
    
    if not result.success:
        logger.error(f'Training failed: {result.error_message}')
        return {'success': False, 'error': result.error_message}
    
    # Log metrics
    logger.info('Training complete!')
    logger.info(f'Training time: {result.training_time_seconds:.1f}s')
    logger.info(f'Rows processed: {result.rows_processed}')
    logger.info('Metrics:')
    for metric, value in result.metrics.items():
        logger.info(f'  {metric}: {value:.4f}')
    
    # Save model
    model_path = f'models/next_run_{model_version}.joblib'
    Path('models').mkdir(exist_ok=True)
    model.save(model_path)
    logger.info(f'Model saved to {model_path}')
    
    # Register version
    version = model.register_version(result.metrics)
    logger.info(f'Model registered as version {version.version_id}')
    
    return {
        'success': True,
        'model_version': model_version,
        'metrics': result.metrics,
        'model_path': model_path,
    }


def train_pa_outcome_model(
    db: connection,
    train_config: TrainingConfig,
    model_version: str
) -> dict:
    """Train PA Outcome Model.
    
    Args:
        db: Database connection
        train_config: Training configuration
        model_version: Version string
        
    Returns:
        Training results dictionary
    """
    logger.info('=' * 60)
    logger.info('Training PA Outcome Model')
    logger.info(f'Version: {model_version}')
    logger.info(f'Train seasons: {train_config.train_seasons}')
    logger.info(f'Test seasons: {train_config.test_seasons}')
    
    # Create model
    config = ModelConfig(
        model_type='pa_outcome',
        model_name='PA Outcome Model',
        version=model_version,
        random_seed=42,
        hyperparameters={
            'model_type': 'xgboost',
            'max_depth': 8,
            'n_estimators': 150,
            'learning_rate': 0.1,
        }
    )
    
    model = PAOutcomeModel(db_connection=db, config=config)
    
    # Train
    result = model.train(train_config)
    
    if not result.success:
        logger.error(f'Training failed: {result.error_message}')
        return {'success': False, 'error': result.error_message}
    
    # Log metrics
    logger.info('Training complete!')
    logger.info(f'Training time: {result.training_time_seconds:.1f}s')
    logger.info(f'Rows processed: {result.rows_processed}')
    logger.info('Metrics:')
    for metric, value in result.metrics.items():
        logger.info(f'  {metric}: {value:.4f}')
    
    # Save model
    model_path = f'models/pa_outcome_{model_version}.joblib'
    Path('models').mkdir(exist_ok=True)
    model.save(model_path)
    logger.info(f'Model saved to {model_path}')
    
    # Register version
    version = model.register_version(result.metrics)
    logger.info(f'Model registered as version {version.version_id}')
    
    return {
        'success': True,
        'model_version': model_version,
        'metrics': result.metrics,
        'model_path': model_path,
    }


def generate_test_predictions(
    db: connection,
    model_type: str,
    model_version: str,
    test_seasons: List[int]
) -> int:
    """Generate predictions on test data.
    
    Args:
        db: Database connection
        model_type: 'next_run' or 'pa_outcome'
        model_version: Model version string
        test_seasons: Seasons to predict
        
    Returns:
        Number of predictions generated
    """
    logger.info(f'Generating {model_type} predictions for test seasons: {test_seasons}')
    
    # Load model
    model_path = f'models/{model_type}_{model_version}.joblib'
    
    if model_type == 'next_run':
        model = NextRunProbabilityModel(db_connection=db)
    else:
        model = PAOutcomeModel(db_connection=db)
    
    if not model.load(model_path):
        logger.error(f'Failed to load model from {model_path}')
        return 0
    
    # Generate predictions for each game in test season
    total_predictions = 0
    
    with db.cursor() as cur:
        for season in test_seasons:
            # Get sample of games
            cur.execute('''
                SELECT DISTINCT game_pk 
                FROM models.next_run_training_data
                WHERE season = %s
                LIMIT 10
            ''', (season,))
            
            games = [row[0] for row in cur.fetchall()]
            
            for game_pk in games:
                if model_type == 'next_run':
                    predictions = model.predict_for_game(game_pk, season)
                    if predictions:
                        model.save_predictions(predictions, model_version)
                        total_predictions += len(predictions)
                else:
                    predictions = model.predict_for_game(game_pk, season)
                    if predictions:
                        model.save_predictions(predictions, model_version, season)
                        total_predictions += len(predictions)
    
    logger.info(f'Generated {total_predictions} predictions')
    return total_predictions


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Train baseball prediction models'
    )
    parser.add_argument(
        '--train-seasons',
        nargs='+',
        type=int,
        required=True,
        help='Seasons to use for training (e.g., 2023 2024 2025)'
    )
    parser.add_argument(
        '--test-seasons',
        nargs='+',
        type=int,
        required=True,
        help='Seasons to use for testing (e.g., 2026)'
    )
    parser.add_argument(
        '--models',
        nargs='+',
        choices=['next_run', 'pa_outcome', 'all'],
        default=['all'],
        help='Which models to train'
    )
    parser.add_argument(
        '--sample-rate',
        type=float,
        default=1.0,
        help='Fraction of data to sample (1.0 = all, 0.1 = 10%%)'
    )
    parser.add_argument(
        '--skip-data-prep',
        action='store_true',
        help='Skip data preparation (use existing training data)'
    )
    parser.add_argument(
        '--skip-predictions',
        action='store_true',
        help='Skip generating test predictions'
    )
    parser.add_argument(
        '--version',
        type=str,
        default=None,
        help='Model version override (default: timestamp-based)'
    )
    
    args = parser.parse_args()
    
    # Generate version if not provided
    if args.version:
        model_version = args.version
    else:
        model_version = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    logger.info('=' * 60)
    logger.info('Model Training Pipeline')
    logger.info('=' * 60)
    logger.info(f'Train seasons: {args.train_seasons}')
    logger.info(f'Test seasons: {args.test_seasons}')
    logger.info(f'Models: {args.models}')
    logger.info(f'Sample rate: {args.sample_rate}')
    logger.info(f'Version: {model_version}')
    
    # Connect to database
    try:
        db = get_db_connection()
        logger.info('Database connected')
    except Exception as e:
        logger.error(f'Failed to connect to database: {e}')
        sys.exit(1)
    
    results = {}
    
    try:
        # Determine which models to train
        train_next_run = 'all' in args.models or 'next_run' in args.models
        train_pa = 'all' in args.models or 'pa_outcome' in args.models
        
        # Data preparation
        if not args.skip_data_prep:
            if train_next_run:
                populate_next_run_training(db, args.train_seasons, args.sample_rate)
                populate_next_run_training(db, args.test_seasons, args.sample_rate)
                compute_next_run_features(db, args.train_seasons + args.test_seasons)
            
            if train_pa:
                populate_pa_outcome_training(db, args.train_seasons, args.sample_rate)
                populate_pa_outcome_training(db, args.test_seasons, args.sample_rate)
                compute_pa_outcome_features(db, args.train_seasons + args.test_seasons)
        
        # Training configuration
        train_config = TrainingConfig(
            train_seasons=args.train_seasons,
            test_seasons=args.test_seasons,
            validation_split=0.2,
            batch_size=1024,
            max_epochs=100,
        )
        
        # Train models
        if train_next_run:
            results['next_run'] = train_next_run_model(
                db, train_config, f'next_run_{model_version}'
            )
        
        if train_pa:
            results['pa_outcome'] = train_pa_outcome_model(
                db, train_config, f'pa_outcome_{model_version}'
            )
        
        # Generate predictions
        if not args.skip_predictions:
            if train_next_run and results.get('next_run', {}).get('success'):
                generate_test_predictions(
                    db, 'next_run', f'next_run_{model_version}', args.test_seasons
                )
            
            if train_pa and results.get('pa_outcome', {}).get('success'):
                generate_test_predictions(
                    db, 'pa_outcome', f'pa_outcome_{model_version}', args.test_seasons
                )
        
        # Save results
        results_file = f'models/training_results_{model_version}.json'
        Path('models').mkdir(exist_ok=True)
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        logger.info(f'Results saved to {results_file}')
        
        # Summary
        logger.info('=' * 60)
        logger.info('Training Complete!')
        logger.info('=' * 60)
        
        for model_name, result in results.items():
            if result.get('success'):
                logger.info(f'{model_name}: SUCCESS')
                for metric, value in result.get('metrics', {}).items():
                    if isinstance(value, float):
                        logger.info(f'  {metric}: {value:.4f}')
            else:
                logger.error(f'{model_name}: FAILED - {result.get("error")}')
        
    except Exception as e:
        logger.exception('Training pipeline failed')
        sys.exit(1)
    finally:
        db.close()
        logger.info('Database connection closed')


if __name__ == '__main__':
    main()
