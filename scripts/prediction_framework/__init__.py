#!/usr/bin/env python3
"""
Prediction Framework - Unified Interface.

Usage:
    from prediction_framework import PredictionEngine

    engine = PredictionEngine()

    # Get active predictor
    predictor = engine.get_predictor('pa_outcome_distribution')

    # Make prediction
    result = predictor.predict(features_df)

    # Or use convenient method
    result = engine.predict('pa_outcome_distribution', features_df)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import psycopg2

from .base import (
    ModelMetadata,
    PredictionTarget,
    Predictor,
    PredictorRegistry,
)
from .db import database_kwargs


class PredictionEngine:
    """Main interface for predictions."""

    def __init__(self, db_kwargs: dict | None = None, root_path: Path | None = None):
        self.db_kwargs = db_kwargs or database_kwargs()
        self.root_path = root_path or Path.cwd()
        self._registry = PredictorRegistry(self.db_kwargs)
        self._predictors: dict[str, Predictor] = {}
        self._load_predictor_classes()

    def _load_predictor_classes(self) -> None:
        """Map target families to predictor classes."""
        self._predictor_classes = {
            "plate_appearance": "PAOutcomeDistributionPredictor",
            "pa_outcome_distribution": "PAOutcomeDistributionPredictor",
            "game_outcome": "GameOutcomePredictor",
            "half_inning": "HalfInningPredictor",
        }

    def get_predictor(self, target_id: str) -> Predictor:
        """Get predictor for target. Cached."""
        if target_id in self._predictors:
            return self._predictors[target_id]

        # Get model metadata
        model_meta = self._registry.get_active_model(target_id)
        if not model_meta:
            raise ValueError(f"No active model for {target_id}")

        # Get target definition
        conn = psycopg2.connect(**self.db_kwargs)
        try:
            target = PredictionTarget.from_db(conn, target_id)
        finally:
            conn.close()

        # Load appropriate predictor
        predictor_class = self._predictor_classes.get(target.target_family)

        if predictor_class == "PAOutcomeDistributionPredictor":
            from .pa_predictor import PAOutcomeDistributionPredictor

            predictor = PAOutcomeDistributionPredictor(target, self.root_path)
        else:
            raise ValueError(f"Unknown predictor family: {target.target_family}")

        # Load model
        model_path = self.root_path / model_meta.artifact_uri
        predictor.load(model_path)

        self._predictors[target_id] = predictor
        return predictor

    def predict(self, target_id: str, features: pd.DataFrame) -> np.ndarray:
        """Convenient prediction method."""
        return self.get_predictor(target_id).predict(features)

    def predict_top_k(
        self, target_id: str, features: pd.DataFrame, k: int = 3
    ) -> tuple[list, list]:
        """Get top k predictions."""
        predictor = self.get_predictor(target_id)
        if hasattr(predictor, "predict_top_k"):
            return predictor.predict_top_k(features, k)
        probs = predictor.predict(features)
        if probs.ndim > 1:
            probs = probs[0]
        top_idx = np.argsort(probs)[::-1][:k]
        return list(predictor.classes[i] for i in top_idx), [float(probs[i]) for i in top_idx]

    def list_targets(self) -> list[str]:
        """List available targets."""
        return self._registry.list_targets()

    def get_model_info(self, target_id: str) -> ModelMetadata | None:
        """Get model metadata."""
        return self._registry.get_active_model(target_id)


__all__ = ["PredictionEngine", "Predictor", "PredictionTarget", "ModelMetadata"]
