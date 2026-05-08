#!/usr/bin/env python3
"""
Flexible Ensemble Training Manager for Baseball Prediction Models

Supports concurrent training of multiple model types with adaptive ensemble methods:
- XGBoost (pitch-level, PA-level, game-level)
- HistGradientBoosting (fast training, good performance)
- Logistic Regression (baseline, interpretability)
- Ensemble methods (weighted averaging, stacking, adaptive selection)

Usage:
    training_manager = EnsembleTrainingManager()
    training_manager.train_ensemble(
        model_types=['xgboost', 'hist_gb', 'logistic'],
        target_level='pitch',
        seasons=[2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023],
        concurrent=True
    )
"""

import concurrent.futures
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, log_loss, roc_auc_score
from sklearn.model_selection import train_test_split

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import os
import psycopg2

logger = logging.getLogger(__name__)


class ModelTrainer:
    """Base class for model trainers with common interface."""
    
    def __init__(self, model_type: str, target_level: str):
        self.model_type = model_type
        self.target_level = target_level
        self.model = None
        self.feature_names = []
        self.training_metrics = {}
        
    def load_data(self, seasons: List[int], sample_rate: float = 1.0) -> Tuple[pd.DataFrame, pd.Series]:
        """Load training data for specific target level."""
        conn = psycopg2.connect(
            host=os.getenv('PGHOST', 'localhost'),
            port=os.getenv('PGPORT', '5432'),
            database=os.getenv('PGDATABASE', 'retrosheet'),
            user=os.getenv('PGUSER', 'retrosheet'),
            password=os.getenv('PGPASSWORD', '')
        )
        
        try:
            if self.target_level == 'pitch':
                return self._load_pitch_data(conn, seasons, sample_rate)
            elif self.target_level == 'pa':
                return self._load_pa_data(conn, seasons, sample_rate)
            elif self.target_level == 'game':
                return self._load_game_data(conn, seasons, sample_rate)
            else:
                raise ValueError(f"Unsupported target level: {self.target_level}")
        finally:
            conn.close()
    
    def _load_pitch_data(self, conn, seasons: List[int], sample_rate: float) -> Tuple[pd.DataFrame, pd.Series]:
        """Load pitch-level data from features_pitch tables."""
        cursor = conn.cursor()
        
        # Build season filter
        season_filter = ""
        params = []
        if seasons:
            placeholders = ','.join(['%s'] * len(seasons))
            season_filter = f"WHERE bf.season IN ({placeholders})"
            params.extend(seasons)
        
        # Add sampling
        if sample_rate < 1.0:
            if season_filter:
                season_filter += " AND random() < %s"
            else:
                season_filter = "WHERE random() < %s"
            params.append(sample_rate)
        
        query = f"""
            SELECT 
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
                ef.velocity_category, ef.zone_region, ef.is_in_zone,
                ef.is_swing, ef.is_whiff, ef.is_hard_hit,
                ef.distance_from_zone_center, ef.horizontal_break, ef.vertical_break,
                ef.score_diff, ef.is_late_game, ef.is_high_leverage,
                ef.base_state_code, ef.count_code,
                -- Target: coarse outcome classification
                CASE 
                    WHEN ef.is_strike THEN 'strike'
                    WHEN ef.is_ball_in_play THEN 'ball_in_play'
                    ELSE 'ball'
                END as target
            FROM features_pitch.base_features bf
            LEFT JOIN features_pitch.engineered_features ef 
                ON bf.pitch_id = ef.pitch_id
            {season_filter}
            LIMIT 100000
        """
        
        cursor.execute(query, params)
        
        # Fetch data directly without pandas to avoid sqlalchemy issues
        columns = [desc[0] for desc in cursor.description]
        data = cursor.fetchall()
        df = pd.DataFrame(data, columns=columns)
        
        # Remove rows with null targets
        df = df.dropna(subset=['target'])
        
        # Separate features and target
        target = df['target'].copy()
        features = df.drop(columns=['target'])
        
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
        
        self.feature_names = features.columns.tolist()
        return features, target
    
    def _load_pa_data(self, conn, seasons: List[int], sample_rate: float) -> Tuple[pd.DataFrame, pd.Series]:
        """Load plate appearance level data."""
        # TODO: Implement PA level data loading
        raise NotImplementedError("PA level data loading not yet implemented")
    
    def _load_game_data(self, conn, seasons: List[int], sample_rate: float) -> Tuple[pd.DataFrame, pd.Series]:
        """Load game level data."""
        # TODO: Implement game level data loading
        raise NotImplementedError("Game level data loading not yet implemented")
    
    def train(self, X: pd.DataFrame, y: pd.Series, X_val: pd.DataFrame, y_val: pd.Series) -> Dict[str, Any]:
        """Train the model - to be implemented by subclasses."""
        raise NotImplementedError("Train method must be implemented by subclasses")
    
    def predict(self, X: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """Make predictions - to be implemented by subclasses."""
        raise NotImplementedError("Predict method must be implemented by subclasses")
    
    def save_model(self, path: str):
        """Save trained model."""
        model_data = {
            'model': self.model,
            'model_type': self.model_type,
            'target_level': self.target_level,
            'feature_names': self.feature_names,
            'training_metrics': self.training_metrics,
            'timestamp': datetime.now().isoformat()
        }
        joblib.dump(model_data, path)
        logger.info(f"Model saved to {path}")


class XGBoostTrainer(ModelTrainer):
    """XGBoost model trainer."""
    
    def __init__(self, target_level: str):
        super().__init__('xgboost', target_level)
        import xgboost as xgb
        self.xgb = xgb
    
    def train(self, X: pd.DataFrame, y: pd.Series, X_val: pd.DataFrame, y_val: pd.Series) -> Dict[str, Any]:
        """Train XGBoost model."""
        from sklearn.preprocessing import LabelEncoder
        
        # Encode target
        label_encoder = LabelEncoder()
        y_encoded = label_encoder.fit_transform(y)
        y_val_encoded = label_encoder.transform(y_val)
        
        # Train model
        self.model = self.xgb.XGBClassifier(
            n_estimators=100,
            max_depth=6,
            learning_rate=0.1,
            random_state=42,
            n_jobs=-1
        )
        
        start_time = time.time()
        self.model.fit(X, y_encoded, eval_set=[(X_val, y_val_encoded)], verbose=False)
        training_time = time.time() - start_time
        
        # Evaluate
        y_pred = self.model.predict(X_val)
        y_pred_proba = self.model.predict_proba(X_val)
        
        self.training_metrics = {
            'accuracy': accuracy_score(y_val_encoded, y_pred),
            'log_loss': log_loss(y_val_encoded, y_pred_proba),
            'training_time': training_time,
            'n_estimators': self.model.n_estimators,
            'max_depth': self.model.max_depth,
            'n_features': X.shape[1],
            'n_classes': len(label_encoder.classes_)
        }
        
        self.label_encoder = label_encoder
        return self.training_metrics
    
    def predict(self, X: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """Make predictions with XGBoost model."""
        y_pred_encoded = self.model.predict(X)
        y_pred_proba = self.model.predict_proba(X)
        
        # Convert back to original labels
        y_pred = self.label_encoder.inverse_transform(y_pred_encoded)
        return y_pred, y_pred_proba


class HistGradientBoostingTrainer(ModelTrainer):
    """Histogram-based Gradient Boosting trainer."""
    
    def __init__(self, target_level: str):
        super().__init__('hist_gb', target_level)
        from sklearn.ensemble import HistGradientBoostingClassifier
        self.HistGradientBoostingClassifier = HistGradientBoostingClassifier
    
    def train(self, X: pd.DataFrame, y: pd.Series, X_val: pd.DataFrame, y_val: pd.Series) -> Dict[str, Any]:
        """Train HistGradientBoosting model."""
        from sklearn.preprocessing import LabelEncoder
        
        # Encode target
        label_encoder = LabelEncoder()
        y_encoded = label_encoder.fit_transform(y)
        y_val_encoded = label_encoder.transform(y_val)
        
        # Train model
        self.model = self.HistGradientBoostingClassifier(
            max_iter=100,
            max_depth=6,
            learning_rate=0.1,
            random_state=42
        )
        
        start_time = time.time()
        self.model.fit(X, y_encoded)
        training_time = time.time() - start_time
        
        # Evaluate
        y_pred = self.model.predict(X_val)
        y_pred_proba = self.model.predict_proba(X_val)
        
        self.training_metrics = {
            'accuracy': accuracy_score(y_val_encoded, y_pred),
            'log_loss': log_loss(y_val_encoded, y_pred_proba),
            'training_time': training_time,
            'max_iter': self.model.max_iter,
            'max_depth': self.model.max_depth,
            'n_features': X.shape[1],
            'n_classes': len(label_encoder.classes_)
        }
        
        self.label_encoder = label_encoder
        return self.training_metrics
    
    def predict(self, X: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """Make predictions with HistGradientBoosting model."""
        y_pred_encoded = self.model.predict(X)
        y_pred_proba = self.model.predict_proba(X)
        
        # Convert back to original labels
        y_pred = self.label_encoder.inverse_transform(y_pred_encoded)
        return y_pred, y_pred_proba


class EnsembleTrainingManager:
    """Flexible ensemble training manager with concurrent training support."""
    
    def __init__(self, model_dir: str = 'data/models/ensemble'):
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)
        self.trained_models = {}
        self.ensemble_weights = {}
        
    def train_ensemble(
        self,
        model_types: List[str],
        target_level: str,
        seasons: Optional[List[int]] = None,
        sample_rate: float = 1.0,
        concurrent: bool = True,
        test_size: float = 0.2
    ) -> Dict[str, Any]:
        """
        Train ensemble of models concurrently or sequentially.
        
        Args:
            model_types: List of model types to train ['xgboost', 'hist_gb', 'logistic']
            target_level: Target level ['pitch', 'pa', 'game']
            seasons: List of seasons to include
            sample_rate: Data sampling rate for faster training
            concurrent: Whether to train models concurrently
            test_size: Proportion for test set
            
        Returns:
            Dictionary with training results and ensemble info
        """
        logger.info(f"Starting ensemble training for {len(model_types)} models at {target_level} level")
        
        # Default seasons
        if seasons is None:
            seasons = [2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023]
        
        # Load data once and share across models
        logger.info("Loading training data...")
        trainer = ModelTrainer('base', target_level)
        X, y = trainer.load_data(seasons, sample_rate)
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=42, stratify=y
        )
        
        # Further split for validation
        X_train, X_val, y_train, y_val = train_test_split(
            X_train, y_train, test_size=0.2, random_state=42, stratify=y_train
        )
        
        logger.info(f"Data splits: Train={len(X_train):,}, Val={len(X_val):,}, Test={len(X_test):,}")
        
        # Create trainers
        trainers = {}
        for model_type in model_types:
            if model_type == 'xgboost':
                trainers[model_type] = XGBoostTrainer(target_level)
            elif model_type == 'hist_gb':
                trainers[model_type] = HistGradientBoostingTrainer(target_level)
            elif model_type == 'logistic':
                # TODO: Implement LogisticRegressionTrainer
                logger.warning(f"Logistic regression trainer not yet implemented, skipping {model_type}")
                continue
            else:
                logger.error(f"Unknown model type: {model_type}")
                continue
        
        # Train models
        if concurrent:
            results = self._train_concurrently(trainers, X_train, y_train, X_val, y_val)
        else:
            results = self._train_sequentially(trainers, X_train, y_train, X_val, y_val)
        
        # Evaluate ensemble
        ensemble_results = self._evaluate_ensemble(results, X_test, y_test)
        
        # Save models
        self._save_ensemble(results, target_level)
        
        # Compile results
        training_results = {
            'target_level': target_level,
            'model_types': model_types,
            'seasons': seasons,
            'sample_rate': sample_rate,
            'data_splits': {
                'train': len(X_train),
                'val': len(X_val),
                'test': len(X_test)
            },
            'individual_results': results,
            'ensemble_results': ensemble_results,
            'timestamp': datetime.now().isoformat()
        }
        
        # Save training report
        report_path = self.model_dir / f"ensemble_report_{target_level}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_path, 'w') as f:
            json.dump(training_results, f, indent=2, default=str)
        
        logger.info(f"Ensemble training completed. Report saved to {report_path}")
        return training_results
    
    def _train_concurrently(
        self, 
        trainers: Dict[str, ModelTrainer], 
        X_train: pd.DataFrame, 
        y_train: pd.Series,
        X_val: pd.DataFrame, 
        y_val: pd.Series
    ) -> Dict[str, Dict[str, Any]]:
        """Train models concurrently using ThreadPoolExecutor."""
        results = {}
        
        def train_single(model_type: str, trainer: ModelTrainer):
            try:
                logger.info(f"Training {model_type} model...")
                start_time = time.time()
                metrics = trainer.train(X_train, y_train, X_val, y_val)
                training_time = time.time() - start_time
                
                results[model_type] = {
                    'trainer': trainer,
                    'metrics': metrics,
                    'training_time': training_time,
                    'status': 'success'
                }
                logger.info(f"{model_type} training completed in {training_time:.2f}s")
                
            except Exception as e:
                logger.error(f"Error training {model_type}: {e}")
                results[model_type] = {
                    'trainer': None,
                    'metrics': {},
                    'training_time': 0,
                    'status': 'failed',
                    'error': str(e)
                }
        
        # Train concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(trainers), 4)) as executor:
            futures = [
                executor.submit(train_single, model_type, trainer)
                for model_type, trainer in trainers.items()
            ]
            
            # Wait for all to complete
            concurrent.futures.wait(futures)
        
        return results
    
    def _train_sequentially(
        self, 
        trainers: Dict[str, ModelTrainer], 
        X_train: pd.DataFrame, 
        y_train: pd.Series,
        X_val: pd.DataFrame, 
        y_val: pd.Series
    ) -> Dict[str, Dict[str, Any]]:
        """Train models sequentially."""
        results = {}
        
        for model_type, trainer in trainers.items():
            try:
                logger.info(f"Training {model_type} model...")
                start_time = time.time()
                metrics = trainer.train(X_train, y_train, X_val, y_val)
                training_time = time.time() - start_time
                
                results[model_type] = {
                    'trainer': trainer,
                    'metrics': metrics,
                    'training_time': training_time,
                    'status': 'success'
                }
                logger.info(f"{model_type} training completed in {training_time:.2f}s")
                
            except Exception as e:
                logger.error(f"Error training {model_type}: {e}")
                results[model_type] = {
                    'trainer': None,
                    'metrics': {},
                    'training_time': 0,
                    'status': 'failed',
                    'error': str(e)
                }
        
        return results
    
    def _evaluate_ensemble(
        self, 
        training_results: Dict[str, Dict[str, Any]], 
        X_test: pd.DataFrame, 
        y_test: pd.Series
    ) -> Dict[str, Any]:
        """Evaluate ensemble performance using different combination methods."""
        successful_models = {
            model_type: result['trainer']
            for model_type, result in training_results.items()
            if result['status'] == 'success'
        }
        
        if len(successful_models) < 2:
            logger.warning("Need at least 2 successful models for ensemble evaluation")
            return {'ensemble_accuracy': 0, 'ensemble_log_loss': float('inf')}
        
        # Get predictions from all successful models
        predictions = []
        probabilities = []
        
        for model_type, trainer in successful_models.items():
            y_pred, y_pred_proba = trainer.predict(X_test)
            predictions.append(y_pred)
            probabilities.append(y_pred_proba)
        
        # Simple voting ensemble
        from scipy.stats import mode
        ensemble_pred = mode(np.array(predictions), axis=0)[0].flatten()
        
        # Average probability ensemble
        avg_proba = np.mean(probabilities, axis=0)
        ensemble_pred_proba = np.argmax(avg_proba, axis=1)
        
        # Convert back to labels if needed
        if hasattr(successful_models[list(successful_models.keys())[0]], 'label_encoder'):
            label_encoder = successful_models[list(successful_models.keys())[0]].label_encoder
            ensemble_pred_proba = label_encoder.inverse_transform(ensemble_pred_proba)
        
        # Calculate metrics
        ensemble_accuracy = accuracy_score(y_test, ensemble_pred)
        ensemble_log_loss = log_loss(
            pd.get_dummies(y_test), 
            avg_proba
        )
        
        # Compare with best individual model
        best_individual_acc = max(
            result['metrics']['accuracy'] 
            for result in training_results.values() 
            if result['status'] == 'success'
        )
        
        improvement = ensemble_accuracy - best_individual_acc
        
        return {
            'ensemble_accuracy': ensemble_accuracy,
            'ensemble_log_loss': ensemble_log_loss,
            'best_individual_accuracy': best_individual_acc,
            'improvement': improvement,
            'n_models': len(successful_models),
            'method': 'voting_averaging'
        }
    
    def _save_ensemble(self, training_results: Dict[str, Dict[str, Any]], target_level: str):
        """Save all trained models and create ensemble metadata."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Save individual models
        for model_type, result in training_results.items():
            if result['status'] == 'success':
                model_path = self.model_dir / f"{model_type}_{target_level}_{timestamp}.joblib"
                result['trainer'].save_model(str(model_path))
        
        # Save ensemble metadata
        ensemble_metadata = {
            'target_level': target_level,
            'timestamp': timestamp,
            'models': {
                model_type: {
                    'status': result['status'],
                    'metrics': result['metrics'],
                    'training_time': result['training_time']
                }
                for model_type, result in training_results.items()
            }
        }
        
        metadata_path = self.model_dir / f"ensemble_metadata_{target_level}_{timestamp}.json"
        with open(metadata_path, 'w') as f:
            json.dump(ensemble_metadata, f, indent=2)


if __name__ == '__main__':
    # Example usage
    manager = EnsembleTrainingManager()
    
    # Train pitch-level ensemble
    results = manager.train_ensemble(
        model_types=['xgboost', 'hist_gb'],
        target_level='pitch',
        seasons=[2015, 2016, 2017],  # Smaller set for testing
        sample_rate=0.1,  # 10% of data for faster training
        concurrent=True
    )
    
    print("Ensemble training completed!")
    print(f"Results: {json.dumps(results, indent=2, default=str)}")
