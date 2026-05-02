#!/usr/bin/env python3
"""
Train Markov Pitch Prediction Model

Trains a Markov chain model on historical pitch sequence data
for use in real-time next-pitch prediction during live games.

Usage:
    python scripts/train_markov_model.py
    python scripts/train_markov_model.py --seasons 2020 2021 2022 2023 2024
    python scripts/train_markov_model.py --persist  # Save model to disk
"""

import argparse
import json
import logging
import pickle
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from baseball.predictions import MarkovPitchPredictor
from baseball.utils.logging_config import get_logger

logger = get_logger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description='Train Markov pitch prediction model'
    )
    parser.add_argument(
        '--seasons', '-s',
        nargs='+',
        type=int,
        help='Seasons to train on (default: all available)'
    )
    parser.add_argument(
        '--persist', '-p',
        action='store_true',
        help='Save trained model to disk'
    )
    parser.add_argument(
        '--output', '-o',
        type=str,
        default='models/markov_pitch_model.pkl',
        help='Output path for model file'
    )
    parser.add_argument(
        '--stats-only', '-t',
        action='store_true',
        help='Print transition statistics only, no training'
    )
    
    args = parser.parse_args()
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    if args.stats_only:
        # Query and display statistics
        from baseball.core.db import get_db_connection
        
        logger.info("Querying pitch transition statistics...")
        
        query = """
        SELECT 
            count_label,
            raw_symbol as prev_pitch,
            next_pitch_symbol,
            COUNT(*) as freq
        FROM pitch_sequence.training_rows
        WHERE next_pitch_symbol IS NOT NULL
        GROUP BY count_label, raw_symbol, next_pitch_symbol
        ORDER BY freq DESC
        LIMIT 50
        """
        
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(query)
        
        print("\nTop 50 Pitch Transitions:")
        print("-" * 80)
        print(f"{'Count':>8} {'Prev':>6} {'Next':>6} {'Freq':>10}")
        print("-" * 80)
        
        total = 0
        for row in cur.fetchall():
            count_label, prev_pitch, next_pitch, freq = row
            print(f"{count_label:>8} {prev_pitch:>6} {next_pitch:>6} {freq:>10}")
            total += freq
        
        print("-" * 80)
        print(f"Total transitions: {total}")
        
        return
    
    # Train the model
    logger.info("Initializing Markov pitch predictor...")
    predictor = MarkovPitchPredictor()
    
    logger.info(f"Training on seasons: {args.seasons or 'all available'}")
    predictor.train(seasons=args.seasons)
    
    if args.persist:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'wb') as f:
            pickle.dump(predictor._transition_matrix, f)
        
        logger.info(f"Model saved to {output_path}")
    
    logger.info("Training complete!")
    
    # Test prediction
    from baseball.predictions import LiveGameContext
    
    test_context = LiveGameContext(
        game_pk=717341,
        inning=3,
        is_top_inning=True,
        outs=1,
        balls=1,
        strikes=1,
        batter_id=12345,
        pitcher_id=67890,
        on_first=True,
        on_second=False,
        on_third=False,
        score_diff=0,
        pitch_count_pa=3,
        last_pitch_type='C',
        last_pitch_result='called_strike'
    )
    
    test_prediction = predictor.predict(test_context)
    if test_prediction:
        print("\nTest Prediction (1-1 count, previous pitch = C):")
        print(f"  Most likely next pitch: {test_prediction.prediction}")
        print(f"  Confidence: {test_prediction.confidence:.1%}")
        print("\n  Top 5 possibilities:")
        for pitch, prob in sorted(
            test_prediction.probabilities.items(),
            key=lambda x: -x[1]
        )[:5]:
            print(f"    {pitch}: {prob:.1%}")


if __name__ == '__main__':
    main()
