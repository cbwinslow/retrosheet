#!/usr/bin/env python3
"""
Unit tests for calibration logic.

Tests the calibration functions in retrosheet/prediction/__init__.py
"""

from __future__ import annotations

import pytest
import numpy as np
from typing import Any

from retrosheet.prediction import apply_calibrators


class TestApplyCalibrators:
    """Test calibrator application."""
    
    def test_no_calibration(self):
        """Test that probabilities are unchanged when calibrators are None."""
        raw_probabilities = np.array([[0.25, 0.75], [0.50, 0.50]])
        calibrators = [None, None]
        
        calibrated = apply_calibrators(raw_probabilities, calibrators)
        
        np.testing.assert_array_equal(calibrated, raw_probabilities)
    
    def test_calibration_with_mock_calibrator(self):
        """Test calibration with mock calibrator objects."""
        raw_probabilities = np.array([[0.25, 0.75], [0.50, 0.50]])
        
        # Create mock calibrator that adds 0.1 to probabilities (capped at 1.0)
        class MockCalibrator:
            def predict_proba(self, X):
                result = X.flatten() + 0.1
                return np.minimum(result, 1.0).reshape(-1, 1)
        
        calibrators = [MockCalibrator(), MockCalibrator()]
        
        calibrated = apply_calibrators(raw_probabilities, calibrators)
        
        # First class: 0.25 -> 0.35, 0.50 -> 0.60
        # Second class: 0.75 -> 0.85, 0.50 -> 0.60
        assert calibrated[0, 0] == pytest.approx(0.35, rel=0.01)
        assert calibrated[1, 0] == pytest.approx(0.60, rel=0.01)
        assert calibrated[0, 1] == pytest.approx(0.85, rel=0.01)
        assert calibrated[1, 1] == pytest.approx(0.60, rel=0.01)
    
    def test_mixed_calibration(self):
        """Test with some calibrators None and some real."""
        raw_probabilities = np.array([[0.25, 0.75]])
        
        class MockCalibrator:
            def predict_proba(self, X):
                return X * 0.9  # Reduce by 10%
        
        calibrators = [MockCalibrator(), None]
        
        calibrated = apply_calibrators(raw_probabilities, calibrators)
        
        # First class should be calibrated (0.25 -> 0.225)
        # Second class should be unchanged (0.75)
        assert calibrated[0, 0] == pytest.approx(0.225, rel=0.01)
        assert calibrated[0, 1] == pytest.approx(0.75, rel=0.01)
    
    def test_single_sample(self):
        """Test calibration with single sample."""
        raw_probabilities = np.array([[0.25, 0.75]])
        
        class MockCalibrator:
            def predict_proba(self, X):
                return X * 0.8  # Reduce by 20%
        
        calibrators = [MockCalibrator(), MockCalibrator()]
        
        calibrated = apply_calibrators(raw_probabilities, calibrators)
        
        assert calibrated[0, 0] == pytest.approx(0.20, rel=0.01)
        assert calibrated[0, 1] == pytest.approx(0.60, rel=0.01)
    
    def test_multi_sample(self):
        """Test calibration with multiple samples."""
        raw_probabilities = np.array([
            [0.25, 0.75],
            [0.50, 0.50],
            [0.10, 0.90],
        ])
        
        class MockCalibrator:
            def predict_proba(self, X):
                return X * 0.9  # Reduce by 10%
        
        calibrators = [MockCalibrator(), MockCalibrator()]
        
        calibrated = apply_calibrators(raw_probabilities, calibrators)
        
        expected = raw_probabilities * 0.9
        np.testing.assert_array_almost_equal(calibrated, expected)
    
    def test_probability_preservation(self):
        """Test that calibrated probabilities are still valid (0-1 range)."""
        raw_probabilities = np.array([[0.25, 0.75], [0.50, 0.50]])
        
        class MockCalibrator:
            def predict_proba(self, X):
                # Ensure output is always in [0, 1] range
                result = X.flatten() + 0.1
                return np.clip(result, 0.0, 1.0).reshape(-1, 1)
        
        calibrators = [MockCalibrator(), MockCalibrator()]
        
        calibrated = apply_calibrators(raw_probabilities, calibrators)
        
        # All probabilities should be in [0, 1] range
        assert np.all(calibrated >= 0.0)
        assert np.all(calibrated <= 1.0)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
