#!/usr/bin/env python3
"""Simple Ensemble Training for Baseball Prediction Models.

This creates a flexible ensemble system that can train multiple models
concurrently and combine their predictions using various ensemble methods.
"""

import concurrent.futures
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, log_loss
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import psycopg2

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SimpleEnsembleTrainer:
    """Simple ensemble trainer that works with existing infrastructure."""
    
    def __init__(self, model_dir: str = 'data/models/ensemble'):
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)
        
    def load_pitch_data(self, seasons: list, sample_rate: float = 1.0):
        """Load pitch-level data from database."""
        conn = psycopg2.connect(
            host='localhost',
            port='5432',
            database='retrosheet',
            user='cbwinslow',
            password='123qweasd'
        )
        
        try:
            cursor = conn.cursor()
            
            # Build season filter
            season_filter = ""
            params = []
            if seasons:
                placeholders = ','.join(['%s'] * len(seasons))
                season_filter = f"WHERE bf.game_year IN ({placeholders})"
                params.extend(seasons)
            
            # Add sampling
            if sample_rate < 1.0:
                if season_filter:
                    season_filter += " AND random() < %s"
                else:
                    season_filter = "WHERE random() < %s"
                params.append(sample_rate)
            
            # Simple query for basic features
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
                    -- Simple target classification
                    CASE 
                        WHEN ef.is_strike THEN 'strike'
                        WHEN ef.is_ball_in_play THEN 'ball_in_play'
                        ELSE 'ball'
                    END as target
                FROM features_pitch.base_features bf
                LEFT JOIN features_pitch.engineered_features ef 
                    ON bf.pitch_id = ef.pitch_id
                {season_filter}
                LIMIT 50000
            """
            
            logger.info(f"Loading pitch data with query for seasons: {seasons}")
            cursor.execute(query, params)
            
            # Fetch data
            columns = [desc[0] for desc in cursor.description]
            data = cursor.fetchall()
            df = pd.DataFrame(data, columns=columns)
            
            # Clean data
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
            
            logger.info(f"Loaded {len(features)} samples with {len(features.columns)} features")
            return features, target
            
        finally:
            conn.close()
    
    def train_xgboost_model(self, X_train, y_train, X_val, y_val):
        """Train XGBoost model."""
        try:
            import xgboost as xgb
            
            # Encode targets
            label_encoder = LabelEncoder()
            y_train_encoded = label_encoder.fit_transform(y_train)
            y_val_encoded = label_encoder.transform(y_val)
            
            # Train model
            model = xgb.XGBClassifier(
                n_estimators=50,  # Smaller for faster training
                max_depth=4,
                learning_rate=0.1,
                random_state=42,
                n_jobs=-1
            )
            
            start_time = time.time()
            model.fit(X_train, y_train_encoded)
            training_time = time.time() - start_time
            
            # Evaluate
            y_pred = model.predict(X_val)
            y_pred_proba = model.predict_proba(X_val)
            
            accuracy = accuracy_score(y_val_encoded, y_pred)
            logloss = log_loss(y_val_encoded, y_pred_proba)
            
            return {
                'model': model,
                'label_encoder': label_encoder,
                'accuracy': accuracy,
                'log_loss': logloss,
                'training_time': training_time,
                'model_type': 'xgboost'
            }
            
        except Exception as e:
            logger.error(f"XGBoost training failed: {e}")
            return {'error': str(e), 'model_type': 'xgboost'}
    
    def train_hist_gb_model(self, X_train, y_train, X_val, y_val):
        """Train Histogram Gradient Boosting model."""
        try:
            from sklearn.ensemble import HistGradientBoostingClassifier
            
            # Encode targets
            label_encoder = LabelEncoder()
            y_train_encoded = label_encoder.fit_transform(y_train)
            y_val_encoded = label_encoder.transform(y_val)
            
            # Train model
            model = HistGradientBoostingClassifier(
                max_iter=50,  # Smaller for faster training
                max_depth=4,
                learning_rate=0.1,
                random_state=42
            )
            
            start_time = time.time()
            model.fit(X_train, y_train_encoded)
            training_time = time.time() - start_time
            
            # Evaluate
            y_pred = model.predict(X_val)
            y_pred_proba = model.predict_proba(X_val)
            
            accuracy = accuracy_score(y_val_encoded, y_pred)
            logloss = log_loss(y_val_encoded, y_pred_proba)
            
            return {
                'model': model,
                'label_encoder': label_encoder,
                'accuracy': accuracy,
                'log_loss': logloss,
                'training_time': training_time,
                'model_type': 'hist_gb'
            }
            
        except Exception as e:
            logger.error(f"HistGB training failed: {e}")
            return {'error': str(e), 'model_type': 'hist_gb'}
    
    def train_models_concurrently(self, X_train, y_train, X_val, y_val):
        """Train multiple models concurrently."""
        models_to_train = [
            ('xgboost', self.train_xgboost_model),
            ('hist_gb', self.train_hist_gb_model)
        ]
        
        results = {}
        
        def train_single(model_name, train_func):
            logger.info(f"Training {model_name} model...")
            start_time = time.time()
            result = train_func(X_train, y_train, X_val, y_val)
            total_time = time.time() - start_time
            
            if 'error' not in result:
                logger.info(f"{model_name} completed in {total_time:.2f}s - Accuracy: {result['accuracy']:.3f}")
                results[model_name] = result
            else:
                logger.error(f"{model_name} failed: {result['error']}")
                results[model_name] = result
        
        # Train concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            futures = [
                executor.submit(train_single, model_name, train_func)
                for model_name, train_func in models_to_train
            ]
            
            # Wait for completion
            concurrent.futures.wait(futures)
        
        return results
    
    def evaluate_ensemble(self, model_results, X_test, y_test):
        """Evaluate ensemble performance."""
        successful_models = {
            name: result for name, result in model_results.items() 
            if 'error' not in result
        }
        
        if len(successful_models) < 2:
            logger.warning("Need at least 2 successful models for ensemble")
            return {'ensemble_accuracy': 0, 'improvement': 0}
        
        # Get predictions
        predictions = []
        probabilities = []
        
        for model_name, result in successful_models.items():
            model = result['model']
            label_encoder = result['label_encoder']
            
            # Encode test targets
            y_test_encoded = label_encoder.transform(y_test)
            
            # Get predictions
            y_pred = model.predict(X_test)
            y_pred_proba = model.predict_proba(X_test)
            
            # Convert back to original labels for consistency
            y_pred_labels = label_encoder.inverse_transform(y_pred)
            
            predictions.append(y_pred_labels)
            probabilities.append(y_pred_proba)
        
        # Simple voting ensemble
        from scipy.stats import mode
        ensemble_pred = mode(np.array(predictions), axis=0)[0].flatten()
        
        # Average probability ensemble
        avg_proba = np.mean(probabilities, axis=0)
        
        # Calculate accuracy
        ensemble_accuracy = accuracy_score(y_test, ensemble_pred)
        
        # Compare with best individual
        best_individual_acc = max(result['accuracy'] for result in successful_models.values())
        improvement = ensemble_accuracy - best_individual_acc
        
        return {
            'ensemble_accuracy': ensemble_accuracy,
            'best_individual_accuracy': best_individual_acc,
            'improvement': improvement,
            'n_models': len(successful_models)
        }
    
    def train_ensemble(self, seasons=None, sample_rate=0.1):
        """Train complete ensemble system."""
        logger.info("Starting ensemble training...")
        
        # Default seasons
        if seasons is None:
            seasons = [2015, 2016, 2017]
        
        # Load data
        X, y = self.load_pitch_data(seasons, sample_rate)
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        # Further split for validation
        X_train, X_val, y_train, y_val = train_test_split(
            X_train, y_train, test_size=0.2, random_state=42, stratify=y_train
        )
        
        logger.info(f"Data splits - Train: {len(X_train)}, Val: {len(X_val)}, Test: {len(X_test)}")
        
        # Train models concurrently
        model_results = self.train_models_concurrently(X_train, y_train, X_val, y_val)
        
        # Evaluate ensemble
        ensemble_results = self.evaluate_ensemble(model_results, X_test, y_test)
        
        # Save results
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        results = {
            'timestamp': timestamp,
            'seasons': seasons,
            'sample_rate': sample_rate,
            'data_splits': {
                'train': len(X_train),
                'val': len(X_val),
                'test': len(X_test)
            },
            'model_results': model_results,
            'ensemble_results': ensemble_results
        }
        
        # Save models
        for model_name, result in model_results.items():
            if 'error' not in result:
                model_path = self.model_dir / f"{model_name}_ensemble_{timestamp}.joblib"
                model_data = {
                    'model': result['model'],
                    'label_encoder': result['label_encoder'],
                    'model_type': result['model_type'],
                    'accuracy': result['accuracy'],
                    'log_loss': result['log_loss'],
                    'training_time': result['training_time']
                }
                joblib.dump(model_data, model_path)
                logger.info(f"Saved {model_name} model to {model_path}")
        
        # Save results
        results_path = self.model_dir / f"ensemble_results_{timestamp}.json"
        with open(results_path, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info(f"Ensemble training completed!")
        logger.info(f"Results saved to {results_path}")
        logger.info(f"Ensemble accuracy: {ensemble_results['ensemble_accuracy']:.3f}")
        logger.info(f"Best individual accuracy: {ensemble_results['best_individual_accuracy']:.3f}")
        logger.info(f"Ensemble improvement: {ensemble_results['improvement']:+.3f}")
        
        return results


def main():
    """Main function to test ensemble training."""
    trainer = SimpleEnsembleTrainer()
    
    try:
        results = trainer.train_ensemble(
            seasons=[2015, 2016],  # Small subset for testing
            sample_rate=0.05  # 5% of data for fast training
        )
        
        print("✅ Ensemble training completed successfully!")
        print(f"Ensemble accuracy: {results['ensemble_results']['ensemble_accuracy']:.3f}")
        print(f"Improvement over best individual: {results['ensemble_results']['improvement']:+.3f}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ensemble training failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    main()
