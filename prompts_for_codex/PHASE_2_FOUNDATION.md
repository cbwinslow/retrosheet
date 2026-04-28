# Phase 2: Foundation - CLI Commands & Core Infrastructure

## Prerequisites
- Phase 1 audit complete
- Answers to 12 critical questions provided
- Revised plan agreed upon

## Goal
Implement foundation CLI commands and fix core stubs. These are prerequisites for all other work.

---

## Task 2.1: Enhance `baseball doctor` Command

### Current State
Basic implementation exists in `baseball/cli.py` (lines 37-82). It checks DB connection and directories.

### Requirements

#### 2.1.1 Database Health Checks
Add to `doctor()` function:

```python
# Check PostgreSQL extensions
checks.append(check_extension('hstore', 'Required for key-value storage'))
checks.append(check_extension('pg_stat_statements', 'Optional for query analysis'))

# Check database version
version = get_db_version()
if version >= 14:
    checks.append(('PostgreSQL Version', f'✅ {version}', 'green'))
else:
    checks.append(('PostgreSQL Version', f'⚠️ {version} (14+ recommended)', 'yellow'))

# Check connection pool
checks.append(check_connection_pool())
```

#### 2.1.2 Chadwick Integration Check
```python
def check_chadwick():
    # Verify cwevent binary exists
    # Run cwevent --version
    # Parse a test event file to verify it works
    # Return status
```

#### 2.1.3 Configuration Validation
```python
def check_configs():
    # Validate YAML syntax for all config files
    # Verify referenced SQL files exist
    # Check for required keys in each config
    # Return list of validation errors
```

#### 2.1.4 Disk Space Check
```python
def check_disk_space():
    # Check data/ directory writable
    # Check >10GB free space
    # Check PostgreSQL data directory
    # Return warnings if low
```

#### 2.1.5 Python Dependencies
```python
def check_dependencies():
    # Critical: psycopg2, pandas, numpy, typer, pydantic
    # Optional: xgboost, sklearn (for ML)
    # Return which are installed
```

### Output Format
The `doctor` command should output:
```
┏━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Component           ┃ Status                     ┃
┡━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Database Connection │ ✅ OK                      │
│ PostgreSQL Version  │ ✅ 15.4                    │
│ hstore Extension    │ ✅ Installed               │
│ Data Directory      │ ✅ OK (45GB free)          │
│ Chadwick Binary     │ ✅ cwevent 0.9.3           │
│ Config Files        │ ✅ All valid               │
│ ...                 │ ...                        │
└─────────────────────┴────────────────────────────┘

✅ All checks passed
```

### Validation
```bash
baseball doctor
# Exit code 0 = all passed
# Exit code 1 = any failed

baseball doctor --json
# Output JSON for CI/CD integration
```

### Testing
Create `tests/unit/test_doctor.py`:
```python
def test_doctor_with_valid_config():
    # Mock all checks to pass
    # Assert exit code 0
    
def test_doctor_with_missing_chadwick():
    # Mock Chadwick check to fail
    # Assert exit code 1
    # Assert proper error message
    
def test_doctor_json_output():
    # Call with --json
    # Assert valid JSON structure
```

---

## Task 2.2: Enhance `baseball status` Command

### Current State
Basic implementation exists (lines 85-130+). Shows recent pipeline runs.

### Requirements

#### 2.2.1 Database Summary
```python
def get_database_summary():
    # Total rows across all schemas
    # Table counts per schema
    # Last update timestamp per schema
    # Return structured data
```

#### 2.2.2 Pipeline Status
```python
def get_pipeline_status():
    # Recent pipeline runs (last 5)
    # Currently running pipelines
    # Success/failure counts (last 24h)
    # Average runtime per pipeline
```

#### 2.2.3 Model Status
```python
def get_model_status():
    # Registered models count
    # Latest trained model per type
    # Model performance summary (last 30 days)
```

#### 2.2.4 Data Freshness
```python
def get_data_freshness():
    # Last MLB data ingestion
    # Last Retrosheet update
    # Last Statcast update
    # Age of data in hours
```

### Output Format
```
Baseball Platform Status

📊 Database Summary
  Total Rows: 45,231,892
  Schemas: 8 (raw_mlb, core, features, serving, ...)
  Last Update: 2026-04-28 03:45 UTC

🔄 Pipeline Activity (Last 24h)
  Runs: 12 total (10 success, 2 failed)
  Currently Running: 1 (daily pipeline, 15m elapsed)
  
🤖 Models
  Registered: 3 (next_run, pa_outcome, win_probability)
  Last Trained: pa_outcome @ 2026-04-27 14:30
  
📡 Data Freshness
  MLB Live: 5 minutes ago
  Retrosheet: 3 hours ago
  Statcast: Current season only
```

### Validation
```bash
baseball status
# Shows real data from database

baseball status --watch
# Updates every 10 seconds (for monitoring)
```

---

## Task 2.3: Implement Bridge CLI Commands

### Current State
Three stub commands in `baseball/cli.py`:
- `bridge resolve` (line 1066-1079)
- `bridge match` (line 1082-1093)
- `bridge lookup` (line 1096-1106)

All raise `NotImplementedError`.

### Background
Read `baseball/services/bridge.py` - it has working methods:
- `resolve_id()` - lines 185-242
- `lookup_canonical()` - lines 244-303
- `get_coverage_stats()` - lines 305-342

### Requirements

#### 2.3.1 Implement `bridge resolve`
```python
@bridge_app.command(name='resolve')
def bridge_resolve(
    source: str = typer.Option(..., '--source', '-s', ...),
    source_id: str = typer.Option(..., '--id', '-i', ...),
    entity_type: str = typer.Option('player', '--type', '-t', ...),
):
    """Resolve a source ID to canonical ID."""
    # Call BridgeService().resolve_id()
    # Display result with confidence score
    # Handle not found gracefully
```

Example output:
```
Resolving player ID 545361 from mlb...

✅ Found canonical mapping:
   Canonical ID: P-12345
   Confidence: 0.95
   Sources: mlb(545361), retrosheet(rodri006), espn(31234)
```

#### 2.3.2 Implement `bridge lookup`
```python
@bridge_app.command(name='lookup')
def bridge_lookup(
    canonical_id: str = typer.Option(..., '--id', '-i', ...),
    entity_type: str = typer.Option('player', '--type', '-t', ...),
):
    """Lookup all source IDs for a canonical ID."""
    # Call BridgeService().lookup_canonical()
    # Display all source mappings
```

#### 2.3.3 Implement `bridge match` (Simplified)
```python
@bridge_app.command(name='match')
def bridge_match(
    entity_type: str = typer.Option(..., '--type', '-t', ...),
    source_a: str = typer.Option(..., '--source-a', ...),
    source_b: str = typer.Option(..., '--source-b', ...),
    limit: int = typer.Option(10, '--limit', '-l', ...),
):
    """Find unmatched entities between two sources."""
    # Query for entities in source_a not in source_b
    # Display table of matches needed
```

### Testing
Create `tests/unit/test_bridge_cli.py`:
```python
def test_bridge_resolve_player():
    # Mock BridgeService.resolve_id
    # Call CLI with known player
    # Assert output contains canonical ID
    
def test_bridge_lookup_canonical():
    # Mock lookup_canonical
    # Call CLI
    # Assert all source IDs displayed
```

---

## Task 2.4: Fix Predict Command Stubs

### Current State
Three stub commands:
- `predict today` (line 539-543)
- `predict live` (line 550-554)
- `predict batch` (line 562-566)

All have TODO comments and exit without doing anything.

### Decision Point (from Phase 1 answers)
If Phase 1 determined these should be implemented:

#### 2.4.1 Implement `predict today`
```python
@predict_app.command(name='today')
def predict_today(
    model: str = typer.Option('win_probability', '--model', '-m', ...),
    output: Path = typer.Option(None, '--output', '-o', ...),
):
    """Run predictions for all games today."""
    # Fetch today's schedule
    # For each game:
    #   - Get current game state
    #   - Compute features
    #   - Run prediction
    #   - Store result
    # Display results table
```

#### 2.4.2 Implement `predict live` (if Phase 1 said yes to WebSocket)
```python
@predict_app.command(name='live')
def predict_live(
    game_pk: int = typer.Option(..., '--game', '-g', ...),
    interval: int = typer.Option(30, '--interval', '-i', ...),
):
    """Run continuous live predictions for a game."""
    # Poll MLB API every interval seconds
    # When state changes:
    #   - Compute features
    #   - Run prediction
    #   - Display updated probabilities
```

---

## Task 2.5: Add Model CLI Commands

### Current State
Model commands in `baseball/cli.py` (lines 700-780+):
- `models list` - shows table but queries nothing
- `models info` - stub
- `models download` - stub
- `models archive` - stub
- `models compare` - stub
- `models export` - stub

### Requirements

#### 2.5.1 Implement `models list`
```python
@models_app.command(name='list')
def models_list():
    """List all registered models."""
    # Query models.registry table
    # Show: name, type, last trained, status
    # Sort by last trained desc
```

#### 2.5.2 Implement `models info`
```python
@models_app.command(name='info')
def models_info(
    model_name: str = typer.Option(..., '--model', '-m', ...),
):
    """Show detailed info about a model."""
    # Load model from registry
    # Show: config, metrics, features used, training date
```

---

## SQL Requirements

For this phase, you may need to create or verify:

1. **Check existing SQL files** (read before modifying):
   - `sql/00_admin/000_admin_pipeline_control.sql`
   - `sql/60_models/600_models_registry.sql`
   - Bridge tables in `sql/40_bridge/`

2. **Potentially add** (if not exists):
   - `sql/80_quality/001_data_quality_checks.sql` - For doctor command
   - `sql/00_admin/005_system_health_log.sql` - For status command

---

## Validation Steps

After completing this phase, run:

```bash
# 1. Test doctor command
baseball doctor
# Should show all checks ✅

# 2. Test status command
baseball status
# Should show real data

# 3. Test bridge commands
baseball bridge resolve --source mlb --id 545361 --type player
# Should return canonical ID

baseball bridge lookup --id P-12345 --type player
# Should show all source IDs

# 4. Run demo script
python scripts/demo_full_system.py --mode quick
# Should show fewer ❌ marks

# 5. Run tests
python -m pytest tests/unit/test_doctor.py tests/unit/test_bridge_cli.py -v
```

---

## Documentation Updates

Update these files as you work:

1. **AGENTS.md**:
   - Mark `baseball doctor` as complete
   - Mark `baseball status` as complete
   - Mark bridge commands as complete

2. **PROJECT_LOG.md**:
   - Add entry: "Phase 2: Foundation CLI commands complete"
   - List which commands now work

3. **FILE_INVENTORY.md**:
   - Add new test files
   - Update CLI command references

---

## Success Criteria

- [ ] `baseball doctor` shows comprehensive health check
- [ ] `baseball status` shows real system status
- [ ] `baseball bridge resolve` works end-to-end
- [ ] `baseball bridge lookup` works end-to-end
- [ ] `baseball models list` shows real models
- [ ] All commands have tests
- [ ] Documentation updated
- [ ] Demo script shows improvement

---

## Time Estimate

4-5 hours for comprehensive implementation and testing.
