# Feature Population Procedure

Complete guide to populating all 220+ engineered features for the pitch-level prediction warehouse.

## Overview

This procedure populates all engineered features in `features_pitch.engineered_features` using a phased approach with SQL-first methodology, batch processing for large datasets, and comprehensive progress tracking.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    FEATURE POPULATION PIPELINE                          │
├─────────────────────────────────────────────────────────────────────────┤
│ Phase 0: Prerequisites                                                  │
│   └─ Verify base_features exists with 7.66M rows                        │
├─────────────────────────────────────────────────────────────────────────┤
│ Phase 1-2: Core Features (46 features)                                  │
│   └─ 005_build_engineered_features.sql                                  │
│   └─ 006_additional_engineered_features.sql                             │
│   └─ 007_populate_additional_features.sql                              │
│   └─ 008_populate_additional_features_batch.sql (batched)              │
├─────────────────────────────────────────────────────────────────────────┤
│ Phase 3-4: Extended Features (40 features)                              │
│   └─ 009_more_engineered_features.sql                                  │
│   └─ 010_populate_more_features.sql                                     │
│   └─ 011_populate_more_features_batch.sql (batched)                    │
├─────────────────────────────────────────────────────────────────────────┤
│ Phase 5-7: Context Features (60 features)                               │
│   └─ 012_context_features_schema.sql                                   │
│   └─ 013_populate_context_features.sql                                  │
│   └─ 014_populate_context_features_batch.sql (batched)               │
├─────────────────────────────────────────────────────────────────────────┤
│ Phase 8-10: Final Features (50+ features)                               │
│   └─ 015_final_features_schema.sql                                      │
│   └─ 016_populate_final_features.sql                                    │
│   └─ 017_populate_final_features_batch.sql (batched)                   │
├─────────────────────────────────────────────────────────────────────────┤
│ Phase 11: Specialized Features                                          │
│   └─ 020_attendance_weather_features.sql                               │
│   └─ 030_momentum_features.sql                                          │
│   └─ 040_umpire_features.sql                                            │
│   └─ 050_postseason_clutch_features.sql                                │
│   └─ 060_batter_pitcher_matchup_features.sql                           │
│   └─ 070_stadium_physics_features.sql                                   │
├─────────────────────────────────────────────────────────────────────────┤
│ Phase 12: Enhanced Views                                                │
│   └─ 099_enhanced_feature_view.sql                                      │
└─────────────────────────────────────────────────────────────────────────┘
```

## Quick Start

### Option 1: Master Orchestrator (Recommended)

```bash
# Verify current status
uv run python scripts/pitch_data/orchestrate_feature_population.py --verify

# Run all phases
uv run python scripts/pitch_data/orchestrate_feature_population.py --all

# Run specific phase
uv run python scripts/pitch_data/orchestrate_feature_population.py --phase 2

# Continue from phase 3 (skip completed)
uv run python scripts/pitch_data/orchestrate_feature_population.py --all --continue 3

# Dry run (show what would be executed)
uv run python scripts/pitch_data/orchestrate_feature_population.py --all --dry-run
```

### Option 2: Batch Runner (For Large Operations)

```bash
# Run batch population loop until complete
chmod +x scripts/pitch_data/batch_feature_runner.sh

./scripts/pitch_data/batch_feature_runner.sh \
    --sql-file sql/features/008_populate_additional_features_batch.sql \
    --max-iterations 100

# Or for context features
./scripts/pitch_data/batch_feature_runner.sh \
    --sql-file sql/features/014_populate_context_features_batch.sql \
    --max-iterations 100
```

### Option 3: SQL Procedures (Warehouse Integration)

```sql
-- Verify feature population status
SELECT * FROM warehouse.feature_population_summary;

-- Check feature stats
SELECT * FROM warehouse.get_feature_stats();

-- Estimate completion time for a column
SELECT * FROM warehouse.estimate_batch_completion('pitch_quality_score');

-- Get unprocessed count
SELECT warehouse.get_unprocessed_count('temp_extreme_flag');
```

## Phase Details

### Phase 0: Prerequisites

**Verifies:**
- `features_pitch.base_features` exists with data
- `features_pitch.engineered_features` table exists

**Row count:** 7,661,992 pitches (2015-2025)

### Phase 1: Core Engineered Features

**Files:**
- `005_build_engineered_features.sql`
- `006_additional_engineered_features.sql`
- `007_populate_additional_features.sql`

**Features:** 46+ core features
- Velocity percentiles and categories
- Strike zone regions (heart, shadow, chase, waste)
- Pitch movement (horizontal/vertical break)
- Two-tier outcome labels (Tier 1: S/B/X, Tier 2: 12 classes)
- Count and sequence features
- Game context (score differential, base states)

### Phase 2: Additional Features Batch

**File:** `008_populate_additional_features_batch.sql`

**Features:** 25+ additional features
- Velocity change from previous pitch (tunneling)
- Spin rate percentiles
- Spin axis characteristics (backspin, topspin, gyro)
- Platoon indicators (same-handed matchup)
- Fatigue metrics (pitcher_fatigue_score)
- Pressure metrics (pa_pressure_index)
- Timing features (early/late season)

**Batch size:** 100,000 rows per iteration

### Phase 3-4: Extended Features

**Files:**
- `009_more_engineered_features.sql`
- `010_populate_more_features.sql`
- `011_populate_more_features_batch.sql`

**Features:** 40+ extended features
- Pitch quality score (composite metric)
- Count leverage indices
- Times Through Order Penalty (TTOP)
- Run Expectancy (RE24)
- Win Probability Added (WPA)
- Payoff pitch detection

### Phase 5-7: Context Features

**Files:**
- `012_context_features_schema.sql`
- `013_populate_context_features.sql`
- `014_populate_context_features_batch.sql`

**Features:** 60+ context features from Categories 2,3,4,7,8

**Weather & Environmental:**
- temp_extreme_flag (hot/cold game indicator)
- wind_effect_score
- humidity_proxy
- altitude_factor

**Momentum & Streaks:**
- team_last_5_win_rate
- team_last_10_win_rate
- team_momentum_delta
- pitcher_last_3_era

**Umpire Effects:**
- umpire_strike_zone_size
- umpire_strike_calls_pct
- umpire_k_friendly
- umpire_consistency_score

**Attendance & Crowd:**
- attendance_vs_capacity_pct
- is_sellout
- crowd_noise_proxy

**Park Factors:**
- park_elevation_feet (Coors effect)
- park_hr_factor_lf/rf/cf
- altitude_factor

### Phase 8-10: Final Features

**Files:**
- `015_final_features_schema.sql`
- `016_populate_final_features.sql`
- `017_populate_final_features_batch.sql`

**Features:** 50+ final features
- Markov chain count states
- Strike/ball accumulation rates
- Batter-pitcher matchup history
- Postseason flags
- Sequence patterns
- Rookie/veteran classification

### Phase 11: Specialized Features

**Files:**
- `020_attendance_weather_features.sql`
- `030_momentum_features.sql`
- `040_umpire_features.sql`
- `050_postseason_clutch_features.sql`
- `060_batter_pitcher_matchup_features.sql`
- `070_stadium_physics_features.sql`

**Additional specialized feature categories**

### Phase 12: Enhanced Views

**Files:**
- `099_enhanced_feature_view.sql`
- `099_phase2_enhanced_feature_view.sql`
- `099_phase3_final_enhanced_view.sql`

**Views for model training and analysis**

## Feature Categories (Research-Backed)

| Category | Count | Description |
|----------|-------|-------------|
| 1. Pitch Physics | 30+ | Velocity, movement, spin, release point |
| 2. Weather/Environment | 10+ | Temperature, wind, humidity, altitude |
| 3. Momentum/Streaks | 15+ | Team form, pitcher recent performance |
| 4. Umpire Effects | 10+ | Zone size, tendencies, experience |
| 5. Batter Profile | 15+ | Hot/cold zones, platoon splits |
| 6. Pitcher Arsenal | 15+ | Repertoire depth, ace identification |
| 7. Park Factors | 15+ | Dimensions, elevation, surface |
| 8. Attendance/Crowd | 10+ | Crowd noise, pressure, sellouts |
| 9. Game Context | 20+ | Score, inning, base state, leverage |
| 10. Sequence/History | 15+ | TTOP, matchup history, prior outcomes |
| 11. Count State | 15+ | Markov chains, RE24, payoffs |
| 12. Clutch/Pressure | 10+ | High leverage, walk-off, save situations |

**Total: 220+ features**

## Monitoring and Verification

### Real-time Progress Tracking

```bash
# Watch population progress in real-time
watch -n 5 "psql -d postgresql://localhost:5432/retrosheet -c \"
SELECT 
    'Unprocessed' as metric,
    COUNT(*) FILTER (WHERE is_same_handed_matchup IS NULL) as batch_008,
    COUNT(*) FILTER (WHERE pitch_quality_score IS NULL) as batch_011,
    COUNT(*) FILTER (WHERE temp_extreme_flag IS NULL) as batch_014
FROM features_pitch.engineered_features;
\""
```

### Verification Queries

```sql
-- Comprehensive population check
SELECT 
    feature_category,
    populated_count,
    total_count,
    percent_complete,
    status
FROM warehouse.feature_population_summary;

-- Check specific feature
SELECT 
    COUNT(*) as total,
    COUNT(pitch_quality_score) as populated,
    ROUND(COUNT(pitch_quality_score)::numeric / COUNT(*) * 100, 2) as pct
FROM features_pitch.engineered_features;

-- Find columns with NULL values
SELECT column_name
FROM information_schema.columns
WHERE table_schema = 'features_pitch'
  AND table_name = 'engineered_features'
  AND column_name NOT IN ('pitch_id', 'engineered_at', 'engineer_version')
  AND EXISTS (
      SELECT 1 FROM features_pitch.engineered_features
      WHERE (column_name)::text IS NULL
      LIMIT 1
  );
```

## Performance Considerations

### Batch Processing

- **Batch size:** 100,000 rows (configurable)
- **Iterations needed:** ~77 for 7.66M rows
- **Time per batch:** ~30 seconds (depends on complexity)
- **Total time:** ~40 minutes per phase (batched)

### Optimization Tips

1. **Run during off-hours** for intensive phases
2. **Use SSD storage** for faster UPDATE operations
3. **Monitor disk space** - temp tables use significant space
4. **Check autovacuum** - large updates need regular vacuuming

### Indexes for Performance

```sql
-- Ensure indexes exist for batch WHERE clauses
CREATE INDEX IF NOT EXISTS idx_eng_feat_null_velocity_change
ON features_pitch.engineered_features(pitch_id)
WHERE velocity_change_from_prev IS NULL;

CREATE INDEX IF NOT EXISTS idx_eng_feat_null_quality_score
ON features_pitch.engineered_features(pitch_id)
WHERE pitch_quality_score IS NULL;
```

## Error Handling

### Common Issues

**Issue: Long-running transaction timeout**
- **Solution:** Use batch scripts with smaller batch sizes

**Issue: Disk space exhausted**
- **Solution:** Run VACUUM between batches, increase disk space

**Issue: Stalled progress (same unprocessed count)**
- **Solution:** Check batch script stall detection, verify WHERE clause logic

### Recovery Procedures

```bash
# If a batch fails, resume from last iteration
./scripts/pitch_data/batch_feature_runner.sh \
    --sql-file sql/features/008_populate_additional_features_batch.sql \
    --max-iterations 100

# The script will detect already-processed rows and continue
```

## Documentation Standards

Per `AGENTS.md` SQL-First Development Rule:

1. All SQL files saved in version control
2. Header comments with purpose, date, dependencies
3. Table/column comments added
4. Verification queries included
5. Git commit with descriptive message

## Related Documentation

- `AGENTS.md` - SQL-First Development Rule
- `docs/FEATURE_ENGINEERING_PLAN.md` - Research-backed feature categories
- `PITCH_MODEL_PROGRESS.md` - Current build status
- `sql/warehouse/005_feature_population_procedures.sql` - SQL procedures

## Files Created/Updated

| File | Purpose |
|------|---------|
| `scripts/pitch_data/orchestrate_feature_population.py` | Master orchestrator with 13 phases |
| `scripts/pitch_data/batch_feature_runner.sh` | Batch SQL runner with progress tracking |
| `sql/warehouse/005_feature_population_procedures.sql` | SQL procedures for warehouse integration |
| `docs/agents/FEATURE_POPULATION_PROCEDURE.md` | This documentation |

## GitHub Issues

- Epic #78: Pitch-Level Model Pipeline
- Sub-Issue #79: Flexible Feature Mart Schema
