# SQL Agent Guidance

**Role**: Schema design, migrations, queries, optimization, and all database operations.

---

## Scope

You are responsible for:
- `sql/` directory organization and structure
- Schema migrations and table definitions
- Query optimization and indexing
- Views and materialized views
- Data quality checks
- Pipeline control tables

---

## Key Documents

| Document | When to Use |
|----------|-------------|
| `docs/keys_and_grains.md` | Entity keys and relationships |
| `docs/architecture.md` | Layer organization and patterns |
| `docs/migration_map.md` | SQL file reorganization |

---

## SQL Directory Structure

```
sql/
  00_admin/              # Pipeline control, checkpoints
  10_raw/                # Source-preserved tables
  20_staging/            # Source-specific cleaned tables
  30_core/               # Canonical entities
  40_bridge/             # Cross-source xref
  50_features/           # ML feature tables
  60_models/             # Model registry, training runs
  70_serving/            # Low-latency read models
  80_quality/            # Data quality checks
```

---

## File Naming Convention

```
{layer}{sequence}_{layer_name}_{description}.sql

Examples:
  000_admin_pipeline_control.sql
  101_raw_mlb_live_feed.sql
  202_stg_mlb_live_events.sql
  301_core_teams.sql
  405_bridge_player_xref.sql
  501_features_run_expectancy.sql
  601_models_registry.sql
  701_serving_predictions.sql
  801_quality_duplicate_check.sql
```

---

## Required SQL Headers

Every SQL file must start with this header:

```sql
/*
File: sql/30_core/301_core_teams.sql
Purpose: Create core teams table with surrogate and natural keys
Author: Agent [identifier]
Date: 2026-04-26
Depends On: 000_admin_database_init.sql
Called By: scripts/migrate_core_tables.sh

Tables Created:
- core.teams (canonical team entities)
- core.teams_history (temporal tracking)

Notes:
- One row per franchise per season
- Includes both retrosheet and mlb identifiers
*/
```

---

## Table Documentation

Every table must have COMMENT statements:

```sql
CREATE TABLE core.teams (
    team_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    franchise_id VARCHAR(10) NOT NULL,
    season INTEGER NOT NULL,
    name VARCHAR(100) NOT NULL,
    city VARCHAR(100),
    mlb_org_id INTEGER,
    retrosheet_id VARCHAR(10),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(franchise_id, season)
);

COMMENT ON TABLE core.teams IS 'Canonical team entities, one per franchise per season';
COMMENT ON COLUMN core.teams.team_id IS 'Surrogate UUID for internal references';
COMMENT ON COLUMN core.teams.franchise_id IS 'Retrosheet franchise identifier';
COMMENT ON COLUMN core.teams.mlb_org_id IS 'MLB API organization ID';
```

---

## Schema Organization

### Raw Tables

- Store source data exactly as received
- Use JSONB for variable schema payloads
- Include checksum for deduplication
- Immutable (no updates)

```sql
CREATE TABLE raw_mlb.live_feed_snapshots (
    snapshot_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    game_pk INTEGER NOT NULL,
    snapshot_timestamp TIMESTAMP NOT NULL,
    payload JSONB NOT NULL,
    payload_checksum VARCHAR(64) NOT NULL,
    ingest_run_id UUID REFERENCES admin.pipeline_runs(run_id),
    UNIQUE(game_pk, payload_checksum)
);
```

### Core Tables

- Surrogate keys (UUID) for internal references
- Natural keys preserved as columns
- Foreign key constraints enforced
- Temporal validity (valid_from/valid_to for SCD Type 2)

```sql
CREATE TABLE core.games (
    game_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    retrosheet_game_id VARCHAR(12) UNIQUE,
    mlb_game_pk INTEGER UNIQUE,
    game_date DATE NOT NULL,
    home_team_id UUID REFERENCES core.teams(team_id),
    away_team_id UUID REFERENCES core.teams(team_id),
    park_id UUID REFERENCES core.parks(park_id),
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Bridge Tables

- Cross-reference between source systems
- Confidence scores for fuzzy matches
- Support manual overrides

```sql
CREATE TABLE bridge.player_xref (
    xref_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    player_id UUID REFERENCES core.players(player_id),
    source_system VARCHAR(20) NOT NULL,
    source_id VARCHAR(50) NOT NULL,
    confidence_score DECIMAL(3,2) DEFAULT 1.0,
    match_type VARCHAR(20) DEFAULT 'exact',
    last_verified_at TIMESTAMP,
    UNIQUE(source_system, source_id)
);
```

---

## Indexing Strategy

### Required Indexes

```sql
-- Primary keys (automatically indexed)
-- Foreign keys (create manually)
CREATE INDEX idx_events_game_id ON core.events(game_id);
CREATE INDEX idx_events_batter_id ON core.events(batter_id);
CREATE INDEX idx_events_pitcher_id ON core.events(pitcher_id);

-- Date ranges for time-series queries
CREATE INDEX idx_games_date ON core.games(game_date);
CREATE INDEX idx_events_date ON core.events USING BRIN (game_date);

-- Text search
CREATE INDEX idx_players_name ON core.players USING GIN (name gin_trgm_ops);
```

### Materialized Views

Use only where justified:

```sql
CREATE MATERIALIZED VIEW serving.daily_standings AS
SELECT ...;

-- Required for CONCURRENTLY refresh
CREATE UNIQUE INDEX idx_daily_standings_pk ON serving.daily_standings(team_id, date);
```

---

## Migration Patterns

### Idempotent Table Creation

```sql
CREATE TABLE IF NOT EXISTS core.teams (
    ...
);
```

### Adding Columns

```sql
ALTER TABLE core.teams 
ADD COLUMN IF NOT EXISTS abbreviation VARCHAR(10);
```

### Backfilling Data

```sql
-- Always do in separate transaction to avoid locks
UPDATE core.teams 
SET abbreviation = SUBSTRING(name, 1, 3)
WHERE abbreviation IS NULL;
```

---

## Data Quality Checks

Create in `sql/80_quality/`:

```sql
-- 801_quality_orphaned_events.sql
SELECT 'orphaned_events' as check_name,
       COUNT(*) as violation_count
FROM core.events e
LEFT JOIN core.games g ON g.game_id = e.game_id
WHERE g.game_id IS NULL;

-- 802_quality_duplicate_games.sql
SELECT 'duplicate_games' as check_name,
       retrosheet_game_id,
       COUNT(*) as count
FROM core.games
GROUP BY retrosheet_game_id
HAVING COUNT(*) > 1;
```

---

## Admin Tables

### Pipeline Control

```sql
-- 000_admin_pipeline_control.sql
CREATE TABLE admin.pipeline_runs (
    run_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pipeline_name VARCHAR(100) NOT NULL,
    started_at TIMESTAMP NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP,
    status VARCHAR(20) DEFAULT 'running',
    records_processed INTEGER DEFAULT 0,
    error_message TEXT,
    config JSONB
);

CREATE TABLE admin.pipeline_checkpoints (
    checkpoint_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pipeline_name VARCHAR(100) NOT NULL,
    checkpoint_key VARCHAR(200) NOT NULL,
    checkpoint_data JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(pipeline_name, checkpoint_key)
);

CREATE TABLE admin.pipeline_errors (
    error_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID REFERENCES admin.pipeline_runs(run_id),
    error_timestamp TIMESTAMP DEFAULT NOW(),
    error_message TEXT,
    context JSONB
);
```

---

## SQL-First Rule

**NEVER** execute SQL without saving to a file:

1. Create `.sql` file in appropriate folder
2. Add header comment
3. Test: `psql -f sql/path/to/file.sql`
4. Commit with descriptive message
5. Update `FILE_INVENTORY.md`

---

## Review Checklist

Before submitting SQL:

- [ ] File has proper header comment
- [ ] Tables have COMMENT ON statements
- [ ] Foreign keys defined where appropriate
- [ ] Indexes created for performance
- [ ] Idempotent (IF NOT EXISTS)
- [ ] `sqlfluff fix` applied
- [ ] Tested with `psql -f`
- [ ] FILE_INVENTORY.md updated

---

## Document Control

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-04-26 | Migration Agent | Initial SQL agent guidance |
