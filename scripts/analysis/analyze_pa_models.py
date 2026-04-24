#!/usr/bin/env python3
"""
Plate Appearance Model Evaluation and Comparison Script

Analyzes trained models, compares performance, and provides insights.
"""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
from sqlalchemy import URL, create_engine, text


ROOT = Path(__file__).resolve().parents[1]


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


def get_model_performance() -> pd.DataFrame:
    """Get performance metrics for all plate appearance models."""
    engine = create_engine(database_url())
    try:
        sql = """
            SELECT
                target_id,
                model_name,
                model_family,
                (metrics->'validation'->>'roc_auc')::numeric as roc_auc,
                (metrics->'validation'->>'accuracy')::numeric as accuracy,
                (metrics->'validation'->>'log_loss')::numeric as log_loss,
                (metrics->'validation'->>'brier_score')::numeric as brier_score,
                (metrics->'validation'->'rows')::integer as validation_rows
            FROM models.model_registry
            WHERE target_id LIKE 'pa_%'
              AND is_active = true
            ORDER BY target_id, roc_auc DESC
        """
        return pd.read_sql_query(text(sql), engine)
    finally:
        engine.dispose()


def get_target_prevalence() -> pd.DataFrame:
    """Get the actual prevalence of each target in the training data."""
    engine = create_engine(database_url())
    try:
        sql = """
            SELECT
                'pa_batter_hit' as target_id,
                AVG(is_hit::int)::numeric as prevalence,
                COUNT(*) as total_samples
            FROM features.plate_appearance_examples

            UNION ALL

            SELECT
                'pa_batter_walk',
                AVG(is_walk::int)::numeric,
                COUNT(*)
            FROM features.plate_appearance_examples

            UNION ALL

            SELECT
                'pa_batter_strikeout',
                AVG(is_strikeout::int)::numeric,
                COUNT(*)
            FROM features.plate_appearance_examples

            UNION ALL

            SELECT
                'pa_batter_home_run',
                AVG(is_home_run::int)::numeric,
                COUNT(*)
            FROM features.plate_appearance_examples

            UNION ALL

            SELECT
                'pa_batter_reach_base',
                AVG(is_reach_base::int)::numeric,
                COUNT(*)
            FROM features.plate_appearance_examples

            UNION ALL

            SELECT
                'pa_batter_extra_base_hit',
                AVG(is_extra_base_hit::int)::numeric,
                COUNT(*)
            FROM features.plate_appearance_examples
        """
        return pd.read_sql_query(text(sql), engine)
    finally:
        engine.dispose()


def analyze_models():
    """Analyze and print model performance insights."""
    print('=== Plate Appearance Model Performance Analysis ===\n')

    # Get performance data
    perf = get_model_performance()
    prev = get_target_prevalence()

    analysis = perf.merge(prev, on='target_id', how='left')
    for column in [
        'roc_auc',
        'accuracy',
        'log_loss',
        'brier_score',
        'prevalence',
    ]:
        analysis[column] = pd.to_numeric(analysis[column], errors='coerce')

    # Calculate baseline (predicting majority class)
    analysis['baseline_accuracy'] = analysis.apply(
        lambda row: max(row['prevalence'], 1 - row['prevalence']),
        axis=1,
    )

    # Calculate improvement over baseline
    analysis['accuracy_improvement'] = analysis['accuracy'] - analysis['baseline_accuracy']

    print('Performance Summary:')
    print('=' * 50)
    summary = (
        analysis.groupby('target_id')
        .agg(
            {
                'roc_auc': 'max',
                'accuracy': 'max',
                'prevalence': 'first',
                'baseline_accuracy': 'first',
                'accuracy_improvement': 'max',
            },
        )
        .round(4)
    )

    for target in summary.index:
        row = summary.loc[target]
        print(f'\n{target}:')
        print(f'  Prevalence: {row["prevalence"]:.1%}')
        print(f'  Best ROC AUC: {row["roc_auc"]:.3f}')
        print(f'  Best Accuracy: {row["accuracy"]:.3f}')
        print(f'  Baseline Accuracy: {row["baseline_accuracy"]:.3f}')
        print(f'  Improvement: {row["accuracy_improvement"]:.3f}')

    print('\n\nTop Models by ROC AUC:')
    print('=' * 30)
    top_models = analysis.nlargest(10, 'roc_auc')[
        ['target_id', 'model_name', 'roc_auc', 'accuracy']
    ]
    print(top_models.to_string(index=False))

    print('\n\nModel Family Comparison:')
    print('=' * 25)
    family_comp = (
        analysis.groupby('model_family').agg({'roc_auc': 'mean', 'accuracy': 'mean'}).round(4)
    )
    print(family_comp)

    print('\n\nRecommendations:')
    print('=' * 15)

    # Identify best performing targets
    best_targets = summary.nlargest(3, 'roc_auc')
    print(f'Most predictable outcomes: {", ".join(best_targets.index.tolist())}')

    # Identify targets needing improvement
    worst_targets = summary.nsmallest(3, 'roc_auc')
    print(f'Areas for improvement: {", ".join(worst_targets.index.tolist())}')

    # Check if gradient boosting consistently outperforms
    gb_better = (
        analysis[analysis['model_family'] == 'hist_gradient_boosting']['roc_auc'].mean()
        > analysis[analysis['model_family'] == 'logistic_regression']['roc_auc'].mean()
    )
    if gb_better:
        print('Gradient boosting models consistently outperform logistic regression')
    else:
        print('Logistic regression models are competitive with gradient boosting')


if __name__ == '__main__':
    analyze_models()
