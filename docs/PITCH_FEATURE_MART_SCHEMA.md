# Pitch-Level Feature Mart Schema Documentation

**CRISP-DM Phase:** 3. Data Preparation  
**Epic:** #78 - Pitch-Level Model Pipeline  
**Sub-Issue:** #78.1 - Flexible Feature Mart Schema Design  
**Date:** 2026-04-23

---

## Executive Summary

This document describes the **flexible, extensible schema** for pitch-level feature marts in the Retrosheet warehouse. The design principle is:

> **"All fields available, selective inclusion"**

Rather than creating separate tables for each model with different field subsets, we use a **normalized schema** where:
- All 118 raw Statcast fields are preserved in `base_features`
- Feature metadata lives in `feature_registry` (enabling dynamic selection)
- Derived features are in separate tables (joined as needed)
- Each model queries exactly the fields it needs via metadata-driven SQL

---

## Schema Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        features_pitch SCHEMA                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐        │
│  │  base_features   │◄───│ feature_registry │    │  model_training  │        │
│  │  (118 fields)    │    │  (metadata)      │    │  (versioned)     │        │
│  └────────┬─────────┘    └──────────────────┘    └──────────────────┘        │
│           │                                                                  │
│           ├──►┌──────────────────┐                                            │
│           │   │engineered_features│  ← Derived metrics                       │
│           │   └──────────────────┘                                            │
│           │                                                                  │
│           ├──►┌──────────────────┐                                            │
│           │   │sequential_features│  ← LSTM windows                            │
│           │   └──────────────────┘                                            │
│           │                                                                  │
│           └──►┌──────────────────┐                                            │
│               │  player_context  │  ← Rolling stats                          │
│               └──────────────────┘                                            │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Table Reference

### 1. `base_features` - The Source of Truth

**Purpose:** Complete preservation of all 118 Statcast fields  
**Rows:** 7.66M (2015-2025)  
**Update Frequency:** Append-only (historical), daily incremental (2025+)

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `pitch_id` | BIGINT PK | Synthetic primary key | 123456789 |
| `game_pk` | INTEGER | MLB game identifier | 745211 |
| `batter_id` | INTEGER | Canonical player ID | 660271 |
| `pitcher_id` | INTEGER | Canonical player ID | 656302 |
| `game_year` | SMALLINT | Season | 2024 |
| `pitch_type` | VARCHAR(2) | Pitch type code | 'FF', 'SL', 'CH' |
| `release_speed` | REAL | Velocity at release | 94.5 |
| `release_spin_rate` | REAL | Spin rate in RPM | 2250 |
| `pfx_x` | REAL | Horizontal movement | -0.52 |
| `pfx_z` | REAL | Vertical movement | 1.23 |
| `plate_x` | REAL | Horizontal location | -0.35 |
| `plate_z` | REAL | Vertical location | 2.15 |
| `launch_speed` | REAL | Exit velocity | 105.2 |
| `launch_angle` | REAL | Launch angle | 22.5 |
| `quality_flag` | VARCHAR(20) | Data quality class | 'normal' |
| `location` | GEOMETRY | PostGIS point | POINT(0 2) |

**Key Design Decisions:**
- ALL 118 Statcast fields preserved (not just "important" ones)
- Quality flagging enables filtering without data loss
- PostGIS geometry column for spatial queries
- Version tracking via `data_version`

---

### 2. `feature_registry` - Metadata Catalog

**Purpose:** Self-documenting feature catalog enabling dynamic queries  
**Rows:** ~150 (one per column across all tables)

| Column | Type | Description |
|--------|------|-------------|
| `feature_id` | SERIAL PK | Unique identifier |
| `table_name` | VARCHAR | Source table |
| `column_name` | VARCHAR | Column name |
| `feature_category` | VARCHAR | Physics/location/context/outcome |
| `feature_type` | VARCHAR | Numeric/categorical/boolean/spatial |
| `is_default` | BOOLEAN | Include in default queries? |
| `is_engineered` | BOOLEAN | Derived from other columns? |
| `model_usage` | VARCHAR[] | Which models use this: ['xgboost', 'lstm'] |
| `data_quality` | JSONB | {null_pct: 0.02, unique_pct: 0.95} |

**Usage Examples:**

```sql
-- Get all default features for XGBoost
SELECT column_name, table_name
FROM features_pitch.feature_registry
WHERE 'xgboost' = ANY(model_usage)
  AND is_default = TRUE;

-- Get feature statistics
SELECT data_quality
FROM features_pitch.feature_registry
WHERE table_name = 'base_features'
  AND column_name = 'release_speed';
```

---

### 3. `engineered_features` - Derived Metrics

**Purpose:** Computed features that don't exist in raw data  
**Rows:** 7.66M (1:1 with base_features)  
**Update Strategy:** Batch computed, additive only

| Column | Type | Description | Derivation |
|--------|------|-------------|------------|
| `velocity_category` | VARCHAR(10) | Speed bucket | CASE WHEN release_speed < 80 THEN 'slow'... |
| `zone_region` | VARCHAR(20) | Statcast zone | heart/shadow/chase/waste |
| `is_strike` | BOOLEAN | Was it a strike? | derived from description |
| `is_whiff` | BOOLEAN | Swing and miss? | description = 'swinging_strike' |
| `is_ball_in_play` | BOOLEAN | Contact made? | type = 'X' |
| `is_hard_hit` | BOOLEAN | Exit velo >= 95? | launch_speed >= 95 |
| `outcome_tier1` | VARCHAR(20) | ball/strike/bip | derived from description |
| `outcome_tier2` | VARCHAR(20) | hit type | derived from events |
| `swing_decision` | VARCHAR(10) | swing/take | derived |
| `pa_pitch_count` | SMALLINT | Pitch # in PA | derived from sequence |
| `prev_pitch_type` | VARCHAR(2) | Previous type | lag() |
| `horizontal_break` | REAL | Movement normalized | adjusted by hand |
| `score_diff` | INTEGER | Score differential | bat_score - fld_score |
| `is_late_game` | BOOLEAN | Inning > 7? | inning > 7 |

**Why Separate Table?**
- NULL-free storage for derived values
- Different refresh schedule (computed nightly)
- Easier to extend without base schema changes

---

### 4. `sequential_features` - LSTM/Transformer Ready

**Purpose:** Sliding window sequences for sequential models  
**Rows:** ~7M (one per pitch with sequence context)  
**JSONB Design:** Enables variable-length sequences

| Column | Type | Description |
|--------|------|-------------|
| `sequence_id` | BIGSERIAL PK | Unique identifier |
| `game_pk` | INTEGER | Game identifier |
| `at_bat_number` | INTEGER | PA within game |
| `pitch_id` | BIGINT FK | Current pitch |
| `sequence_position` | SMALLINT | 1st, 2nd, 3rd pitch... |
| `window_3pitch` | JSONB | [pitch_{t-2}, pitch_{t-1}, pitch_t] |
| `window_5pitch` | JSONB | [pitch_{t-4}, ..., pitch_t] |
| `full_pa_sequence` | JSONB | All pitches in PA |
| `pitch_type_sequence` | VARCHAR[] | ['FF', 'SL', 'CH'] |
| `velocity_sequence` | REAL[] | [94.5, 85.2, 78.1] |
| `pitches_since_last_fastball` | SMALLINT | Distance to last FF |
| `location_pattern` | VARCHAR(20) | 'high_low', 'inside_outside' |

**JSONB Structure Example:**
```json
{
  "pitches": [
    {"pitch_type": "FF", "plate_x": -0.5, "plate_z": 2.1, "result": "called_strike"},
    {"pitch_type": "SL", "plate_x": 0.8, "plate_z": 1.8, "result": "foul"},
    {"pitch_type": "CH", "plate_x": 0.2, "plate_z": 2.3, "result": "swinging_strike"}
  ],
  "count_progression": ["0-0", "0-1", "0-2"],
  "time_span_seconds": 45.2
}
```

---

### 5. `player_context` - Rolling Statistics

**Purpose:** Time-aware player performance metrics  
**Composite PK:** (player_id, season, game_date, role, window_type)  
**Windows:** '30day', 'season', 'career'

| Column | Type | Description |
|--------|------|-------------|
| `player_id` | INTEGER | Player identifier |
| `season` | SMALLINT | Year |
| `game_date` | DATE | As of date |
| `role` | VARCHAR(10) | 'batter' or 'pitcher' |
| `window_type` | VARCHAR(20) | '30day', 'season', 'career' |
| `pa_count` | INTEGER | Sample size |
| `k_rate` | REAL | Strikeout rate |
| `bb_rate` | REAL | Walk rate |
| `avg_estimated_woba` | REAL | Expected wOBA |
| `hard_hit_rate` | REAL | Hard contact % |
| `swing_rate` | REAL | Swing % |
| `whiff_rate` | REAL | Whiff % |
| `o_swing_rate` | REAL | Chase rate |
| `pitch_mix` | JSONB | {'FF': 0.45, 'SL': 0.25} |
| `arsenal_size` | INTEGER | Distinct pitch types |
| `avg_velocity` | REAL | Average velocity |

**Usage Pattern:**
```sql
-- Join player context to training data
SELECT 
    bf.*,
    bpc.k_rate as batter_k_rate,
    ppc.zone_rate as pitcher_zone_pct
FROM features_pitch.base_features bf
LEFT JOIN features_pitch.player_context bpc
    ON bpc.player_id = bf.batter_id
    AND bpc.season = bf.game_year
    AND bpc.game_date = bf.game_date
    AND bpc.role = 'batter'
    AND bpc.window_type = 'season'
```

---

### 6. `model_training_set` - Versioned Training Data

**Purpose:** Reproducible, materialized training sets  
**Rows:** Variable (one per pitch per model version)  
**Key Concept:** `data_hash` enables exact reproduction

| Column | Type | Description |
|--------|------|-------------|
| `training_id` | BIGSERIAL PK | Unique |
| `model_name` | VARCHAR | e.g., 'pitch_outcome_tier1' |
| `model_version` | VARCHAR | Semantic version |
| `pitch_id` | BIGINT FK | Source pitch |
| `feature_names` | TEXT[] | ['release_speed', 'plate_x', ...] |
| `feature_vector` | REAL[] | [94.5, -0.35, ...] |
| `target_type` | VARCHAR | 'outcome_tier1', 'pitch_type' |
| `target_label` | VARCHAR | 'strike', 'FF' |
| `target_value` | REAL | Numeric target or class index |
| `split_set` | VARCHAR | 'train', 'val', 'test' |
| `data_hash` | VARCHAR(64) | SHA-256 of source state |
| `feature_query_hash` | VARCHAR(64) | Hash of generation query |

**Reproducibility Guarantee:**
```python
# Given a model version, reproduce exact training data
def reproduce_training(model_name, model_version):
    query = f"""
    SELECT feature_names, feature_vector, target_value
    FROM features_pitch.model_training_set
    WHERE model_name = '{model_name}'
      AND model_version = '{model_version}'
      AND split_set = 'train'
    """
    return pd.read_sql(query, conn)
```

---

### 7. `pitch_sequences` - PA-Level Aggregation

**Purpose:** One row per plate appearance with full sequence  
**Rows:** ~4.8M (one per PA)

| Column | Type | Description |
|--------|------|-------------|
| `sequence_id` | BIGSERIAL PK | Unique |
| `pa_id` | BIGINT | game_pk * 1000 + at_bat_number |
| `pitch_sequence` | INTEGER[] | [pitch_id_1, pitch_id_2, ...] |
| `pitches_in_pa` | SMALLINT | Count |
| `sequence_outcome` | VARCHAR | Final PA result |
| `avg_velocity` | REAL | Mean velocity in sequence |
| `velocity_range` | REAL | Max - min |
| `pitch_type_count` | SMALLINT | Distinct types used |
| `started_with_fastball` | BOOLEAN | First pitch was FF? |
| `sequence_classification` | VARCHAR | 'quick_out', 'battle' |
| `sequence_details` | JSONB | Full pitch data array |

---

## Design Principles

### 1. Flexibility Over Optimization

**Anti-pattern (avoided):**
```sql
-- BAD: Hardcoded columns for specific model
CREATE TABLE model_x_features (
    release_speed REAL,
    plate_x REAL,
    plate_z REAL
    -- ... missing many fields
);
```

**Our approach:**
```sql
-- GOOD: All fields preserved, select as needed
SELECT 
    fr.column_name,
    CASE WHEN fr.is_engineered THEN 'ef.' || fr.column_name
         ELSE 'bf.' || fr.column_name END as qualified_name
FROM features_pitch.feature_registry fr
WHERE 'xgboost' = ANY(fr.model_usage);
```

### 2. Additive, Non-Destructive Changes

- Never `ALTER TABLE ... DROP COLUMN`
- Never overwrite historical data
- New features added as new columns or new tables
- Old versions remain accessible

### 3. Metadata-Driven Queries

```sql
-- Generate feature list for any model
CREATE OR REPLACE FUNCTION get_model_features(p_model_name VARCHAR)
RETURNS TABLE (column_name TEXT, source_table TEXT) AS $$
BEGIN
    RETURN QUERY
    SELECT fr.column_name,
           CASE WHEN fr.is_engineered THEN 'engineered_features'
                ELSE 'base_features' END as source_table
    FROM features_pitch.feature_registry fr
    WHERE p_model_name = ANY(fr.model_usage)
      AND fr.is_default = TRUE;
END;
$$ LANGUAGE plpgsql;
```

---

## Usage Patterns

### Pattern 1: XGBoost Training Data

```sql
-- Full training set with all relevant features
SELECT 
    -- Base physics
    bf.release_speed,
    bf.release_spin_rate,
    bf.pfx_x,
    bf.pfx_z,
    bf.plate_x,
    bf.plate_z,
    bf.zone,
    -- Context
    bf.balls,
    bf.strikes,
    bf.outs_when_up,
    bf.inning,
    bf.on_1b,
    bf.on_2b,
    bf.on_3b,
    -- Engineered
    ef.velocity_category,
    ef.zone_region,
    ef.is_in_zone,
    ef.score_diff,
    -- Player context
    bpc.k_rate as batter_k_rate,
    bpc.avg_estimated_woba as batter_woba,
    ppc.zone_rate as pitcher_zone_pct,
    -- Target
    ef.outcome_tier1 as target
FROM features_pitch.base_features bf
JOIN features_pitch.engineered_features ef USING (pitch_id)
LEFT JOIN features_pitch.player_context bpc
    ON bpc.player_id = bf.batter_id
    AND bpc.season = bf.game_year
    AND bpc.game_date = bf.game_date
    AND bpc.role = 'batter'
    AND bpc.window_type = 'season'
LEFT JOIN features_pitch.player_context ppc
    ON ppc.player_id = bf.pitcher_id
    AND ppc.season = bf.game_year
    AND ppc.game_date = bf.game_date
    AND ppc.role = 'pitcher'
    AND ppc.window_type = 'season'
WHERE bf.quality_flag = 'normal'
  AND bf.game_year BETWEEN 2015 AND 2023;
```

### Pattern 2: LSTM Sequence Data

```sql
-- Get sequences for LSTM training
SELECT 
    sf.sequence_id,
    sf.pitch_type_sequence,
    sf.velocity_sequence,
    sf.window_3pitch,
    -- Current pitch target
    ef.pitch_type as target_pitch_type,
    ef.plate_x as target_plate_x,
    ef.plate_z as target_plate_z
FROM features_pitch.sequential_features sf
JOIN features_pitch.engineered_features ef 
    ON ef.pitch_id = sf.pitch_id
WHERE sf.sequence_position >= 3  -- Need at least 3 prior pitches
  AND sf.game_year BETWEEN 2015 AND 2023;
```

### Pattern 3: Feature Selection via Registry

```sql
-- Dynamically select features for a new model
SELECT 
    'bf.' || fr.column_name as select_clause,
    fr.description,
    fr.data_quality->>'null_pct' as null_pct
FROM features_pitch.feature_registry fr
WHERE fr.table_name = 'base_features'
  AND fr.feature_category IN ('physics', 'location')
  AND (fr.data_quality->>'null_pct')::float < 0.05
ORDER BY fr.importance_score DESC
LIMIT 20;
```

---

## Performance Considerations

### Indexes

| Table | Index | Purpose |
|-------|-------|---------|
| base_features | (game_year) | Season filtering |
| base_features | (batter_id) | Player lookups |
| base_features | (pitcher_id) | Player lookups |
| base_features | (game_pk, at_bat_number) | PA lookups |
| base_features | (quality_flag) WHERE quality_flag='normal' | Quality filtering |
| base_features | USING GIST(location) | Spatial queries |
| engineered_features | (outcome_tier1) | Target filtering |
| sequential_features | (game_pk, at_bat_number) | PA lookups |
| player_context | (player_id, season, role, window_type) | Context lookups |
| model_training_set | (model_name, model_version, split_set) | Training queries |

### Partitioning Strategy (Future)

```sql
-- Consider partitioning large tables by season
CREATE TABLE features_pitch.base_features_2024 PARTITION OF features_pitch.base_features
    FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');
```

---

## Data Lineage

```
┌─────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│ raw_mlb.statcast│────►│base_features     │────►│engineered_features│
│ (source)        │     │ (preserved)      │     │ (derived)         │
└─────────────────┘     └──────────────────┘     └──────────────────┘
          │                      │                       │
          │                      ▼                       ▼
          │             ┌──────────────────┐     ┌──────────────────┐
          │             │feature_registry  │     │sequential_features│
          │             │ (metadata)       │     │ (LSTM windows)    │
          │             └──────────────────┘     └──────────────────┘
          │                      │
          ▼                      ▼
┌────────────────────────────────────────────────────────────────────┐
│                    model_training_set                              │
│                    (materialized training data)                     │
└────────────────────────────────────────────────────────────────────┘
```

---

## Related Documentation

- `docs/PITCH_PLAYER_ANALYSIS_ARCHITECTURE.md` - Data flow and architecture
- `docs/STATCAST_MODELS_RESEARCH_REPORT.md` - External model research
- `docs/diagrams/PITCH_FEATURE_MART_ERD.puml` - ERD diagram
- `docs/diagrams/PITCH_DATA_FLOW.puml` - Data flow diagram
- `sql/features/003_pitch_flexible_mart.sql` - Schema SQL

---

## CRISP-DM Phase Integration

| CRISP-DM Phase | Schema Component | Status |
|----------------|------------------|--------|
| 2. Data Understanding | base_features, quality flags | ✅ Complete |
| 3. Data Preparation | feature_registry, engineered_features | 🔄 In Progress |
| 3. Data Preparation | sequential_features, player_context | ⏳ Planned |
| 3. Data Preparation | model_training_set | ⏳ Planned |
| 4. Modeling | Views and materialized training sets | ⏳ Planned |

---

## Change Log

| Date | Version | Change |
|------|---------|--------|
| 2026-04-23 | 1.0 | Initial schema design |
| 2026-04-23 | 1.0 | feature_registry populated with base features |

---

**Next Steps:**
1. Execute `003_pitch_flexible_mart.sql` to create schema
2. Populate `base_features` from `locations`
3. Run feature engineering pipeline
4. Build sequential features
5. Calculate player context
6. Materialize first training set
