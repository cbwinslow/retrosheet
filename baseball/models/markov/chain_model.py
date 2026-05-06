"""
Markov Chain Model for Pitch Prediction

Implements transition probability-based pitch prediction using
Markov chains with count state and pitcher-specific modeling.
"""

import asyncio
import numpy as np
import pandas as pd
from typing import List, Dict, Optional, Tuple, Union
from dataclasses import dataclass
from datetime import datetime
import pickle
import json

from baseball.models.base import BaseModel, ModelResult
from baseball.models.markov.transition_matrix import TransitionMatrix
from baseball.models.markov.state_analyzer import StateAnalyzer


@dataclass
class MarkovConfig:
    """Configuration for Markov chain model"""
    order: int = 1  # First-order Markov chain
    include_count_state: bool = True
    include_pitcher_specific: bool = True
    include_batter_specific: bool = True
    smoothing_factor: float = 0.1  # Laplace smoothing
    min_transitions: int = 5  # Minimum transitions for reliable probabilities
    use_weighted_transitions: bool = True
    recency_weight: float = 0.1  # Weight for recent transitions


class MarkovChainModel(BaseModel):
    """
    Markov chain model for pitch prediction.
    
    Uses transition probabilities between pitch types and count states
    to predict next pitch outcomes.
    """
    
    def __init__(self, config: Optional[MarkovConfig] = None):
        self.config = config or MarkovConfig()
        self.transition_matrix = TransitionMatrix()
        self.state_analyzer = StateAnalyzer()
        self.is_trained = False
        self._performance_metrics = {}
        
        # Model statistics
        self.total_transitions = 0
        self.unique_pitches = set()
        self.pitch_counts = {}
        
    async def predict(self, context: 'PredictionContext') -> ModelPrediction:
        """
        Predict next pitch using Markov chain probabilities.
        
        Args:
            context: Prediction context with current state and history
            
        Returns:
            ModelPrediction with pitch probabilities and confidence
        """
        if not self.is_trained:
            raise ValueError("Model must be trained before making predictions")
        
        # Extract current state
        current_state = self._extract_current_state(context)
        
        # Get transition probabilities
        predictions = self._get_transition_predictions(current_state, context)
        
        # Calculate confidence
        confidence = self._calculate_markov_confidence(predictions, current_state)
        
        return ModelPrediction(
            predictions=predictions,
            confidence=confidence,
            model_info=self.get_model_info(),
            timestamp=datetime.now()
        )
    
    def _extract_current_state(self, context: 'PredictionContext') -> Dict[str, Union[str, int]]:
        """Extract current state for Markov prediction"""
        state = {}
        
        # Count state
        if self.config.include_count_state:
            state['balls'] = context.get('balls', 0)
            state['strikes'] = context.get('strikes', 0)
            state['count_label'] = f"{state['balls']}-{state['strikes']}"
        
        # Recent pitches (for higher-order chains)
        recent_pitches = context.get('recent_pitches', [])
        if self.config.order > 1 and len(recent_pitches) >= self.config.order:
            state['recent_sequence'] = tuple(recent_pitches[-self.config.order:])
        
        # Pitcher and batter context
        if self.config.include_pitcher_specific:
            state['pitcher_id'] = context.get('pitcher_id', 0)
        
        if self.config.include_batter_specific:
            state['batter_id'] = context.get('batter_id', 0)
        
        return state
    
    def _get_transition_predictions(self, current_state: Dict, context: 'PredictionContext') -> List[Dict]:
        """Get predictions based on transition probabilities"""
        predictions = []
        
        # Try specific transitions first
        if self.config.include_pitcher_specific:
            pitcher_predictions = self._get_pitcher_specific_predictions(current_state, context)
            if pitcher_predictions:
                predictions.extend(pitcher_predictions)
        
        if self.config.include_batter_specific:
            batter_predictions = self._get_batter_specific_predictions(current_state, context)
            if batter_predictions:
                predictions.extend(batter_predictions)
        
        # Fall back to general transitions
        general_predictions = self._get_general_predictions(current_state)
        predictions.extend(general_predictions)
        
        # Sort by probability and remove duplicates
        unique_predictions = {}
        for pred in predictions:
            symbol = pred['pitch_symbol']
            if symbol not in unique_predictions or pred['probability'] > unique_predictions[symbol]['probability']:
                unique_predictions[symbol] = pred
        
        return sorted(unique_predictions.values(), key=lambda x: x['probability'], reverse=True)
    
    def _get_pitcher_specific_predictions(self, current_state: Dict, context: 'PredictionContext') -> List[Dict]:
        """Get pitcher-specific transition predictions"""
        pitcher_id = current_state.get('pitcher_id', 0)
        
        if pitcher_id == 0:
            return []
        
        # Get pitcher-specific transitions
        if self.config.include_count_state:
            count_label = current_state.get('count_label', '0-0')
            transitions = self.transition_matrix.get_pitcher_count_transitions(pitcher_id, count_label)
        else:
            transitions = self.transition_matrix.get_pitcher_transitions(pitcher_id)
        
        if not transitions:
            return []
        
        # Convert to predictions
        predictions = []
        for pitch_symbol, prob in transitions.items():
            if prob > 0.01:  # Only include meaningful probabilities
                predictions.append({
                    'pitch_symbol': pitch_symbol,
                    'probability': float(prob),
                    'source': 'pitcher_specific',
                    'pitcher_id': pitcher_id
                })
        
        return predictions
    
    def _get_batter_specific_predictions(self, current_state: Dict, context: 'PredictionContext') -> List[Dict]:
        """Get batter-specific transition predictions"""
        batter_id = current_state.get('batter_id', 0)
        
        if batter_id == 0:
            return []
        
        # Get batter-specific transitions
        if self.config.include_count_state:
            count_label = current_state.get('count_label', '0-0')
            transitions = self.transition_matrix.get_batter_count_transitions(batter_id, count_label)
        else:
            transitions = self.transition_matrix.get_batter_transitions(batter_id)
        
        if not transitions:
            return []
        
        # Convert to predictions
        predictions = []
        for pitch_symbol, prob in transitions.items():
            if prob > 0.01:  # Only include meaningful probabilities
                predictions.append({
                    'pitch_symbol': pitch_symbol,
                    'probability': float(prob),
                    'source': 'batter_specific',
                    'batter_id': batter_id
                })
        
        return predictions
    
    def _get_general_predictions(self, current_state: Dict) -> List[Dict]:
        """Get general transition predictions"""
        transitions = []
        
        if self.config.include_count_state:
            count_label = current_state.get('count_label', '0-0')
            count_transitions = self.transition_matrix.get_count_transitions(count_label)
            
            if count_transitions:
                for pitch_symbol, prob in count_transitions.items():
                    transitions.append({
                        'pitch_symbol': pitch_symbol,
                        'probability': float(prob),
                        'source': 'count_general',
                        'count_state': count_label
                    })
        
        # General pitch transitions (if not using count state)
        if not self.config.include_count_state:
            recent_sequence = current_state.get('recent_sequence', ())
            if len(recent_sequence) >= self.config.order:
                seq_transitions = self.transition_matrix.get_sequence_transitions(recent_sequence)
                
                for pitch_symbol, prob in seq_transitions.items():
                    transitions.append({
                        'pitch_symbol': pitch_symbol,
                        'probability': float(prob),
                        'source': 'sequence_general',
                        'sequence': recent_sequence
                    })
        
        return transitions
    
    def _calculate_markov_confidence(self, predictions: List[Dict], current_state: Dict) -> float:
        """Calculate confidence based on Markov prediction quality"""
        if not predictions:
            return 0.0
        
        # Base confidence from top prediction
        top_confidence = predictions[0].get('probability', 0.0)
        
        # Adjust based on data reliability
        total_transitions = self.transition_matrix.get_total_transitions()
        
        if total_transitions > 0:
            # Higher confidence with more transition data
            data_factor = min(1.0, total_transitions / 1000.0)
        else:
            data_factor = 0.1
        
        # Adjust based on prediction source specificity
        source = predictions[0].get('source', 'general')
        if source == 'pitcher_specific':
            specificity_factor = 1.2
        elif source == 'batter_specific':
            specificity_factor = 1.1
        elif source == 'count_general':
            specificity_factor = 1.0
        else:
            specificity_factor = 0.8
        
        return top_confidence * data_factor * specificity_factor
    
    async def train(self, training_data: List[Dict]) -> 'TrainingResult':
        """
        Train Markov chain model on pitch sequence data.
        
        Args:
            training_data: List of training examples with pitch sequences
            
        Returns:
            TrainingResult with training metrics
        """
        # Initialize transition tracking
        self.transition_matrix.clear()
        self.total_transitions = 0
        self.unique_pitches = set()
        self.pitch_counts = {}
        
        # Process training data
        for example in training_data:
            self._process_training_example(example)
        
        # Apply smoothing
        if self.config.smoothing_factor > 0:
            self._apply_smoothing()
        
        # Apply recency weighting if enabled
        if self.config.use_weighted_transitions:
            self._apply_recency_weighting()
        
        # Mark as trained
        self.is_trained = True
        
        # Calculate performance metrics
        accuracy = self._calculate_training_accuracy(training_data)
        
        self._performance_metrics.accuracy = accuracy
        self._performance_metrics.training_loss = 1.0 - accuracy
        
        return TrainingResult(
            success=True,
            final_accuracy=accuracy,
            final_loss=1.0 - accuracy,
            training_epochs=1,  # Markov chains don't use epochs
            training_samples=len(training_data),
            total_transitions=self.total_transitions,
            unique_pitches=len(self.unique_pitches)
        )
    
    def _process_training_example(self, example: Dict):
        """Process a single training example"""
        pitch_sequence = example.get('pitch_sequence', [])
        pitcher_id = example.get('pitcher_id', 0)
        batter_id = example.get('batter_id', 0)
        
        # Process transitions
        for i in range(len(pitch_sequence) - 1):
            current_pitch = pitch_sequence[i]
            next_pitch = pitch_sequence[i + 1]
            
            # Count state (if available)
            count_state = None
            if 'count_state' in example:
                count_state = example['count_state'][i]
            
            # Record transition
            self._record_transition(
                current_pitch, next_pitch, count_state,
                pitcher_id, batter_id
            )
            
            # Track statistics
            self.unique_pitches.add(current_pitch)
            self.unique_pitches.add(next_pitch)
            self.pitch_counts[current_pitch] = self.pitch_counts.get(current_pitch, 0) + 1
            self.pitch_counts[next_pitch] = self.pitch_counts.get(next_pitch, 0) + 1
            self.total_transitions += 1
    
    def _record_transition(self, current_pitch: str, next_pitch: str, 
                       count_state: Optional[str], pitcher_id: int, batter_id: int):
        """Record a transition in the transition matrix"""
        # General transition
        if self.config.order == 1:
            self.transition_matrix.add_transition(current_pitch, next_pitch)
        
        # Count-specific transitions
        if self.config.include_count_state and count_state:
            self.transition_matrix.add_count_transition(
                current_pitch, next_pitch, count_state
            )
        
        # Pitcher-specific transitions
        if self.config.include_pitcher_specific and pitcher_id != 0:
            self.transition_matrix.add_pitcher_transition(
                current_pitch, next_pitch, pitcher_id
            )
            
            if self.config.include_count_state and count_state:
                self.transition_matrix.add_pitcher_count_transition(
                    current_pitch, next_pitch, pitcher_id, count_state
                )
        
        # Batter-specific transitions
        if self.config.include_batter_specific and batter_id != 0:
            self.transition_matrix.add_batter_transition(
                current_pitch, next_pitch, batter_id
            )
            
            if self.config.include_count_state and count_state:
                self.transition_matrix.add_batter_count_transition(
                    current_pitch, next_pitch, batter_id, count_state
                )
    
    def _apply_smoothing(self):
        """Apply Laplace smoothing to transition probabilities"""
        self.transition_matrix.apply_smoothing(self.config.smoothing_factor)
    
    def _apply_recency_weighting(self):
        """Apply recency weighting to transitions"""
        self.transition_matrix.apply_recency_weighting(self.config.recency_weight)
    
    def _calculate_training_accuracy(self, training_data: List[Dict]) -> float:
        """Calculate training accuracy using leave-one-out validation"""
        correct = 0
        total = 0
        
        for example in training_data:
            pitch_sequence = example.get('pitch_sequence', [])
            pitcher_id = example.get('pitcher_id', 0)
            batter_id = example.get('batter_id', 0)
            
            for i in range(len(pitch_sequence) - 1):
                current_pitch = pitch_sequence[i]
                next_pitch = pitch_sequence[i + 1]
                
                # Get prediction
                context = {
                    'recent_pitches': pitch_sequence[:i+1],
                    'pitcher_id': pitcher_id,
                    'batter_id': batter_id
                }
                
                if 'count_state' in example:
                    context['balls'] = example['count_state'][i].get('balls', 0)
                    context['strikes'] = example['count_state'][i].get('strikes', 0)
                
                prediction = self._predict_single_pitch(context)
                
                if prediction and prediction == next_pitch:
                    correct += 1
                total += 1
        
        return correct / total if total > 0 else 0.0
    
    def _predict_single_pitch(self, context: Dict) -> Optional[str]:
        """Predict single pitch for accuracy calculation"""
        current_state = self._extract_current_state(context)
        predictions = self._get_transition_predictions(current_state, context)
        
        return predictions[0]['pitch_symbol'] if predictions else None
    
    def get_model_info(self) -> ModelInfo:
        """Get model information and metadata"""
        return ModelInfo(
            name="MarkovChainModel",
            model_type="transition_probability",
            algorithm="Markov Chain",
            version="1.0.0",
            description="Markov chain model with count state and player-specific transitions",
            parameters={
                'order': self.config.order,
                'include_count_state': self.config.include_count_state,
                'include_pitcher_specific': self.config.include_pitcher_specific,
                'include_batter_specific': self.config.include_batter_specific,
                'smoothing_factor': self.config.smoothing_factor,
                'min_transitions': self.config.min_transitions,
                'total_transitions': self.total_transitions,
                'unique_pitches': len(self.unique_pitches)
            },
            is_trained=self.is_trained,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
    
    def get_performance_metrics(self) -> dict:
        """Get current performance metrics"""
        return self._performance_metrics
    
    def get_transition_matrix(self) -> Dict:
        """Get the transition matrix for analysis"""
        return self.transition_matrix.get_matrix_copy()
    
    def get_pitch_statistics(self) -> Dict[str, Union[int, float]]:
        """Get pitch frequency statistics"""
        total = sum(self.pitch_counts.values())
        
        if total == 0:
            return {}
        
        return {
            pitch: count / total 
            for pitch, count in self.pitch_counts.items()
        }
    
    def analyze_transitions(self, max_results: int = 20) -> List[Dict]:
        """Analyze most common transitions"""
        return self.transition_matrix.get_top_transitions(max_results)
    
    def save_model(self, filepath: str):
        """Save model to file"""
        model_data = {
            'transition_matrix': self.transition_matrix.get_matrix_copy(),
            'config': self.config,
            'is_trained': self.is_trained,
            'performance_metrics': self._performance_metrics,
            'total_transitions': self.total_transitions,
            'unique_pitches': list(self.unique_pitches),
            'pitch_counts': self.pitch_counts
        }
        
        with open(filepath, 'wb') as f:
            pickle.dump(model_data, f)
    
    def load_model(self, filepath: str):
        """Load model from file"""
        with open(filepath, 'rb') as f:
            model_data = pickle.load(f)
        
        self.transition_matrix.load_matrix(model_data['transition_matrix'])
        self.config = model_data['config']
        self.is_trained = model_data['is_trained']
        self._performance_metrics = model_data['performance_metrics']
        self.total_transitions = model_data['total_transitions']
        self.unique_pitches = set(model_data['unique_pitches'])
        self.pitch_counts = model_data['pitch_counts']


@dataclass
class TrainingResult:
    """Result of model training"""
    success: bool
    final_accuracy: float
    final_loss: float
    training_epochs: int
    training_samples: int
    total_transitions: Optional[int] = None
    unique_pitches: Optional[int] = None
