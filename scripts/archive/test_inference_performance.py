#!/usr/bin/env python3
"""
Test inference performance optimizations
"""

from __future__ import annotations

import time
import psycopg2
from scripts.fast_prediction_service import PredictionService


def test_database_query_performance():
    """Test raw database query performance vs optimized inference."""

    # Test parameters
    test_cases = [
        {
            'season': 2023,
            'inning': 1,
            'is_bottom_inning': False,
            'outs_before': 0,
            'start_bases': 0,
            'balls': 0,
            'strikes': 0,
            'home_score_diff': 0,
            'batter_hand': 'R',
            'pitcher_hand': 'R'
        }
        for _ in range(10)  # Test 10 different scenarios
    ]

    # Test database function performance
    conn = psycopg2.connect(
        host="localhost",
        port="5432",
        dbname="retrosheet",
        user="postgres",
        password=""
    )

    print("Testing database function performance...")

    start_time = time.time()
    for i, params in enumerate(test_cases):
        with conn.cursor() as cur:
            cur.execute("""
                SELECT * FROM inference.get_plate_appearance_features(
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NULL, NULL, NULL, NULL
                )
            """, (
                params['season'], params['inning'], params['is_bottom_inning'],
                params['outs_before'], params['start_bases'], params['balls'],
                params['strikes'], params['home_score_diff'],
                params['batter_hand'], params['pitcher_hand']
            ))
            result = cur.fetchone()
    db_time = time.time() - start_time

    print(".4f"
    # Test optimized materialized view performance
    print("\nTesting materialized view performance...")

    start_time = time.time()
    for i, params in enumerate(test_cases):
        with conn.cursor() as cur:
            # Use a representative query that would hit the optimized view
            cur.execute("""
                SELECT COUNT(*) FROM inference.plate_appearance_features
                WHERE season = %s AND inning = %s AND is_bottom_inning = %s
                AND outs_before = %s AND start_bases = %s
            """, (
                params['season'], params['inning'], params['is_bottom_inning'],
                params['outs_before'], params['start_bases']
            ))
            result = cur.fetchone()
    mv_time = time.time() - start_time

    print(".4f"
    conn.close()

    print(".2f")


def test_prediction_service_performance():
    """Test the fast prediction service performance."""

    print("\nTesting prediction service performance...")

    # Initialize service (loads models into memory)
    start_time = time.time()
    service = PredictionService(max_connections=2)
    load_time = time.time() - start_time

    print(".2f"
    # Test batch predictions
    batch_requests = [
        {
            'target_id': 'pa_batter_hit',
            'game_state': {
                'season': 2023,
                'inning': 1,
                'is_bottom_inning': False,
                'outs_before': 0,
                'start_bases': 0,
                'balls': 0,
                'strikes': 0,
                'home_score_diff': 0,
                'batter_hand': 'R',
                'pitcher_hand': 'R'
            }
        }
        for _ in range(50)  # Test 50 predictions
    ]

    start_time = time.time()
    results = service.predict_batch(batch_requests)
    prediction_time = time.time() - start_time

    successful_predictions = sum(1 for r in results if 'error' not in r)
    total_predictions = len(results)

    print(f"Batch predictions: {successful_predictions}/{total_predictions} successful")
    print(".4f"
    print(".1f")


if __name__ == "__main__":
    test_database_query_performance()
    test_prediction_service_performance()