"""
Hierarchical XGBoost Model for Pitch Prediction

Implements a two-tier hierarchical classification approach:
1. Tier 1: Ball / Strike / Ball-in-Play prediction
2. Tier 2: Detailed outcome prediction for Ball-in-Play cases
"""

import asyncio
import numpy as np
import pandas as pd
import xgboost as xgb
from typing import List, Dict, Optional, Tuple, Union
from dataclasses import dataclass
from datetime import datetime
import pickle
import json

from baseball.models.base import BaseModel, ModelPrediction, ModelInfo, PerformanceMetrics
from baseball.models.xgboost.feature_engine import FeatureEngine
from baseball.models.xgboost.explainer import ModelExplainer


@dataclass
class HierarchicalConfig:
    """Configuration for hierarchical XGBoost model"""
    tier1_params: Dict = None
    tier2_params: Dict = None
    feature_engineering: bool = True
    cross_validation: bool = True
    cv_folds: int = 5
    early_stopping_rounds: int = 50
    eval_metric: str = 'logloss'
    random_state: int = 42
    
    def __post_init__(self):
        if self.tier1_params is None:
            self.tier1_params = {
                'objective': 'multi:softprob',
                'num_class': 3,  # Ball, Strike, Ball-in-Play
                'max_depth': 6,
                'learning_rate': 0.1,
                'n_estimators': 200,
                'subsample': 0.8,
                'colsample_bytree': 0.8,
                'random_state': self.random_state
            }
        
        if self.tier2_params is None:
            self.tier2_params = {
                'objective': 'multi:softprob',
                'num_class': 7,  # Single, Double, Triple, HR, Out, Error, FC
                'max_depth': 4,
                'learning_rate': 0.1,
                'n_estimators': 150,
                'subsample': 0.8,
                'colsample_bytree': 0.8,
                'random_state': self.random_state
            }


class HierarchicalXGBoostModel(BaseModel):
    """
    Hierarchical XGBoost model for pitch prediction.
    
    Uses two-tier classification:
    1. First tier: Predict Ball/Strike/Ball-in-Play
    2. Second tier: Predict detailed outcome if Ball-in-Play
    """
    
    # Tier 1 classes
    TIER1_CLASSES = ['Ball', 'Strike', 'Ball_in_Play']
    
    # Tier 2 classes (for Ball-in-Play outcomes)
    TIER2_CLASSES = ['Single', 'Double', 'Triple', 'Home_Run', 'Out', 'Error', 'Fielders_Choice']
    
    def __init__(self, config: Optional[HierarchicalConfig] = None):
        self.config = config or HierarchicalConfig()
        self.tier1_model = None
        self.tier2_model = None
        self.feature_engine = FeatureEngine()
        self.explainer = ModelExplainer()
        self.is_trained = False
        self._performance_metrics = PerformanceMetrics()
        
        # Initialize models
        self._initialize_models()
    
    def _initialize_models(self):
        """Initialize XGBoost models"""
        self.tier1_model = xgb.XGBClassifier(**self.config.tier1_params)
        self.tier2_model = xgb.XGBClassifier(**self.config.tier2_params)
    
    async def predict(self, context: 'PredictionContext') -> ModelPrediction:
        """
        Predict pitch outcome using hierarchical approach.
        
        Args:
            context: Prediction context with game state and features
            
        Returns:
            ModelPrediction with hierarchical probabilities and confidence
        """
        if not self.is_trained:
            raise ValueError("Model must be trained before making predictions")
        
        # Extract features from context
        features = self._extract_features(context)
        feature_df = pd.DataFrame([features])
        
        # Tier 1 prediction
        tier1_probs = self.tier1_model.predict_proba(feature_df)[0]
        tier1_pred = self.tier1_model.predict(feature_df)[0]
        
        # Initialize final predictions
        final_predictions = []
        
        # Map tier 1 to final predictions
        if tier1_pred == 0:  # Ball
            final_predictions.append({
                'pitch_symbol': 'B',
                'probability': float(tier1_probs[0]),
                'tier': 1,
                'confidence': float(tier1_probs[0])
            })
        elif tier1_pred == 1:  # Strike
            # Determine strike type based on context
            strike_symbol = self._predict_strike_type(context, tier1_probs[1])
            final_predictions.append({
                'pitch_symbol': strike_symbol,
                'probability': float(tier1_probs[1]),
                'tier': 1,
                'confidence': float(tier1_probs[1])
            })
        else:  # Ball in Play
            # Tier 2 prediction for detailed outcome
            tier2_probs = self.tier2_model.predict_proba(feature_df)[0]
            tier2_pred = self.tier2_model.predict(feature_df)[0]
            
            # Map tier 2 to pitch symbols
            bip_symbol = self._map_tier2_to_symbol(tier2_pred)
            combined_prob = tier1_probs[2] * tier2_probs[tier2_pred]
            
            final_predictions.append({
                'pitch_symbol': bip_symbol,
                'probability': float(combined_prob),
                'tier': 2,
                'confidence': float(combined_prob),
                'tier1_prob': float(tier1_probs[2]),
                'tier2_prob': float(tier2_probs[tier2_pred])
            })
        
        # Add alternative predictions
        alternatives = self._generate_alternatives(tier1_probs, context)
        final_predictions.extend(alternatives)
        
        # Calculate overall confidence
        confidence = self._calculate_hierarchical_confidence(final_predictions)
        
        return ModelPrediction(
            predictions=final_predictions,
            confidence=confidence,
            model_info=self.get_model_info(),
            timestamp=datetime.now()
        )
    
    def _extract_features(self, context: 'PredictionContext') -> Dict:
        """Extract features from prediction context"""
        features = {}
        
        # Count state
        features['balls'] = context.get('balls', 0)
        features['strikes'] = context.get('strikes', 0)
        features['outs'] = context.get('outs', 0)
        
        # Game context
        features['inning'] = context.get('inning', 1)
        features['is_top_inning'] = int(context.get('is_top_inning', True))
        features['home_score'] = context.get('home_score', 0)
        features['away_score'] = context.get('away_score', 0)
        features['run_difference'] = features['home_score'] - features['away_score']
        
        # Player context
        features['batter_id'] = context.get('batter_id', 0)
        features['pitcher_id'] = context.get('pitcher_id', 0)
        
        # Pitcher stats (if available)
        pitcher_stats = context.get('pitcher_stats', {})
        features['pitcher_era'] = pitcher_stats.get('era', 0.0)
        features['pitcher_whip'] = pitcher_stats.get('whip', 0.0)
        features['pitcher_k_rate'] = pitcher_stats.get('k_rate', 0.0)
        features['pitcher_bb_rate'] = pitcher_stats.get('bb_rate', 0.0)
        
        # Batter stats (if available)
        batter_stats = context.get('batter_stats', {})
        features['batter_avg'] = batter_stats.get('avg', 0.0)
        features['batter_obp'] = batter_stats.get('obp', 0.0)
        features['batter_slg'] = batter_stats.get('slg', 0.0)
        features['batter_k_rate'] = batter_stats.get('k_rate', 0.0)
        features['batter_bb_rate'] = batter_stats.get('bb_rate', 0.0)
        
        # Recent pitch sequence
        recent_pitches = context.get('recent_pitches', [])
        features['recent_ball_rate'] = sum(1 for p in recent_pitches[-5:] if p in ['B', 'J', 'W']) / max(1, len(recent_pitches[-5:]))
        features['recent_strike_rate'] = sum(1 for p in recent_pitches[-5:] if p in ['C', 'S', 'F', 'K', 'L', 'M', 'V']) / max(1, len(recent_pitches[-5:]))
        
        # Leverage index (if available)
        features['leverage_index'] = context.get('leverage_index', 1.0)
        
        return features
    
    def _predict_strike_type(self, context: 'PredictionContext', strike_prob: float) -> str:
        """Predict specific strike type based on context"""
        # Simple heuristic - could be enhanced with a separate model
        batter_k_rate = context.get('batter_stats', {}).get('k_rate', 0.2)
        pitcher_k_rate = context.get('pitcher_stats', {}).get('k_rate', 0.2)
        
        combined_k_rate = (batter_k_rate + pitcher_k_rate) / 2
        
        if combined_k_rate > 0.25:
            return 'K'  # Swinging strike
        elif combined_k_rate < 0.15:
            return 'C'  # Called strike
        else:
            return 'S'  # Swinging strike (default)
    
    def _map_tier2_to_symbol(self, tier2_pred: int) -> str:
        """Map tier 2 prediction to pitch symbol"""
        symbol_map = {
            0: '1',  # Single
            1: '2',  # Double
            2: '3',  # Triple
            3: 'H',  # Home Run
            4: 'X',  # Out
            5: 'E',  # Error
            6: '1'   # Fielder's Choice (treated as single)
        }
        return symbol_map.get(tier2_pred, 'X')
    
    def _generate_alternatives(self, tier1_probs: np.ndarray, context: 'PredictionContext') -> List[Dict]:
        """Generate alternative predictions"""
        alternatives = []
        
        # Add top 2 tier 1 alternatives
        sorted_indices = np.argsort(tier1_probs)[::-1]
        
        for i, idx in enumerate(sorted_indices[1:3]):  # Skip top prediction
            if tier1_probs[idx] > 0.1:  # Only include if probability > 10%
                if idx == 0:  # Ball
                    alternatives.append({
                        'pitch_symbol': 'B',
                        'probability': float(tier1_probs[idx]),
                        'tier': 1,
                        'alternative_rank': i + 1
                    })
                elif idx == 1:  # Strike
                    strike_symbol = self._predict_strike_type(context, tier1_probs[idx])
                    alternatives.append({
                        'pitch_symbol': strike_symbol,
                        'probability': float(tier1_probs[idx]),
                        'tier': 1,
                        'alternative_rank': i + 1
                    })
        
        return alternatives
    
    def _calculate_hierarchical_confidence(self, predictions: List[Dict]) -> float:
        """Calculate confidence based on hierarchical prediction structure"""
        if not predictions:
            return 0.0
        
        # Use top prediction confidence
        top_confidence = predictions[0].get('confidence', 0.0)
        
        # Adjust based on prediction tier
        top_tier = predictions[0].get('tier', 1)
        tier_adjustment = 1.0 if top_tier == 2 else 0.9  # Tier 2 predictions are more specific
        
        return top_confidence * tier_adjustment
    
    async def train(self, training_data: List[Dict]) -> 'TrainingResult':
        """
        Train the hierarchical XGBoost model.
        
        Args:
            training_data: List of training examples with features and outcomes
            
        Returns:
            TrainingResult with training metrics
        """
        # Prepare training data
        X, y_tier1, y_tier2 = self._prepare_training_data(training_data)
        
        # Train Tier 1 model
        tier1_result = self._train_tier1(X, y_tier1)
        
        # Train Tier 2 model (only on Ball-in-Play cases)
        bip_mask = y_tier1 == 2  # Ball-in-Play
        if bip_mask.sum() > 0:
            tier2_result = self._train_tier2(X[bip_mask], y_tier2[bip_mask])
        else:
            tier2_result = {'accuracy': 0.0, 'loss': 0.0}
        
        # Mark as trained
        self.is_trained = True
        
        # Update performance metrics
        self._performance_metrics.accuracy = tier1_result['accuracy']
        self._performance_metrics.training_loss = tier1_result['loss']
        
        return TrainingResult(
            success=True,
            final_accuracy=tier1_result['accuracy'],
            final_loss=tier1_result['loss'],
            training_epochs=1,  # XGBoost doesn't use epochs
            training_samples=len(training_data),
            tier1_accuracy=tier1_result['accuracy'],
            tier2_accuracy=tier2_result.get('accuracy', 0.0)
        )
    
    def _prepare_training_data(self, training_data: List[Dict]) -> Tuple[pd.DataFrame, np.ndarray, np.ndarray]:
        """Prepare training data from raw format"""
        features_list = []
        tier1_targets = []
        tier2_targets = []
        
        for example in training_data:
            # Extract features
            features = self.feature_engine.extract_features(example)
            features_list.append(features)
            
            # Extract targets
            pitch_symbol = example.get('pitch_symbol', '')
            tier1_target = self._map_symbol_to_tier1(pitch_symbol)
            tier2_target = self._map_symbol_to_tier2(pitch_symbol)
            
            tier1_targets.append(tier1_target)
            tier2_targets.append(tier2_target)
        
        X = pd.DataFrame(features_list)
        y_tier1 = np.array(tier1_targets)
        y_tier2 = np.array(tier2_targets)
        
        return X, y_tier1, y_tier2
    
    def _map_symbol_to_tier1(self, symbol: str) -> int:
        """Map pitch symbol to tier 1 class"""
        if symbol in ['B', 'J', 'W']:  # Balls
            return 0
        elif symbol in ['C', 'S', 'F', 'K', 'L', 'M', 'V']:  # Strikes
            return 1
        else:  # Ball in play
            return 2
    
    def _map_symbol_to_tier2(self, symbol: str) -> int:
        """Map pitch symbol to tier 2 class (for Ball-in-Play)"""
        symbol_map = {
            '1': 0, 'I': 0,  # Single
            '2': 1,          # Double
            '3': 2,          # Triple
            'H': 3,          # Home Run
            'X': 4,          # Out
            'E': 5,          # Error
            '1': 6           # Fielder's Choice (treated as single)
        }
        return symbol_map.get(symbol, 4)  # Default to Out
    
    def _train_tier1(self, X: pd.DataFrame, y: np.ndarray) -> Dict:
        """Train tier 1 model"""
        if self.config.cross_validation:
            # Use cross-validation
            cv_results = xgb.cv(
                self.config.tier1_params,
                xgb.DMatrix(X, label=y),
                num_boost_round=self.config.tier1_params['n_estimators'],
                nfold=self.config.cv_folds,
                early_stopping_rounds=self.config.early_stopping_rounds,
                metrics=self.config.eval_metric,
                seed=self.config.random_state
            )
            
            best_iteration = len(cv_results)
            self.tier1_model.set_params(n_estimators=best_iteration)
        
        # Train final model
        self.tier1_model.fit(X, y)
        
        # Calculate accuracy
        y_pred = self.tier1_model.predict(X)
        accuracy = (y_pred == y).mean()
        
        return {'accuracy': accuracy, 'loss': 1.0 - accuracy}
    
    def _train_tier2(self, X: pd.DataFrame, y: np.ndarray) -> Dict:
        """Train tier 2 model"""
        if self.config.cross_validation:
            # Use cross-validation
            cv_results = xgb.cv(
                self.config.tier2_params,
                xgb.DMatrix(X, label=y),
                num_boost_round=self.config.tier2_params['n_estimators'],
                nfold=self.config.cv_folds,
                early_stopping_rounds=self.config.early_stopping_rounds,
                metrics=self.config.eval_metric,
                seed=self.config.random_state
            )
            
            best_iteration = len(cv_results)
            self.tier2_model.set_params(n_estimators=best_iteration)
        
        # Train final model
        self.tier2_model.fit(X, y)
        
        # Calculate accuracy
        y_pred = self.tier2_model.predict(X)
        accuracy = (y_pred == y).mean()
        
        return {'accuracy': accuracy, 'loss': 1.0 - accuracy}
    
    def get_model_info(self) -> ModelInfo:
        """Get model information and metadata"""
        return ModelInfo(
            name="HierarchicalXGBoostModel",
            model_type="hierarchical_classification",
            algorithm="XGBoost",
            version="1.0.0",
            description="Two-tier hierarchical model: Ball/Strike/BIP → detailed outcome",
            parameters={
                'tier1_classes': len(self.TIER1_CLASSES),
                'tier2_classes': len(self.TIER2_CLASSES),
                'tier1_params': self.config.tier1_params,
                'tier2_params': self.config.tier2_params,
                'feature_engineering': self.config.feature_engineering
            },
            is_trained=self.is_trained,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
    
    def get_performance_metrics(self) -> PerformanceMetrics:
        """Get current performance metrics"""
        return self._performance_metrics
    
    def get_feature_importance(self) -> Dict[str, float]:
        """Get feature importance from tier 1 model"""
        if not self.is_trained:
            return {}
        
        importance = self.tier1_model.feature_importances_
        feature_names = self.feature_engine.get_feature_names()
        
        return dict(zip(feature_names, importance))
    
    def explain_prediction(self, context: 'PredictionContext') -> Dict:
        """Explain prediction using SHAP values"""
        if not self.is_trained:
            return {}
        
        features = self._extract_features(context)
        feature_df = pd.DataFrame([features])
        
        return self.explainer.explain(
            self.tier1_model,
            feature_df,
            feature_names=self.feature_engine.get_feature_names()
        )
    
    def save_model(self, filepath: str):
        """Save model to file"""
        model_data = {
            'tier1_model': self.tier1_model,
            'tier2_model': self.tier2_model,
            'config': self.config,
            'feature_engine': self.feature_engine,
            'explainer': self.explainer,
            'is_trained': self.is_trained,
            'performance_metrics': self._performance_metrics
        }
        
        with open(filepath, 'wb') as f:
            pickle.dump(model_data, f)
    
    def load_model(self, filepath: str):
        """Load model from file"""
        with open(filepath, 'rb') as f:
            model_data = pickle.load(f)
        
        self.tier1_model = model_data['tier1_model']
        self.tier2_model = model_data['tier2_model']
        self.config = model_data['config']
        self.feature_engine = model_data['feature_engine']
        self.explainer = model_data['explainer']
        self.is_trained = model_data['is_trained']
        self._performance_metrics = model_data['performance_metrics']


@dataclass
class TrainingResult:
    """Result of model training"""
    success: bool
    final_accuracy: float
    final_loss: float
    training_epochs: int
    training_samples: int
    tier1_accuracy: Optional[float] = None
    tier2_accuracy: Optional[float] = None
