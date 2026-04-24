#!/usr/bin/env python3
"""
Base classes for modular prediction framework.

Strategy pattern:
- Predictor: interface for all predictors
- Target: defines what we're predicting
- Registry: lookup and manage predictors
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Generic, TypeVar

import numpy as np
import pandas as pd
import psycopg2

from .db import database_kwargs

T = TypeVar("T")
R = TypeVar("R")


@dataclass
class PredictionTarget:
    """Definition of a prediction target."""

    target_id: str
    target_name: str
    target_family: str
    description: str

    @classmethod
    def from_db(cls, conn, target_id: str) -> PredictionTarget:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT target_id, target_name, target_family, description
                FROM predictions.prediction_targets 
                WHERE target_id = %s
            """,
                (target_id,),
            )
            row = cur.fetchone()
            if not row:
                raise ValueError(f"Target {target_id} not found")
            return cls(row[0], row[1], row[2], row[3])


@dataclass
class ModelMetadata:
    """Loaded model metadata."""

    model_id: int
    target_id: str
    model_name: str
    model_family: str
    model_version: str
    artifact_uri: str
    feature_spec: dict
    metrics: dict | None = None


class Predictor(ABC, Generic[T, R]):
    """Base class for all predictors."""

    def __init__(self, target: PredictionTarget):
        self.target = target
        self._model = None
        self._calibration = None

    @abstractmethod
    def load(self, artifact_path: Path) -> None:
        """Load model from disk."""
        pass

    @abstractmethod
    def predict(self, features: pd.DataFrame) -> np.ndarray:
        """Make prediction. Returns probability distribution."""
        pass

    @abstractmethod
    def predict_raw(self, features: pd.DataFrame) -> np.ndarray:
        """Raw prediction before calibration."""
        pass

    def calibrate(self, probabilities: np.ndarray) -> np.ndarray:
        """Apply calibration if available."""
        if self._calibration is None:
            return probabilities
        calibrated = probabilities.copy()
        for i, calibrator in enumerate(self._calibration):
            calibrated[:, i] = calibrator.predict(probabilities[:, i].reshape(-1, 1)).flatten()
        calibrated = np.clip(calibrated, 1e-12, 1.0)
        return calibrated / calibrated.sum(axis=1, keepdims=True)

    @property
    @abstractmethod
    def classes(self) -> list[str]:
        """Class labels."""
        pass


class PredictorRegistry:
    """Registry for managing predictors."""

    def __init__(self, db_kwargs: dict | None = None):
        self.db_kwargs = db_kwargs or database_kwargs()

    def get_active_model(self, target_id: str) -> ModelMetadata | None:
        """Get active model for target."""
        conn = psycopg2.connect(**self.db_kwargs)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT model_id, target_id, model_name, model_family,
                           model_version, artifact_uri, feature_spec, metrics
                    FROM models.model_registry
                    WHERE target_id = %s AND is_active = TRUE
                    ORDER BY created_at DESC
                    LIMIT 1
                """,
                    (target_id,),
                )
                row = cur.fetchone()
                if not row:
                    return None
                fs = (
                    row[6]
                    if isinstance(row[6], dict)
                    else json.loads(row[6])
                    if isinstance(row[6], str)
                    else row[6]
                )
                m = (
                    row[7]
                    if isinstance(row[7], dict)
                    else json.loads(row[7])
                    if isinstance(row[7], str)
                    else row[7]
                    if row[7]
                    else None
                )
                return ModelMetadata(
                    model_id=row[0],
                    target_id=row[1],
                    model_name=row[2],
                    model_family=row[3],
                    model_version=row[4],
                    artifact_uri=row[5],
                    feature_spec=fs,
                    metrics=m,
                )
        finally:
            conn.close()

    def get_active_calibration(self, target_id: str) -> dict | None:
        """Get active calibration for target."""
        conn = psycopg2.connect(**self.db_kwargs)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT artifact_uri, calibration_type
                    FROM models.calibration_artifacts
                    WHERE target_id = %s AND is_active = TRUE
                    LIMIT 1
                """,
                    (target_id,),
                )
                row = cur.fetchone()
                if not row:
                    return None
                return {"uri": row[0], "type": row[1]}
        finally:
            conn.close()

    def list_targets(self) -> list[str]:
        """List all available targets."""
        conn = psycopg2.connect(**self.db_kwargs)
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT target_id FROM predictions.prediction_targets 
                    WHERE is_active = TRUE
                """)
                return [r[0] for r in cur.fetchall()]
        finally:
            conn.close()
