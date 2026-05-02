"""
Training Pipeline Orchestrator

Unified interface for running training experiments.
Wraps and extends the existing TrainingPipeline from baseball.models.training.
"""

import time
from typing import Any, Dict, List, Optional

from baseball.models.training import TrainingPipeline, TrainingResult
from baseball.models.registry import ModelRegistry

from .config import ExperimentConfig, ExperimentResult, ModelType, TrainingConfig, create_default_config
from .tracker import ExperimentTracker


class TrainingOrchestrator:
    """
    Orchestrates training experiments with multiple configurations.
    
    Wraps the existing TrainingPipeline and adds:
    - Experiment tracking
    - Multiple configuration runs
    - Comparison with baselines
    - Automatic best model selection
    
    Usage:
        from baseball.training import TrainingOrchestrator, ExperimentConfig
        
        orchestrator = TrainingOrchestrator()
        
        # Run with default config
        result = orchestrator.run_experiment(
            model_type=ModelType.PITCH_LEVEL,
            seasons=[2020, 2021, 2022, 2023, 2024],
            experiment_name='pitch_v1'
        )
        
        # Run with custom configs
        config1 = TrainingConfig(seasons=[2022, 2023, 2024], hyperparameters={'n_estimators': 100})
        config2 = TrainingConfig(seasons=[2022, 2023, 2024], hyperparameters={'n_estimators': 200})
        
        result = orchestrator.run_experiment_with_configs(
            experiment_name='pitch_grid_search',
            model_type=ModelType.PITCH_LEVEL,
            configs=[config1, config2]
        )
    """
    
    def __init__(
        self,
        artifacts_dir: str = "models/artifacts",
        experiments_dir: str = "models/experiments"
    ):
        """Initialize the orchestrator."""
        self.artifacts_dir = artifacts_dir
        self.tracker = ExperimentTracker(experiments_dir)
        self.registry = ModelRegistry(artifacts_dir)
    
    def run_experiment(
        self,
        model_type: ModelType,
        seasons: List[int],
        experiment_name: str,
        description: str = "",
        hyperparameter_overrides: Optional[Dict[str, Any]] = None,
        feature_set: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        promote_best: bool = False
    ) -> ExperimentResult:
        """
        Run a training experiment with default configuration.
        
        Args:
            model_type: Type of model to train
            seasons: List of seasons for training data
            experiment_name: Name for this experiment
            description: Optional description
            hyperparameter_overrides: Override default hyperparameters
            feature_set: Optional specific feature set to use
            tags: Optional tags for the experiment
            promote_best: Whether to promote best model to production
        
        Returns:
            ExperimentResult with all training runs and best model
        """
        # Create default config with overrides
        config = create_default_config(
            model_type,
            seasons,
            feature_set=feature_set,
            **(hyperparameter_overrides or {})
        )
        
        return self.run_experiment_with_configs(
            experiment_name=experiment_name,
            model_type=model_type,
            configs=[config],
            description=description,
            tags=tags,
            promote_best=promote_best
        )
    
    def run_experiment_with_configs(
        self,
        experiment_name: str,
        model_type: ModelType,
        configs: List[TrainingConfig],
        description: str = "",
        tags: Optional[List[str]] = None,
        compare_baseline: bool = True,
        promote_best: bool = False
    ) -> ExperimentResult:
        """
        Run experiment with multiple training configurations.
        
        Args:
            experiment_name: Name for this experiment
            model_type: Type of model to train
            configs: List of training configurations to try
            description: Optional description
            tags: Optional tags for the experiment
            compare_baseline: Whether to compare with baseline model
            promote_best: Whether to promote best model to production
        
        Returns:
            ExperimentResult with all runs and best model
        """
        # Create experiment config
        exp_config = ExperimentConfig(
            experiment_name=experiment_name,
            model_type=model_type,
            description=description,
            tags=tags or [],
            training_configs=configs,
            compare_baseline=compare_baseline
        )
        
        # Initialize result
        result = ExperimentResult(
            experiment_id=exp_config.experiment_id,
            experiment_name=experiment_name,
            model_type=model_type,
            training_results=[],
            status="running"
        )
        
        # Log experiment start
        self.tracker.log_experiment_start(
            exp_config.experiment_id,
            experiment_name,
            model_type.value,
            {
                "description": description,
                "tags": tags,
                "num_configs": len(configs)
            }
        )
        
        start_time = time.time()
        
        try:
            # Run each configuration
            best_model_id = None
            best_accuracy = 0.0
            
            for i, config in enumerate(configs):
                print(f"\nRunning configuration {i+1}/{len(configs)}...")
                
                # Get model class based on type
                model_class = self._get_model_class(model_type)
                
                # Create and run training pipeline
                pipeline = TrainingPipeline(
                    model_class=model_class,
                    model_name=f"{experiment_name}_run_{i}",
                    version="1.0.0",
                    artifacts_dir=self.artifacts_dir
                )
                
                training_result = pipeline.train(
                    seasons=config.seasons,
                    test_size=config.test_size,
                    cv_folds=config.cv_folds,
                    hyperparameters=config.hyperparameters,
                    feature_set=config.feature_set,
                    promote_to_production=False  # We'll promote the best at the end
                )
                
                result.training_results.append(training_result)
                
                # Log this run
                if training_result.success:
                    accuracy = training_result.metrics.get("accuracy", 0)
                    self.tracker.log_training_run(
                        exp_config.experiment_id,
                        run_id=i,
                        metrics=training_result.metrics,
                        model_id=training_result.model_id,
                        hyperparameters=config.hyperparameters
                    )
                    
                    # Track best model
                    if accuracy > best_accuracy:
                        best_accuracy = accuracy
                        best_model_id = training_result.model_id
                else:
                    print(f"  Warning: Run {i} failed: {training_result.error_message}")
            
            # Promote best model if requested
            if promote_best and best_model_id:
                print(f"\nPromoting best model (ID: {best_model_id}) to production...")
                self.registry.promote_to_production(best_model_id)
            
            # Calculate improvement vs baseline if we have comparison data
            vs_baseline = None
            if compare_baseline and best_model_id:
                vs_baseline = self._calculate_vs_baseline(
                    model_type, best_accuracy
                )
            
            # Update result
            result.best_model_id = best_model_id
            result.best_metric = best_accuracy
            result.vs_baseline_improvement = vs_baseline
            result.status = "completed"
            result.completed_at = time.isoformat()
            result.duration_seconds = time.time() - start_time
            
            # Log experiment completion
            final_metrics = {"accuracy": best_accuracy}
            if result.training_results:
                # Aggregate other metrics from best run
                for tr in result.training_results:
                    if tr.model_id == best_model_id and tr.metrics:
                        final_metrics.update(tr.metrics)
                        break
            
            self.tracker.log_experiment_complete(
                exp_config.experiment_id,
                final_metrics,
                best_model_id
            )
            
        except Exception as e:
            result.status = "failed"
            result.duration_seconds = time.time() - start_time
            self.tracker.log_experiment_failed(exp_config.experiment_id, str(e))
            raise
        
        return result
    
    def _get_model_class(self, model_type: ModelType):
        """Get the appropriate model class for the model type."""
        # Import here to avoid circular dependencies
        if model_type == ModelType.PITCH_LEVEL:
            from baseball.models.pitch_level import PitchLevelModel
            return PitchLevelModel
        elif model_type == ModelType.PA_OUTCOME:
            from baseball.models.pa_outcome import PAOutcomeModel
            return PAOutcomeModel
        elif model_type == ModelType.WIN_PROBABILITY:
            from baseball.models.win_probability_model import WinProbabilityModel
            return WinProbabilityModel
        elif model_type == ModelType.SWING_PROBABILITY:
            from baseball.models.swing_probability import SwingProbabilityModel
            return SwingProbabilityModel
        elif model_type == ModelType.CONTACT_PROBABILITY:
            from baseball.models.contact_probability import ContactProbabilityModel
            return ContactProbabilityModel
        else:
            from baseball.models.base import BaseModel
            return BaseModel
    
    def _calculate_vs_baseline(
        self,
        model_type: ModelType,
        new_accuracy: float
    ) -> Optional[float]:
        """Calculate improvement vs baseline model."""
        try:
            # Get production model as baseline
            prod_model = self.registry.get_production_model(model_type.value)
            if prod_model and hasattr(prod_model, 'metadata'):
                baseline_accuracy = prod_model.metadata.get('accuracy', 0)
                if baseline_accuracy > 0:
                    return new_accuracy - baseline_accuracy
        except Exception:
            pass
        return None
    
    def list_experiments(
        self,
        model_type: Optional[ModelType] = None,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """List experiments with optional filtering."""
        return self.tracker.list_experiments(
            model_type=model_type.value if model_type else None,
            status=status,
            limit=limit
        )
    
    def get_experiment(self, experiment_id: str) -> Optional[Dict[str, Any]]:
        """Get experiment details by ID."""
        return self.tracker.get_experiment(experiment_id)
    
    def compare_experiments(
        self,
        experiment_ids: List[str],
        metric: str = "accuracy"
    ) -> Dict[str, Any]:
        """Compare multiple experiments."""
        return self.tracker.compare_experiments(experiment_ids, metric)
    
    def get_best_model_from_experiment(
        self,
        experiment_id: str
    ) -> Optional[int]:
        """Get the best model ID from an experiment."""
        exp_data = self.tracker.get_experiment(experiment_id)
        if exp_data:
            return exp_data.get("best_model_id")
        return None
