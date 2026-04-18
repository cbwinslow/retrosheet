# Feature Store Architecture

This document describes the design and architecture of the feature store for the Retrosheet Prediction Warehouse.

## Overview

The feature store provides centralized management of ML features for both historical training and live inference. It ensures feature consistency, enables efficient feature reuse, and supports feature versioning and quality monitoring.

## Current Architecture

### Batch Feature Store (PostgreSQL)

The current implementation uses PostgreSQL as the batch feature store:

- **Feature Tables**: `features.*` schema tables store pre-computed features
- **Feature Marts**: Materialized views for specific modeling targets
- **Feature Views**: Views for feature lookup during inference
- **Temporal Partitioning**: Features organized by season for efficient querying

### Live Feature Extraction

Live features are computed on-demand during inference:

- **Live Scorer**: `scripts/predict_live_pa_outcome_distribution.py` computes features from live game state
- **Feature Query**: SQL queries extract features from `core.live_games` and `core.live_events`
- **State Snapshot**: Game state captured for logging and debugging

## Proposed Enhancements

### DuckDB for Batch Feature Store

**Rationale:**
- DuckDB provides OLAP performance for analytical queries
- Columnar storage optimized for feature lookups
- Zero-copy integration with Pandas for Python workflows
- Supports complex aggregations and window functions

**Use Cases:**
- Large-scale feature computation and aggregation
- Feature backfilling and historical analysis
- Feature distribution analysis and drift detection
- Batch inference for backtesting

**Implementation Considerations:**
- Keep PostgreSQL as the primary database for transactional workloads
- Use DuckDB as a complementary analytical engine
- Sync feature tables from PostgreSQL to DuckDB on schedule
- Maintain feature parity between both systems

### Redis for Live Game State Features

**Rationale:**
- Sub-millisecond latency for live feature lookups
- In-memory caching of frequently accessed game states
- Supports pub/sub for real-time feature updates
- Automatic expiration for stale data

**Use Cases:**
- Real-time feature lookups during live inference
- Caching of pitcher/batter career stats
- Live game state broadcasting to multiple consumers
- Feature freshness monitoring

**Implementation Considerations:**
- Cache key design: `game_id:inning:top_bottom:batter_id`
- TTL configuration based on game state freshness requirements
- Write-through cache pattern for consistency
- Fallback to PostgreSQL on cache miss

## Feature Freshness SLAs

### Batch Features

| Feature Type | Freshness SLA | Update Frequency |
|-------------|---------------|------------------|
| Career Prior Stats | End of previous season | Seasonal |
| Season-to-Date Stats | End of previous day | Daily |
| Park Factors | End of previous season | Seasonal |
| Team Form | End of previous day | Daily |

### Live Features

| Feature Type | Freshness SLA | Update Frequency |
|-------------|---------------|------------------|
| Game State (inning, outs, bases) | < 5 seconds | Per play |
| Pitch Count | < 5 seconds | Per pitch |
| Batter/Pitcher Matchup | < 5 seconds | Per PA |
| Live Career Stats | < 1 minute | Per game |

## Feature Versioning

### Version Schema

Feature versions tracked in `features.feature_versions`:

```sql
CREATE TABLE features.feature_versions (
    feature_version_id SERIAL PRIMARY KEY,
    feature_name TEXT NOT NULL,
    version TEXT NOT NULL,
    feature_spec JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    retired_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT true
);
```

### Versioning Strategy

- **Semantic Versioning**: `major.minor.patch` (e.g., `1.2.3`)
  - `major`: Breaking changes to feature definition
  - `minor`: Additive changes (new features, new columns)
  - `patch`: Bug fixes, performance improvements
- **Backward Compatibility**: Maintain previous versions for at least 2 seasons
- **Deprecation Notice**: 6-month notice before retiring a feature version
- **Feature Registry**: Central catalog of all feature versions and their definitions

### Implementation

- Feature tables include `feature_version` column
- Models reference specific feature versions in `models.model_registry`
- Inference uses feature version specified in model metadata
- Feature version migrations tracked in `docs/agents/PROJECT_LOG.md`

## Feature Quality Monitoring

### Monitoring Metrics

| Metric | Description | Threshold |
|--------|-------------|-----------|
| Null Rate | Percentage of null feature values | < 5% |
| Outlier Rate | Percentage of values outside expected range | < 1% |
| Drift Score | KL divergence from training distribution | < 0.1 |
| Freshness | Age of feature data | Per SLA |
| Cardinality | Number of unique values | Expected range |

### Monitoring Implementation

```sql
-- Feature quality checks
CREATE TABLE features.feature_quality_checks (
    check_id SERIAL PRIMARY KEY,
    feature_name TEXT NOT NULL,
    feature_version TEXT NOT NULL,
    check_type TEXT NOT NULL,
    check_value NUMERIC,
    check_threshold NUMERIC,
    check_passed BOOLEAN NOT NULL,
    checked_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Materialized view for daily quality summaries
CREATE MATERIALIZED VIEW features.feature_quality_daily AS
SELECT
    feature_name,
    feature_version,
    check_type,
    DATE(checked_at) AS check_date,
    AVG(check_value) AS avg_check_value,
    MIN(check_value) AS min_check_value,
    MAX(check_value) AS max_check_value,
    SUM(CASE WHEN check_passed THEN 1 ELSE 0 END) * 100.0 / COUNT(*) AS pass_rate
FROM features.feature_quality_checks
GROUP BY feature_name, feature_version, check_type, DATE(checked_at);
```

### Alerting

- **Critical Alerts**: Null rate > 10%, freshness SLA breach
- **Warning Alerts**: Drift score > 0.15, outlier rate > 2%
- **Info Alerts**: Feature version deprecated, new feature version available

## Feature Store Architecture Diagram

```
┌─────────────────┐
│   Retrosheet    │
│   (Chadwick)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   PostgreSQL    │
│   (Core Data)   │
└────────┬────────┘
         │
         ├──────────────┐
         │              │
         ▼              ▼
┌─────────────────┐  ┌─────────────────┐
│  Batch Features │  │  Live Features  │
│  (features.*)   │  │  (computed on   │
└────────┬────────┘  │  demand)        │
         │           └────────┬────────┘
         │                    │
         ▼                    ▼
┌─────────────────┐  ┌─────────────────┐
│   DuckDB        │  │   Redis         │
│  (Analytics)    │  │  (Cache)        │
└─────────────────┘  └─────────────────┘
```

## Migration Path

### Phase 1: DuckDB Integration (Optional)
1. Set up DuckDB instance alongside PostgreSQL
2. Implement sync pipeline for feature tables
3. Migrate analytical queries to DuckDB
4. Benchmark performance improvements
5. Decide on production adoption

### Phase 2: Redis Integration (Optional)
1. Set up Redis instance for live feature caching
2. Implement cache layer in live scorer
3. Configure TTL and cache invalidation
4. Benchmark latency improvements
5. Decide on production adoption

### Phase 3: Feature Versioning (Recommended)
1. Create `features.feature_versions` table
2. Add `feature_version` column to feature tables
3. Update model registry to reference feature versions
4. Implement feature version selection in inference
5. Document versioning strategy in PROCEDURES.md

### Phase 4: Quality Monitoring (Recommended)
1. Create `features.feature_quality_checks` table
2. Implement quality check pipeline
3. Set up alerting for quality breaches
4. Create quality dashboard
5. Integrate with model training pipeline

## Limitations

- DuckDB and Redis integration require additional infrastructure
- Cache invalidation complexity for Redis
- Feature versioning adds maintenance overhead
- Quality monitoring requires defining thresholds per feature

## Future Work

- [ ] Evaluate DuckDB for batch feature store (optional)
- [ ] Implement Redis for live game state features (optional)
- [ ] Design feature freshness SLAs (complete)
- [ ] Implement feature versioning (recommended)
- [ ] Add feature quality monitoring (recommended)
- [ ] Document feature store architecture (complete)
