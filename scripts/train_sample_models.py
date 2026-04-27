"""Sample model training script for quick testing.

Trains Next-Run and PA Outcome models on a small sample
of historical data for demonstration purposes.

Author: Agent cbwinslow/retrosheet
Date: 2026-04-26
"""

import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent.parent))

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier


def train_sample_next_run_model():
    """Train a sample Next-Run Probability Model."""
    print('Training sample Next-Run Probability Model...')

    # Generate synthetic training data
    np.random.seed(42)
    n_samples = 1000

    # Features: inning, outs, base_state, run_diff, we, li, matchup_score
    X = np.random.rand(n_samples, 7)

    # Target: 1 if run scored, 0 otherwise
    # Higher probability with runners on base (base_state > 0)
    # Higher probability with lower outs
    y = (X[:, 2] * 0.3 + (1 - X[:, 1] / 3) * 0.3 + X[:, 4] * 0.2 > 0.5).astype(int)

    # Train simple model
    model = RandomForestClassifier(n_estimators=50, max_depth=5, random_state=42)
    model.fit(X, y)

    # Save model
    output_path = Path('models/next_run_sample.joblib')
    output_path.parent.mkdir(exist_ok=True)

    joblib.dump(
        {
            'model': model,
            'config': {
                'model_type': 'random_forest',
                'n_estimators': 50,
                'max_depth': 5,
            },
            'feature_names': [
                'inning',
                'outs',
                'base_state',
                'run_diff',
                'we',
                'li',
                'matchup_score',
            ],
        },
        output_path,
    )

    print(f'  Model saved to: {output_path}')
    print(f'  Training accuracy: {model.score(X, y):.3f}')
    print()

    return model


def train_sample_pa_outcome_model():
    """Train a sample PA Outcome Model."""
    print('Training sample PA Outcome Model...')

    # Generate synthetic training data
    np.random.seed(43)
    n_samples = 1000

    # Features: inning, outs, base_state, batter_matchup, pitcher_matchup
    X = np.random.rand(n_samples, 5)

    # Target: 0=out, 1=walk, 2=single, 3=double, 4=triple, 5=HR
    # Simplified: better matchup = better outcomes
    probs = np.random.rand(n_samples, 6)
    probs[:, 0] *= 0.7  # Out most likely
    probs[:, 1] *= 0.3  # Walk
    probs[:, 2] *= 0.4  # Single
    probs[:, 3] *= 0.2  # Double
    probs[:, 4] *= 0.05  # Triple
    probs[:, 5] *= 0.15  # HR

    # Adjust based on matchup score
    for i in range(n_samples):
        matchup_bonus = X[i, 3] * X[i, 4]
        probs[i, 5] += matchup_bonus * 0.2  # HR more likely with good matchup
        probs[i, 2] += matchup_bonus * 0.1  # Single more likely

    y = probs.argmax(axis=1)

    # Train simple model
    model = RandomForestClassifier(n_estimators=50, max_depth=5, random_state=43)
    model.fit(X, y)

    # Save model
    output_path = Path('models/pa_outcome_sample.joblib')
    output_path.parent.mkdir(exist_ok=True)

    joblib.dump(
        {
            'model': model,
            'config': {
                'model_type': 'random_forest',
                'n_estimators': 50,
                'max_depth': 5,
                'classes': ['out', 'walk', 'single', 'double', 'triple', 'home_run'],
            },
            'feature_names': [
                'inning',
                'outs',
                'base_state',
                'batter_matchup',
                'pitcher_matchup',
            ],
        },
        output_path,
    )

    print(f'  Model saved to: {output_path}')
    print(f'  Training accuracy: {model.score(X, y):.3f}')
    print()

    return model


def test_predictions():
    """Test models with sample predictions."""
    print('Testing sample predictions...')
    print()

    from baseball.serving import ModelServer

    server = ModelServer(model_dir='models')

    # Load sample models
    server.load_model('next_run', 'sample')
    server.load_model('pa_outcome', 'sample')

    # Test Next-Run prediction
    print('Next-Run Prediction Test:')
    features = {
        'inning': 7,
        'outs': 1,
        'base_state': 5,  # Runners on 1st & 3rd
        'run_diff': 2,
        'we': 0.65,
        'li': 1.8,
        'matchup_score': 0.6,
    }
    result = server.predict('next_run', features)
    print(f'  Input: {features}')
    print(f'  Prediction: {result}')
    print()

    # Test PA Outcome prediction
    print('PA Outcome Prediction Test:')
    features = {
        'inning': 3,
        'outs': 2,
        'base_state': 1,  # Runner on 1st
        'batter_matchup': 0.7,
        'pitcher_matchup': 0.4,
    }
    result = server.predict('pa_outcome', features)
    print(f'  Input: {features}')
    print(f'  Prediction: {result}')
    print()

    # Show server stats
    print('Server Stats:')
    stats = server.get_stats()
    print(f'  Models loaded: {stats["models_loaded"]}')
    print(f'  Predictions served: {stats["predictions_served"]}')
    print()


def main():
    """Main entry point."""
    print('=' * 60)
    print('Sample Model Training')
    print('=' * 60)
    print()

    # Train sample models
    train_sample_next_run_model()
    train_sample_pa_outcome_model()

    print('=' * 60)
    print()

    # Test predictions
    test_predictions()

    print('=' * 60)
    print('Sample models trained and tested successfully!')
    print('=' * 60)


if __name__ == '__main__':
    main()
