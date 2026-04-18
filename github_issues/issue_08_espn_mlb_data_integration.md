# Issue #8: ESPN MLB Data Integration

**Status**: Completed  
**Created**: April 2026  
**Related Docs**: [AGENTS.md](../AGENTS.md), [FILE_INVENTORY.md](../docs/agents/FILE_INVENTORY.md), [PROCEDURES.md](../docs/agents/PROCEDURES.md)

## Goal

Integrate ESPN API as an additional external data source for MLB data, supplementing existing Retrosheet and MLB Stats API sources.

## Current State

- ESPN API tested and confirmed working (http://site.api.espn.com/apis/site/v2/sports/baseball/mlb)
- `raw_espn` schema created with tables for game snapshots, schedule snapshots, player stats, and team stats
- Generalized fetch script created with checksum-based deduplication
- Documentation updated to reflect ESPN integration

## Scope

- Create `raw_espn` schema for source-preserved ESPN data
- Implement generalized fetch script for schedule and game data
- Update documentation (FILE_INVENTORY.md, AGENTS.md, PROCEDURES.md)
- Create Letta memory for ESPN integration details
- Follow project's canonical data path enforcement rules

## Non-Goals

- Transform ESPN data to canonical shapes (deferred until use cases identified)
- Create ESPN bridge tables (deferred until ID mapping requirements identified)
- Integrate ESPN data into feature marts (deferred until value proposition established)

## Acceptance Criteria

- [x] `raw_espn` schema created with appropriate tables and indexes
- [x] `scripts/fetch_espn_mlb.py` script implemented with schedule and game fetch commands
- [x] Checksum-based deduplication to avoid duplicate fetches
- [x] Source-preserved JSON storage with fetch provenance (HTTP status, response time, checksum)
- [x] `docs/agents/FILE_INVENTORY.md` updated with ESPN scripts and schema
- [x] `AGENTS.md` updated to include `raw_espn` in data layers
- [x] `docs/agents/PROCEDURES.md` updated with ESPN workflow
- [x] Letta memory created for ESPN integration details

## Relevant Files

### SQL
- [sql/220_espn_schema.sql](../sql/220_espn_schema.sql) - Schema definition for raw_espn tables

### Scripts
- [scripts/fetch_espn_mlb.py](../scripts/fetch_espn_mlb.py) - Generalized ESPN data fetcher

### Documentation
- [docs/agents/FILE_INVENTORY.md](../docs/agents/FILE_INVENTORY.md) - Updated with ESPN scripts and schema
- [AGENTS.md](../AGENTS.md) - Updated to include raw_espn in data layers
- [docs/agents/PROCEDURES.md](../docs/agents/PROCEDURES.md) - Updated with ESPN workflow

## Validation Expectations

- Schema creation successful (psql -f sql/220_espn_schema.sql)
- Script can fetch schedule data: `python3 scripts/fetch_espn_mlb.py schedule --date 2024-04-15`
- Script can fetch game data: `python3 scripts/fetch_espn_mlb.py game --game-id 401434845`
- Checksum deduplication prevents duplicate storage
- Documentation follows project's canonical procedures

## Parent Roadmap Issue

Related to external data integration efforts alongside [sql/200_external_data.sql](../sql/200_external_data.sql) and MLB Stats API integration.

## Implementation Details

### Data Source
ESPN API (http://site.api.espn.com/apis/site/v2/sports/baseball/mlb)

### Schema
- `raw_espn.game_snapshots`: Stores raw JSON responses from ESPN scoreboard API
- `raw_espn.schedule_snapshots`: Stores raw JSON responses from ESPN schedule API
- `raw_espn.player_stats_snapshots`: Stores raw JSON responses from ESPN player statistics API
- `raw_espn.team_stats_snapshots`: Stores raw JSON responses from ESPN team statistics API

### Data Flow
ESPN API → raw_espn.*_snapshots (source-preserved JSON) → (future: bridge → core)

### Notes
- ESPN data is supplemental to Retrosheet and MLB Stats API data
- Uses checksum-based deduplication to avoid duplicate fetches
- Preserves request parameters, HTTP status, response time, and checksum
- Future work: create bridge tables for ESPN IDs and transform to canonical shapes

## Decisions Made

1. **Direct ESPN API over sportsdataverse-py**: The sportsdataverse package had dependency issues (pkg_resources). Direct ESPN API calls using requests library are more reliable and maintainable.

2. **Source-preserved raw layer**: Following project's canonical data path enforcement, ESPN data is stored source-preserved in raw_espn schema before any transformation.

3. **Deferred transformation**: ESPN data transformation to canonical shapes is deferred until specific use cases are identified, avoiding premature optimization.

4. **Checksum-based deduplication**: Implemented SHA256 checksum to prevent duplicate fetches of identical data.

## Next Steps

- Test fetch script with actual ESPN data
- Monitor ESPN API rate limits and implement backoff if needed
- Identify use cases for ESPN data transformation
- Create bridge tables for ESPN IDs when transformation requirements emerge
- Consider adding player stats and team stats fetch commands

## Related Issues

- Issue #5: Documentation & Issue Linking – established documentation standards
- Issue #6: Model Training Pipeline – may benefit from additional external data sources
