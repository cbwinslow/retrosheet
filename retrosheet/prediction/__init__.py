#!/usr/bin/env python3
"""
Shared prediction service module for plate appearance outcome predictions.

This module extracts common logic used by both historical and live prediction
scripts to ensure consistency and reduce code duplication.
"""

from __future__ import annotations

from typing import Any

import joblib
import pandas as pd
import psycopg2
from sqlalchemy import create_engine, text

from train_pa_outcome_distribution import ROOT, TARGET_ID, database_kwargs, database_url


DEFAULT_MODEL_NAME = "hist_gradient_boosting_multiclass"


def load_registered_model(
    *,
    model_name: str,
    model_version: str | None,
) -> tuple[Any, dict[str, Any], dict[str, Any]]:
    """
    Load a registered model from the model registry.
    
    Returns:
        tuple of (model, feature_spec, metadata)
    """
    conn = psycopg2.connect(**database_kwargs())
    try:
        with conn.cursor() as cur:
            if model_version:
                cur.execute(
                    """
                    SELECT model_name, model_version, artifact_uri, feature_spec, metrics, is_active, model_id
                    FROM models.model_registry
                    WHERE target_id = %s
                      AND model_name = %s
                      AND model_version = %s
                    """,
                    (TARGET_ID, model_name, model_version),
                )
            else:
                cur.execute(
                    """
                    SELECT model_name, model_version, artifact_uri, feature_spec, metrics, is_active, model_id
                    FROM models.model_registry
                    WHERE target_id = %s
                      AND model_name = %s
                      AND is_active = true
                    ORDER BY created_at DESC
                    LIMIT 1
                    """,
                    (TARGET_ID, model_name),
                )
            
            row = cur.fetchone()
            if not row:
                raise ValueError(
                    f"Model not found: target_id={TARGET_ID}, model_name={model_name}, model_version={model_version}"
                )
            
            (
                model_name,
                model_version,
                artifact_uri,
                feature_spec,
                metrics,
                is_active,
                model_id,
            ) = row
            
            metadata = {
                "model_name": model_name,
                "model_version": model_version,
                "artifact_uri": artifact_uri,
                "feature_spec": feature_spec,
                "metrics": metrics,
                "is_active": is_active,
                "model_id": model_id,
            }
            
            model_path = ROOT / artifact_uri
            model = joblib.load(model_path)
            
            return model, feature_spec, metadata
    finally:
        conn.close()


def load_calibration_artifact(
    *,
    model_id: int,
    calibration_report_name: str | None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """
    Load calibration artifact for a model.
    
    Returns:
        tuple of (calibration_artifact, calibration_metadata)
    """
    conn = psycopg2.connect(**database_kwargs())
    try:
        with conn.cursor() as cur:
            if calibration_report_name:
                cur.execute(
                    """
                    SELECT calibration_report_id, report_name, calibration_method, artifact_uri, classes, calibrators
                    FROM models.calibration_reports
                    WHERE model_id = %s
                      AND report_name = %s
                    """,
                    (model_id, calibration_report_name),
                )
            else:
                cur.execute(
                    """
                    SELECT calibration_report_id, report_name, calibration_method, artifact_uri, classes, calibrators
                    FROM models.calibration_reports
                    WHERE model_id = %s
                    ORDER BY created_at DESC
                    LIMIT 1
                    """,
                    (model_id,),
                )
            
            row = cur.fetchone()
            if not row:
                raise ValueError(
                    f"Calibration artifact not found: model_id={model_id}, calibration_report_name={calibration_report_name}"
                )
            
            (
                calibration_report_id,
                report_name,
                calibration_method,
                artifact_uri,
                classes,
                calibrators,
            ) = row
            
            calibration_metadata = {
                "calibration_report_id": calibration_report_id,
                "report_name": report_name,
                "calibration_method": calibration_method,
                "artifact_uri": artifact_uri,
            }
            
            calibration_artifact = {
                "classes": classes,
                "calibrators": calibrators,
            }
            
            return calibration_artifact, calibration_metadata
    finally:
        conn.close()


def apply_calibrators(
    raw_probabilities: np.ndarray,
    calibrators: list[dict[str, Any]],
) -> np.ndarray:
    """
    Apply calibration to raw probability outputs.
    
    Args:
        raw_probabilities: Raw model probabilities (n_samples, n_classes)
        calibrators: List of calibrator objects, one per class
        
    Returns:
        Calibrated probabilities
    """
    calibrated = np.zeros_like(raw_probabilities)
    for i, calibrator in enumerate(calibrators):
        if calibrator is not None:
            calibrated[:, i] = calibrator.predict_proba(raw_probabilities[:, i].reshape(-1, 1)).flatten()
        else:
            calibrated[:, i] = raw_probabilities[:, i]
    return calibrated


def derived_probabilities(probabilities: dict[str, float]) -> dict[str, float]:
    """
    Calculate derived probabilities from class probabilities.
    
    Args:
        probabilities: Dictionary of class_name -> probability
        
    Returns:
        Dictionary of derived metrics
    """
    return {
        "hit": probabilities.get("single", 0) + probabilities.get("double", 0) + probabilities.get("triple", 0) + probabilities.get("home_run", 0),
        "out": probabilities.get("strikeout", 0) + probabilities.get("ground_out", 0) + probabilities.get("fly_out", 0) + probabilities.get("line_out", 0) + probabilities.get("pop_out", 0),
        "walk": probabilities.get("walk", 0) + probabilities.get("hit_by_pitch", 0),
        "extra_base_hit": probabilities.get("double", 0) + probabilities.get("triple", 0) + probabilities.get("home_run", 0),
        "on_base": probabilities.get("single", 0) + probabilities.get("double", 0) + probabilities.get("triple", 0) + probabilities.get("home_run", 0) + probabilities.get("walk", 0) + probabilities.get("hit_by_pitch", 0),
    }


__all__ = [
    "DEFAULT_MODEL_NAME",
    "load_registered_model",
    "load_calibration_artifact",
    "apply_calibrators",
    "derived_probabilities",
]
