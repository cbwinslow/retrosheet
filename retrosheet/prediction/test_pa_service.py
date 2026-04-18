#!/usr/bin/env python3
"""
Unit tests for the PA prediction service module.

Tests the shared prediction logic in retrosheet/prediction/__init__.py
"""

from __future__ import annotations

import pytest
import numpy as np
from typing import Any

from retrosheet.prediction import (
    derived_probabilities,
    DEFAULT_MODEL_NAME,
)


class TestDerivedProbabilities:
    """Test derived probability calculations."""
    
    def test_hit_probability(self):
        """Test hit probability calculation."""
        probabilities = {
            'single': 0.15,
            'double': 0.05,
            'triple': 0.01,
            'home_run': 0.03,
            'strikeout': 0.20,
            'ground_out': 0.25,
            'fly_out': 0.20,
            'line_out': 0.08,
            'pop_out': 0.02,
            'walk': 0.08,
            'hit_by_pitch': 0.01,
        }
        
        derived = derived_probabilities(probabilities)
        
        assert derived['hit'] == pytest.approx(0.24, rel=0.01)
        assert derived['hit'] == probabilities['single'] + probabilities['double'] + probabilities['triple'] + probabilities['home_run']
    
    def test_out_probability(self):
        """Test out probability calculation."""
        probabilities = {
            'single': 0.15,
            'double': 0.05,
            'triple': 0.01,
            'home_run': 0.03,
            'strikeout': 0.20,
            'ground_out': 0.25,
            'fly_out': 0.20,
            'line_out': 0.08,
            'pop_out': 0.02,
            'walk': 0.08,
            'hit_by_pitch': 0.01,
        }
        
        derived = derived_probabilities(probabilities)
        
        assert derived['out'] == pytest.approx(0.75, rel=0.01)
        assert derived['out'] == probabilities['strikeout'] + probabilities['ground_out'] + probabilities['fly_out'] + probabilities['line_out'] + probabilities['pop_out']
    
    def test_walk_probability(self):
        """Test walk probability calculation."""
        probabilities = {
            'single': 0.15,
            'double': 0.05,
            'triple': 0.01,
            'home_run': 0.03,
            'strikeout': 0.20,
            'ground_out': 0.25,
            'fly_out': 0.20,
            'line_out': 0.08,
            'pop_out': 0.02,
            'walk': 0.08,
            'hit_by_pitch': 0.01,
        }
        
        derived = derived_probabilities(probabilities)
        
        assert derived['walk'] == pytest.approx(0.09, rel=0.01)
        assert derived['walk'] == probabilities['walk'] + probabilities['hit_by_pitch']
    
    def test_extra_base_hit_probability(self):
        """Test extra base hit probability calculation."""
        probabilities = {
            'single': 0.15,
            'double': 0.05,
            'triple': 0.01,
            'home_run': 0.03,
            'strikeout': 0.20,
            'ground_out': 0.25,
            'fly_out': 0.20,
            'line_out': 0.08,
            'pop_out': 0.02,
            'walk': 0.08,
            'hit_by_pitch': 0.01,
        }
        
        derived = derived_probabilities(probabilities)
        
        assert derived['extra_base_hit'] == pytest.approx(0.09, rel=0.01)
        assert derived['extra_base_hit'] == probabilities['double'] + probabilities['triple'] + probabilities['home_run']
    
    def test_on_base_probability(self):
        """Test on-base probability calculation."""
        probabilities = {
            'single': 0.15,
            'double': 0.05,
            'triple': 0.01,
            'home_run': 0.03,
            'strikeout': 0.20,
            'ground_out': 0.25,
            'fly_out': 0.20,
            'line_out': 0.08,
            'pop_out': 0.02,
            'walk': 0.08,
            'hit_by_pitch': 0.01,
        }
        
        derived = derived_probabilities(probabilities)
        
        assert derived['on_base'] == pytest.approx(0.33, rel=0.01)
        assert derived['on_base'] == probabilities['single'] + probabilities['double'] + probabilities['triple'] + probabilities['home_run'] + probabilities['walk'] + probabilities['hit_by_pitch']
    
    def test_missing_outcomes(self):
        """Test derived probabilities with missing outcomes."""
        probabilities = {
            'single': 0.15,
            'double': 0.05,
            'home_run': 0.03,
        }
        
        derived = derived_probabilities(probabilities)
        
        # Missing outcomes should default to 0
        assert derived['hit'] == 0.23
        assert derived['out'] == 0.0
        assert derived['walk'] == 0.0
        assert derived['extra_base_hit'] == 0.08
        assert derived['on_base'] == 0.23


class TestDefaultModelName:
    """Test default model name constant."""
    
    def test_default_model_name(self):
        """Test that default model name is set correctly."""
        assert DEFAULT_MODEL_NAME == "hist_gradient_boosting_multiclass"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
