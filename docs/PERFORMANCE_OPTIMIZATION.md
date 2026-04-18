# Performance Optimization Guide

This document describes performance optimization strategies for the Retrosheet Prediction Warehouse, focusing on prediction serving latency, database query optimization, and model loading performance.

## Current Performance Baseline

### Prediction Serving Latency

**Historical Scorer** (`scripts/predict_pa_outcome_distribution.py`):
- Model loading: ~1-2 seconds (first request)
- Feature query: ~50-100ms
- Prediction inference: ~10-50ms
- Total latency: ~100-200ms (warm), ~1-2s (cold)

**Live Scorer** (`scripts/predict_live_pa_outcome_distribution.py`):
- Model loading: ~1-2 seconds (first request)
- Feature query: ~50-100ms
- Prediction inference: ~10-50ms
- Persistence: ~20-50ms
- Total latency: ~150-300ms (warm), ~1.5-2.5s (cold)

### Database Query Performance

**Feature Queries:**
- Single plate appearance feature lookup: ~50-100ms
- Batch feature lookup (100 records): ~200-500ms
- Historical feature aggregation: ~500ms-2s

**Live Data Queries:**
- Live game state lookup: ~20-50ms
- Live events lookup: ~30-80ms
- Combined live feature query: ~50-150ms

## Optimization Strategies

### 1. Model Loading Optimization

**Current Issues:**
- Models loaded from disk on every script invocation
- No model caching between requests
- Cold start penalty on first prediction

**Solutions:**

**A. Model Caching Service**
```python
# scripts/lib/model_cache.py
import joblib
from functools import lru_cache
from pathlib import Path
from typing import Any

class ModelCache:
    """Cache for loaded models to avoid repeated disk I/O."""
    
    def __init__(self, max_size: int = 10):
        self.max_size = max_size
        self.cache = {}
    
    def get(self, model_path: Path) -> Any:
        """Get model from cache or load from disk."""
        cache_key = str(model_path)
        
        if cache_key not in self.cache:
            if len(self.cache) >= self.max_size:
                # Remove least recently used
                self.cache.pop(next(iter(self.cache)))
            self.cache[cache_key] = joblib.load(model_path)
        
        return self.cache[cache_key]

# Global model cache instance
model_cache = ModelCache()
```

**B. Pre-load Models on Service Start**
```python
# In API route or service initialization
from retrosheet.prediction import load_registered_model, DEFAULT_MODEL_NAME

# Pre-load active models
ACTIVE_MODELS = [
    (DEFAULT_MODEL_NAME, None),  # Use active version
    # Add other models as needed
]

for model_name, model_version in ACTIVE_MODELS:
    model, feature_spec, metadata = load_registered_model(
        model_name=model_name,
        model_version=model_version,
    )
    # Store in cache
```

**Expected Improvement:**
- Cold start: 1-2s → ~50ms (90-95% reduction)
- Warm latency: No change (already fast)

### 2. Database Query Optimization

**Current Issues:**
- No query result caching
- No connection pooling
- Suboptimal indexes for feature queries
- N+1 query pattern in some operations

**Solutions:**

**A. Query Result Caching**
```python
# scripts/lib/query_cache.py
from functools import lru_cache
from typing import Any
import hashlib
import json

def cache_key(query: str, params: dict) -> str:
    """Generate cache key from query and parameters."""
    key_str = query + json.dumps(params, sort_keys=True)
    return hashlib.md5(key_str.encode()).hexdigest()

@lru_cache(maxsize=1000)
def cached_query(cache_key: str, query_fn):
    """Cache query results."""
    return query_fn()

# Usage in prediction scripts
def get_features_cached(game_id: str, plate_appearance_id: int) -> pd.DataFrame:
    """Get features with caching."""
    cache_key = f"{game_id}:{plate_appearance_id}"
    return cached_query(cache_key, lambda: get_features_uncached(game_id, plate_appearance_id))
```

**B. Connection Pooling**
```python
# In database configuration
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

engine = create_engine(
    database_url(),
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,  # Verify connections before use
    pool_recycle=3600,  # Recycle connections after 1 hour
)
```

**C. Index Optimization**
```sql
-- Add composite indexes for common feature query patterns
CREATE INDEX IF NOT EXISTS idx_plate_appearance_game_pa
    ON core.plate_appearances (game_id, plate_appearance_id);

CREATE INDEX IF NOT EXISTS idx_events_game_inning
    ON core.events (game_id, inning, is_bottom_inning);

CREATE INDEX IF NOT EXISTS idx_features_pa_season
    ON features.plate_appearance_advanced_examples (plate_appearance_id, feature_season);
```

**D. Batch Feature Loading**
```python
# Instead of loading features one at a time
def get_features_batch(plate_appearance_ids: list[int]) -> pd.DataFrame:
    """Load features for multiple plate appearances in one query."""
    query = f"""
        SELECT * FROM features.plate_appearance_advanced_examples
        WHERE plate_appearance_id IN ({','.join(map(str, plate_appearance_ids))})
    """
    return pd.read_sql(query, engine)
```

**Expected Improvement:**
- Feature query: 50-100ms → ~20-40ms (50-60% reduction)
- Batch query (100 records): 200-500ms → ~50-100ms (75-80% reduction)

### 3. Prediction Inference Optimization

**Current Issues:**
- No vectorized batch prediction
- Calibration applied individually
- No prediction result caching

**Solutions:**

**A. Batch Prediction Support**
```python
# In retrosheet/prediction/pa_service.py
def predict_batch(
    frames: list[pd.DataFrame],
    model: Any,
    feature_spec: dict[str, Any],
    apply_calibration: bool = True,
) -> list[dict[str, Any]]:
    """Make predictions for multiple feature frames in batch."""
    # Combine frames into single DataFrame
    combined_df = pd.concat(frames, ignore_index=True)
    
    # Extract features
    features = combined_df[feature_spec['numeric_features'] + feature_spec['categorical_features']]
    
    # Batch prediction
    raw_probabilities = model.predict_proba(features)
    
    # Apply calibration if needed
    if apply_calibration:
        raw_probabilities = apply_calibrators(raw_probabilities, calibrators)
    
    # Split results back to individual predictions
    results = []
    for i, frame in enumerate(frames):
        result = {
            'game_id': frame['game_id'].iloc[0],
            'plate_appearance_id': frame['plate_appearance_id'].iloc[0],
            'class_probabilities': dict(zip(model.classes_, raw_probabilities[i])),
            'derived_probabilities': derived_probabilities(
                dict(zip(model.classes_, raw_probabilities[i]))
            ),
        }
        results.append(result)
    
    return results
```

**B. Prediction Result Caching**
```python
# Cache predictions for identical feature sets
@lru_cache(maxsize=5000)
def predict_cached(
    feature_hash: str,
    model_id: int,
) -> dict[str, Any]:
    """Cache prediction results by feature hash."""
    # Compute prediction
    result = predict_uncached(features, model_id)
    return result

def compute_feature_hash(frame: pd.DataFrame) -> str:
    """Compute hash of feature frame for caching."""
    feature_values = frame.to_dict('records')[0]
    feature_str = json.dumps(feature_values, sort_keys=True)
    return hashlib.md5(feature_str.encode()).hexdigest()
```

**Expected Improvement:**
- Batch prediction (100 records): 1-5s → ~100-300ms (90-95% reduction)
- Cached predictions: ~10-50ms → ~1-5ms (90-95% reduction)

### 4. Calibration Optimization

**Current Issues:**
- Calibrators loaded separately from model
- No calibration caching
- Calibration applied per-prediction

**Solutions:**

**A. Bundle Calibration with Model**
```python
# During model registration, bundle calibrators
def register_model_with_calibration(
    model: Any,
    calibrators: list[Any],
    feature_spec: dict[str, Any],
    metrics: dict[str, Any],
) -> int:
    """Register model with bundled calibrators."""
    # Save model with calibrators
    artifact_bundle = {
        'model': model,
        'calibrators': calibrators,
        'feature_spec': feature_spec,
    }
    artifact_path = ROOT / f"data/models/{model_name}_{model_version}.pkl"
    joblib.dump(artifact_bundle, artifact_path)
    
    # Register in database
    # ... (registration logic)
```

**B. Calibration Lookup Table**
```python
# Pre-compute calibration for common probability ranges
def build_calibration_lookup(calibrator: Any, bins: int = 100) -> dict:
    """Build lookup table for fast calibration."""
    lookup = {}
    for i in range(bins):
        prob = i / bins
        calibrated = calibrator.predict_proba([[prob]])[0][0]
        lookup[prob] = calibrated
    return lookup

# Use lookup table instead of calibrator.predict_proba
def apply_calibration_lookup(
    probability: float,
    lookup: dict,
) -> float:
    """Apply calibration using lookup table."""
    bin_key = round(probability, 2)  # Round to 2 decimal places
    return lookup.get(bin_key, probability)
```

**Expected Improvement:**
- Calibration overhead: ~5-10ms → ~1-2ms (80% reduction)

## Performance Benchmarks

### Target Performance Metrics

| Metric | Current | Target | Improvement |
|--------|---------|--------|-------------|
| Cold start latency | 1-2s | < 500ms | 75% |
| Warm latency | 100-200ms | < 50ms | 50-75% |
| Batch prediction (100) | 1-5s | < 500ms | 90% |
| Feature query | 50-100ms | < 30ms | 50-70% |
| Model loading | 1-2s | < 100ms | 95% |

### Benchmarking Script

```python
# scripts/benchmark_prediction.py
import time
import statistics
from typing import Callable

def benchmark(fn: Callable, iterations: int = 100) -> dict:
    """Benchmark a function over multiple iterations."""
    times = []
    
    for _ in range(iterations):
        start = time.perf_counter()
        fn()
        end = time.perf_counter()
        times.append((end - start) * 1000)  # Convert to ms
    
    return {
        'mean_ms': statistics.mean(times),
        'median_ms': statistics.median(times),
        'p95_ms': statistics.quantiles(times, n=100)[94],
        'p99_ms': statistics.quantiles(times, n=100)[98],
        'min_ms': min(times),
        'max_ms': max(times),
    }

# Usage
results = benchmark(
    lambda: predict_pa_outcome_distribution(
        game_id="test_game",
        plate_appearance_id=1,
    ),
    iterations=100
)
print(results)
```

## Implementation Roadmap

### Phase 1: Quick Wins (Week 1)
- [ ] Add connection pooling to database configuration
- [ ] Add composite indexes for feature queries
- [ ] Implement model caching service
- [ ] Add prediction result caching

### Phase 2: Query Optimization (Week 2)
- [ ] Implement query result caching
- [ ] Optimize feature queries with batch loading
- [ ] Add EXPLAIN ANALYZE profiling
- [ ] Document query performance patterns

### Phase 3: Inference Optimization (Week 3)
- [ ] Implement batch prediction support
- [ ] Bundle calibration with model
- [ ] Build calibration lookup tables
- [ ] Add performance benchmarking script

### Phase 4: Monitoring (Week 4)
- [ ] Add performance metrics to reliability dashboard
- [ ] Set up performance alerting
- [ ] Create performance regression tests
- [ ] Document performance benchmarks

## Monitoring

### Performance Metrics to Track

**Database Metrics:**
- Query execution time (P50, P95, P99)
- Connection pool utilization
- Cache hit rate
- Index usage statistics

**Prediction Metrics:**
- Model loading time
- Feature query time
- Inference time
- Total end-to-end latency
- Cache hit rate

**System Metrics:**
- CPU utilization
- Memory usage
- Disk I/O
- Network latency

### Alerting Thresholds

| Metric | Warning | Critical |
|--------|---------|----------|
| P95 latency | > 100ms | > 500ms |
| P99 latency | > 200ms | > 1s |
| Cache hit rate | < 50% | < 20% |
| Connection pool utilization | > 80% | > 95% |

## Best Practices

### Database Query Optimization
- Use EXPLAIN ANALYZE to profile slow queries
- Add appropriate indexes for common query patterns
- Use batch operations instead of loops
- Avoid SELECT *, select only needed columns
- Use connection pooling to reduce overhead

### Model Serving Optimization
- Cache models in memory to avoid disk I/O
- Use batch prediction for multiple requests
- Cache prediction results for identical inputs
- Bundle calibration with model artifacts
- Pre-load models on service start

### Code Optimization
- Profile code before optimizing
- Focus on hot paths (frequently called functions)
- Use vectorized operations (NumPy, Pandas)
- Avoid unnecessary data copies
- Use appropriate data structures

## Future Work

- [ ] Implement GPU acceleration for model inference
- [ ] Explore model quantization for faster inference
- [ ] Implement distributed prediction serving
- [ ] Add A/B testing for performance optimizations
- [ ] Implement automatic performance regression detection
