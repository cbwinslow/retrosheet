"""
Feature Ablation Study for Pitch-Level Models (Option A)

Validates which feature groups actually improve predictions.
Trains multiple models with progressively larger feature sets:
1. Baseline: Raw Statcast only (118 features)
2. + Velocity/Movement: Original engineered features (46+)
3. + Additional engineered (25)
4. + More from KB research (40)
5. + Context features (60)
6. + Final Markov/Matchup (50)

Measures: accuracy, log_loss, AUC, training time per feature group

Usage:
    uv run python scripts/pitch_models/feature_ablation_study.py --quick
    uv run python scripts/pitch_models/feature_ablation_study.py --full
"""

import os
import sys
import time
import json
import pickle
import argparse
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split, StratifiedKFold
from sklearn.metrics import accuracy_score, log_loss, roc_auc_score
import xgboost as xgb
import psycopg2

# Configuration
DB_URL = os.getenv('DATABASE_URL', 'postgresql://localhost:5432/retrosheet')
RESULTS_DIR = 'models/ablation_study'
os.makedirs(RESULTS_DIR, exist_ok=True)


@dataclass
class FeatureGroup:
    """Defines a feature group for ablation testing."""
    name: str
    description: str
    columns: List[str]
    source_tables: List[str]


# Define feature groups in order of addition
FEATURE_GROUPS = [
    FeatureGroup(
        name="baseline",
        description="Raw Statcast fields (118 columns)",
        columns=[
            'game_year', 'game_pk', 'game_date', 'sv_id',
            'batter_id', 'pitcher_id',
            'pitch_type', 'pitch_name', 'pitch_number',
            'balls', 'strikes', 'outs_when_up', 'inning', 'inning_topbot',
            'on_1b', 'on_2b', 'on_3b',
            'stand', 'p_throws', 'home_team', 'away_team', 'type',
            'start_speed', 'effective_speed', 'release_spin_rate',
            'release_pos_x', 'release_pos_y', 'release_pos_z', 'release_extension',
            'pfx_x', 'pfx_z', 'spin_axis',
            'plate_x', 'plate_z', 'zone', 'sz_top', 'sz_bot',
            'vx0', 'vy0', 'vz0', 'ax', 'ay', 'az',
            'launch_speed', 'launch_angle', 'hit_distance',
            'home_score', 'away_score', 'bat_score', 'fld_score',
            'delta_home_win_exp', 'delta_run_exp',
        ],
        source_tables=['features_pitch.base_features']
    ),

    FeatureGroup(
        name="velocity_movement",
        description="Engineered: velocity %iles, strike zone regions, movement (46+)",
        columns=[
            'velocity_percentile', 'velocity_diff_from_avg',
            'is_fastball', 'is_breaking', 'is_offspeed',
            'zone_region', 'is_in_zone', 'is_shadow_zone', 'is_chase_zone',
            'distance_from_center', 'horizontal_break', 'vertical_break',
            'approach_angle', 'spin_efficiency', 'induced_vertical_break',
            'plate_x_normalized', 'plate_z_normalized', 'height_above_center',
            'perceived_velocity', 'velocity_diff', 'release_approach_angle',
            'extension_effectiveness', 'release_height', 'release_side',
            'total_movement', 'movement_angle', 'spin_axis_quadrant',
        ],
        source_tables=['features_pitch.engineered_features']
    ),

    FeatureGroup(
        name="additional",
        description="Additional engineered: tunneling, spin, platoon, fatigue (25+)",
        columns=[
            'pitcher_fatigue_score', 'velocity_change_from_prev',
            'spin_rate_percentile', 'spin_efficiency_score',
            'is_same_handed_matchup', 'platoon_advantage',
            'pitch_tunneling_metric', 'release_distance_delta',
            'pa_pressure_index', 'is_high_pressure_pa',
            'is_walk_off_situation', 'is_ace_pitcher', 'is_closer_situation',
            'time_since_prev_pitch', 'prev_was_strike', 'prev_was_ball',
            'consecutive_same_type', 'pitcher_repertoire_depth',
            'batter_performance_vs_type', 'batter_swing_rate_vs_type',
        ],
        source_tables=['features_pitch.engineered_features']
    ),

    FeatureGroup(
        name="kb_research",
        description="KB research features: quality, count leverage, TTOP, RE24 (40+)",
        columns=[
            'pitch_quality_score', 'pitch_quality_percentile',
            'count_leverage_index', 'is_payoff_pitch', 'is_3_0_count',
            'times_through_order_detailed', 'ttop_penalty_applies',
            'run_expectancy_24', 'win_probability_added',
            'is_runner_on_base', 'base_state_code',
            'game_month', 'is_opening_series', 'is_day_game',
            'pitch_type_family', 'is_primary_pitch_type',
            'is_batter_hot_zone', 'is_batter_cold_zone',
            'score_diff_bucket', 'times_faced_this_game',
        ],
        source_tables=['features_pitch.engineered_features']
    ),

    FeatureGroup(
        name="context",
        description="Context: weather, momentum, umpire, park, attendance (60+)",
        columns=[
            'temp_extreme_flag', 'wind_effect_score', 'altitude_factor',
            'is_shadow_game', 'batting_team_last_5_win_rate',
            'pitcher_last_3_era', 'pitcher_last_3_strikeout_rate',
            'umpire_strike_zone_size', 'umpire_k_friendly',
            'attendance_vs_capacity_pct', 'is_sellout',
            'park_elevation_feet', 'park_overall_hr_factor',
            'pitcher_days_rest', 'is_short_rest_start',
            'pitcher_season_workload', 'home_field_advantage_score',
        ],
        source_tables=['features_pitch.engineered_features']
    ),

    FeatureGroup(
        name="final",
        description="Final: Markov chains, matchup history, sequence (50+)",
        columns=[
            'strike_accumulation_rate', 'ball_accumulation_rate',
            'expected_pitches_remaining', 'is_absorbing_state',
            'count_pressure_index', 'is_favorable_hitter_count',
            'matchup_prior_pa_count', 'matchup_prior_ba',
            'matchup_first_time_facing', 'matchup_success_trend',
            'is_postseason', 'month_of_season', 'is_season_opener',
            'prev_2_pitch_types', 'is_repeated_pitch', 'is_alternating_pattern',
            'pitch_sequence_category', 'is_platoon_advantage_batter',
            'is_rookie_batter', 'batter_experience_level',
        ],
        source_tables=['features_pitch.engineered_features']
    ),
]


def build_cumulative_groups() -> List[Tuple[str, List[str]]]:
    """
    Build cumulative feature groups for ablation testing.
    Returns: [(group_name, all_features_up_to_this_point), ...]
    """
    cumulative = []
    all_features = []

    for group in FEATURE_GROUPS:
        all_features.extend(group.columns)
        cumulative.append((
            f"baseline+{group.name}",
            all_features.copy(),
            group.description
        ))

    return cumulative


def load_data_for_features(conn, features: List[str], sample_size: Optional[int] = None) -> pd.DataFrame:
    """Load data with specified features."""

    # Build feature list (check which exist in database)
    # For simplicity, we'll query from engineered_features which has everything
    feature_cols = ', '.join([f"ef.{f}" for f in features if f not in ['game_year', 'game_pk']])

    query = f"""
    SELECT
        ef.pitch_id,
        ef.outcome_tier1 as target,
        bf.game_year,
        {feature_cols}
    FROM features_pitch.engineered_features ef
    JOIN features_pitch.base_features bf ON ef.pitch_id = bf.pitch_id
    WHERE ef.outcome_tier1 IS NOT NULL
      AND ef.outcome_tier1 != 'U'
      AND ef.is_valid_for_training = TRUE
    """

    if sample_size:
        query += f" ORDER BY RANDOM() LIMIT {sample_size}"

    df = pd.read_sql(query, conn)
    return df


def prepare_features(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series]:
    """Prepare features for training."""
    y = df['target']
    X = df.drop(['target', 'pitch_id', 'game_year'], axis=1, errors='ignore')

    # Handle categoricals
    cat_cols = X.select_dtypes(include=['object']).columns
    for col in cat_cols:
        X[col] = X[col].fillna('UNKNOWN')
        dummies = pd.get_dummies(X[col], prefix=col, drop_first=True)
        X = pd.concat([X.drop(col, axis=1), dummies], axis=1)

    # Fill numeric NAs
    num_cols = X.select_dtypes(include=[np.number]).columns
    for col in num_cols:
        X[col] = X[col].fillna(X[col].median())

    # Encode target
    y_encoded = pd.Categorical(y).codes

    return X, pd.Series(y_encoded, index=y.index)


def train_and_evaluate(X: pd.DataFrame, y: pd.Series, group_name: str) -> Dict:
    """Train model and return metrics."""

    # Stratified split by year
    train_mask = X.index % 5 != 0  # 80% train
    X_train, X_test = X[train_mask], X[~train_mask]
    y_train, y_test = y[train_mask], y[~train_mask]

    if len(X_test) == 0:
        # Fallback to random split
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )

    # XGBoost params (consistent across all tests)
    model = xgb.XGBClassifier(
        objective='multi:softprob',
        num_class=len(np.unique(y)),
        eval_metric='mlogloss',
        max_depth=6,
        learning_rate=0.1,
        n_estimators=200,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        n_jobs=-1,
        tree_method='hist',
    )

    start_time = time.time()
    model.fit(X_train, y_train, verbose=False)
    train_time = time.time() - start_time

    # Predictions
    y_pred = model.predict(X_test)
    y_pred_proba = model.predict_proba(X_test)

    # Metrics
    results = {
        'group': group_name,
        'n_features': X.shape[1],
        'train_samples': len(X_train),
        'test_samples': len(X_test),
        'train_time_seconds': train_time,
        'accuracy': float(accuracy_score(y_test, y_pred)),
        'log_loss': float(log_loss(y_test, y_pred_proba)),
        'auc_macro': float(roc_auc_score(y_test, y_pred_proba, multi_class='ovo', average='macro')),
    }

    return results, model


def run_ablation_study(conn, sample_size: Optional[int] = None) -> List[Dict]:
    """Run full ablation study across all feature groups."""

    cumulative_groups = build_cumulative_groups()
    all_results = []

    print("="*70)
    print("FEATURE ABLATION STUDY")
    print("="*70)
    print(f"Sample size: {sample_size or 'FULL DATASET'}")
    print(f"Testing {len(cumulative_groups)} feature configurations")
    print("="*70)

    for group_name, features, description in cumulative_groups:
        print(f"\n{'='*70}")
        print(f"Testing: {group_name}")
        print(f"Description: {description}")
        print(f"Features: {len(features)}")
        print("="*70)

        try:
            # Load data
            print("Loading data...")
            df = load_data_for_features(conn, features, sample_size)
            print(f"Loaded {len(df):,} rows")

            if len(df) < 1000:
                print(f"WARNING: Insufficient data ({len(df)} rows), skipping...")
                continue

            # Prepare features
            X, y = prepare_features(df)
            print(f"Feature matrix: {X.shape}")

            # Train and evaluate
            results, model = train_and_evaluate(X, y, group_name)
            all_results.append(results)

            # Print results
            print(f"\nResults:")
            print(f"  Accuracy:  {results['accuracy']:.4f}")
            print(f"  Log Loss:  {results['log_loss']:.4f}")
            print(f"  AUC:       {results['auc_macro']:.4f}")
            print(f"  Train Time: {results['train_time_seconds']:.1f}s")

            # Save model
            model_file = f"{RESULTS_DIR}/{group_name}_model.pkl"
            with open(model_file, 'wb') as f:
                pickle.dump(model, f)

        except Exception as e:
            print(f"ERROR in {group_name}: {str(e)}")
            import traceback
            traceback.print_exc()
            continue

    return all_results


def analyze_results(results: List[Dict]):
    """Analyze and visualize ablation results."""

    print("\n" + "="*70)
    print("ABLATION STUDY SUMMARY")
    print("="*70)

    df = pd.DataFrame(results)

    # Calculate marginal improvements
    df['accuracy_gain'] = df['accuracy'].diff().fillna(0)
    df['log_loss_reduction'] = -df['log_loss'].diff().fillna(0)  # Negative = reduction
    df['auc_gain'] = df['auc_macro'].diff().fillna(0)
    df['time_per_feature'] = df['train_time_seconds'] / df['n_features']

    print("\nFeature Group Performance:")
    print(df[['group', 'n_features', 'accuracy', 'log_loss', 'auc_macro',
              'train_time_seconds']].to_string(index=False))

    print("\nMarginal Improvements (vs previous group):")
    print(df[['group', 'accuracy_gain', 'log_loss_reduction', 'auc_gain']].to_string(index=False))

    print("\nEfficiency (training time per feature):")
    print(df[['group', 'n_features', 'train_time_seconds', 'time_per_feature']].to_string(index=False))

    # Recommendations
    print("\n" + "="*70)
    print("RECOMMENDATIONS")
    print("="*70)

    # Find best ROI (accuracy gain / features added)
    df['roi'] = df['accuracy_gain'] / df['n_features']
    best_roi = df.loc[df['roi'].idxmax()]

    print(f"\nBest ROI: {best_roi['group']}")
    print(f"  Accuracy gain: +{best_roi['accuracy_gain']:.4f}")
    print(f"  Features added: {best_roi['n_features']}")
    print(f"  ROI: {best_roi['roi']:.6f} accuracy per feature")

    # Find diminishing returns point
    print(f"\nDiminishing Returns Analysis:")
    for i, row in df.iterrows():
        if i == 0:
            continue
        prev = df.iloc[i-1]
        gain = row['accuracy'] - prev['accuracy']
        if gain < 0.001:  # Less than 0.1% improvement
            print(f"  Diminishing returns start at: {row['group']}")
            print(f"    Gain from previous: +{gain:.4f} accuracy")
            break

    # Save results
    results_file = f"{RESULTS_DIR}/ablation_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to: {results_file}")


def main():
    parser = argparse.ArgumentParser(description='Feature Ablation Study')
    parser.add_argument('--quick', action='store_true',
                       help='Use 50k sample for quick test')
    parser.add_argument('--full', action='store_true',
                       help='Use full dataset (slow)')
    args = parser.parse_args()

    sample_size = 50000 if args.quick else None
    if not args.quick and not args.full:
        print("Use --quick for 50k sample or --full for complete dataset")
        print("Defaulting to quick mode...")
        sample_size = 50000

    print(f"Starting ablation study with sample_size={sample_size}")

    conn = psycopg2.connect(DB_URL)
    try:
        results = run_ablation_study(conn, sample_size)
        analyze_results(results)
    finally:
        conn.close()


if __name__ == '__main__':
    main()
