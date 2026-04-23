#!/usr/bin/env python3
"""
PA Outcome Distribution Predictor.

Predicts probability distribution over plate appearance outcomes:
- strikeout, walk, single, double, triple, home_run
- ground_out, air_or_other_out, productive_out
- reach_on_error_or_fc, hit_by_pitch
"""
from __future__ import annotations
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from .base import Predictor, PredictionTarget


class PAOutcomeDistributionPredictor(Predictor[pd.DataFrame, np.ndarray]):
    """Predicts PA outcome probability distribution."""
    
    def __init__(self, target: PredictionTarget, root_path: Path | None = None):
        super().__init__(target)
        self.root_path = root_path or Path.cwd()
    
    def load(self, artifact_path: Path) -> None:
        """Load model and calibration from disk."""
        self._model = joblib.load(artifact_path)
        
        # Try to load calibration
        calib_path = artifact_path.with_name(
            artifact_path.stem.replace('_multiclass', '') + '_calibration.joblib'
        )
        if not calib_path.exists():
            # Try standard calibration path
            calib_path = artifact_path.parent / 'calibration' / 'pa_outcome_distribution' / (
                artifact_path.stem.replace('pa_outcome_distribution_', '') + 
                '_isotonic_artifact.joblib'
            )
        
        if calib_path.exists():
            calib_data = joblib.load(calib_path)
            self._calibration = calib_data.get('calibrators', [])
            self._calibration_classes = calib_data.get('classes', [])
        else:
            self._calibration = None
    
    def predict_raw(self, features: pd.DataFrame) -> np.ndarray:
        """Raw prediction before calibration."""
        if self._model is None:
            raise ValueError("Model not loaded")
        return self._model.predict_proba(features)
    
    def predict(self, features: pd.DataFrame) -> np.ndarray:
        """Prediction with calibration."""
        raw_probs = self.predict_raw(features)
        return self.calibrate(raw_probs)
    
    @property
    def classes(self) -> list[str]:
        """Outcome classes."""
        return list(self._model.classes_)
    
    def predict_top_k(self, features: pd.DataFrame, k: int = 3) -> tuple[list[str], list[float]]:
        """Get top k predictions."""
        probs = self.predict(features)
        if probs.ndim > 1:
            probs = probs[0]
        
        top_idx = np.argsort(probs)[::-1][:k]
        classes = self.classes
        return [classes[i] for i in top_idx], [float(probs[i]) for i in top_idx]
    
    def format_prediction(self, features: pd.DataFrame) -> str:
        """Format prediction as readable string."""
        top_classes, top_probs = self.predict_top_k(features)
        lines = ["Top predictions:"]
        for cls, prob in zip(top_classes, top_probs):
            lines.append(f"  {cls}: {prob:.1%}")
        return "\n".join(lines)