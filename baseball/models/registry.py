"""
Model Registry for the baseball prediction warehouse.

Provides model versioning, artifact management, and deployment lifecycle.
Integrates with the SQL models.registry table for persistence.

Author: Agent Cascade
Date: 2026-04-28
"""

import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict

from baseball.core.db import get_db_connection
from baseball.models.base import BaseModel, ModelMetadata


@dataclass
class ModelRegistryEntry:
    """Represents a registered model version."""
    model_id: Optional[int] = None
    model_name: str = ""
    model_version: str = "1.0.0"
    model_type: str = "classification"
    training_date: Optional[datetime] = None
    training_dataset: str = ""
    training_start_date: Optional[str] = None
    training_end_date: Optional[str] = None
    hyperparameters: Dict[str, Any] = None
    feature_set: List[str] = None
    training_config: Dict[str, Any] = None
    primary_metric: str = ""
    primary_metric_value: float = 0.0
    validation_metrics: Dict[str, float] = None
    cv_folds: int = 5
    cv_mean: float = 0.0
    cv_std: float = 0.0
    artifact_path: str = ""
    artifact_hash: str = ""
    artifact_size_bytes: int = 0
    framework: str = "sklearn"
    framework_version: str = ""
    status: str = "staging"
    promoted_at: Optional[datetime] = None
    promoted_by: str = ""
    training_run_id: Optional[int] = None
    
    def __post_init__(self):
        if self.hyperparameters is None:
            self.hyperparameters = {}
        if self.feature_set is None:
            self.feature_set = []
        if self.training_config is None:
            self.training_config = {}
        if self.validation_metrics is None:
            self.validation_metrics = {}


class ModelRegistry:
    """
    Central registry for ML model versioning and lifecycle management.
    
    Provides:
    - Model registration with versioning
    - Artifact storage and retrieval
    - Status management (staging -> production -> archived)
    - Production model discovery
    
    Usage:
        registry = ModelRegistry()
        
        # Register a new model
        entry = registry.register_model(
            model_name="win_probability",
            model_version="1.0.0",
            model_type="classification",
            artifact_path="/path/to/model.pkl",
            primary_metric="log_loss",
            primary_metric_value=0.45
        )
        
        # Promote to production
        registry.promote_model(entry.model_id, promoted_by="user")
        
        # Get production model
        prod_model = registry.get_production_model("win_probability")
    """
    
    def __init__(self, artifacts_dir: str = "models/artifacts"):
        self.artifacts_dir = Path(artifacts_dir)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
    
    def register_model(
        self,
        model_name: str,
        model_version: str,
        model_type: str,
        artifact_path: str,
        primary_metric: str,
        primary_metric_value: float,
        hyperparameters: Optional[Dict[str, Any]] = None,
        feature_set: Optional[List[str]] = None,
        training_config: Optional[Dict[str, Any]] = None,
        validation_metrics: Optional[Dict[str, float]] = None,
        framework: str = "sklearn",
        framework_version: str = "",
        cv_folds: int = 5,
        cv_mean: float = 0.0,
        cv_std: float = 0.0,
        training_dataset: str = "",
        training_start_date: Optional[str] = None,
        training_end_date: Optional[str] = None
    ) -> ModelRegistryEntry:
        """
        Register a new model version in the registry.
        
        Args:
            model_name: Model identifier (e.g., "win_probability")
            model_version: Semantic version (e.g., "1.0.0")
            model_type: "classification", "regression", or "time_series"
            artifact_path: Path to serialized model file
            primary_metric: Metric name (e.g., "log_loss", "rmse")
            primary_metric_value: Metric value
            hyperparameters: Model hyperparameters dict
            feature_set: List of feature names used
            training_config: Training configuration dict
            validation_metrics: Full validation metrics dict
            framework: ML framework used
            framework_version: Framework version string
            cv_folds: Number of cross-validation folds
            cv_mean: Mean CV score
            cv_std: CV standard deviation
            training_dataset: Training dataset identifier
            training_start_date: Training data start date (YYYY-MM-DD)
            training_end_date: Training data end date (YYYY-MM-DD)
            
        Returns:
            ModelRegistryEntry with assigned model_id
        """
        # Calculate artifact hash and size
        artifact_path_obj = Path(artifact_path)
        if artifact_path_obj.exists():
            artifact_size = artifact_path_obj.stat().st_size
            artifact_hash = self._calculate_hash(artifact_path_obj)
        else:
            artifact_size = 0
            artifact_hash = ""
        
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT models.register_model(
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    """,
                    (
                        model_name,
                        model_version,
                        model_type,
                        artifact_path,
                        primary_metric,
                        primary_metric_value,
                        json.dumps(hyperparameters or {}),
                        json.dumps(feature_set or []),
                        json.dumps(training_config or {}),
                        json.dumps(validation_metrics or {})
                    )
                )
                model_id = cur.fetchone()[0]
                
                # Update additional fields
                cur.execute(
                    """
                    UPDATE models.registry SET
                        artifact_size_bytes = %s,
                        artifact_hash = %s,
                        framework = %s,
                        framework_version = %s,
                        cv_folds = %s,
                        cv_mean = %s,
                        cv_std = %s,
                        training_dataset = %s,
                        training_start_date = %s,
                        training_end_date = %s
                    WHERE model_id = %s
                    """,
                    (
                        artifact_size,
                        artifact_hash,
                        framework,
                        framework_version,
                        cv_folds,
                        cv_mean,
                        cv_std,
                        training_dataset,
                        training_start_date,
                        training_end_date,
                        model_id
                    )
                )
                conn.commit()
                
                return self.get_model_by_id(model_id)
        finally:
            conn.close()
    
    def get_model_by_id(self, model_id: int) -> Optional[ModelRegistryEntry]:
        """Get model registry entry by ID."""
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT * FROM models.registry WHERE model_id = %s
                    """,
                    (model_id,)
                )
                row = cur.fetchone()
                if row:
                    return self._row_to_entry(row, cur.description)
                return None
        finally:
            conn.close()
    
    def get_production_model(self, model_name: str) -> Optional[ModelRegistryEntry]:
        """Get the current production model for a model type."""
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT * FROM models.v_production_models 
                    WHERE model_name = %s
                    """,
                    (model_name,)
                )
                row = cur.fetchone()
                if row:
                    return self._row_to_entry(row, cur.description)
                return None
        finally:
            conn.close()
    
    def promote_model(
        self, 
        model_id: int, 
        promoted_by: str = "system"
    ) -> bool:
        """
        Promote a model to production status.
        
        Archives the current production model if one exists.
        
        Args:
            model_id: Model to promote
            promoted_by: User/system promoting the model
            
        Returns:
            True if successful
        """
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT models.promote_model(%s, %s)",
                    (model_id, promoted_by)
                )
                conn.commit()
                return True
        finally:
            conn.close()
    
    def list_models(
        self, 
        model_name: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[ModelRegistryEntry]:
        """List models with optional filters."""
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                query = "SELECT * FROM models.registry WHERE 1=1"
                params = []
                
                if model_name:
                    query += " AND model_name = %s"
                    params.append(model_name)
                if status:
                    query += " AND status = %s"
                    params.append(status)
                
                query += " ORDER BY training_date DESC LIMIT %s"
                params.append(limit)
                
                cur.execute(query, params)
                
                return [self._row_to_entry(row, cur.description) for row in cur.fetchall()]
        finally:
            conn.close()
    
    def get_model_history(self, model_name: str) -> List[ModelRegistryEntry]:
        """Get version history for a specific model."""
        return self.list_models(model_name=model_name, limit=50)
    
    def archive_model(self, model_id: int) -> bool:
        """Archive a model (move from production/staging to archived)."""
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE models.registry 
                    SET status = 'archived', updated_at = NOW()
                    WHERE model_id = %s
                    """,
                    (model_id,)
                )
                conn.commit()
                return cur.rowcount > 0
        finally:
            conn.close()
    
    def delete_model(self, model_id: int) -> bool:
        """
        Delete a model from the registry.
        
        Only allowed for staging models. Production models must be archived first.
        """
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    DELETE FROM models.registry 
                    WHERE model_id = %s AND status = 'staging'
                    """,
                    (model_id,)
                )
                conn.commit()
                return cur.rowcount > 0
        finally:
            conn.close()
    
    def _calculate_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash of a file."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    def _row_to_entry(self, row, description) -> ModelRegistryEntry:
        """Convert database row to ModelRegistryEntry."""
        columns = [desc[0] for desc in description]
        data = dict(zip(columns, row))
        
        # Parse JSON fields
        for field in ['hyperparameters', 'feature_set', 'training_config', 'validation_metrics']:
            if field in data and data[field]:
                if isinstance(data[field], str):
                    data[field] = json.loads(data[field])
        
        # Convert to ModelRegistryEntry
        return ModelRegistryEntry(
            model_id=data.get('model_id'),
            model_name=data.get('model_name', ''),
            model_version=data.get('model_version', '1.0.0'),
            model_type=data.get('model_type', 'classification'),
            training_date=data.get('training_date'),
            training_dataset=data.get('training_dataset', ''),
            training_start_date=data.get('training_start_date'),
            training_end_date=data.get('training_end_date'),
            hyperparameters=data.get('hyperparameters', {}),
            feature_set=data.get('feature_set', []),
            training_config=data.get('training_config', {}),
            primary_metric=data.get('primary_metric', ''),
            primary_metric_value=data.get('primary_metric_value', 0.0),
            validation_metrics=data.get('validation_metrics', {}),
            cv_folds=data.get('cv_folds', 5),
            cv_mean=data.get('cv_mean', 0.0),
            cv_std=data.get('cv_std', 0.0),
            artifact_path=data.get('artifact_path', ''),
            artifact_hash=data.get('artifact_hash', ''),
            artifact_size_bytes=data.get('artifact_size_bytes', 0),
            framework=data.get('framework', 'sklearn'),
            framework_version=data.get('framework_version', ''),
            status=data.get('status', 'staging'),
            promoted_at=data.get('promoted_at'),
            promoted_by=data.get('promoted_by', ''),
            training_run_id=data.get('training_run_id')
        )


# Global registry instance
_registry = None

def get_registry() -> ModelRegistry:
    """Get singleton ModelRegistry instance."""
    global _registry
    if _registry is None:
        _registry = ModelRegistry()
    return _registry
