"""Model server for loading and caching prediction models.

Provides efficient model loading, caching, and management for
production prediction serving.

Author: Agent cbwinslow/retrosheet
Date: 2026-04-26
"""

import hashlib
import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional, Tuple

import joblib
import psycopg2
from psycopg2.extensions import connection

logger = logging.getLogger(__name__)


@dataclass
class CachedPrediction:
    """Cached prediction result.
    
    Attributes:
        key: Cache key (hash of input features)
        result: Prediction result
        timestamp: When prediction was made
        ttl_seconds: Time to live in cache
    """
    key: str
    result: Any
    timestamp: float
    ttl_seconds: int = 300  # 5 minute default TTL
    
    @property
    def is_expired(self) -> bool:
        """Check if cache entry has expired."""
        return (time.time() - self.timestamp) > self.ttl_seconds
    
    @property
    def age_seconds(self) -> float:
        """Get age of cache entry in seconds."""
        return time.time() - self.timestamp


class ModelCache:
    """LRU cache for prediction results.
    
    Caches predictions to reduce compute load and latency.
    Uses input feature hashing for cache keys.
    
    Example:
        >>> cache = ModelCache(max_size=10000, default_ttl=300)
        >>> 
        >>> # Check cache
        >>> cached = cache.get(features_dict)
        >>> if cached:
        >>>     return cached
        >>> 
        >>> # Compute and cache
        >>> result = model.predict(features)
        >>> cache.set(features_dict, result)
    """
    
    def __init__(self, max_size: int = 10000, default_ttl: int = 300):
        """Initialize model cache.
        
        Args:
            max_size: Maximum number of cached predictions
            default_ttl: Default time-to-live in seconds
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: Dict[str, CachedPrediction] = {}
        self._lock = Lock()
        self._hits = 0
        self._misses = 0
    
    def _make_key(self, features: Dict[str, Any]) -> str:
        """Create cache key from features.
        
        Args:
            features: Feature dictionary
            
        Returns:
            Hash string for cache lookup
        """
        # Sort keys for consistent hashing
        feature_str = json.dumps(features, sort_keys=True, default=str)
        return hashlib.md5(feature_str.encode()).hexdigest()
    
    def get(self, features: Dict[str, Any]) -> Optional[Any]:
        """Get cached prediction if available.
        
        Args:
            features: Input features
            
        Returns:
            Cached result or None
        """
        key = self._make_key(features)
        
        with self._lock:
            cached = self._cache.get(key)
            
            if cached is None:
                self._misses += 1
                return None
            
            if cached.is_expired:
                del self._cache[key]
                self._misses += 1
                return None
            
            self._hits += 1
            return cached.result
    
    def set(self, features: Dict[str, Any], result: Any, 
            ttl: Optional[int] = None) -> None:
        """Cache prediction result.
        
        Args:
            features: Input features
            result: Prediction result
            ttl: Time-to-live (uses default if not specified)
        """
        key = self._make_key(features)
        ttl = ttl or self.default_ttl
        
        with self._lock:
            # Evict oldest if at capacity
            if len(self._cache) >= self.max_size:
                self._evict_oldest()
            
            self._cache[key] = CachedPrediction(
                key=key,
                result=result,
                timestamp=time.time(),
                ttl_seconds=ttl
            )
    
    def _evict_oldest(self) -> None:
        """Evict oldest cache entries when at capacity."""
        # Remove expired entries first
        expired = [k for k, v in self._cache.items() if v.is_expired]
        for k in expired:
            del self._cache[k]
        
        # If still at capacity, remove oldest
        if len(self._cache) >= self.max_size:
            oldest = min(self._cache.items(), key=lambda x: x[1].timestamp)
            del self._cache[oldest[0]]
    
    def clear(self) -> None:
        """Clear all cached predictions."""
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics.
        
        Returns:
            Dictionary with cache stats
        """
        with self._lock:
            total = self._hits + self._misses
            hit_rate = self._hits / total if total > 0 else 0
            
            return {
                'size': len(self._cache),
                'max_size': self.max_size,
                'hits': self._hits,
                'misses': self._misses,
                'hit_rate': hit_rate,
                'expired': sum(1 for v in self._cache.values() if v.is_expired),
            }
    
    def invalidate(self, pattern: Optional[str] = None) -> int:
        """Invalidate cache entries.
        
        Args:
            pattern: Optional key pattern to match (None = all)
            
        Returns:
            Number of entries invalidated
        """
        with self._lock:
            if pattern is None:
                count = len(self._cache)
                self._cache.clear()
                return count
            
            to_remove = [k for k in self._cache.keys() if pattern in k]
            for k in to_remove:
                del self._cache[k]
            return len(to_remove)


class ModelServer:
    """Server for loading and serving prediction models.
    
    Manages model lifecycle:
    - Loading from disk or database
    - Version management
    - Hot-swapping
    - Health checks
    
    Example:
        >>> server = ModelServer(db_connection=conn, model_dir='models')
        >>> 
        >>> # Load latest production model
        >>> server.load_model('next_run', 'production')
        >>> 
        >>> # Make prediction
        >>> result = server.predict('next_run', features)
        >>> 
        >>> # Health check
        >>> health = server.health_check()
        >>> print(f"Models loaded: {health['models_loaded']}")
    """
    
    def __init__(self, db_connection: Optional[connection] = None,
                 model_dir: str = 'models',
                 enable_cache: bool = True,
                 cache_size: int = 10000):
        """Initialize model server.
        
        Args:
            db_connection: Database connection for metadata
            model_dir: Directory containing model files
            enable_cache: Whether to enable prediction caching
            cache_size: Maximum cache size
        """
        self.db = db_connection
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(exist_ok=True)
        
        # Model storage
        self._models: Dict[str, Any] = {}  # model_name -> model object
        self._model_versions: Dict[str, str] = {}  # model_name -> version
        self._model_metadata: Dict[str, Dict] = {}  # model_name -> metadata
        self._lock = Lock()
        
        # Prediction cache
        self._cache = ModelCache(max_size=cache_size) if enable_cache else None
        
        # Server stats
        self._start_time = time.time()
        self._prediction_count = 0
        self._error_count = 0
    
    def load_model(self, model_name: str, version: str = 'latest') -> bool:
        """Load a model from disk.
        
        Args:
            model_name: Model name ('next_run' or 'pa_outcome')
            version: Model version ('latest', 'production', or specific)
            
        Returns:
            True if successful
        """
        try:
            # Resolve version
            if version == 'latest':
                version = self._get_latest_version(model_name)
            elif version == 'production':
                version = self._get_production_version(model_name)
            
            model_path = self.model_dir / f'{model_name}_{version}.joblib'
            
            if not model_path.exists():
                logger.error(f'Model file not found: {model_path}')
                return False
            
            # Load model
            logger.info(f'Loading {model_name} model from {model_path}')
            data = joblib.load(model_path)
            
            with self._lock:
                self._models[model_name] = data['model']
                self._model_versions[model_name] = version
                self._model_metadata[model_name] = {
                    'version': version,
                    'loaded_at': time.time(),
                    'path': str(model_path),
                    'config': data.get('config', {}),
                }
            
            logger.info(f'Model {model_name} v{version} loaded successfully')
            return True
            
        except Exception as e:
            logger.error(f'Failed to load model {model_name}: {e}')
            return False
    
    def _get_latest_version(self, model_name: str) -> str:
        """Get latest version from filesystem."""
        pattern = f'{model_name}_*.joblib'
        files = list(self.model_dir.glob(pattern))
        
        if not files:
            return 'unknown'
        
        # Sort by modification time
        latest = max(files, key=lambda p: p.stat().st_mtime)
        # Extract version from filename
        version = latest.stem.replace(f'{model_name}_', '')
        return version
    
    def _get_production_version(self, model_name: str) -> str:
        """Get production version from database."""
        if self.db is None:
            return self._get_latest_version(model_name)
        
        try:
            with self.db.cursor() as cur:
                cur.execute('''
                    SELECT model_version 
                    FROM models.model_versions 
                    WHERE model_type = %s AND status = 'production'
                    ORDER BY promoted_at DESC
                    LIMIT 1
                ''', (model_name,))
                
                row = cur.fetchone()
                if row:
                    return row[0]
        except Exception as e:
            logger.error(f'Failed to get production version: {e}')
        
        return self._get_latest_version(model_name)
    
    def unload_model(self, model_name: str) -> bool:
        """Unload a model from memory.
        
        Args:
            model_name: Model to unload
            
        Returns:
            True if successful
        """
        with self._lock:
            if model_name in self._models:
                del self._models[model_name]
                del self._model_versions[model_name]
                del self._model_metadata[model_name]
                logger.info(f'Model {model_name} unloaded')
                return True
        return False
    
    def predict(self, model_name: str, features: Dict[str, Any],
                use_cache: bool = True) -> Optional[Dict[str, Any]]:
        """Make a prediction using loaded model.
        
        Args:
            model_name: Model to use
            features: Input features
            use_cache: Whether to use prediction cache
            
        Returns:
            Prediction result or None if failed
        """
        self._prediction_count += 1
        
        # Check cache first
        if use_cache and self._cache:
            cached = self._cache.get(features)
            if cached is not None:
                return cached
        
        # Get model
        with self._lock:
            model = self._models.get(model_name)
            if model is None:
                logger.error(f'Model {model_name} not loaded')
                self._error_count += 1
                return None
        
        try:
            # Make prediction
            if model_name == 'next_run':
                result = self._predict_next_run(model, features)
            elif model_name == 'pa_outcome':
                result = self._predict_pa_outcome(model, features)
            else:
                logger.error(f'Unknown model type: {model_name}')
                return None
            
            # Cache result
            if self._cache and use_cache:
                self._cache.set(features, result)
            
            return result
            
        except Exception as e:
            logger.error(f'Prediction failed: {e}')
            self._error_count += 1
            return None
    
    def _predict_next_run(self, model, features: Dict[str, Any]) -> Dict[str, Any]:
        """Make next-run prediction."""
        import numpy as np
        
        # Build feature vector
        feature_vector = self._build_feature_vector(features, 'next_run')
        X = np.array([feature_vector])
        
        # Predict
        if hasattr(model, 'predict_proba'):
            prob = model.predict_proba(X)[0, 1]
        else:
            prob = float(model.predict(X)[0])
        
        return {
            'model': 'next_run',
            'run_probability': float(prob),
            'prediction': prob > 0.5,
            'confidence': abs(prob - 0.5) * 2,
            'timestamp': time.time(),
        }
    
    def _predict_pa_outcome(self, model, features: Dict[str, Any]) -> Dict[str, Any]:
        """Make PA outcome prediction."""
        import numpy as np
        
        # Build feature vector
        feature_vector = self._build_feature_vector(features, 'pa_outcome')
        X = np.array([feature_vector])
        
        # Predict probabilities
        if hasattr(model, 'predict_proba'):
            probs = model.predict_proba(X)[0]
        else:
            # One-hot encode single prediction
            pred = int(model.predict(X)[0])
            probs = np.zeros(6)
            probs[pred] = 1.0
        
        classes = ['out', 'walk', 'single', 'double', 'triple', 'home_run']
        prob_dict = {cls: float(probs[i]) for i, cls in enumerate(classes)}
        
        predicted_class = classes[np.argmax(probs)]
        
        return {
            'model': 'pa_outcome',
            'predicted_outcome': predicted_class,
            'probabilities': prob_dict,
            'prob_hit': sum(prob_dict[c] for c in ['single', 'double', 'triple', 'home_run']),
            'prob_on_base': sum(prob_dict[c] for c in ['walk', 'single', 'double', 'triple', 'home_run']),
            'confidence': float(np.max(probs)),
            'timestamp': time.time(),
        }
    
    def _build_feature_vector(self, features: Dict[str, Any], 
                             model_type: str) -> List[float]:
        """Build feature vector from feature dictionary."""
        # This would use the same feature columns as training
        # For now, extract common features
        vector = [
            float(features.get('inning', 1)),
            float(features.get('outs', 0)),
            float(features.get('base_state', 0)),
            float(features.get('run_diff', 0)),
            float(features.get('we', 0.5)),
            float(features.get('li', 1.0)),
            float(features.get('matchup_score', 0.5)),
            float(features.get('batter_l14_ops', 0.7)),
            float(features.get('pitcher_l14_era', 4.5)),
        ]
        return vector
    
    def get_loaded_models(self) -> List[str]:
        """Get list of loaded model names."""
        with self._lock:
            return list(self._models.keys())
    
    def get_model_info(self, model_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a loaded model."""
        with self._lock:
            metadata = self._model_metadata.get(model_name)
            if metadata:
                return {
                    'name': model_name,
                    'version': metadata['version'],
                    'loaded_at': metadata['loaded_at'],
                    'path': metadata['path'],
                    'config': metadata.get('config', {}),
                }
        return None
    
    def health_check(self) -> Dict[str, Any]:
        """Perform health check.
        
        Returns:
            Health status dictionary
        """
        with self._lock:
            uptime = time.time() - self._start_time
            
            return {
                'status': 'healthy' if self._models else 'degraded',
                'uptime_seconds': uptime,
                'models_loaded': len(self._models),
                'model_names': list(self._models.keys()),
                'predictions_served': self._prediction_count,
                'errors': self._error_count,
                'error_rate': self._error_count / max(1, self._prediction_count),
                'cache_stats': self._cache.get_stats() if self._cache else None,
            }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get server statistics."""
        return {
            'uptime_seconds': time.time() - self._start_time,
            'predictions_served': self._prediction_count,
            'error_count': self._error_count,
            'models_loaded': len(self._models),
            'cache': self._cache.get_stats() if self._cache else None,
        }
    
    def reload_all(self) -> Dict[str, bool]:
        """Reload all models.
        
        Returns:
            Dictionary of model names to success status
        """
        results = {}
        
        for model_name in list(self._models.keys()):
            version = self._model_versions.get(model_name, 'latest')
            # Unload first
            self.unload_model(model_name)
            # Reload
            results[model_name] = self.load_model(model_name, version)
        
        return results
