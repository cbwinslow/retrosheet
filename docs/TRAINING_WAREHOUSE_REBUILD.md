# Warehouse Rebuild Process Training

This guide provides step-by-step instructions for rebuilding the Retrosheet Prediction Warehouse from scratch.

## Overview

The warehouse rebuild process ingests Retrosheet data, processes it with Chadwick tools, loads it into PostgreSQL, and creates feature marts for model training.

## Prerequisites

- PostgreSQL 14+ installed and running
- Python 3.9+ with required dependencies
- Chadwick tools installed (cwevent, cwgame, cwdaily, cwsub, cwcomment)
- Retrosheet data downloaded to `data/raw/retrosheet/`
- Database named `retrosheet` created

## Step-by-Step Process

### Step 1: Check Dependencies

```bash
python3 scripts/warehouse.py check-deps
```

This verifies that all required tools (psql, git, Chadwick tools) are installed and accessible.

**Expected Output:** All tools should show "ok"

### Step 2: Fetch Retrosheet Data

```bash
python3 scripts/warehouse.py fetch-retrosheet --years 2000-2025
```

This downloads Retrosheet event files for the specified years to `data/raw/retrosheet/`.

**Parameters:**
- `--years`: Year range to download (e.g., `2000-2025` or `2000,2001,2002`)

**Expected Output:** Downloaded files listed by year and team

### Step 3: Initialize Database

```bash
python3 scripts/warehouse.py init-db
```

This runs all SQL migrations to create the warehouse schema.

**Expected Output:** Migration files applied in order

### Step 4: Extract Chadwick Data

```bash
python3 scripts/warehouse.py extract-chadwick --years 2000-2025 --outputs all
```

This runs Chadwick tools to extract structured data from Retrosheet event files.

**Parameters:**
- `--years`: Year range to process
- `--outputs`: Which outputs to generate (all, events, games, daily, subs, comments)

**Expected Output:** CSV files created in `data/processed/retrosheet/`

**What This Does:**
- `cwevent`: Extracts play-by-play event data
- `cwgame`: Extracts game metadata and lineups
- `cwdaily`: Extracts daily player statistics
- `cwsub`: Extracts substitution records
- `cwcomment`: Extracts comments and ejections

### Step 5: Load Chadwick Data

```bash
python3 scripts/warehouse.py load-chadwick --years 2000-2025 --outputs all
```

This loads the extracted Chadwick data into PostgreSQL tables.

**Parameters:**
- `--years`: Year range to load
- `--outputs`: Which outputs to load

**Expected Output:** Row counts for each loaded table

**Tables Populated:**
- `raw_retrosheet.events_*`: Raw event data
- `raw_retrosheet.games_*`: Raw game data
- `raw_retrosheet.daily_*`: Daily statistics
- `raw_retrosheet.subs_*`: Substitution records
- `raw_retrosheet.comments_*`: Comments and ejections

### Step 6: Run Core Migrations

```bash
psql -d retrosheet -f sql/010_core_tables.sql
psql -d retrosheet -f sql/020_reference_tables.sql
psql -d retrosheet -f sql/030_core_views.sql
```

This creates the core canonical tables and views.

**What This Does:**
- Creates typed baseball entities in `core` schema
- Creates reference tables for players, teams, parks
- Creates canonical views for games, events, plate appearances

### Step 7: Load Reference Metadata

```bash
python3 scripts/load_reference_metadata.py
```

This loads player handedness and refreshes feature materialized views.

**Expected Output:** Updated row counts for player metadata

### Step 8: Load Auxiliary Metadata

```bash
python3 scripts/load_auxiliary_retrosheet.py
```

This loads additional Retrosheet auxiliary data (rosters, All-Star games, schedules, umpires, coaches).

**Expected Output:** Row counts for auxiliary tables

### Step 9: Create Feature Marts

```bash
psql -d retrosheet -f sql/050_feature_marts.sql
```

This creates indexed ML feature marts for model training.

**What This Does:**
- Creates `features.plate_appearance_outcome_examples`
- Creates `features.plate_appearance_outcome_grouped_examples`
- Adds indexes for efficient querying

### Step 10: Create Advanced Feature Marts (Optional)

```bash
psql -d retrosheet -f sql/060_advanced_feature_marts.sql
```

This creates higher-signal feature marts with career priors, matchup history, and team form.

**What This Does:**
- Creates `features.plate_appearance_advanced_examples`
- Adds career-prior player rates
- Adds batter-pitcher matchup history
- Adds park run environment factors
- Adds rolling team form statistics

### Step 11: Validate Data Quality

```bash
python3 scripts/validate_data_quality.py
```

This runs data quality checks on the warehouse.

**Expected Output:** Summary of passed/failed checks

**If Checks Fail:**
1. Review failed checks in output
2. Investigate root cause
3. Fix data or schema issues
4. Re-run validation

## Using the Rebuild Script

For convenience, use the canonical rebuild script:

```bash
./scripts/rebuild_warehouse.sh
```

This runs all steps in the correct order with error handling.

## Troubleshooting

### Issue: Chadwick tool not found

**Solution:** Install Chadwick tools from https://chadwick.sourceforge.net/

### Issue: Database connection failed

**Solution:** Check PostgreSQL is running and database exists:
```bash
pg_ctl status
psql -l
```

### Issue: Out of memory during extraction

**Solution:** Process years in smaller batches:
```bash
python3 scripts/warehouse.py extract-chadwick --years 2000-2005 --outputs all
python3 scripts/warehouse.py extract-chadwick --years 2006-2010 --outputs all
```

### Issue: Migration fails halfway through

**Solution:** Check which migrations were applied:
```bash
psql -d retrosheet -c "SELECT filename FROM schema_migrations ORDER BY applied_at;"
```

### Issue: Data quality checks fail

**Solution:** Run validation with output file:
```bash
python3 scripts/validate_data_quality.py --output validation_report.json
```

Review the JSON output for detailed failure information.

## Validation

After rebuild, validate with:

```bash
# Check row counts
psql -d retrosheet -c "SELECT COUNT(*) FROM core.games;"
psql -d retrosheet -c "SELECT COUNT(*) FROM core.events;"
psql -d retrosheet -c "SELECT COUNT(*) FROM features.plate_appearance_advanced_examples;"

# Run data quality validation
python3 scripts/validate_data_quality.py

# Test model training
python3 scripts/train_pa_outcome_distribution.py --feature-set advanced --train-years 2000-2022 --validation-years 2023-2025
```

## Performance Tips

- Use `--outputs` parameter to process only needed outputs
- Process years in batches for large rebuilds
- Use parallel processing where available
- Monitor disk space during extraction (processed files can be large)

## Next Steps

After successful rebuild:
1. Train models using `scripts/train_pa_outcome_distribution.py`
2. Calibrate models using `scripts/calibrate_pa_outcome_model.py`
3. Validate predictions using `scripts/analyze_pa_outcome_calibration.py`
4. Set up live data ingestion if needed
