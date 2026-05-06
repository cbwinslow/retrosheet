#!/usr/bin/env python3
"""
Train Two-Tier XGBoost Pitch-Level Model

Implements a hierarchical classification approach:
- Tier 1: {Ball, Strike, Ball-in-Play} (coarse outcome)
- Tier 2: {Single, Double, Triple, HR, Out} (fine-grained ball-in-play outcomes)

This model serves as the baseline for pitch-level prediction accuracy
targeting >80% coarse outcome accuracy (vs SMU benchmark of 58%).

Usage:
    python train_tier1_xgboost.py --target tier1 --seasons 2015-2023
    python train_tier1_xgboost.py --target tier2 --seasons 2015-2023
    python train_tier1_xgboost.py --ensemble --save-model
"""

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import joblib
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import accuracy_score, classification_report, log_loss
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import psycopg2
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PitchTier1XGBoostModel:
    """Two-Tier XGBoost model for pitch-level outcome prediction."""
    
    def __init__(self, target_tier: str = 'tier1'):
        """
        Initialize the model.
        
        Args:
            target_tier: 'tier1' for {ball, strike, ball_in_play}
                        'tier2' for {single, double, triple, hr, out}
        """
        self.target_tier = target_tier
        self.model = None
        self.label_encoder = LabelEncoder()
        self.feature_names = []
        self.target_column = f'outcome_{target_tier}'
        self.model_version = f"v1.0_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # XGBoost parameters optimized for pitch classification
        self.xgb_params = {
            'objective': 'multi:softprob',
            'eval_metric': 'mlogloss',
            'max_depth': 6,
            'learning_rate': 0.1,
            'n_estimators': 200,
            'subsample': 0.8,
            'colsample_bytree': 0.8,
            'random_state': 42,
            'n_jobs': -1,
            'tree_method': 'hist'  # Faster training on large datasets
        }
        
        # Feature columns for training
        self.core_features = [
            # Physics features
            'release_speed', 'release_spin_rate', 'effective_speed',
            'release_pos_x', 'release_pos_y', 'release_pos_z',
            'pfx_x', 'pfx_z', 'spin_axis',
            'plate_x', 'plate_z', 'zone',
            
            # Game state
            'balls', 'strikes', 'outs_when_up', 'inning',
            'on_1b', 'on_2b', 'on_3b',
            'home_score', 'away_score', 'bat_score', 'fld_score',
            
            # Batter-pitcher matchup
            'stand', 'p_throws',
            
            # Velocity components
            'vx0', 'vy0', 'vz0',
            'ax', 'ay', 'az',
            
            # Batted ball data (when available)
            'launch_speed', 'launch_angle', 'bb_type',
            
            # Win probability
            'delta_home_win_exp', 'delta_run_exp', 'home_win_exp'
        ]
        
        # Engineered features for tier2 (more context)
        self.engineered_features = [
            'velocity_category', 'zone_region', 'is_in_zone',
            'is_swing', 'is_whiff', 'is_hard_hit',
            'distance_from_zone_center', 'horizontal_break', 'vertical_break',
            'score_diff', 'is_late_game', 'is_high_leverage',
            'base_state_code', 'count_code'
        ]
    
    def load_training_data(
        self, 
        seasons: Optional[List[int]] = None,
        sample_rate: float = 1.0
    ) -> Tuple[pd.DataFrame, pd.Series]:
        """
        Load training data from the feature mart.
        
        Args:
            seasons: List of seasons to include (None = all)
            sample_rate: Fraction of data to sample (for faster testing)
            
        Returns:
            Tuple of (features_df, target_series)
        """
        conn = psycopg2.connect(
            host='localhost',
            port='5432',
            database='retrosheet',
            user='cbwinslow',
            password='123qweasd'
        )
        
        # Build season filter
        season_filter = ""
        params = []
        
        if seasons:
            season_filter = "WHERE bf.game_year = ANY(%s)"
            params.append(seasons)
        
        # Sample additional filter
        if sample_rate < 1.0:
            if season_filter:
                season_filter += " AND random() < %s"
            else:
                season_filter = "WHERE random() < %s"
            params.append(sample_rate)
        
        # Load base features + engineered features
        query = f"""
            SELECT 
                -- Base features
                bf.release_speed, bf.release_spin_rate, bf.effective_speed,
                bf.release_pos_x, bf.release_pos_y, bf.release_pos_z,
                bf.pfx_x, bf.pfx_z, bf.spin_axis,
                bf.plate_x, bf.plate_z, bf.zone,
                bf.balls, bf.strikes, bf.outs_when_up, bf.inning,
                bf.on_1b, bf.on_2b, bf.on_3b,
                bf.home_score, bf.away_score, bf.bat_score, bf.fld_score,
                bf.stand, bf.p_throws,
                bf.vx0, bf.vy0, bf.vz0,
                bf.ax, bf.ay, bf.az,
                bf.launch_speed, bf.launch_angle, bf.bb_type,
                bf.delta_home_win_exp, bf.delta_run_exp, bf.home_win_exp,
                
                -- Engineered features
                ef.velocity_category, ef.zone_region, ef.is_in_zone,
                ef.is_swing, ef.is_whiff, ef.is_hard_hit,
                ef.distance_from_zone_center, ef.horizontal_break, ef.vertical_break,
                ef.score_diff, ef.is_late_game, ef.is_high_leverage,
                ef.base_state_code, ef.count_code,
                
                -- Target variable
                ef.{self.target_column}
                
            FROM features_pitch.base_features bf
            LEFT JOIN features_pitch.engineered_features ef 
                ON bf.pitch_id = ef.pitch_id
            {season_filter}
        """
        
        logger.info(f"Loading training data with query: {query[:100]}...")
        
        df = pd.read_sql(query, conn, params=params)
        conn.close()
        
        # Remove rows with null targets
        df = df.dropna(subset=[self.target_column])
        
        # Separate features and target
        target = df[self.target_column].copy()
        features = df.drop(columns=[self.target_column])
        
        # Convert categorical columns
        categorical_cols = ['stand', 'p_throws', 'bb_type', 'velocity_category', 'zone_region', 'count_code']
        for col in categorical_cols:
            if col in features.columns:
                features[col] = features[col].astype('category')
        
        # Convert boolean columns to int
        bool_cols = ['on_1b', 'on_2b', 'on_3b', 'is_in_zone', 'is_swing', 'is_whiff', 
                     'is_hard_hit', 'is_late_game', 'is_high_leverage']
        for col in bool_cols:
            if col in features.columns:
                features[col] = features[col].fillna(False).astype(int)
        
        # Store feature names
        self.feature_names = list(features.columns)
        
        logger.info(f"Loaded {len(features):,} training examples")
        logger.info(f"Target distribution: {target.value_counts().to_dict()}")
        
        return features, target
    
    def preprocess_data(
        self, 
        X: pd.DataFrame, 
        y: pd.Series,
        fit_encoders: bool = True
    ) -> Tuple[pd.DataFrame, pd.Series]:
        """
        Preprocess features and target.
        
        Args:
            X: Feature DataFrame
            y: Target Series
            fit_encoders: Whether to fit encoders (train) or use existing (test)
            
        Returns:
            Tuple of processed (X, y)
        """
        X_processed = X.copy()
        y_processed = y.copy()
        
        # Encode categorical variables
        categorical_cols = X_processed.select_dtypes(include=['category', 'object']).columns
        
        for col in categorical_cols:
            if fit_encoders:
                # For training, fit new encoders
                if hasattr(self, f'{col}_encoder'):
                    encoder = getattr(self, f'{col}_encoder')
                else:
                    encoder = LabelEncoder()
                    setattr(self, f'{col}_encoder', encoder)
                
                # Handle missing values
                X_processed[col] = X_processed[col].fillna('missing')
                encoder.fit(X_processed[col])
                X_processed[col] = encoder.transform(X_processed[col])
            else:
                # For testing, use existing encoders
                if hasattr(self, f'{col}_encoder'):
                    encoder = getattr(self, f'{col}_encoder')
                    X_processed[col] = X_processed[col].fillna('missing')
                    # Handle unseen categories
                    mask = ~X_processed[col].isin(encoder.classes_)
                    X_processed.loc[mask, col] = encoder.classes_[0]
                    X_processed[col] = encoder.transform(X_processed[col])
        
        # Encode target
        if fit_encoders:
            self.label_encoder.fit(y_processed)
        y_processed = self.label_encoder.transform(y_processed)
        
        # Fill remaining missing values
        X_processed = X_processed.fillna(0)
        
        return X_processed, y_processed
    
    def train(
        self, 
        X_train: pd.DataFrame, 
        y_train: pd.Series,
        X_val: pd.DataFrame, 
        y_val: pd.Series
    ) -> Dict[str, float]:
        """
        Train the XGBoost model.
        
        Args:
            X_train, y_train: Training data
            X_val, y_val: Validation data
            
        Returns:
            Dictionary with training metrics
        """
        logger.info(f"Training {self.target_tier} model with {len(X_train):,} samples")
        
        # Preprocess data
        X_train_proc, y_train_proc = self.preprocess_data(X_train, y_train, fit_encoders=True)
        X_val_proc, y_val_proc = self.preprocess_data(X_val, y_val, fit_encoders=False)
        
        # Create XGBoost model
        self.model = xgb.XGBClassifier(**self.xgb_params)
        
        # Train with early stopping
        self.model.fit(
            X_train_proc, y_train_proc,
            eval_set=[(X_val_proc, y_val_proc)],
            early_stopping_rounds=20,
            verbose=False
        )
        
        # Predictions and metrics
        y_pred = self.model.predict(X_val_proc)
        y_pred_proba = self.model.predict_proba(X_val_proc)
        
        # Calculate metrics
        accuracy = accuracy_score(y_val_proc, y_pred)
        logloss = log_loss(y_val_proc, y_pred_proba)
        
        # Convert back to original labels for reporting
        y_pred_labels = self.label_encoder.inverse_transform(y_pred)
        y_val_labels = self.label_encoder.inverse_transform(y_val_proc)
        
        # Classification report
        report = classification_report(y_val_labels, y_pred_labels, output_dict=True)
        
        metrics = {
            'accuracy': accuracy,
            'log_loss': logloss,
            'n_classes': len(self.label_encoder.classes_),
            'n_features': X_train_proc.shape[1],
            'n_estimators': self.model.n_estimators,
            'best_iteration': self.model.best_iteration
        }
        
        logger.info(f"Training complete. Accuracy: {accuracy:.4f}, Log Loss: {logloss:.4f}")
        logger.info(f"Classes: {list(self.label_encoder.classes_)}")
        
        return metrics
    
    def predict(self, X: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """
        Make predictions on new data.
        
        Args:
            X: Feature DataFrame
            
        Returns:
            Tuple of (predicted_classes, probabilities)
        """
        if self.model is None:
            raise ValueError("Model not trained yet")
        
        X_proc, _ = self.preprocess_data(X, pd.Series([0]), fit_encoders=False)
        
        predictions = self.model.predict(X_proc)
        probabilities = self.model.predict_proba(X_proc)
        
        # Convert back to original labels
        predictions_labels = self.label_encoder.inverse_transform(predictions)
        
        return predictions_labels, probabilities
    
    def save_model(self, path: str) -> None:
        """Save the trained model and encoders."""
        if self.model is None:
            raise ValueError("No model to save")
        
        model_data = {
            'model': self.model,
            'label_encoder': self.label_encoder,
            'feature_names': self.feature_names,
            'target_tier': self.target_tier,
            'model_version': self.model_version,
            'xgb_params': self.xgb_params,
            'metrics': getattr(self, 'training_metrics', {})
        }
        
        # Save categorical encoders
        categorical_cols = ['stand', 'p_throws', 'bb_type', 'velocity_category', 'zone_region', 'count_code']
        for col in categorical_cols:
            if hasattr(self, f'{col}_encoder'):
                model_data[f'{col}_encoder'] = getattr(self, f'{col}_encoder')
        
        joblib.dump(model_data, path)
        logger.info(f"Model saved to {path}")
    
    def load_model(self, path: str) -> None:
        """Load a saved model."""
        model_data = joblib.load(path)
        
        self.model = model_data['model']
        self.label_encoder = model_data['label_encoder']
        self.feature_names = model_data['feature_names']
        self.target_tier = model_data['target_tier']
        self.model_version = model_data['model_version']
        self.xgb_params = model_data['xgb_params']
        self.training_metrics = model_data.get('metrics', {})
        
        # Load categorical encoders
        categorical_cols = ['stand', 'p_throws', 'bb_type', 'velocity_category', 'zone_region', 'count_code']
        for col in categorical_cols:
            if f'{col}_encoder' in model_data:
                setattr(self, f'{col}_encoder', model_data[f'{col}_encoder'])
        
        logger.info(f"Model loaded from {path}")


def evaluate_model_performance(
    model: PitchTier1XGBoostModel,
    X_test: pd.DataFrame,
    y_test: pd.Series
) -> Dict[str, Union[float, str]]:
    """
    Comprehensive model evaluation.
    
    Args:
        model: Trained model
        X_test, y_test: Test data
        
    Returns:
        Dictionary with evaluation metrics
    """
    # Make predictions
    y_pred, y_pred_proba = model.predict(X_test)
    
    # Convert to numeric for metrics
    y_test_encoded = model.label_encoder.transform(y_test)
    y_pred_encoded = model.label_encoder.transform(y_pred)
    
    # Basic metrics
    accuracy = accuracy_score(y_test_encoded, y_pred_encoded)
    logloss = log_loss(y_test_encoded, y_pred_proba)
    
    # Detailed classification report
    report = classification_report(y_test, y_pred, output_dict=True)
    
    # Per-class metrics
    per_class_metrics = {}
    for class_name in model.label_encoder.classes_:
        if class_name in report:
            per_class_metrics[class_name] = {
                'precision': report[class_name]['precision'],
                'recall': report[class_name]['recall'],
                'f1': report[class_name]['f1-score'],
                'support': report[class_name]['support']
            }
    
    return {
        'accuracy': accuracy,
        'log_loss': logloss,
        'per_class_metrics': per_class_metrics,
        'model_version': model.model_version,
        'target_tier': model.target_tier,
        'n_classes': len(model.label_encoder.classes_)
    }


def main():
    parser = argparse.ArgumentParser(
        description='Train Two-Tier XGBoost pitch-level model'
    )
    parser.add_argument(
        '--target', '-t',
        choices=['tier1', 'tier2'],
        default='tier1',
        help='Target tier to train (default: tier1)'
    )
    parser.add_argument(
        '--seasons', '-s',
        nargs='+',
        type=int,
        default=[2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023],
        help='Seasons to include in training (default: 2015-2023)'
    )
    parser.add_argument(
        '--sample-rate', '-r',
        type=float,
        default=1.0,
        help='Sample rate for faster training (default: 1.0)'
    )
    parser.add_argument(
        '--test-size', '-e',
        type=float,
        default=0.2,
        help='Proportion for test set (default: 0.2)'
    )
    parser.add_argument(
        '--save-model', '-m',
        action='store_true',
        help='Save trained model to disk'
    )
    parser.add_argument(
        '--model-dir',
        default='data/models/pitch_level',
        help='Directory to save models (default: data/models/pitch_level)'
    )
    
    args = parser.parse_args()
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create model directory
    model_dir = Path(args.model_dir)
    model_dir.mkdir(parents=True, exist_ok=True)
    
    # Initialize model
    model = PitchTier1XGBoostModel(target_tier=args.target)
    
    # Load data
    logger.info(f"Loading training data for seasons: {args.seasons}")
    X, y = model.load_training_data(seasons=args.seasons, sample_rate=args.sample_rate)
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, 
        test_size=args.test_size, 
        random_state=42,
        stratify=y
    )
    
    # Further split training for validation
    X_train, X_val, y_train, y_val = train_test_split(
        X_train, y_train, 
        test_size=0.2, 
        random_state=42,
        stratify=y_train
    )
    
    logger.info(f"Data splits: Train={len(X_train):,}, Val={len(X_val):,}, Test={len(X_test):,}")
    
    # Train model
    training_metrics = model.train(X_train, y_train, X_val, y_val)
    model.training_metrics = training_metrics
    
    # Evaluate on test set
    test_metrics = evaluate_model_performance(model, X_test, y_test)
    
    # Print results
    print(f"\n{'='*60}")
    print(f"Pitch-Level XGBoost Model Results")
    print(f"{'='*60}")
    print(f"Target Tier: {args.target}")
    print(f"Model Version: {model.model_version}")
    print(f"Training Seasons: {args.seasons}")
    print(f"Sample Rate: {args.sample_rate}")
    print(f"\nTraining Metrics:")
    print(f"  Accuracy: {training_metrics['accuracy']:.4f}")
    print(f"  Log Loss: {training_metrics['log_loss']:.4f}")
    print(f"  Classes: {training_metrics['n_classes']}")
    print(f"  Features: {training_metrics['n_features']}")
    print(f"  Estimators: {training_metrics['n_estimators']}")
    print(f"\nTest Set Performance:")
    print(f"  Accuracy: {test_metrics['accuracy']:.4f}")
    print(f"  Log Loss: {test_metrics['log_loss']:.4f}")
    
    print(f"\nPer-Class Performance:")
    for class_name, metrics in test_metrics['per_class_metrics'].items():
        print(f"  {class_name:15}: P={metrics['precision']:.3f} R={metrics['recall']:.3f} F1={metrics['f1']:.3f}")
    
    # Benchmark comparison
    if args.target == 'tier1':
        print(f"\nBenchmark Comparison:")
        print(f"  SMU Baseline: 58.0% accuracy")
        print(f"  This Model:   {test_metrics['accuracy']*100:.1f}% accuracy")
        improvement = test_metrics['accuracy'] - 0.58
        print(f"  Improvement:  {improvement*100:+.1f} percentage points")
    
    # Save model
    if args.save_model:
        model_path = model_dir / f"pitch_{args.target}_xgboost_{model.model_version}.joblib"
        model.save_model(str(model_path))
        
        # Save evaluation report
        report_path = model_dir / f"pitch_{args.target}_report_{model.model_version}.json"
        import json
        with open(report_path, 'w') as f:
            json.dump({
                'training_metrics': training_metrics,
                'test_metrics': test_metrics,
                'model_info': {
                    'target_tier': args.target,
                    'model_version': model.model_version,
                    'seasons': args.seasons,
                    'sample_rate': args.sample_rate,
                    'feature_names': model.feature_names
                }
            }, f, indent=2)
        
        print(f"\nModel saved to: {model_path}")
        print(f"Report saved to: {report_path}")


if __name__ == '__main__':
    main()
