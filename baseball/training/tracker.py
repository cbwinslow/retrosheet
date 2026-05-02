"""
Experiment Tracking for Training Runs

Tracks experiments, metrics, and model versions.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from baseball.core.db import get_db_connection


class ExperimentTracker:
    """
    Track training experiments and their results.
    
    Stores experiment metadata, metrics, and links to trained models.
    """
    
    def __init__(self, experiments_dir: str = "models/experiments"):
        """Initialize the experiment tracker."""
        self.experiments_dir = Path(experiments_dir)
        self.experiments_dir.mkdir(parents=True, exist_ok=True)
    
    def log_experiment_start(
        self,
        experiment_id: str,
        experiment_name: str,
        model_type: str,
        config: Dict[str, Any]
    ) -> None:
        """Log the start of an experiment."""
        experiment_file = self.experiments_dir / f"{experiment_id}.json"
        
        experiment_data = {
            "experiment_id": experiment_id,
            "experiment_name": experiment_name,
            "model_type": model_type,
            "config": config,
            "status": "running",
            "started_at": datetime.now().isoformat(),
            "completed_at": None,
            "metrics": {},
            "training_runs": [],
            "best_model_id": None,
            "artifacts": []
        }
        
        with open(experiment_file, 'w') as f:
            json.dump(experiment_data, f, indent=2)
    
    def log_training_run(
        self,
        experiment_id: str,
        run_id: int,
        metrics: Dict[str, float],
        model_id: Optional[int] = None,
        hyperparameters: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log a single training run within an experiment."""
        experiment_file = self.experiments_dir / f"{experiment_id}.json"
        
        if not experiment_file.exists():
            raise ValueError(f"Experiment {experiment_id} not found")
        
        with open(experiment_file, 'r') as f:
            experiment_data = json.load(f)
        
        run_data = {
            "run_id": run_id,
            "model_id": model_id,
            "hyperparameters": hyperparameters or {},
            "metrics": metrics,
            "timestamp": datetime.now().isoformat()
        }
        
        experiment_data["training_runs"].append(run_data)
        
        # Update best model if this one is better
        current_best = experiment_data.get("best_model_id")
        if model_id and (current_best is None or metrics.get("accuracy", 0) > experiment_data["metrics"].get("accuracy", 0)):
            experiment_data["best_model_id"] = model_id
            experiment_data["metrics"] = metrics
        
        with open(experiment_file, 'w') as f:
            json.dump(experiment_data, f, indent=2)
    
    def log_experiment_complete(
        self,
        experiment_id: str,
        final_metrics: Dict[str, float],
        best_model_id: Optional[int] = None
    ) -> None:
        """Log experiment completion."""
        experiment_file = self.experiments_dir / f"{experiment_id}.json"
        
        if not experiment_file.exists():
            raise ValueError(f"Experiment {experiment_id} not found")
        
        with open(experiment_file, 'r') as f:
            experiment_data = json.load(f)
        
        experiment_data["status"] = "completed"
        experiment_data["completed_at"] = datetime.now().isoformat()
        experiment_data["metrics"] = final_metrics
        if best_model_id:
            experiment_data["best_model_id"] = best_model_id
        
        with open(experiment_file, 'w') as f:
            json.dump(experiment_data, f, indent=2)
    
    def log_experiment_failed(
        self,
        experiment_id: str,
        error_message: str
    ) -> None:
        """Log experiment failure."""
        experiment_file = self.experiments_dir / f"{experiment_id}.json"
        
        if experiment_file.exists():
            with open(experiment_file, 'r') as f:
                experiment_data = json.load(f)
        else:
            experiment_data = {"experiment_id": experiment_id}
        
        experiment_data["status"] = "failed"
        experiment_data["completed_at"] = datetime.now().isoformat()
        experiment_data["error"] = error_message
        
        with open(experiment_file, 'w') as f:
            json.dump(experiment_data, f, indent=2)
    
    def get_experiment(self, experiment_id: str) -> Optional[Dict[str, Any]]:
        """Get experiment data by ID."""
        experiment_file = self.experiments_dir / f"{experiment_id}.json"
        
        if not experiment_file.exists():
            return None
        
        with open(experiment_file, 'r') as f:
            return json.load(f)
    
    def list_experiments(
        self,
        model_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """List experiments with optional filtering."""
        experiments = []
        
        for exp_file in sorted(self.experiments_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            with open(exp_file, 'r') as f:
                exp_data = json.load(f)
            
            if model_type and exp_data.get("model_type") != model_type:
                continue
            if status and exp_data.get("status") != status:
                continue
            
            experiments.append(exp_data)
            
            if len(experiments) >= limit:
                break
        
        return experiments
    
    def compare_experiments(
        self,
        experiment_ids: List[str],
        metric: str = "accuracy"
    ) -> Dict[str, Any]:
        """Compare multiple experiments on a specific metric."""
        comparison = {
            "metric": metric,
            "experiments": [],
            "best_experiment": None,
            "best_value": None
        }
        
        best_value = float('-inf')
        
        for exp_id in experiment_ids:
            exp_data = self.get_experiment(exp_id)
            if not exp_data:
                continue
            
            value = exp_data.get("metrics", {}).get(metric, 0)
            
            exp_summary = {
                "experiment_id": exp_id,
                "experiment_name": exp_data.get("experiment_name"),
                "model_type": exp_data.get("model_type"),
                "status": exp_data.get("status"),
                metric: value,
                "best_model_id": exp_data.get("best_model_id")
            }
            
            comparison["experiments"].append(exp_summary)
            
            if value > best_value:
                best_value = value
                comparison["best_experiment"] = exp_id
                comparison["best_value"] = value
        
        return comparison
