# Live Data Ingestion Training Guide

This guide provides step-by-step instructions for ingesting live MLB game data into the Retrosheet Prediction Warehouse.

## Overview

The live data ingestion pipeline enables real-time MLB game data to be ingested alongside historical Retrosheet data, maintaining clean separation between data sources while enabling unified analysis through the `analysis` views.

## Prerequisites

- PostgreSQL database with warehouse initialized
- Bridge tables populated (`bridge.player_xref`, `bridge.team_xref`, `bridge.park_xref`)
- Python environment with required dependencies
- MLB Stats API access (public API, no authentication required)

## Architecture

### Data Flow

```
MLB Stats API → raw_mlb.live_feed_snapshots → core.live_games/core.live_events → features.live_* → analysis.combined_*
```

### Key Components

- **Schedule Discovery**: `scripts/fetch_mlb_schedule.py` - Identifies active/completed games
- **Game Ingestion**: `scripts/warehouse.py fetch-live-game` - Downloads live game feeds
- **Transformation**: `scripts/transform_live_game.py` - Transforms to canonical schema
- **Batch Processing**: `scripts/ingest_live_games.py` - Orchestrates multiple games
- **Bridge Tables**: `bridge.*` - ID mapping between MLB and Retrosheet systems

## One-Time Setup

### 1. Populate Bridge Tables

Bridge tables enable ID translation between MLB IDs and Retrosheet IDs.

```bash
python3 scripts/populate_bridge_tables.py
```

This script:
- Downloads Chadwick Bureau Register CSV files
- Parses player register rows
- Populates `bridge.player_xref` with MLB ↔ Retrosheet player ID mappings
- Populates `bridge.team_xref` with current/canonical MLB franchise mappings
- Populates `bridge.park_xref` with MLB venue-id mappings

Expected output:
- `bridge.player_xref`: ~20,000 rows
- `bridge.team_xref`: 30 rows with MLB team IDs
- `bridge.park_xref`: 45 rows with MLB venue IDs

### 2. Verify Bridge Table Population

```bash
psql -d retrosheet -c "SELECT COUNT(*) FROM bridge.player_xref;"
psql -d retrosheet -c "SELECT COUNT(*) FROM bridge.team_xref WHERE mlb_team_id IS NOT NULL;"
psql -d retrosheet -c "SELECT COUNT(*) FROM bridge.park_xref WHERE mlb_venue_id IS NOT NULL;"
```

## Daily Ingestion Workflow

### Step 1: Discover Games

Identify games that have started or completed recently.

```bash
python3 scripts/fetch_mlb_schedule.py --yesterday
```

Options:
- `--yesterday`: Discover games from yesterday
- `--date YYYY-MM-DD`: Discover games from specific date
- `--days N`: Discover games from last N days

Expected output:
- List of game PKs (primary keys) for active/completed games
- Game status (scheduled, in_progress, final)

### Step 2: Ingest Games

Ingest the discovered games into the warehouse.

```bash
python3 scripts/ingest_live_games.py --schedule
```

Options:
- `--schedule`: Use schedule discovery results
- `--game-pk <GAME_PK>`: Ingest specific game
- `--limit N`: Limit to N games (for testing)

This script:
- Fetches live game feed JSON from MLB API
- Stores source-preserved JSON in `raw_mlb.live_feed_snapshots`
- Transforms to canonical schema using bridge table lookups
- Upserts into `core.live_games` and `core.live_events`
- Refreshes `features.live_plate_appearance_advanced_count_examples`

### Step 3: Validate Ingestion

Verify that data was ingested correctly.

```bash
# Check live games count
psql -d retrosheet -c "SELECT COUNT(*) FROM core.live_games WHERE created_at > NOW() - INTERVAL '1 day';"

# Check live events count
psql -d retrosheet -c "SELECT COUNT(*) FROM core.live_events WHERE created_at > NOW() - INTERVAL '1 day';"

# Check for MLB### fallback IDs (should be minimal after bridge repair)
psql -d retrosheet -c "SELECT COUNT(*) FROM core.live_games WHERE home_team_id LIKE 'MLB%' OR away_team_id LIKE 'MLB%';"
```

## Data Quality Checks

### Schema Validation

```bash
python3 scripts/validate_data_quality.py
```

### Null Rate Monitoring

```bash
psql -d retrosheet -c "
SELECT 
    COUNT(*) AS total,
    COUNT(home_team_id) FILTER (WHERE home_team_id IS NULL) AS null_home_team,
    COUNT(away_team_id) FILTER (WHERE away_team_id IS NULL) AS null_away_team
FROM core.live_games
WHERE created_at > NOW() - INTERVAL '1 day';
"
```

### Referential Integrity

```bash
psql -d retrosheet -c "
SELECT 
    COUNT(*) AS total,
    COUNT(home_team_id) FILTER (WHERE home_team_id NOT IN (SELECT team_id FROM bridge.team_xref)) AS orphan_home,
    COUNT(away_team_id) FILTER (WHERE away_team_id NOT IN (SELECT team_id FROM bridge.team_xref)) AS orphan_away
FROM core.live_games
WHERE created_at > NOW() - INTERVAL '1 day';
"
```

## Troubleshooting

### Issue: Games Not Discovered

**Symptoms:** `fetch_mlb_schedule.py` returns no games

**Solutions:**
1. Check date parameter is correct
2. Verify MLB Stats API is accessible
3. Check for MLB off-season (no games scheduled)
4. Try a different date

### Issue: Transformation Fails with MLB### IDs

**Symptoms:** Live games have `MLB###` fallback team/park IDs

**Solutions:**
1. Verify bridge tables are populated
2. Check if venue is in `bridge.park_xref`
3. Run `scripts/replay_live_bridge_backfill.py` to re-transform with updated bridge
4. Add missing venue to bridge tables manually

### Issue: Feature Parity View Empty

**Symptoms:** `features.live_plate_appearance_advanced_count_examples` has no rows

**Solutions:**
1. Verify live games exist in `core.live_games`
2. Verify live events exist in `core.live_events`
3. Check feature parity view SQL for errors
4. Re-run `sql/122_live_pa_feature_parity.sql`

### Issue: Duplicate Game Ingestion

**Symptoms:** Same game ingested multiple times

**Solutions:**
1. Ingestion script should handle duplicates automatically
2. Check `raw_mlb.live_feed_snapshots` for duplicate game_pks
3. Use `--limit` for testing before full ingestion

## Analysis with Combined Data

Use `analysis.*` views for unified queries across historical and live data.

### Check Data Source Statistics

```sql
SELECT * FROM analysis.get_data_source_stats();
```

Expected output:
- Historical games count
- Live games count
- Historical events count
- Live events count

### Query Recent Games

```sql
SELECT 
    game_id,
    game_date,
    source_type,
    home_team_id,
    away_team_id,
    home_score,
    away_score
FROM analysis.combined_games
WHERE game_date >= CURRENT_DATE - INTERVAL '7 days'
ORDER BY game_date DESC;
```

### Query Combined Events

```sql
SELECT 
    ce.game_id,
    ce.event_type,
    ce.source_type,
    cg.game_date
FROM analysis.combined_events ce
JOIN analysis.combined_games cg USING (game_id)
WHERE ce.source_type = 'mlb_live'
ORDER BY cg.game_date DESC
LIMIT 10;
```

## Controlled Replay

If bridge tables are updated after initial ingestion, replay stored snapshots through the repaired transform path.

```bash
python3 scripts/replay_live_bridge_backfill.py --season-from 2019 --season-to 2019 --limit 50
```

Guidelines:
1. Start with bounded season slice and small limit
2. Prefer regular-season slices first
3. Validate sample of replayed rows before scaling up
4. Check park priors and team rolling features after replay

## Monitoring

### Ingestion Metrics

Track these metrics regularly:
- Games discovered per day
- Games ingested successfully
- Transformation success rate
- Null rates in live tables
- MLB### fallback ID rate

### Alert Thresholds

Set up alerts for:
- Ingestion failure rate > 5%
- Null rate > 10% for critical fields
- MLB### fallback ID rate > 20%
- Live data freshness > 24 hours

## Best Practices

1. **Run daily:** Schedule ingestion to run daily after games complete
2. **Validate after ingestion:** Always run data quality checks
3. **Monitor fallback IDs:** Track MLB### IDs and update bridge tables
4. **Use analysis views:** Query `analysis.*` for combined historical + live data
5. **Keep historical separate:** Never merge raw MLB rows into historical raw layers
6. **Document issues:** Log ingestion issues in `docs/PROJECT_LOG.md`

## Next Steps

After live data ingestion is working:
- Train models on historical data
- Validate models on live data
- Set up automated daily ingestion
- Monitor live prediction quality
- Compare live vs historical feature distributions

## References

- `docs/LIVE_DATA_ARCHITECTURE.md` - Complete live data architecture
- `docs/agents/PROCEDURES.md` - Canonical procedures for live ingestion
- `docs/TROUBLESHOOTING.md` - Common issues and solutions
- `docs/FAQ.md` - Frequently asked questions
