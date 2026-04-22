# PostgreSQL Baseball Pipeline Architecture Assessment

**Date:** 2026-04-22
**Purpose:** Evaluate current pipeline architecture, identify gaps, and design a streamlined real-time update strategy

## Executive Summary

The retrosheet warehouse has a solid foundation with clear separation of concerns (raw → bridge → core → features → models → predictions). However, the pipeline lacks automated real-time update capabilities and has several one-off workflow fixes that should be streamlined into PostgreSQL procedures.

## Current Architecture Review

### Data Layers (Well-Designed)

```
raw_retrosheet → raw_mlb → raw_espn
    ↓
bridge (ID mappings)
    ↓
core (canonical entities)
    ↓
features (ML-ready)
    ↓
models (registry)
    ↓
predictions (outputs)
    ↓
analysis (combined historical + live)
```

**Strengths:**
- Clear separation of concerns
- Source-preserved raw data
- Bridge layer for ID reconciliation
- Canonical core entities
- Feature marts for ML
- Model registry for versioning
- Analysis layer for combined queries

### Current Procedures (Partial Coverage)

**Bridge Population Procedures (Recently Added):**
- `bridge.populate_all_bridge_tables()` - Master orchestrator
- `bridge.populate_game_xref()` - Game cross-reference
- `bridge.populate_season_aware_team_xref()` - Season-aware team mappings
- `bridge.populate_coach_xref()` - Coach cross-reference
- `bridge.populate_umpire_xref()` - Umpire cross-reference
- `bridge.populate_park_xref()` - Park cross-reference
- `bridge.populate_player_xref()` - Player cross-reference

**Missing Procedures:**
- Materialized view refresh procedures
- Real-time data update procedures
- Automated pipeline orchestration procedures
- Data quality check procedures
- Feature mart update procedures

### Materialized Views (No Automated Refresh)

**Current State:**
- 18 materialized views across core, features, mlb, and optimization schemas
- Manual refresh only via `REFRESH MATERIALIZED VIEW CONCURRENTLY`
- No centralized refresh strategy
- No automated scheduling
- No dependency management

**Issues:**
1. Feature marts (PA examples) must be refreshed after new data ingestion
2. Analysis views (combined historical + live) must be refreshed after live updates
3. No automated refresh after bridge table updates
4. No refresh procedures for orchestrating dependent view updates

### One-Off Workflow Fixes Identified

**SQL Mangling Workaround:**
- Created `tmp/diagnose_sql_mangling.sh` for debugging
- Created `tmp/apply_confidence_scoring.sh` for migration
- Created `tmp/run_coach_umpire_procedures.sh` for procedures
- **Should be:** Centralized procedure `bridge.refresh_all_bridge_tables()`

**Bridge Table Updates:**
- Individual Python scripts for each bridge table type
- No centralized orchestration
- **Should be:** Single master procedure with dependency management

**Live Data Ingestion:**
- Separate scripts for schedule discovery, game ingestion, transformation
- No automated pipeline
- **Should be:** Stored procedure orchestration or PostgreSQL triggers

## Industry Best Practices Research

### MLB's Approach (Google Cloud)
- **Storage:** Cloud SQL for PostgreSQL for game data
- **Batch Processing:** Dataflow jobs move data from Bigtable/Cloud SQL to Cloud Storage nightly
- **Pattern:** Batch-oriented, not real-time
- **Lesson:** Real-time not always required; batch can be sufficient

### Real-Time Materialized View Options

**1. pg_ivm Extension (Incremental View Maintenance)**
- **Pros:** Native PostgreSQL extension, incremental updates, always fresh
- **Cons:** Requires extension installation, limited view complexity
- **Use Case:** Simple aggregations that need real-time updates

**2. Scheduled Refresh (Cron + CONCURRENTLY)**
- **Pros:** Standard PostgreSQL, no extensions, supports complex views
- **Cons:** Not truly real-time, requires scheduling infrastructure
- **Use Case:** Feature marts that can tolerate 5-15 minute staleness

**3. External Streaming (Materialize, RisingWave, Estuary)**
- **Pros:** True real-time, complex transformations, SQL-compatible
- **Cons:** Additional infrastructure, operational complexity
- **Use Case:** High-frequency trading or real-time analytics

**4. Trigger-Based Refresh**
- **Pros:** Immediate updates, native PostgreSQL
- **Cons:** Can cause cascade refresh storms, performance impact
- **Use Case:** Critical views that must be always fresh

## Recommended Architecture Improvements

### 1. Centralized Refresh Procedures

**Create `maintenance.refresh_schema(schema_name, concurrent)` procedure:**
```sql
CREATE OR REPLACE PROCEDURE maintenance.refresh_schema(
    p_schema_name TEXT,
    p_concurrent BOOLEAN DEFAULT TRUE
)
LANGUAGE plpgsql
AS $$
DECLARE
    mv_record RECORD;
    refresh_cmd TEXT;
BEGIN
    FOR mv_record IN 
        SELECT schemaname, matviewname 
        FROM pg_matviews 
        WHERE schemaname = p_schema_name
        ORDER BY matviewname
    LOOP
        IF p_concurrent THEN
            refresh_cmd := format('REFRESH MATERIALIZED VIEW CONCURRENTLY %I.%I', 
                                   mv_record.schemaname, mv_record.matviewname);
        ELSE
            refresh_cmd := format('REFRESH MATERIALIZED VIEW %I.%I', 
                                   mv_record.schemaname, mv_record.matviewname);
        END IF;
        
        EXECUTE refresh_cmd;
        RAISE NOTICE 'Refreshed %.%', mv_record.schemaname, mv_record.matviewname;
    END LOOP;
END;
$$;
```

**Create `maintenance.refresh_all_materialized_views(concurrent)` procedure:**
```sql
CREATE OR REPLACE PROCEDURE maintenance.refresh_all_materialized_views(
    p_concurrent BOOLEAN DEFAULT TRUE
)
LANGUAGE plpgsql
AS $$
DECLARE
    schema_name TEXT;
BEGIN
    FOR schema_name IN SELECT DISTINCT schemaname FROM pg_matviews ORDER BY schemaname
    LOOP
        CALL maintenance.refresh_schema(schema_name, p_concurrent);
    END LOOP;
END;
$$;
```

### 2. Dependency-Aware Refresh Strategy

**Create `maintenance.refresh_features_after_ingestion()` procedure:**
```sql
CREATE OR REPLACE PROCEDURE maintenance.refresh_features_after_ingestion()
LANGUAGE plpgsql
AS $$
BEGIN
    -- Refresh feature marts in dependency order
    CALL maintenance.refresh_schema('features', TRUE);
    
    -- Refresh analysis views (depend on features)
    CALL maintenance.refresh_schema('analysis', TRUE);
    
    -- Refresh predictions views (depend on features)
    CALL maintenance.refresh_schema('predictions', TRUE);
END;
$$;
```

**Create `maintenance.refresh_live_after_ingestion()` procedure:**
```sql
CREATE OR REPLACE PROCEDURE maintenance.refresh_live_after_ingestion()
LANGUAGE plpgsql
AS $$
BEGIN
    -- Refresh live-specific views
    CALL maintenance.refresh_schema('analysis', TRUE);
    
    -- Refresh live feature parity views
    REFRESH MATERIALIZED VIEW CONCURRENTLY features.live_plate_appearance_advanced_count_examples;
END;
$$;
```

### 3. Real-Time Update Strategy

**Option A: Scheduled Refresh (Recommended for Baseball Pipeline)**
- Refresh feature marts every 15 minutes during game hours
- Refresh analysis views after each live game ingestion
- Use `pg_cron` extension for scheduling
- Acceptable latency: 5-15 minutes for most use cases

**Option B: Trigger-Based Refresh (For Critical Views)**
- Create triggers on `core.live_games` and `core.live_events`
- Refresh dependent materialized views on INSERT/UPDATE
- Limit to critical views only to avoid cascade storms
- Use for real-time dashboard views

**Option C: pg_ivm Extension (Future Enhancement)**
- Install pg_ivm for incremental view maintenance
- Convert high-frequency views to pg_ivm
- Keep complex feature marts as scheduled refresh
- Hybrid approach: pg_ivm for simple aggregations, scheduled for complex

### 4. Pipeline Orchestration Procedures

**Create `pipeline.ingest_live_games()` procedure:**
```sql
CREATE OR REPLACE PROCEDURE pipeline.ingest_live_games()
LANGUAGE plpgsql
AS $$
DECLARE
    game_count INT;
BEGIN
    -- This would call Python scripts via PL/Python or external triggers
    -- For now, document the expected sequence
    
    -- 1. Fetch schedule
    -- 2. For each game: fetch live feed, store in raw_mlb
    -- 3. Transform to core.live_games and core.live_events
    -- 4. Refresh live views
    CALL maintenance.refresh_live_after_ingestion();
    
    -- 5. Log completion
    -- INSERT INTO pipeline.run_log ...
END;
$$;
```

**Create `pipeline.refresh_warehouse()` procedure:**
```sql
CREATE OR REPLACE PROCEDURE pipeline.refresh_warehouse()
LANGUAGE plpgsql
AS $$
BEGIN
    -- Refresh in dependency order
    CALL maintenance.refresh_schema('features', TRUE);
    CALL maintenance.refresh_schema('analysis', TRUE);
    CALL maintenance.refresh_schema('predictions', TRUE);
    CALL maintenance.refresh_schema('mlb', TRUE);
END;
$$;
```

### 5. Data Quality Monitoring

**Create `maintenance.check_data_quality()` procedure:**
```sql
CREATE OR REPLACE PROCEDURE maintenance.check_data_quality()
LANGUAGE plpgsql
AS $$
DECLARE
    check_result RECORD;
BEGIN
    -- Check bridge table coverage
    SELECT * FROM bridge.bridge_data_quality INTO check_result;
    
    -- Check for NULL confidence scores
    SELECT COUNT(*) FROM bridge.player_xref WHERE confidence_score IS NULL;
    
    -- Check for orphaned IDs
    SELECT COUNT(*) FROM bridge.orphaned_external_ids;
    
    -- Log results to monitoring table
END;
$$;
```

## Implementation Priority

### Phase 1: Foundation (Immediate)
1. Create `maintenance` schema
2. Implement `maintenance.refresh_schema()` procedure
3. Implement `maintenance.refresh_all_materialized_views()` procedure
4. Test manual refresh procedures

### Phase 2: Dependency Management (Week 1)
1. Implement `maintenance.refresh_features_after_ingestion()`
2. Implement `maintenance.refresh_live_after_ingestion()`
3. Document refresh dependencies
4. Create refresh schedule documentation

### Phase 3: Scheduling (Week 2)
1. Install `pg_cron` extension
2. Schedule feature mart refreshes (every 15 minutes during game hours)
3. Schedule daily full warehouse refreshes
4. Add monitoring for failed refreshes

### Phase 4: Real-Time Enhancement (Future)
1. Evaluate pg_ivm extension for critical views
2. Implement trigger-based refresh for dashboard views
3. Consider external streaming tools if real-time requirements increase

## Comparison to Industry Standards

**What We're Doing Well:**
- ✓ Clear data layer separation
- ✓ Source-preserved raw data
- ✓ Bridge layer for ID reconciliation
- ✓ Feature marts for ML
- ✓ Model registry for versioning

**What Needs Improvement:**
- ✗ No automated materialized view refresh
- ✗ No centralized refresh orchestration
- ✗ No dependency-aware refresh strategy
- ✗ No real-time update capability
- ✗ One-off workflow fixes not in procedures
- ✗ No data quality monitoring procedures

**Industry Alignment:**
- MLB uses batch processing (we match this pattern)
- We lack the scheduling infrastructure they have (Dataflow, cron)
- We have better separation of concerns than many ad-hoc pipelines
- We need to add automated refresh to match production pipelines

## Adaptability Assessment

**Current Pipeline Adaptability:**
- New data sources: Easy to add (raw schema → bridge → core pattern)
- New features: Easy to add (feature mart pattern exists)
- New models: Easy to add (model registry exists)
- Real-time updates: NOT supported (manual only)
- Play-by-play data ingestion: Partially supported (live events exist)

**Adaptability Improvements Needed:**
1. Generic refresh procedures for any new materialized view
2. Standardized data quality checks for any new table
3. Automated refresh scheduling for any new feature
4. Play-by-play data transformation procedures (not just ingestion)

## Next Steps

1. **Create maintenance schema and procedures** (Week 1)
2. **Implement pg_cron for scheduling** (Week 2)
3. **Add data quality monitoring** (Week 2)
4. **Document refresh strategy** (Week 2)
5. **Evaluate real-time options** (Future)

## Conclusion

The retrosheet warehouse has excellent architecture for historical batch processing but lacks automated real-time update capabilities. The recommended approach is to:

1. Add centralized refresh procedures
2. Implement scheduled refresh via pg_cron
3. Create dependency-aware refresh strategies
4. Add data quality monitoring procedures

This approach aligns with MLB's batch-oriented pattern while providing near-real-time capabilities (5-15 minute latency) suitable for baseball prediction use cases. True real-time (sub-second) is not required for most baseball analytics and would add significant operational complexity.
