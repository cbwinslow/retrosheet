# ESPN Bridge Table Requirements

## Overview

ESPN bridge tables enable mapping between ESPN API IDs and Retrosheet canonical IDs. ESPN uses integer IDs that match MLBAM IDs, simplifying the mapping process.

## Dependencies

### Required Data Sources

1. **raw_espn.game_snapshots** - ESPN game data with JSON payloads
   - Must contain game data for desired years (2024-2025)
   - JSON structure includes player and team IDs

2. **bridge.player_xref** - Player ID cross-references
   - Must be populated from Chadwick Register
   - Provides mlb_id → retrosheet_id mapping
   - Required for ESPN player ID mapping

3. **bridge.team_xref** - Team ID cross-references
   - Must be populated from Chadwick Register
   - Provides mlb_team_id → retrosheet_team_id mapping
   - Required for ESPN team ID mapping

### Prerequisite Scripts

1. `scripts/populate_bridge_tables.py` - Populates player_xref and team_xref from Chadwick Register
2. `scripts/data_ingestion/fetch_espn_mlb.py` - Fetches ESPN game data into raw_espn tables

## Implementation Status

### Completed

- ✅ ESPN ID format documented (integer IDs, same as MLBAM)
- ✅ Bridge table schema exists (bridge.external_player_xref, bridge.external_team_xref)
- ✅ Bridge mapping script created (scripts/bridge/populate_espn_bridge.py)
- ✅ Documentation updated (BRIDGE_TABLE_IMPLEMENTATION.md)

### Pending

- ⏳ Fetch ESPN game data for 2024-2025 seasons
- ⏳ Populate bridge.player_xref and bridge.team_xref from Chadwick Register
- ⏳ Run populate_espn_bridge.py to create ESPN mappings
- ⏳ Validate ESPN mapping coverage
- ⏳ Implement ESPN coach ID mapping (JSON structure investigation needed)
- ⏳ Implement ESPN umpire ID mapping (JSON structure investigation needed)

## ESPN ID Mapping Strategy

### Player IDs

ESPN player IDs are integer MLBAM IDs. Mapping strategy:
```sql
-- Extract ESPN player ID from JSON
-- Match to bridge.player_xref.mlb_id
-- Insert into bridge.external_player_xref
```

**JSON Path**: `events[].competitors[].roster[].player.id`

### Team IDs

ESPN team IDs are integer MLB team IDs. Mapping strategy:
```sql
-- Extract ESPN team ID from JSON
-- Match to bridge.team_xref.mlb_team_id
-- Insert into bridge.external_team_xref
```

**JSON Path**: `events[].competitors[].team.id`

### Coach IDs

ESPN coach ID location in JSON needs investigation. Current status: Placeholder implementation.

### Umpire IDs

ESPN umpire ID location in JSON needs investigation. Current status: Placeholder implementation.

## Validation

### Coverage Checks

```sql
-- Check ESPN player mapping coverage
SELECT COUNT(*) FROM bridge.external_player_xref WHERE external_source = 'espn';

-- Check ESPN team mapping coverage
SELECT COUNT(*) FROM bridge.external_team_xref WHERE external_source = 'espn';

-- Check for unmapped ESPN players
SELECT COUNT(*) FROM raw_espn.game_snapshots 
WHERE raw_payload @> '{"events": [{"competitors": [{"roster": [{"player": {"id": "..."}}]}]}]}'
AND (raw_payload->'events'->0->'competitors'->0->'roster'->0->'player'->>'id')::int NOT IN (
    SELECT mlb_id FROM bridge.player_xref WHERE mlb_id IS NOT NULL
);
```

### Data Quality Checks

- Ensure no NULL retrosheet_player_id in external_player_xref
- Ensure no NULL retrosheet_team_id in external_team_xref
- Verify ESPN IDs are integers
- Check for duplicate mappings (should be prevented by unique constraints)

## Known Limitations

1. **Coach/Umpire IDs**: JSON structure not yet investigated, placeholder implementation
2. **Historical Data**: Only 2024-2025 seasons have data
3. **Coverage Gaps**: Some ESPN players/teams may not have Retrosheet equivalents
4. **JSON Extraction**: Complex JSON path extraction may need refinement based on actual data

## Next Steps

1. Fetch ESPN game data for 2024-2025 using `scripts/data_ingestion/fetch_espn_mlb.py`
2. Populate bridge tables from Chadwick Register using `scripts/populate_bridge_tables.py`
3. Run `scripts/bridge/populate_espn_bridge.py` to create ESPN mappings
4. Validate mapping coverage and data quality
5. Investigate ESPN coach/umpire JSON structure for additional mappings

## Related Documentation

- `docs/BRIDGE_TABLE_IMPLEMENTATION.md` - Comprehensive bridge table implementation details
- `docs/ID_RECONCILIATION.md` - ID reconciliation methods and strategies
- `scripts/bridge/populate_espn_bridge.py` - ESPN bridge mapping script
