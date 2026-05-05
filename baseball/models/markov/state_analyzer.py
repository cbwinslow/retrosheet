"""
State Analyzer for Markov Chain Models

Analyzes pitch sequences and count states to provide insights
for Markov chain pitch prediction models.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Union, Any
from dataclasses import dataclass
import json


@dataclass
class StateAnalysis:
    """Results of state analysis"""
    state_type: str
    frequency: float
    transition_entropy: float
    predictability: float
    common_outcomes: List[Tuple[str, float]]
    analysis_timestamp: str


class StateAnalyzer:
    """
    Analyzer for Markov chain states and transitions.
    
    Provides statistical analysis of pitch sequences, count states,
    and transition patterns for model insights and validation.
    """
    
    def __init__(self):
        self.analysis_cache = {}
        self.pitch_symbols = set()
        
    def analyze_count_state(self, count_label: str, transitions: Dict[str, Dict[str, int]]) -> StateAnalysis:
        """Analyze a specific count state"""
        if count_label in self.analysis_cache:
            return self.analysis_cache[count_label]
        
        if count_label not in transitions:
            return StateAnalysis(
                state_type=count_label,
                frequency=0.0,
                transition_entropy=0.0,
                predictability=0.0,
                common_outcomes=[],
                analysis_timestamp=""
            )
        
        # Calculate metrics
        frequency = self._calculate_state_frequency(count_label, transitions)
        entropy = self._calculate_transition_entropy(transitions[count_label])
        predictability = self._calculate_predictability(transitions[count_label])
        common_outcomes = self._get_common_outcomes(transitions[count_label])
        
        analysis = StateAnalysis(
            state_type=count_label,
            frequency=frequency,
            transition_entropy=entropy,
            predictability=predictability,
            common_outcomes=common_outcomes,
            analysis_timestamp=pd.Timestamp.now().isoformat()
        )
        
        self.analysis_cache[count_label] = analysis
        return analysis
    
    def analyze_pitch_sequence(self, sequence: Tuple[str, ...], 
                             transitions: Dict[Tuple[str, ...], Dict[str, int]]) -> StateAnalysis:
        """Analyze a pitch sequence pattern"""
        sequence_key = str(sequence)
        
        if sequence_key in self.analysis_cache:
            return self.analysis_cache[sequence_key]
        
        if sequence not in transitions:
            return StateAnalysis(
                state_type=f"sequence_{sequence_key}",
                frequency=0.0,
                transition_entropy=0.0,
                predictability=0.0,
                common_outcomes=[],
                analysis_timestamp=""
            )
        
        # Calculate metrics
        frequency = self._calculate_sequence_frequency(sequence, transitions)
        entropy = self._calculate_transition_entropy(transitions[sequence])
        predictability = self._calculate_predictability(transitions[sequence])
        common_outcomes = self._get_common_outcomes(transitions[sequence])
        
        analysis = StateAnalysis(
            state_type=f"sequence_{sequence_key}",
            frequency=frequency,
            transition_entropy=entropy,
            predictability=predictability,
            common_outcomes=common_outcomes,
            analysis_timestamp=pd.Timestamp.now().isoformat()
        )
        
        self.analysis_cache[sequence_key] = analysis
        return analysis
    
    def analyze_player_patterns(self, player_id: int, player_type: str,
                               transitions: Dict[int, Dict[str, Dict[str, int]]]) -> Dict[str, Any]:
        """Analyze player-specific patterns"""
        if player_id not in transitions:
            return {}
        
        player_transitions = transitions[player_id]
        
        # Overall analysis
        overall_entropy = self._calculate_transition_entropy(player_transitions)
        overall_predictability = self._calculate_predictability(player_transitions)
        
        # Most common transitions
        common_transitions = self._get_common_outcomes(player_transitions)
        
        # Pitch type preferences
        pitch_preferences = self._analyze_pitch_preferences(player_transitions)
        
        # State-specific analysis
        state_analysis = {}
        for from_pitch, to_transitions in player_transitions.items():
            state_analysis[from_pitch] = {
                'entropy': self._calculate_transition_entropy(to_transitions),
                'predictability': self._calculate_predictability(to_transitions),
                'common_outcomes': self._get_common_outcomes(to_transitions)
            }
        
        return {
            'player_id': player_id,
            'player_type': player_type,
            'overall_entropy': overall_entropy,
            'overall_predictability': overall_predictability,
            'common_transitions': common_transitions,
            'pitch_preferences': pitch_preferences,
            'state_analysis': state_analysis,
            'analysis_timestamp': pd.Timestamp.now().isoformat()
        }
    
    def _calculate_state_frequency(self, state: str, transitions: Dict[str, Dict[str, int]]) -> float:
        """Calculate frequency of a state"""
        total_transitions = sum(
            sum(to_transitions.values()) 
            for to_transitions in transitions.values()
        )
        
        if total_transitions == 0:
            return 0.0
        
        state_transitions = sum(
            sum(to_transitions.values()) 
            for from_pitch, to_transitions in transitions.items()
            if from_pitch == state or any(state in str(k) for k in transitions.keys())
        )
        
        return state_transitions / total_transitions
    
    def _calculate_sequence_frequency(self, sequence: Tuple[str, ...], 
                                    transitions: Dict[Tuple[str, ...], Dict[str, int]]) -> float:
        """Calculate frequency of a sequence"""
        total_transitions = sum(
            sum(to_transitions.values()) 
            for to_transitions in transitions.values()
        )
        
        if total_transitions == 0:
            return 0.0
        
        sequence_transitions = sum(transitions[sequence].values()) if sequence in transitions else 0
        
        return sequence_transitions / total_transitions
    
    def _calculate_transition_entropy(self, transitions: Dict[str, int]) -> float:
        """Calculate Shannon entropy of transitions"""
        if not transitions:
            return 0.0
        
        total = sum(transitions.values())
        if total == 0:
            return 0.0
        
        entropy = 0.0
        for count in transitions.values():
            if count > 0:
                probability = count / total
                entropy -= probability * np.log2(probability)
        
        return entropy
    
    def _calculate_predictability(self, transitions: Dict[str, int]) -> float:
        """Calculate predictability (1 - normalized entropy)"""
        if not transitions:
            return 0.0
        
        entropy = self._calculate_transition_entropy(transitions)
        max_entropy = np.log2(len(transitions))
        
        if max_entropy == 0:
            return 1.0
        
        return 1.0 - (entropy / max_entropy)
    
    def _get_common_outcomes(self, transitions: Dict[str, int], top_n: int = 5) -> List[Tuple[str, float]]:
        """Get most common transition outcomes"""
        if not transitions:
            return []
        
        total = sum(transitions.values())
        if total == 0:
            return []
        
        # Sort by frequency
        sorted_transitions = sorted(
            transitions.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        # Convert to probabilities and return top N
        return [
            (pitch, count / total)
            for pitch, count in sorted_transitions[:top_n]
        ]
    
    def _analyze_pitch_preferences(self, transitions: Dict[str, Dict[str, int]]) -> Dict[str, float]:
        """Analyze pitch type preferences"""
        pitch_counts = {}
        
        for from_pitch, to_transitions in transitions.items():
            for to_pitch, count in to_transitions.items():
                pitch_counts[to_pitch] = pitch_counts.get(to_pitch, 0) + count
        
        total = sum(pitch_counts.values())
        if total == 0:
            return {}
        
        return {
            pitch: count / total
            for pitch, count in pitch_counts.items()
        }
    
    def compare_states(self, state1: str, state2: str, 
                      transitions: Dict[str, Dict[str, int]]) -> Dict[str, Any]:
        """Compare two states"""
        analysis1 = self.analyze_count_state(state1, transitions)
        analysis2 = self.analyze_count_state(state2, transitions)
        
        # Get transition distributions
        dist1 = transitions.get(state1, {})
        dist2 = transitions.get(state2, {})
        
        # Calculate similarity metrics
        jaccard_similarity = self._calculate_jaccard_similarity(dist1, dist2)
        kl_divergence = self._calculate_kl_divergence(dist1, dist2)
        
        return {
            'state1': state1,
            'state2': state2,
            'analysis1': {
                'frequency': analysis1.frequency,
                'entropy': analysis1.transition_entropy,
                'predictability': analysis1.predictability
            },
            'analysis2': {
                'frequency': analysis2.frequency,
                'entropy': analysis2.transition_entropy,
                'predictability': analysis2.predictability
            },
            'similarity_metrics': {
                'jaccard_similarity': jaccard_similarity,
                'kl_divergence': kl_divergence
            },
            'comparison_timestamp': pd.Timestamp.now().isoformat()
        }
    
    def _calculate_jaccard_similarity(self, dist1: Dict[str, int], dist2: Dict[str, int]) -> float:
        """Calculate Jaccard similarity between two distributions"""
        set1 = set(dist1.keys())
        set2 = set(dist2.keys())
        
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        
        return intersection / union if union > 0 else 0.0
    
    def _calculate_kl_divergence(self, dist1: Dict[str, int], dist2: Dict[str, int]) -> float:
        """Calculate KL divergence between two distributions"""
        if not dist1 or not dist2:
            return float('inf')
        
        # Convert to probabilities
        total1 = sum(dist1.values())
        total2 = sum(dist2.values())
        
        if total1 == 0 or total2 == 0:
            return float('inf')
        
        prob1 = {k: v / total1 for k, v in dist1.items()}
        prob2 = {k: v / total2 for k, v in dist2.items()}
        
        # Calculate KL divergence
        kl_div = 0.0
        for pitch, p1 in prob1.items():
            p2 = prob2.get(pitch, 0)
            if p1 > 0 and p2 > 0:
                kl_div += p1 * np.log2(p1 / p2)
            elif p1 > 0 and p2 == 0:
                kl_div = float('inf')
                break
        
        return kl_div
    
    def identify_anomalous_transitions(self, transitions: Dict[str, Dict[str, int]], 
                                     threshold: float = 2.0) -> List[Dict[str, Any]]:
        """Identify anomalous transitions using statistical methods"""
        anomalies = []
        
        # Calculate overall transition statistics
        all_transitions = {}
        for from_pitch, to_transitions in transitions.items():
            for to_pitch, count in to_transitions.items():
                all_transitions[(from_pitch, to_pitch)] = count
        
        if not all_transitions:
            return anomalies
        
        # Calculate mean and standard deviation
        counts = list(all_transitions.values())
        mean_count = np.mean(counts)
        std_count = np.std(counts)
        
        # Identify anomalies (more than threshold standard deviations from mean)
        for (from_pitch, to_pitch), count in all_transitions.items():
            z_score = (count - mean_count) / std_count if std_count > 0 else 0
            
            if abs(z_score) > threshold:
                anomalies.append({
                    'from_pitch': from_pitch,
                    'to_pitch': to_pitch,
                    'count': count,
                    'z_score': z_score,
                    'anomaly_type': 'high_frequency' if z_score > threshold else 'low_frequency'
                })
        
        return sorted(anomalies, key=lambda x: abs(x['z_score']), reverse=True)
    
    def generate_state_report(self, transitions: Dict[str, Dict[str, int]]) -> Dict[str, Any]:
        """Generate comprehensive state analysis report"""
        # Analyze all count states
        state_analyses = {}
        for count_label in transitions.keys():
            state_analyses[count_label] = self.analyze_count_state(count_label, transitions)
        
        # Overall statistics
        total_transitions = sum(
            sum(to_transitions.values()) 
            for to_transitions in transitions.values()
        )
        
        # Most predictable states
        predictable_states = sorted(
            [(state, analysis.predictability) for state, analysis in state_analyses.items()],
            key=lambda x: x[1],
            reverse=True
        )
        
        # Most unpredictable states
        unpredictable_states = sorted(
            [(state, analysis.transition_entropy) for state, analysis in state_analyses.items()],
            key=lambda x: x[1],
            reverse=True
        )
        
        # Anomalous transitions
        anomalies = self.identify_anomalous_transitions(transitions)
        
        return {
            'total_transitions': total_transitions,
            'total_states': len(state_analyses),
            'state_analyses': state_analyses,
            'most_predictable_states': predictable_states[:5],
            'most_unpredictable_states': unpredictable_states[:5],
            'anomalous_transitions': anomalies[:10],
            'report_timestamp': pd.Timestamp.now().isoformat()
        }
    
    def clear_cache(self):
        """Clear analysis cache"""
        self.analysis_cache.clear()
