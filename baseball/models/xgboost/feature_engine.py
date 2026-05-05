"""
Feature Engineering for XGBoost Models

Handles feature extraction, transformation, and engineering
for hierarchical XGBoost pitch prediction models.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Union
from dataclasses import dataclass


@dataclass
class FeatureConfig:
    """Configuration for feature engineering"""
    include_player_stats: bool = True
    include_game_context: bool = True
    include_recent_performance: bool = True
    include_leverage_metrics: bool = True
    interaction_features: bool = True
    polynomial_features: bool = False
    normalize_features: bool = True


class FeatureEngine:
    """
    Feature engineering engine for XGBoost models.
    
    Extracts and transforms features from pitch prediction context
    for hierarchical classification.
    """
    
    def __init__(self, config: Optional[FeatureConfig] = None):
        self.config = config or FeatureConfig()
        self.feature_names = []
        self.feature_importance = {}
        
    def extract_features(self, context: Dict) -> Dict[str, Union[int, float]]:
        """
        Extract features from prediction context.
        
        Args:
            context: Prediction context with game state, player stats, etc.
            
        Returns:
            Dictionary of engineered features
        """
        features = {}
        
        # Basic count state
        features.update(self._extract_count_features(context))
        
        # Game context
        if self.config.include_game_context:
            features.update(self._extract_game_features(context))
        
        # Player statistics
        if self.config.include_player_stats:
            features.update(self._extract_player_features(context))
        
        # Recent performance
        if self.config.include_recent_performance:
            features.update(self._extract_recent_features(context))
        
        # Leverage metrics
        if self.config.include_leverage_metrics:
            features.update(self._extract_leverage_features(context))
        
        # Interaction features
        if self.config.interaction_features:
            features.update(self._create_interaction_features(features))
        
        # Normalize features
        if self.config.normalize_features:
            features = self._normalize_features(features)
        
        # Update feature names
        self.feature_names = list(features.keys())
        
        return features
    
    def _extract_count_features(self, context: Dict) -> Dict[str, Union[int, float]]:
        """Extract basic count state features"""
        features = {}
        
        # Basic counts
        features['balls'] = int(context.get('balls', 0))
        features['strikes'] = int(context.get('strikes', 0))
        features['outs'] = int(context.get('outs', 0))
        
        # Count combinations
        features['count_balls_plus_strikes'] = features['balls'] + features['strikes']
        features['count_balls_minus_strikes'] = features['balls'] - features['strikes']
        
        # Count states (one-hot encoded)
        for balls in range(4):
            features[f'count_balls_{balls}'] = 1 if features['balls'] == balls else 0
        
        for strikes in range(3):
            features[f'count_strikes_{strikes}'] = 1 if features['strikes'] == strikes else 0
        
        # Special count states
        features['is_full_count'] = 1 if (features['balls'] == 3 and features['strikes'] == 2) else 0
        features['is_two_strike_count'] = 1 if features['strikes'] == 2 else 0
        features['is_three_ball_count'] = 1 if features['balls'] == 3 else 0
        
        return features
    
    def _extract_game_features(self, context: Dict) -> Dict[str, Union[int, float]]:
        """Extract game context features"""
        features = {}
        
        # Inning information
        features['inning'] = int(context.get('inning', 1))
        features['is_top_inning'] = int(context.get('is_top_inning', True))
        features['inning_number'] = features['inning']
        
        # Late game situations
        features['is_late_inning'] = 1 if features['inning'] >= 7 else 0
        
        # Score differential
        home_score = int(context.get('home_score', 0))
        away_score = int(context.get('away_score', 0))
        features['home_score'] = home_score
        features['away_score'] = away_score
        features['run_difference'] = home_score - away_score
        features['absolute_run_difference'] = abs(features['run_difference'])
        
        # Score states
        features['home_team_winning'] = 1 if features['run_difference'] > 0 else 0
        features['away_team_winning'] = 1 if features['run_difference'] < 0 else 0
        features['game_is_tied'] = 1 if features['run_difference'] == 0 else 0
        
        # Bases situation (if available)
        bases = context.get('bases', {})
        features['runner_on_first'] = int(bases.get('first', False))
        features['runner_on_second'] = int(bases.get('second', False))
        features['runner_on_third'] = int(bases.get('third', False))
        
        # Base runners
        features['runners_on_base'] = (features['runner_on_first'] + 
                                     features['runner_on_second'] + 
                                     features['runner_on_third'])
        features['runners_in_scoring_position'] = (features['runner_on_second'] + 
                                                  features['runner_on_third'])
        
        # Outs in inning
        features['outs_in_inning'] = features['outs']
        features['is_two_outs'] = 1 if features['outs'] == 2 else 0
        
        return features
    
    def _extract_player_features(self, context: Dict) -> Dict[str, Union[int, float]]:
        """Extract player statistics features"""
        features = {}
        
        # Pitcher statistics
        pitcher_stats = context.get('pitcher_stats', {})
        features['pitcher_era'] = float(pitcher_stats.get('era', 0.0))
        features['pitcher_whip'] = float(pitcher_stats.get('whip', 0.0))
        features['pitcher_k_rate'] = float(pitcher_stats.get('k_rate', 0.0))
        features['pitcher_bb_rate'] = float(pitcher_stats.get('bb_rate', 0.0))
        features['pitcher_hr_rate'] = float(pitcher_stats.get('hr_rate', 0.0))
        features['pitcher_avg_against'] = float(pitcher_stats.get('avg_against', 0.0))
        
        # Pitcher quality indicators
        features['pitcher_is_high_k_rate'] = 1 if features['pitcher_k_rate'] > 0.25 else 0
        features['pitcher_is_high_bb_rate'] = 1 if features['pitcher_bb_rate'] > 0.10 else 0
        features['pitcher_is_low_era'] = 1 if features['pitcher_era'] < 3.0 else 0
        
        # Batter statistics
        batter_stats = context.get('batter_stats', {})
        features['batter_avg'] = float(batter_stats.get('avg', 0.0))
        features['batter_obp'] = float(batter_stats.get('obp', 0.0))
        features['batter_slg'] = float(batter_stats.get('slg', 0.0))
        features['batter_ops'] = features['batter_obp'] + features['batter_slg']
        features['batter_k_rate'] = float(batter_stats.get('k_rate', 0.0))
        features['batter_bb_rate'] = float(batter_stats.get('bb_rate', 0.0))
        features['batter_hr_rate'] = float(batter_stats.get('hr_rate', 0.0))
        
        # Batter quality indicators
        features['batter_is_high_avg'] = 1 if features['batter_avg'] > 0.300 else 0
        features['batter_is_high_obp'] = 1 if features['batter_obp'] > 0.350 else 0
        features['batter_is_high_slg'] = 1 if features['batter_slg'] > 0.500 else 0
        features['batter_is_high_k_rate'] = 1 if features['batter_k_rate'] > 0.25 else 0
        
        # Batter handedness (if available)
        batter_hand = batter_stats.get('bats', 'R')
        features['batter_is_lefty'] = 1 if batter_hand == 'L' else 0
        features['batter_is_switch'] = 1 if batter_hand == 'S' else 0
        
        # Pitcher handedness (if available)
        pitcher_hand = pitcher_stats.get('throws', 'R')
        features['pitcher_is_lefty'] = 1 if pitcher_hand == 'L' else 0
        
        # Handedness matchups
        features['lefty_vs_lefty'] = 1 if (features['batter_is_lefty'] and features['pitcher_is_lefty']) else 0
        features['lefty_vs_righty'] = 1 if (features['batter_is_lefty'] and not features['pitcher_is_lefty']) else 0
        features['righty_vs_lefty'] = 1 if (not features['batter_is_lefty'] and features['pitcher_is_lefty']) else 0
        
        return features
    
    def _extract_recent_features(self, context: Dict) -> Dict[str, Union[int, float]]:
        """Extract recent performance features"""
        features = {}
        
        # Recent pitch sequence
        recent_pitches = context.get('recent_pitches', [])
        
        if recent_pitches:
            # Recent pitch rates (last 5 pitches)
            recent_5 = recent_pitches[-5:] if len(recent_pitches) >= 5 else recent_pitches
            
            features['recent_ball_rate_5'] = sum(1 for p in recent_5 if p in ['B', 'J', 'W']) / len(recent_5)
            features['recent_strike_rate_5'] = sum(1 for p in recent_5 if p in ['C', 'S', 'F', 'K', 'L', 'M', 'V']) / len(recent_5)
            features['recent_bip_rate_5'] = sum(1 for p in recent_5 if p not in ['B', 'J', 'W', 'C', 'S', 'F', 'K', 'L', 'M', 'V']) / len(recent_5)
            
            # Recent pitch rates (last 10 pitches)
            recent_10 = recent_pitches[-10:] if len(recent_pitches) >= 10 else recent_pitches
            
            features['recent_ball_rate_10'] = sum(1 for p in recent_10 if p in ['B', 'J', 'W']) / len(recent_10)
            features['recent_strike_rate_10'] = sum(1 for p in recent_10 if p in ['C', 'S', 'F', 'K', 'L', 'M', 'V']) / len(recent_10)
            features['recent_bip_rate_10'] = sum(1 for p in recent_10 if p not in ['B', 'J', 'W', 'C', 'S', 'F', 'K', 'L', 'M', 'V']) / len(recent_10)
            
            # Pitch sequence patterns
            features['consecutive_balls'] = self._count_consecutive(recent_pitches, ['B', 'J', 'W'])
            features['consecutive_strikes'] = self._count_consecutive(recent_pitches, ['C', 'S', 'F', 'K', 'L', 'M', 'V'])
            
            # Recent outcome patterns
            features['recent_hits_rate'] = sum(1 for p in recent_10 if p in ['1', '2', '3', 'H']) / len(recent_10)
            features['recent_strikeouts_rate'] = sum(1 for p in recent_10 if p in ['K', 'L', 'M']) / len(recent_10)
        else:
            # Default values if no recent pitches
            features['recent_ball_rate_5'] = 0.33  # League average
            features['recent_strike_rate_5'] = 0.44
            features['recent_bip_rate_5'] = 0.23
            features['recent_ball_rate_10'] = 0.33
            features['recent_strike_rate_10'] = 0.44
            features['recent_bip_rate_10'] = 0.23
            features['consecutive_balls'] = 0
            features['consecutive_strikes'] = 0
            features['recent_hits_rate'] = 0.23
            features['recent_strikeouts_rate'] = 0.08
        
        return features
    
    def _extract_leverage_features(self, context: Dict) -> Dict[str, Union[int, float]]:
        """Extract leverage and situation importance features"""
        features = {}
        
        # Leverage index
        features['leverage_index'] = float(context.get('leverage_index', 1.0))
        features['is_high_leverage'] = 1 if features['leverage_index'] > 2.0 else 0
        features['is_medium_leverage'] = 1 if 1.0 < features['leverage_index'] <= 2.0 else 0
        features['is_low_leverage'] = 1 if features['leverage_index'] <= 1.0 else 0
        
        # Game state importance
        home_score = int(context.get('home_score', 0))
        away_score = int(context.get('away_score', 0))
        inning = int(context.get('inning', 1))
        outs = int(context.get('outs', 0))
        
        # Close game situations
        run_diff = abs(home_score - away_score)
        features['is_close_game'] = 1 if run_diff <= 2 else 0
        
        # Late and close
        features['is_late_and_close'] = 1 if (inning >= 7 and run_diff <= 2) else 0
        
        # High pressure situations
        features['is_high_pressure'] = 1 if (inning >= 8 and run_diff <= 1 and outs <= 1) else 0
        
        # Runners in scoring position with less than 2 outs
        bases = context.get('bases', {})
        runners_scoring = int(bases.get('second', False)) + int(bases.get('third', False))
        features['risp_less_than_2_outs'] = 1 if (runners_scoring > 0 and outs < 2) else 0
        
        return features
    
    def _create_interaction_features(self, features: Dict) -> Dict[str, Union[int, float]]:
        """Create interaction features between existing features"""
        interaction_features = {}
        
        # Count x Player interactions
        if 'strikes' in features and 'batter_k_rate' in features:
            interaction_features['strikes_x_batter_k_rate'] = features['strikes'] * features['batter_k_rate']
        
        if 'balls' in features and 'batter_bb_rate' in features:
            interaction_features['balls_x_batter_bb_rate'] = features['balls'] * features['batter_bb_rate']
        
        # Score x Inning interactions
        if 'run_difference' in features and 'inning' in features:
            interaction_features['run_diff_x_inning'] = features['run_difference'] * features['inning']
        
        # Pitcher x Batter quality interactions
        if 'pitcher_k_rate' in features and 'batter_k_rate' in features:
            interaction_features['pitcher_k_rate_x_batter_k_rate'] = features['pitcher_k_rate'] * features['batter_k_rate']
        
        if 'pitcher_era' in features and 'batter_avg' in features:
            interaction_features['pitcher_era_x_batter_avg'] = features['pitcher_era'] * features['batter_avg']
        
        # Leverage x Outs interactions
        if 'leverage_index' in features and 'outs' in features:
            interaction_features['leverage_x_outs'] = features['leverage_index'] * features['outs']
        
        return interaction_features
    
    def _normalize_features(self, features: Dict) -> Dict:
        """Normalize continuous features to [0, 1] range"""
        normalized = features.copy()
        
        # Define normalization ranges for key features
        normalization_ranges = {
            'pitcher_era': (0.0, 10.0),
            'pitcher_whip': (0.0, 2.0),
            'pitcher_k_rate': (0.0, 0.4),
            'pitcher_bb_rate': (0.0, 0.2),
            'batter_avg': (0.0, 0.4),
            'batter_obp': (0.0, 0.5),
            'batter_slg': (0.0, 0.8),
            'batter_k_rate': (0.0, 0.4),
            'batter_bb_rate': (0.0, 0.2),
            'leverage_index': (0.0, 5.0),
            'run_difference': (-10.0, 10.0)
        }
        
        for feature, (min_val, max_val) in normalization_ranges.items():
            if feature in normalized:
                value = normalized[feature]
                if max_val > min_val:
                    normalized[feature] = (value - min_val) / (max_val - min_val)
                else:
                    normalized[feature] = 0.0
        
        return normalized
    
    def _count_consecutive(self, sequence: List[str], target_symbols: List[str]) -> int:
        """Count consecutive occurrences of target symbols at end of sequence"""
        if not sequence:
            return 0
        
        count = 0
        for pitch in reversed(sequence):
            if pitch in target_symbols:
                count += 1
            else:
                break
        
        return count
    
    def get_feature_names(self) -> List[str]:
        """Get list of feature names"""
        return self.feature_names.copy()
    
    def get_feature_importance(self, model) -> Dict[str, float]:
        """Get feature importance from trained model"""
        if hasattr(model, 'feature_importances_'):
            importance = model.feature_importances_
            feature_names = self.get_feature_names()
            
            if len(importance) == len(feature_names):
                self.feature_importance = dict(zip(feature_names, importance))
                return self.feature_importance
        
        return {}
    
    def get_top_features(self, n: int = 10) -> List[Tuple[str, float]]:
        """Get top n most important features"""
        if not self.feature_importance:
            return []
        
        sorted_features = sorted(
            self.feature_importance.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        return sorted_features[:n]
