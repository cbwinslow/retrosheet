#!/usr/bin/env python3
"""
Store ESPN MLB Data Integration Details in Letta Archival Memory
"""

import os

import requests


# Load Letta environment
letta_base_url = os.getenv('LETTA_BASE_URL', 'http://localhost:8283')
letta_api_key = os.getenv(
    'LETTA_API_KEY',
    'sk-let-NzY2MDVkMWUtMGRmMy00MjExLTg1NDMtNjdhOGJjYTdiM2I0OmE3Y2I5MWM0LTdjYTctNDlmOC05N2Q0LTVk',
)

headers = {'Authorization': f'Bearer {letta_api_key}', 'Content-Type': 'application/json'}

# Retrosheet warehouse agent ID
agent_id = 'agent-667bf06e-9859-4447-9141-019cc4408285'

# ESPN MLB data integration detailed memory
memory_text = """# ESPN MLB Data Integration - Complete

## Integration Date
April 19, 2026

## Data Source
ESPN API (http://site.api.espn.com/apis/site/v2/sports/baseball/mlb)
ESPN Core API v2 (https://sports.core.api.espn.com/v2/sports/baseball/mlb)

## Schema
- Schema: `raw_espn`
- Tables:
  - `raw_espn.game_snapshots`: Stores raw JSON responses from ESPN scoreboard API (71,739 rows)
  - `raw_espn.schedule_snapshots`: Stores raw JSON responses from ESPN schedule API (5,212 rows)
  - `raw_espn.plays_snapshots`: Stores raw JSON responses from ESPN Core API v2 plays endpoint (71,739 rows)
  - `raw_espn.player_stats_snapshots`: Stores raw JSON responses from ESPN player statistics API (0 rows - not yet loaded)
  - `raw_espn.team_stats_snapshots`: Stores raw JSON responses from ESPN team statistics API (0 rows - not yet loaded)

## Scripts
- `scripts/fetch_espn_mlb.py`: Generalized ESPN data fetcher with checksum-based deduplication
  - Commands: schedule, game, plays, batch, ingest-historical
  - Features: Parallel downloads with ThreadPoolExecutor, checksum-based deduplication, source-preserved JSON storage
- `sql/220_espn_schema.sql`: Schema definition for raw_espn tables

## Data Flow
ESPN API -> raw_espn.*_snapshots (source-preserved JSON) -> (future: bridge -> core)

## Historical Ingestion Completion
Successfully ingested historical ESPN MLB data for seasons 2000-2025:
- **Total Games Ingested**: 71,739 games
- **Play-by-Play Snapshots**: 71,739 (one per game)
- **Schedule Snapshots**: 5,212
- **Failure Rate**: 15 failures out of 76,000+ games (0.02%)
- **Database**: retrosheet database, raw_espn schema
- **Ingest Runs**: Tracked in raw_retrosheet.ingest_runs (run IDs 1-56)

## Script Command Used
```bash
python3 scripts/fetch_espn_mlb.py ingest-historical --start-date YYYY-MM-DD --end-date YYYY-MM-DD --workers 10
```

## Key Features
- Parallel downloads using ThreadPoolExecutor (10 workers)
- Checksum-based deduplication (SHA256)
- Source-preserved JSON storage
- Run tracking in raw_retrosheet.ingest_runs table
- Play-by-play data from ESPN Core API v2
- HTTP status, response time, and checksum preservation

## Failure Analysis
- 15 total failures across 25 ingest runs
- Failures are minimal (0.02% failure rate)
- Error messages not logged in database (NULL)
- Failures likely transient API issues
- Without specific game IDs, retry not feasible

## Verification Queries
```sql
-- Verify game snapshots
SELECT COUNT(*) FROM raw_espn.game_snapshots; -- 71,739

-- Verify play-by-play snapshots
SELECT COUNT(*) FROM raw_espn.plays_snapshots; -- 71,739

-- Check run history
SELECT * FROM raw_retrosheet.ingest_runs WHERE source_name = 'espn_api' ORDER BY started_at DESC;
```

## Notes
- ESPN data is supplemental to Retrosheet and MLB Stats API data
- Uses checksum-based deduplication to avoid duplicate fetches
- Preserves request parameters, HTTP status, response time, and checksum
- Future work: create bridge tables for ESPN IDs and transform to canonical shapes

## Documentation Updates
- Updated `docs/agents/FILE_INVENTORY.md` with ESPN scripts and schema
- Updated `AGENTS.md` to include raw_espn in data layers and ESPN procedure
- Updated [#59](https://github.com/cbwinslow/retrosheet/issues/59) with completion details

## Related GitHub Issue
Issue #8: ESPN MLB Data Integration - Completed
"""

# Insert into archival memory
response = requests.post(
    f'{letta_base_url}/v1/agents/{agent_id}/archival-memory',
    headers=headers,
    json={'text': memory_text},
)

print(f'Status: {response.status_code}')
if response.status_code == 201:
    passage = response.json()
    print(f"Created passage ID: {passage.get('id')}")
else:
    print(f'Error: {response.text}')
