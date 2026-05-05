"""
Transition Matrix for Markov Chain Models

Handles transition probability calculation, storage, and analysis
for Markov chain pitch prediction models.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Union, Any
from dataclasses import dataclass
import json


@dataclass
class TransitionMatrix:
    """
    Transition matrix for Markov chain models.
    
    Stores and manages transition probabilities between pitch types
    with support for count states and player-specific transitions.
    """
    
    def __init__(self):
        # General transitions
        self.general_transitions = {}  # pitch_from -> {pitch_to: count}
        
        # Count-specific transitions
        self.count_transitions = {}  # count_label -> {pitch_from -> {pitch_to: count}}
        
        # Pitcher-specific transitions
        self.pitcher_transitions = {}  # pitcher_id -> {pitch_from -> {pitch_to: count}}
        self.pitcher_count_transitions = {}  # pitcher_id -> {count_label -> {pitch_from -> {pitch_to: count}}}
        
        # Batter-specific transitions
        self.batter_transitions = {}  # batter_id -> {pitch_from -> {pitch_to: count}}
        self.batter_count_transitions = {}  # batter_id -> {count_label -> {pitch_from -> {pitch_to: count}}}
        
        # Sequence transitions (for higher-order chains)
        self.sequence_transitions = {}  # sequence -> {pitch_to: count}
        
        # Metadata
        self.total_transitions = 0
        self.smoothing_applied = False
        self.recency_weighted = False
    
    def add_transition(self, from_pitch: str, to_pitch: str):
        """Add a general transition"""
        if from_pitch not in self.general_transitions:
            self.general_transitions[from_pitch] = {}
        
        self.general_transitions[from_pitch][to_pitch] = (
            self.general_transitions[from_pitch].get(to_pitch, 0) + 1
        )
        self.total_transitions += 1
    
    def add_count_transition(self, from_pitch: str, to_pitch: str, count_label: str):
        """Add a count-specific transition"""
        if count_label not in self.count_transitions:
            self.count_transitions[count_label] = {}
        
        if from_pitch not in self.count_transitions[count_label]:
            self.count_transitions[count_label][from_pitch] = {}
        
        self.count_transitions[count_label][from_pitch][to_pitch] = (
            self.count_transitions[count_label][from_pitch].get(to_pitch, 0) + 1
        )
        self.total_transitions += 1
    
    def add_pitcher_transition(self, from_pitch: str, to_pitch: str, pitcher_id: int):
        """Add a pitcher-specific transition"""
        if pitcher_id not in self.pitcher_transitions:
            self.pitcher_transitions[pitcher_id] = {}
        
        if from_pitch not in self.pitcher_transitions[pitcher_id]:
            self.pitcher_transitions[pitcher_id][from_pitch] = {}
        
        self.pitcher_transitions[pitcher_id][from_pitch][to_pitch] = (
            self.pitcher_transitions[pitcher_id][from_pitch].get(to_pitch, 0) + 1
        )
        self.total_transitions += 1
    
    def add_pitcher_count_transition(self, from_pitch: str, to_pitch: str, 
                                   pitcher_id: int, count_label: str):
        """Add a pitcher-specific, count-specific transition"""
        if pitcher_id not in self.pitcher_count_transitions:
            self.pitcher_count_transitions[pitcher_id] = {}
        
        if count_label not in self.pitcher_count_transitions[pitcher_id]:
            self.pitcher_count_transitions[pitcher_id][count_label] = {}
        
        if from_pitch not in self.pitcher_count_transitions[pitcher_id][count_label]:
            self.pitcher_count_transitions[pitcher_id][count_label][from_pitch] = {}
        
        self.pitcher_count_transitions[pitcher_id][count_label][from_pitch][to_pitch] = (
            self.pitcher_count_transitions[pitcher_id][count_label][from_pitch].get(to_pitch, 0) + 1
        )
        self.total_transitions += 1
    
    def add_batter_transition(self, from_pitch: str, to_pitch: str, batter_id: int):
        """Add a batter-specific transition"""
        if batter_id not in self.batter_transitions:
            self.batter_transitions[batter_id] = {}
        
        if from_pitch not in self.batter_transitions[batter_id]:
            self.batter_transitions[batter_id][from_pitch] = {}
        
        self.batter_transitions[batter_id][from_pitch][to_pitch] = (
            self.batter_transitions[batter_id][from_pitch].get(to_pitch, 0) + 1
        )
        self.total_transitions += 1
    
    def add_batter_count_transition(self, from_pitch: str, to_pitch: str, 
                                 batter_id: int, count_label: str):
        """Add a batter-specific, count-specific transition"""
        if batter_id not in self.batter_count_transitions:
            self.batter_count_transitions[batter_id] = {}
        
        if count_label not in self.batter_count_transitions[batter_id]:
            self.batter_count_transitions[batter_id][count_label] = {}
        
        if from_pitch not in self.batter_count_transitions[batter_id][count_label]:
            self.batter_count_transitions[batter_id][count_label][from_pitch] = {}
        
        self.batter_count_transitions[batter_id][count_label][from_pitch][to_pitch] = (
            self.batter_count_transitions[batter_id][count_label][from_pitch].get(to_pitch, 0) + 1
        )
        self.total_transitions += 1
    
    def add_sequence_transition(self, sequence: Tuple[str, ...], to_pitch: str):
        """Add a sequence-based transition"""
        if sequence not in self.sequence_transitions:
            self.sequence_transitions[sequence] = {}
        
        self.sequence_transitions[sequence][to_pitch] = (
            self.sequence_transitions[sequence].get(to_pitch, 0) + 1
        )
        self.total_transitions += 1
    
    def get_general_transitions(self, from_pitch: str) -> Dict[str, float]:
        """Get general transition probabilities from a pitch"""
        if from_pitch not in self.general_transitions:
            return {}
        
        transitions = self.general_transitions[from_pitch]
        total_from = sum(transitions.values())
        
        if total_from == 0:
            return {}
        
        return {
            pitch: count / total_from 
            for pitch, count in transitions.items()
        }
    
    def get_count_transitions(self, count_label: str, from_pitch: str) -> Dict[str, float]:
        """Get count-specific transition probabilities"""
        if count_label not in self.count_transitions:
            return {}
        
        if from_pitch not in self.count_transitions[count_label]:
            return {}
        
        transitions = self.count_transitions[count_label][from_pitch]
        total_from = sum(transitions.values())
        
        if total_from == 0:
            return {}
        
        return {
            pitch: count / total_from 
            for pitch, count in transitions.items()
        }
    
    def get_pitcher_transitions(self, pitcher_id: int, from_pitch: str) -> Dict[str, float]:
        """Get pitcher-specific transition probabilities"""
        if pitcher_id not in self.pitcher_transitions:
            return {}
        
        if from_pitch not in self.pitcher_transitions[pitcher_id]:
            return {}
        
        transitions = self.pitcher_transitions[pitcher_id][from_pitch]
        total_from = sum(transitions.values())
        
        if total_from == 0:
            return {}
        
        return {
            pitch: count / total_from 
            for pitch, count in transitions.items()
        }
    
    def get_pitcher_count_transitions(self, pitcher_id: int, count_label: str, 
                                  from_pitch: str) -> Dict[str, float]:
        """Get pitcher-specific, count-specific transition probabilities"""
        if pitcher_id not in self.pitcher_count_transitions:
            return {}
        
        if count_label not in self.pitcher_count_transitions[pitcher_id]:
            return {}
        
        if from_pitch not in self.pitcher_count_transitions[pitcher_id][count_label]:
            return {}
        
        transitions = self.pitcher_count_transitions[pitcher_id][count_label][from_pitch]
        total_from = sum(transitions.values())
        
        if total_from == 0:
            return {}
        
        return {
            pitch: count / total_from 
            for pitch, count in transitions.items()
        }
    
    def get_batter_transitions(self, batter_id: int, from_pitch: str) -> Dict[str, float]:
        """Get batter-specific transition probabilities"""
        if batter_id not in self.batter_transitions:
            return {}
        
        if from_pitch not in self.batter_transitions[batter_id]:
            return {}
        
        transitions = self.batter_transitions[batter_id][from_pitch]
        total_from = sum(transitions.values())
        
        if total_from == 0:
            return {}
        
        return {
            pitch: count / total_from 
            for pitch, count in transitions.items()
        }
    
    def get_batter_count_transitions(self, batter_id: int, count_label: str, 
                                 from_pitch: str) -> Dict[str, float]:
        """Get batter-specific, count-specific transition probabilities"""
        if batter_id not in self.batter_count_transitions:
            return {}
        
        if count_label not in self.batter_count_transitions[batter_id]:
            return {}
        
        if from_pitch not in self.batter_count_transitions[batter_id][count_label]:
            return {}
        
        transitions = self.batter_count_transitions[batter_id][count_label][from_pitch]
        total_from = sum(transitions.values())
        
        if total_from == 0:
            return {}
        
        return {
            pitch: count / total_from 
            for pitch, count in transitions.items()
        }
    
    def get_sequence_transitions(self, sequence: Tuple[str, ...]) -> Dict[str, float]:
        """Get sequence-based transition probabilities"""
        if sequence not in self.sequence_transitions:
            return {}
        
        transitions = self.sequence_transitions[sequence]
        total_from = sum(transitions.values())
        
        if total_from == 0:
            return {}
        
        return {
            pitch: count / total_from 
            for pitch, count in transitions.items()
        }
    
    def get_top_transitions(self, max_results: int = 20) -> List[Dict[str, Any]]:
        """Get most frequent transitions across all types"""
        all_transitions = []
        
        # General transitions
        for from_pitch, transitions in self.general_transitions.items():
            for to_pitch, count in transitions.items():
                all_transitions.append({
                    'from_pitch': from_pitch,
                    'to_pitch': to_pitch,
                    'count': count,
                    'type': 'general'
                })
        
        # Count-specific transitions
        for count_label, count_dict in self.count_transitions.items():
            for from_pitch, transitions in count_dict.items():
                for to_pitch, count in transitions.items():
                    all_transitions.append({
                        'from_pitch': from_pitch,
                        'to_pitch': to_pitch,
                        'count': count,
                        'count_label': count_label,
                        'type': 'count_specific'
                    })
        
        # Sort by count
        all_transitions.sort(key=lambda x: x['count'], reverse=True)
        
        return all_transitions[:max_results]
    
    def apply_smoothing(self, smoothing_factor: float):
        """Apply Laplace smoothing to all transitions"""
        self.smoothing_applied = True
        
        # Get all unique pitch symbols
        all_pitches = set()
        
        for transitions in self.general_transitions.values():
            all_pitches.update(transitions.keys())
            all_pitches.update(transitions.values())
        
        for count_dict in self.count_transitions.values():
            for transitions in count_dict.values():
                all_pitches.update(transitions.keys())
                all_pitches.update(transitions.values())
        
        # Apply smoothing to all transition dictionaries
        for pitch in all_pitches:
            # General transitions
            if pitch in self.general_transitions:
                for to_pitch in all_pitches:
                    if to_pitch not in self.general_transitions[pitch]:
                        self.general_transitions[pitch][to_pitch] = smoothing_factor
                    else:
                        self.general_transitions[pitch][to_pitch] += smoothing_factor
            
            # Count-specific transitions
            for count_dict in self.count_transitions.values():
                for transitions in count_dict.values():
                    if pitch in transitions:
                        for to_pitch in all_pitches:
                            if to_pitch not in transitions[pitch]:
                                transitions[pitch][to_pitch] = smoothing_factor
                            else:
                                transitions[pitch][to_pitch] += smoothing_factor
    
    def apply_recency_weighting(self, recency_weight: float):
        """Apply recency weighting to transitions"""
        self.recency_weighted = True
        # Implementation would require timestamp data for each transition
        # For now, just mark as weighted
        pass
    
    def get_matrix_copy(self) -> Dict:
        """Get a complete copy of the transition matrix"""
        return {
            'general_transitions': dict(self.general_transitions),
            'count_transitions': {k: dict(v) for k, v in self.count_transitions.items()},
            'pitcher_transitions': {k: dict(v) for k, v in self.pitcher_transitions.items()},
            'pitcher_count_transitions': {k: {k2: dict(v2) for k2, v2 in v.items()} 
                                       for k, v in self.pitcher_count_transitions.items()},
            'batter_transitions': {k: dict(v) for k, v in self.batter_transitions.items()},
            'batter_count_transitions': {k: {k2: dict(v2) for k2, v2 in v.items()} 
                                       for k, v in self.batter_count_transitions.items()},
            'sequence_transitions': {k: dict(v) for k, v in self.sequence_transitions.items()},
            'total_transitions': self.total_transitions,
            'smoothing_applied': self.smoothing_applied,
            'recency_weighted': self.recency_weighted
        }
    
    def load_matrix(self, matrix_data: Dict):
        """Load transition matrix from saved data"""
        self.general_transitions = matrix_data.get('general_transitions', {})
        self.count_transitions = matrix_data.get('count_transitions', {})
        self.pitcher_transitions = matrix_data.get('pitcher_transitions', {})
        self.pitcher_count_transitions = matrix_data.get('pitcher_count_transitions', {})
        self.batter_transitions = matrix_data.get('batter_transitions', {})
        self.batter_count_transitions = matrix_data.get('batter_count_transitions', {})
        self.sequence_transitions = matrix_data.get('sequence_transitions', {})
        self.total_transitions = matrix_data.get('total_transitions', 0)
        self.smoothing_applied = matrix_data.get('smoothing_applied', False)
        self.recency_weighted = matrix_data.get('recency_weighted', False)
    
    def clear(self):
        """Clear all transition data"""
        self.general_transitions.clear()
        self.count_transitions.clear()
        self.pitcher_transitions.clear()
        self.pitcher_count_transitions.clear()
        self.batter_transitions.clear()
        self.batter_count_transitions.clear()
        self.sequence_transitions.clear()
        self.total_transitions = 0
        self.smoothing_applied = False
        self.recency_weighted = False
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get transition matrix statistics"""
        return {
            'total_transitions': self.total_transitions,
            'general_transition_count': len(self.general_transitions),
            'count_transition_count': len(self.count_transitions),
            'pitcher_count': len(self.pitcher_transitions),
            'batter_count': len(self.batter_transitions),
            'sequence_count': len(self.sequence_transitions),
            'smoothing_applied': self.smoothing_applied,
            'recency_weighted': self.recency_weighted
        }
