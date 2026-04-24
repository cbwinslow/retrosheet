# Reproducibility Audit & Documentation Gap-Fill Prompt

**For:** KiloCode / Cline / Cascade Agents  
**Priority:** CRITICAL - All Future Work Depends On This  
**Estimated Effort:** 8-12 hours  
**Context:** This prompt instructs you to audit our entire baseball prediction warehouse and fill in all documentation gaps to make the project fully reproducible by other researchers.

---

## Your Mission

The project owner has identified that we have NOT been following proper reproducibility standards. We need to go back through EVERYTHING we've built and create the paper trail that should have existed from day one.

**Goal:** Make this project reproducible by a researcher who knows nothing about our work.

**CRITICAL REQUIREMENT:** To close this issue, you MUST create:
1. Missing SQL files for any ad-hoc database operations that exist
2. Missing wrapper scripts for all data pipelines
3. Missing COMMENT ON statements for all tables/columns
4. E2E test scripts that verify everything works
5. Documentation that allows another AI agent to reproduce everything

**This task is NOT complete until all gaps are closed with version-controlled artifacts.**

---

## Phase 1: Audit Current State (2-3 hours)

### 1.1 Inventory All SQL Files

List every SQL file in the project and categorize:

```bash
find /home/cbwinslow/workspace/retrosheet -name "*.sql" -type f | sort
```

For each SQL file, determine:
- Does it have a header comment with File/Purpose/Author/Date/Depends On/Called By?
- Does it have COMMENT ON statements for every table it creates?
- Does it have COMMENT ON statements for every column?
- Is it documented in `docs/agents/FILE_INVENTORY.md`?
- Is it part of a procedure in `docs/agents/PROCEDURES.md`?
- Does it have a wrapper script that calls it?

### 1.2 Inventory All Python Scripts

```bash
find /home/cbwinslow/workspace/retrosheet/scripts -name "*.py" -type f | sort
```

For each script:
- Does it have a docstring explaining what it does?
- Does it have command-line argument documentation?
- Is it documented in `docs/agents/FILE_INVENTORY.md`?
- Does it write to a log or tracking table?
- Does it have input/output documentation?

### 1.3 Check Database Table Documentation

Connect to the database and check:

```sql
-- Tables without comments
SELECT schemaname, tablename 
FROM pg_tables 
WHERE schemaname IN ('core', 'features', 'features_pitch', 'raw_mlb', 'raw_retrosheet', 'bridge', 'predictions', 'models')
AND NOT EXISTS (
    SELECT 1 FROM pg_description 
    WHERE objoid = (schemaname || '.' || tablename)::regclass::oid
);

-- Columns without comments
SELECT c.table_schema, c.table_name, c.column_name
FROM information_schema.columns c
WHERE c.table_schema IN ('core', 'features', 'features_pitch', 'raw_mlb', 'raw_retrosheet', 'bridge', 'predictions', 'models')
AND NOT EXISTS (
    SELECT 1 FROM pg_description d
    JOIN pg_class pc ON pc.oid = d.objoid
    JOIN pg_namespace pn ON pn.oid = pc.relnamespace
    JOIN pg_attribute pa ON pa.attrelid = pc.oid AND pa.attnum = d.objsubid
    WHERE pn.nspname = c.table_schema 
    AND pc.relname = c.table_name 
    AND pa.attname = c.column_name
);
```

---

## Phase 2: Fix Documentation Gaps (5-7 hours)

### 2.1 Create SQL Header Comments

For every SQL file missing a header, add:

```sql
/*
File: sql/core/050_feature_marts.sql
Purpose: Build ML-ready feature marts from core data
Author: Agent [identifier]
Date: 2026-04-24
Depends On: core.games, core.events, core.plate_appearances
Called By: scripts/rebuild_warehouse.sh

Tables Created:
- features.batter_prior_season (batter prior-season aggregates)
- features.pitcher_prior_season (pitcher prior-season aggregates)
- features.team_prior_season (team prior-season aggregates)
- features.context_prior_season (game context features)
- features.half_inning_outcome_summary (half-inning outcomes for simulation)

Notes:
- Uses feature_season = game_year + 1 to avoid leakage
- All aggregates exclude the current season
- Materialized views for performance
*/
```

### 2.2 Add Table/Column Comments

Create a new SQL file: `sql/maintenance/900_add_missing_comments.sql`

For every table without a comment, add:
```sql
COMMENT ON TABLE core.games IS 'Canonical historical games from Retrosheet/Chadwick. 62,598 rows (1898-2025). Source-preserved from Chadwick cwgame output.';
```

For every column without a comment, add:
```sql
COMMENT ON COLUMN core.games.game_id IS 'Retrosheet game ID format: {home_team}{YYYYMMDD}{game_num}';
COMMENT ON COLUMN core.games.home_team_id IS 'Retrosheet 3-char team ID (e.g., ANA, BOS, NYA)';
```

### 2.3 Create Wrapper Scripts

For every major data pipeline, create a wrapper script:

**Example: `scripts/pitch_data/update_all_pitch_features.sh`**
```bash
#!/bin/bash
# File: scripts/pitch_data/update_all_pitch_features.sh
# Purpose: Orchestrate all pitch-level feature updates
# Author: Agent [identifier]
# Date: 2026-04-24
#
# This script calls granular procedures in order:
# 1. Load base features from raw_mlb.statcast
# 2. Build engineered features
# 3. Update pitcher arsenals
# 4. Update player profiles
# 5. Validate row counts

set -e

echo "=== Pitch Feature Update Pipeline ==="
echo "Started: $(date)"

echo "[1/5] Loading base features..."
psql -f sql/features/004_alter_base_features_types.sql

echo "[2/5] Building engineered features..."
psql -f sql/features/005_build_engineered_features.sql

echo "[3/5] Updating pitcher arsenals..."
psql -f sql/features/010_pitcher_arsenal_features.sql

echo "[4/5] Updating player profiles..."
psql -f sql/features/002_player_profile_mart.sql

echo "[5/5] Running validation..."
psql -c "SELECT COUNT(*) as total_pitches FROM features_pitch.base_features;"
psql -c "SELECT COUNT(*) as engineered_features FROM features_pitch.engineered_features;"

echo "=== Pipeline Complete ==="
echo "Finished: $(date)"
```

Create wrappers for:
- `scripts/warehouse/rebuild_core_tables.sh` - All core table rebuilds
- `scripts/warehouse/rebuild_feature_marts.sh` - All feature mart rebuilds
- `scripts/bridge/populate_all_bridge_tables.sh` - Bridge table population
- `scripts/ml/train_all_models.sh` - Model training pipeline
- `scripts/ml/update_live_predictions.sh` - Live prediction pipeline

### 2.4 Update FILE_INVENTORY.md

For every SQL file and script, ensure FILE_INVENTORY.md has:

```markdown
| File | Purpose | Canonical Position | Depends On | Creates/Updates |
|------|---------|-------------------|------------|-----------------|
| `sql/core/050_feature_marts.sql` | Build ML-ready feature marts from core data | After core tables, before model training | core.games, core.events | features.batter_prior_season, features.pitcher_prior_season, features.team_prior_season |
```

### 2.5 Update PROCEDURES.md

For every workflow, ensure PROCEDURES.md has:

```markdown
## Update Pitch-Level Features

Purpose: Refresh all pitch-level features from Statcast data.

Command:
```bash
./scripts/pitch_data/update_all_pitch_features.sh
```

Expected order:
1. Load base features from raw_mlb.statcast
2. Build engineered features (movement, location, physics)
3. Update pitcher arsenals (pitch-type breakdowns)
4. Update player profiles (batter zones, pitcher arsenals)
5. Validate row counts match raw data

Granular steps (for debugging):
```bash
psql -f sql/features/004_alter_base_features_types.sql
psql -f sql/features/005_build_engineered_features.sql
psql -f sql/features/010_pitcher_arsenal_features.sql
psql -f sql/features/002_player_profile_mart.sql
```

Validation:
```sql
-- Check pitch counts
SELECT game_year, COUNT(*) 
FROM features_pitch.base_features 
GROUP BY game_year ORDER BY game_year;

-- Check for missing engineered features
SELECT COUNT(*) as missing 
FROM features_pitch.base_features b
LEFT JOIN features_pitch.engineered_features e ON b.pitch_id = e.pitch_id
WHERE e.pitch_id IS NULL;
```
```

---

## Phase 3: Create Missing Documentation (2-3 hours)

### 3.1 Create Table Dictionary

Create `docs/TABLE_DICTIONARY.md` with EVERY table:

```markdown
# Table Dictionary

## Core Tables

### core.games
**Purpose:** Canonical historical games from Retrosheet/Chadwick  
**Rows:** 62,598 (1898-2025)  
**Source:** Chadwick cwgame output with -n flag for headers  
**SQL File:** `sql/core/010_core_games_events.sql`  

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| game_id | VARCHAR(12) | Retrosheet game ID: {home_team}{YYYYMMDD}{game_num} | ANA202506060 |
| game_date | DATE | Date game was played | 2025-06-06 |
| home_team_id | VARCHAR(3) | Retrosheet 3-char team ID | ANA |
| away_team_id | VARCHAR(3) | Retrosheet 3-char team ID | BOS |
| home_score | INTEGER | Final score, home team | 5 |
| away_score | INTEGER | Final score, away team | 3 |

**Key Relationships:**
- `home_team_id` -> `core.teams_reference.team_id`
- `away_team_id` -> `core.teams_reference.team_id`

**Indexes:**
- PRIMARY KEY (game_id)
- idx_games_date (game_date)
- idx_games_home_team (home_team_id, game_year)

**Sample Query:**
```sql
SELECT * FROM core.games 
WHERE home_team_id = 'ANA' 
AND game_date >= '2025-01-01';
```
```

Repeat for EVERY table in core, features, features_pitch, bridge, predictions, models, raw_mlb, raw_retrosheet.

### 3.2 Create Column Dictionary SQL

Create `sql/maintenance/901_column_dictionary_view.sql`:

```sql
/*
File: sql/maintenance/901_column_dictionary_view.sql
Purpose: Create a queryable column dictionary view
Author: Agent [identifier]
Date: 2026-04-24
*/

CREATE OR REPLACE VIEW maintenance.column_dictionary AS
SELECT 
    c.table_schema,
    c.table_name,
    c.column_name,
    c.data_type,
    c.is_nullable,
    pgd.description as column_comment,
    c.column_default,
    c.character_maximum_length
FROM information_schema.columns c
LEFT JOIN pg_catalog.pg_description pgd 
    ON pgd.objoid = (c.table_schema || '.' || c.table_name)::regclass::oid
    AND pgd.objsubid = c.ordinal_position
WHERE c.table_schema IN ('core', 'features', 'features_pitch', 'bridge', 'predictions', 'models', 'raw_mlb', 'raw_retrosheet')
ORDER BY c.table_schema, c.table_name, c.ordinal_position;

COMMENT ON VIEW maintenance.column_dictionary IS 'Queryable dictionary of all columns in baseball warehouse schemas';
```

### 3.3 Create Data Lineage Document

Create `docs/DATA_LINEAGE.md` showing the flow:

```markdown
# Data Lineage

## Overview

```
Retrosheet Event Files ( Chadwick ) 
    -> raw_retrosheet.chadwick_events
    -> core.events
    -> core.plate_appearances
    -> features.plate_appearance_outcome_examples
    -> models.model_registry (training)

Statcast API ( pybaseball )
    -> raw_mlb.statcast
    -> features_pitch.locations
    -> features_pitch.base_features
    -> features_pitch.engineered_features
    -> models.model_registry (training)

MLB Stats API ( live )
    -> raw_mlb.live_feed_snapshots
    -> core.live_games / core.live_events
    -> features.live_plate_appearance_advanced_count_examples
    -> predictions.prediction_runs
```

## Detailed Lineage by Table

### core.games

**Source:** Chadwick cwgame output  
**Input Files:** data/retrosheet/event/*.EV*  
**Loading Script:** `scripts/warehouse.py load-chadwick`  
**SQL File:** `sql/core/010_core_games_events.sql`  
**Downstream Consumers:**
- core.events (via game_id)
- core.plate_appearances (via game_id)
- features.batter_prior_season (aggregates by game_year)

**Row Count History:**
- 2026-04-18: 62,598 rows (loaded from 1898-2025 event files)
```

---

## Phase 4: E2E Testing Environment Setup (2 hours)

### 4.1 Create Test Database Schema

Create `sql/test/001_create_test_schema.sql`:
```sql
/*
File: sql/test/001_create_test_schema.sql
Purpose: Create isolated test schema for E2E validation
Author: Agent [identifier]
Date: 2026-04-24
Called By: scripts/test/e2e_test_runner.sh
*/

-- Drop and recreate test schema
DROP SCHEMA IF EXISTS test CASCADE;
CREATE SCHEMA test;

-- Grant permissions
GRANT ALL ON SCHEMA test TO CURRENT_USER;

-- Create test tracking table
CREATE TABLE test.runs (
    run_id SERIAL PRIMARY KEY,
    test_name VARCHAR(255) NOT NULL,
    started_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    status VARCHAR(20) DEFAULT 'running',
    error_message TEXT,
    row_counts JSONB
);

COMMENT ON TABLE test.runs IS 'Tracks E2E test execution and results';
```

### 4.2 Create Test Data Fixtures

Create `sql/test/002_test_fixtures.sql`:
```sql
/*
File: sql/test/002_test_fixtures.sql
Purpose: Create minimal test data for E2E validation
Author: Agent [identifier]
Date: 2026-04-24
Called By: scripts/test/e2e_test_runner.sh
*/

-- Create test game data (subset of real data)
CREATE TABLE test.sample_games AS
SELECT * FROM core.games 
WHERE game_date >= '2024-01-01' 
LIMIT 100;

-- Create test events data
CREATE TABLE test.sample_events AS
SELECT e.* 
FROM core.events e
JOIN test.sample_games g ON e.game_id = g.game_id;

-- Add comments
COMMENT ON TABLE test.sample_games IS 'Test fixture: 100 games from 2024';
COMMENT ON TABLE test.sample_events IS 'Test fixture: Events for sample games';
```

### 4.3 Create E2E Test Runner Script

Create `scripts/test/e2e_test_runner.sh`:
```bash
#!/bin/bash
# File: scripts/test/e2e_test_runner.sh
# Purpose: Run end-to-end tests on all data pipelines
# Author: Agent [identifier]
# Date: 2026-04-24
#
# Usage: ./scripts/test/e2e_test_runner.sh [--quick|--full]

set -e

TEST_MODE="${1:---quick}"
TEST_SCHEMA="test"
RUN_ID=$(date +%s)

echo "=== E2E Test Runner ==="
echo "Run ID: $RUN_ID"
echo "Mode: $TEST_MODE"
echo "Started: $(date)"

# Initialize test schema
echo "[1/5] Setting up test schema..."
psql -f sql/test/001_create_test_schema.sql
psql -c "INSERT INTO test.runs (test_name, run_id) VALUES ('e2e_pipeline', $RUN_ID);"

# Test core table rebuild
echo "[2/5] Testing core table procedures..."
if psql -f sql/core/001_init.sql 2>&1 | grep -q "ERROR"; then
    echo "FAIL: Core init failed"
    psql -c "UPDATE test.runs SET status='failed', error_message='Core init failed' WHERE run_id=$RUN_ID;"
    exit 1
fi

# Test feature mart creation
echo "[3/5] Testing feature mart procedures..."
for sql_file in sql/features/*.sql; do
    echo "  Testing: $sql_file"
    if ! psql -f "$sql_file" > /dev/null 2>&1; then
        echo "  WARNING: $sql_file had issues (may be dependencies)"
    fi
done

# Test bridge procedures
echo "[4/5] Testing bridge table procedures..."
psql -c "SELECT bridge.validate_all_bridge_tables();"

# Validate row counts
echo "[5/5] Validating row counts..."
psql -c "
UPDATE test.runs 
SET status='completed', 
    completed_at=NOW(),
    row_counts=(
        SELECT jsonb_build_object(
            'core_games', (SELECT COUNT(*) FROM core.games),
            'core_events', (SELECT COUNT(*) FROM core.events),
            'features_pitch_base', (SELECT COUNT(*) FROM features_pitch.base_features),
            'bridge_player_xref', (SELECT COUNT(*) FROM bridge.player_xref)
        )
    )
WHERE run_id=$RUN_ID;
"

echo "=== E2E Tests Complete ==="
echo "Results:"
psql -c "SELECT * FROM test.runs WHERE run_id=$RUN_ID;"
```

Make it executable:
```bash
chmod +x scripts/test/e2e_test_runner.sh
```

### 4.4 Create SQL Validation Script

Create `scripts/test/validate_sql_files.sh`:
```bash
#!/bin/bash
# File: scripts/test/validate_sql_files.sh
# Purpose: Validate all SQL files have proper headers and comments
# Author: Agent [identifier]
# Date: 2026-04-24

echo "=== SQL File Validation ==="

ERRORS=0

for f in $(find /home/cbwinslow/workspace/retrosheet -name "*.sql" -type f); do
    # Check for header comment
    if ! head -5 "$f" | grep -q "File:"; then
        echo "ERROR: Missing header: $f"
        ((ERRORS++))
    fi
    
    # Check for CREATE TABLE statements without comments
    if grep -q "CREATE TABLE" "$f"; then
        if ! grep -q "COMMENT ON TABLE" "$f"; then
            echo "WARNING: Missing table comments: $f"
        fi
    fi
done

if [ $ERRORS -eq 0 ]; then
    echo "All SQL files have headers"
else
    echo "$ERRORS SQL files missing headers"
    exit 1
fi
```

### 4.5 Create Rebuild Verification Script

Create `scripts/test/verify_rebuild.sh`:
```bash
#!/bin/bash
# File: scripts/test/verify_rebuild.sh
# Purpose: Verify warehouse can be rebuilt from scratch
# Author: Agent [identifier]
# Date: 2026-04-24
#
# WARNING: This drops and recreates tables - use with caution!

set -e

echo "=== Warehouse Rebuild Verification ==="
echo "This will verify the rebuild_warehouse.sh script works correctly"
echo "Started: $(date)"

# Run the actual rebuild (in test mode)
TEST_MODE=1 ./scripts/rebuild_warehouse.sh

# Verify key tables exist and have data
echo "Verifying core tables..."

TABLES=(
    "core.games:1000"
    "core.events:10000"
    "core.plate_appearances:5000"
    "bridge.player_xref:1000"
    "bridge.team_xref:30"
)

for table_spec in "${TABLES[@]}"; do
    IFS=':' read -r table min_rows <<< "$table_spec"
    count=$(psql -t -c "SELECT COUNT(*) FROM $table;" | xargs)
    if [ "$count" -lt "$min_rows" ]; then
        echo "ERROR: $table has only $count rows (expected >= $min_rows)"
        exit 1
    fi
    echo "OK: $table has $count rows"
done

echo "=== Rebuild Verification Complete ==="
```

## Phase 5: Validation & Verification (1 hour)

### 5.1 Verify All SQL Files Have Headers

```bash
# Find SQL files without proper headers
for f in $(find /home/cbwinslow/workspace/retrosheet -name "*.sql" -type f); do
    if ! head -10 "$f" | grep -q "File:"; then
        echo "Missing header: $f"
    fi
done
```

### 4.2 Verify All Tables Have Comments

```sql
-- This should return 0 rows when complete
SELECT schemaname, tablename 
FROM pg_tables 
WHERE schemaname IN ('core', 'features', 'features_pitch', 'raw_mlb', 'raw_retrosheet', 'bridge', 'predictions', 'models')
AND NOT EXISTS (
    SELECT 1 FROM pg_description 
    WHERE objoid = (schemaname || '.' || tablename)::regclass::oid
);
```

### 4.3 Verify Wrapper Scripts Work

Run each wrapper script with `--dry-run` or on a subset of data to verify:
- All paths are correct
- All SQL files exist
- No missing dependencies

---

## Deliverables Checklist

Before marking this task complete, verify:

- [ ] Every SQL file has a header comment (File/Purpose/Author/Date/Depends On/Called By)
- [ ] Every table has a COMMENT ON statement
- [ ] Every column has a COMMENT ON statement
- [ ] FILE_INVENTORY.md updated with all files
- [ ] PROCEDURES.md updated with all workflows
- [ ] Wrapper scripts created for all major pipelines
- [ ] docs/TABLE_DICTIONARY.md created with all tables documented
- [ ] docs/DATA_LINEAGE.md created showing data flow
- [ ] sql/maintenance/900_add_missing_comments.sql created and executed
- [ ] sql/maintenance/901_column_dictionary_view.sql created
- [ ] All scripts tested and working
- [ ] Git commit made with all changes
- [ ] PROJECT_LOG.md updated with audit completion
- [ ] E2E testing environment created (sql/test/, scripts/test/)
- [ ] sql/test/001_create_test_schema.sql created
- [ ] sql/test/002_test_fixtures.sql created
- [ ] scripts/test/e2e_test_runner.sh created and executable
- [ ] scripts/test/validate_sql_files.sh created
- [ ] scripts/test/verify_rebuild.sh created
- [ ] E2E tests pass successfully

---

## E2E Testing Environment FAQ

### Can we do this for free on my PC?

**YES.** The E2E environment uses your existing PostgreSQL instance. No Docker, no cloud, no additional cost.

### How does it work?

1. **Test Schema**: Uses a separate `test` schema in your existing database - isolated from production data
2. **Test Fixtures**: Creates small, fast test datasets from your real data (e.g., 100 games instead of 62,000)
3. **Test Scripts**: Bash scripts that run SQL files and verify they work
4. **Validation**: Checks that SQL files have headers, tables have comments, row counts are reasonable

### What gets tested?

- All SQL files execute without errors
- All tables have COMMENT ON statements
- All SQL files have proper headers
- Wrapper scripts run successfully
- Row counts match expected ranges
- Database functions/procedures work

### How do I run the tests?

```bash
# Quick test (5 minutes)
./scripts/test/e2e_test_runner.sh --quick

# Validate SQL file headers
./scripts/test/validate_sql_files.sh

# Full verification (30+ minutes)
./scripts/test/verify_rebuild.sh
```

### What if a test fails?

1. Check `test.runs` table for error messages
2. Fix the SQL/script
3. Re-run the test
4. Commit the fix

### Can an AI agent use this to fill gaps?

**YES.** An AI agent can:
1. Run `validate_sql_files.sh` to find SQL files missing headers
2. Add the headers
3. Re-run to verify
4. Repeat for COMMENT ON statements
5. Create missing wrapper scripts
6. Run `e2e_test_runner.sh` to verify everything works

---

## AI Agent Gap-Fill Procedure

When another AI agent (KiloCode/Cline) picks up this task, they should follow this loop:

### Gap-Fill Loop

```
1. RUN: ./scripts/test/validate_sql_files.sh
2. IDENTIFY: SQL files missing headers or comments
3. CREATE: Missing SQL files/procedures to close gaps
4. ADD: Headers, comments, documentation
5. COMMIT: Save progress
6. RE-RUN: Validate again
7. REPEAT: Until all tests pass
```

### Example Gap-Fill Task

**Finding:** `sql/core/060_advanced_feature_marts.sql` missing header

**Action:**
1. Add header comment to file
2. Run `validate_sql_files.sh` to confirm
3. Commit: "Add header to 060_advanced_feature_marts.sql"
4. Move to next gap

**Finding:** No wrapper script for pitch data pipeline

**Action:**
1. Create `scripts/pitch_data/update_all_pitch_features.sh`
2. Add proper header comment
3. Make executable: `chmod +x`
4. Test: `./scripts/pitch_data/update_all_pitch_features.sh --dry-run`
5. Commit: "Add pitch data pipeline wrapper script"

---

## Critical Rules to Follow

1. **NEVER execute SQL without saving to a file first**
2. **ALWAYS use explicit column mappings** (no SELECT *)
3. **ALWAYS document row counts** in comments
4. **ALWAYS test scripts** before marking complete
5. **ALWAYS update FILE_INVENTORY.md** when adding files
6. **ALWAYS update PROCEDURES.md** when adding workflows

---

## Notes

- This is NOT about creating new functionality - it's about documenting what EXISTS
- Focus on completeness over perfection
- If you find something that doesn't make sense, document it anyway and add a note
- The goal is reproducibility: another researcher should be able to git clone and rebuild

---

## Questions?

If you find something ambiguous:
1. Check `docs/agents/CURRENT_SNAPSHOT.md` for context
2. Check `docs/PROJECT_LOG.md` for history
3. Check `AGENTS.md` for conventions
4. If still unclear, document what you found and move on

---

**Start by reading:**
1. `/home/cbwinslow/workspace/retrosheet/AGENTS.md` (especially the new REPRODUCIBILITY MANDATE section)
2. `/home/cbwinslow/workspace/retrosheet/docs/agents/FILE_INVENTORY.md`
3. `/home/cbwinslow/workspace/retrosheet/docs/agents/PROCEDURES.md`

Then begin the audit.
