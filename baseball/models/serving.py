"""
Model Serving Layer

Provides fast inference for trained models with:
- Model loading/caching
- Batch prediction support
- A/B testing framework
- Performance metrics tracking

Usage:
    from baseball.models.serving import ModelServer
    
    server = ModelServer()
    
    # Load production model
    server.load_model('pitch_level', 'production')
    
    # Single prediction
    prediction = server.predict(features)
    
    # Batch prediction
    predictions = server.predict_batch(feature_batch)
"""

import pickle
import time
from typing import Optional, Any
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from baseball.core.db import get_db_connection
from baseball.models.registry import ModelRegistry


@dataclass
class PredictionResult:
    """Result from a model prediction."""
    prediction: Any
    probabilities: Optional[dict] = None
    confidence: Optional[float] = None
    inference_time_ms: float = 0.0
    model_version: str = ""
    
    
@dataclass
class BatchPredictionResult:
    """Result from batch prediction."""
    predictions: list
    probabilities: Optional[list] = None
    inference_time_ms: float = 0.0
    throughput: float = 0.0  # predictions per second
    model_version: str = ""


@dataclass
class ABTestConfig:
    """Configuration for A/B testing between models."""
    model_a: str
    model_b: str
    split_ratio: float = 0.5  # 0.5 = 50/50 split
    model_a_traffic: float = field(init=False)
    
    def __post_init__(self):
        self.model_a_traffic = self.split_ratio


class ModelCache:
    """
    LRU cache for loaded models.
    
    Avoids repeated disk I/O for frequently accessed models.
    """
    
    def __init__(self, max_size: int = 5):
        self.max_size = max_size
        self._cache: dict[str, Any] = {}
        self._access_times: dict[str, float] = {}
    
    def get(self, model_key: str) -> Optional[Any]:
        """Get model from cache."""
        if model_key in self._cache:
            self._access_times[model_key] = time.time()
            return self._cache[model_key]
        return None
    
    def put(self, model_key: str, model: Any) -> None:
        """Add model to cache."""
        # Evict oldest if at capacity
        if len(self._cache) >= self.max_size:
            oldest_key = min(self._access_times, key=self._access_times.get)
            del self._cache[oldest_key]
            del self._access_times[oldest_key]
        
        self._cache[model_key] = model
        self._access_times[model_key] = time.time()
    
    def clear(self) -> None:
        """Clear all cached models."""
        self._cache.clear()
        self._access_times.clear()


class ModelServer:
    """
    Model serving layer for real-time predictions.
    
    Features:
    - Fast model loading with LRU cache
    - Single and batch prediction
    - A/B testing support
    - Performance metrics tracking
    
    Usage:
        server = ModelServer()
        
        # Load production model
        server.load_model('pitch_level')
        
        # Predict
        result = server.predict(feature_vector)
        print(f"Prediction: {result.prediction} (confidence: {result.confidence:.2f})")
    """
    
    def __init__(self, cache_size: int = 5):
        self.registry = ModelRegistry()
        self.cache = ModelCache(max_size=cache_size)
        self._current_model: Optional[Any] = None
        self._current_version: str = ""
        self._ab_test_config: Optional[ABTestConfig] = None
        self._prediction_count: int = 0
    
    def load_model(
        self,
        model_name: str,
        version: str = 'production',
        artifact_path: Optional[str] = None
    ) -> bool:
        """
        Load a model for serving.
        
        Args:
            model_name: Model identifier
            version: 'production', 'staging', or specific version
            artifact_path: Direct path to model file (bypass registry)
            
        Returns:
            True if loaded successfully
        """
        cache_key = f"{model_name}:{version}"
        
        # Check cache first
        cached = self.cache.get(cache_key)
        if cached:
            self._current_model = cached
            self._current_version = version
            return True
        
        # Load from registry or path
        if artifact_path:
            model = self._load_from_path(artifact_path)
        elif version == 'production':
            entry = self.registry.get_production_model(model_name)
            if not entry:
                return False
            model = self._load_from_path(entry.artifact_path)
        else:
            entries = self.registry.list_models(model_name, status='staging')
            if not entries:
                return False
            entry = entries[0]
            model = self._load_from_path(entry.artifact_path)
        
        if model:
            self._current_model = model
            self._current_version = version
            self.cache.put(cache_key, model)
            return True
        
        return False
    
    def _load_from_path(self, path: str) -> Optional[Any]:
        """Load model from file path."""
        try:
            with open(path, 'rb') as f:
                return pickle.load(f)
        except Exception:
            return None
    
    def predict(
        self,
        features: np.ndarray,
        return_probs: bool = True
    ) -> PredictionResult:
        """
        Make a single prediction.
        
        Args:
            features: Feature vector (numpy array)
            return_probs: Return probability distribution
            
        Returns:
            PredictionResult with prediction and metadata
        """
        if self._current_model is None:
            raise RuntimeError("No model loaded. Call load_model() first.")
        
        start_time = time.perf_counter()
        
        # Handle different model types
        if hasattr(self._current_model, 'predict_proba'):
            probs = self._current_model.predict_proba(features.reshape(1, -1))[0]
            prediction = self._current_model.classes_[np.argmax(probs)]
            confidence = float(np.max(probs))
            prob_dict = {
                cls: float(prob) 
                for cls, prob in zip(self._current_model.classes_, probs)
            } if return_probs else None
        else:
            prediction = self._current_model.predict(features.reshape(1, -1))[0]
            prob_dict = None
            confidence = None
        
        inference_time = (time.perf_counter() - start_time) * 1000
        self._prediction_count += 1
        
        return PredictionResult(
            prediction=prediction,
            probabilities=prob_dict,
            confidence=confidence,
            inference_time_ms=inference_time,
            model_version=self._current_version
        )
    
    def predict_batch(
        self,
        features: np.ndarray,
        batch_size: int = 32
    ) -> BatchPredictionResult:
        """
        Make batch predictions.
        
        Args:
            features: Feature matrix (n_samples, n_features)
            batch_size: Process in chunks if large
            
        Returns:
            BatchPredictionResult with predictions and throughput
        """
        if self._current_model is None:
            raise RuntimeError("No model loaded. Call load_model() first.")
        
        n_samples = features.shape[0]
        start_time = time.perf_counter()
        
        # Process in batches if needed
        if n_samples > batch_size:
            predictions = []
            for i in range(0, n_samples, batch_size):
                batch = features[i:i + batch_size]
                batch_preds = self._current_model.predict(batch)
                predictions.extend(batch_preds)
        else:
            predictions = self._current_model.predict(features)
        
        inference_time = (time.perf_counter() - start_time) * 1000
        throughput = n_samples / (inference_time / 1000)
        self._prediction_count += n_samples
        
        return BatchPredictionResult(
            predictions=predictions.tolist() if hasattr(predictions, 'tolist') else list(predictions),
            inference_time_ms=inference_time,
            throughput=throughput,
            model_version=self._current_version
        )
    
    def setup_ab_test(self, model_a: str, model_b: str, split: float = 0.5) -> None:
        """
        Configure A/B test between two models.
        
        Args:
            model_a: First model name/version
            model_b: Second model name/version
            split: Traffic split to model_a (0.5 = 50/50)
        """
        self._ab_test_config = ABTestConfig(model_a, model_b, split)
    
    def predict_with_ab(
        self,
        features: np.ndarray,
        user_id: Optional[str] = None
    ) -> PredictionResult:
        """
        Predict with A/B test routing.
        
        Routes prediction to model A or B based on traffic split.
        Uses user_id hash for consistent routing if provided.
        
        Args:
            features: Feature vector
            user_id: Optional user identifier for consistent routing
            
        Returns:
            PredictionResult with model indicator
        """
        if not self._ab_test_config:
            return self.predict(features)
        
        # Determine which model to use
        if user_id:
            # Hash user_id for consistent routing
            import hashlib
            hash_val = int(hashlib.md5(user_id.encode()).hexdigest(), 16)
            use_model_a = (hash_val % 100) < (self._ab_test_config.split_ratio * 100)
        else:
            use_model_a = np.random.random() < self._ab_test_config.split_ratio
        
        # Load appropriate model
        model_key = self._ab_test_config.model_a if use_model_a else self._ab_test_config.model_b
        self.load_model(model_key)
        
        result = self.predict(features)
        
        # Add A/B metadata
        result.model_version = f"{'A' if use_model_a else 'B'}:{result.model_version}"
        
        return result
    
    def get_performance_stats(self) -> dict:
        """Get serving performance statistics."""
        return {
            'predictions_served': self._prediction_count,
            'model_version': self._current_version,
            'cache_size': len(self.cache._cache),
            'ab_test_active': self._ab_test_config is not None
        }
    
    def clear_cache(self) -> None:
        """Clear model cache."""
        self.cache.clear()


# Convenience functions
def load_model(model_name: str, version: str = 'production') -> ModelServer:
    """Quick function to load and return a configured ModelServer."""
    server = ModelServer()
    server.load_model(model_name, version)
    return server


def predict(features: np.ndarray, model_name: str = 'pitch_level') -> PredictionResult:
    """Quick function for one-off predictions."""
    server = load_model(model_name)
    return server.predict(features)
