# Confidence Scoring Framework for Bridge Tables

## Overview

The confidence scoring framework provides a standardized way to track the quality and reliability of ID mappings across bridge tables. This helps identify low-quality mappings that need manual review and understand overall data quality.

## Confidence Score Levels

| Score | Level | Description | Examples |
|-------|-------|-------------|----------|
| 1.0 | Direct | Direct mapping from authoritative source | Chadwick Register, MLB API |
| 0.9 | High | High-confidence cross-reference | Name + ID match from trusted source |
| 0.8 | Medium | Medium-confidence cross-reference | ID match only via cross-reference |
| 0.7 | Low | Low-confidence cross-reference | Name match only |
| 0.5 | Fuzzy | Fuzzy match | Similar names, approximate dates |
| 0.3 | Placeholder | Placeholder or inferred mapping | ID-only without name verification |
| 0.1 | Unverified | Unverified or uncertain mapping | Manual entry, uncertain source |

## Schema Changes

### Added Columns

All bridge tables now include:
- `confidence_score` (NUMERIC(3,2)): Confidence score from 0.0 to 1.0
- `confidence_source` (TEXT): Source of confidence assessment

### Tables Modified

- `bridge.player_xref`
- `bridge.team_xref`
- `bridge.park_xref`
- `bridge.game_xref`
- `bridge.coach_xref`
- `bridge.umpire_xref`
- `bridge.external_player_xref`
- `bridge.external_team_xref`

### Indexes Added

Indexes on `confidence_score` for all bridge tables to enable efficient filtering by confidence level.

## Views

### confidence_score_distribution

Shows distribution of confidence scores across all bridge tables with percentages.

```sql
SELECT * FROM bridge.confidence_score_distribution ORDER BY table_name, confidence_score DESC;
```

### low_confidence_mappings

Lists all mappings with confidence scores below 0.7 requiring manual review.

```sql
SELECT * FROM bridge.low_confidence_mappings ORDER BY confidence_score ASC;
```

### confidence_summary_by_source

Summary statistics of confidence scores by table and source.

```sql
SELECT * FROM bridge.confidence_summary_by_source ORDER BY table_name, avg_confidence DESC;
```

## Default Confidence Scores

### player_xref
- Default: 0.8 (Chadwick Register)
- Source: 'chadwick_register'

### team_xref
- Default: 0.8 (Chadwick Register)
- Source: 'chadwick_register'

### park_xref
- Default: 0.8 (Chadwick Register)
- Source: 'chadwick_register'

### game_xref
- Default: 0.8 (Automated match)
- Source: 'automated_match'

### coach_xref
- Default: 0.3 (Retrosheet ID only, no names)
- Source: 'retrosheet_id_only'

### umpire_xref
- Default: 0.7 (Retrosheet name match)
- Source: 'retrosheet_name_match'

### external_player_xref
- Default: 0.8 (ID cross-reference)
- Source: 'id_cross_reference'

### external_team_xref
- Default: 0.8 (ID cross-reference)
- Source: 'id_cross_reference'

## Usage in Bridge Population Scripts

When populating bridge tables, set appropriate confidence scores based on the mapping method:

### Example: High-confidence mapping from Chadwick Register
```python
cur.execute("""
    INSERT INTO bridge.player_xref (retrosheet_id, mlb_id, confidence_score, confidence_source)
    VALUES (%s, %s, 1.0, 'chadwick_register')
    ON CONFLICT (retrosheet_id) DO UPDATE SET
        mlb_id = EXCLUDED.mlb_id,
        confidence_score = EXCLUDED.confidence_score,
        confidence_source = EXCLUDED.confidence_source
""", (retrosheet_id, mlb_id))
```

### Example: Medium-confidence cross-reference
```python
cur.execute("""
    INSERT INTO bridge.external_player_xref (external_source, external_player_id, retrosheet_player_id, confidence_score, confidence_source)
    VALUES (%s, %s, %s, 0.8, 'id_cross_reference')
    ON CONFLICT (external_source, external_player_id) DO UPDATE SET
        retrosheet_player_id = EXCLUDED.retrosheet_player_id,
        confidence_score = EXCLUDED.confidence_score,
        confidence_source = EXCLUDED.confidence_source
""", (external_source, external_player_id, retrosheet_player_id))
```

### Example: Low-confidence placeholder
```python
cur.execute("""
    INSERT INTO bridge.coach_xref (retrosheet_coach_id, source_system, coach_name, confidence_score, confidence_source)
    VALUES (%s, %s, %s, 0.3, 'retrosheet_id_only')
    ON CONFLICT (retrosheet_coach_id) DO UPDATE SET
        coach_name = EXCLUDED.coach_name,
        confidence_score = EXCLUDED.confidence_score,
        confidence_source = EXCLUDED.confidence_source
""", (coach_id, 'retrosheet', coach_id))
```

## Confidence Score Adjustment

When improving mappings (e.g., adding names to coach entries), update the confidence score:

```sql
-- Example: Upgrade coach mapping from placeholder to name match
UPDATE bridge.coach_xref
SET 
    confidence_score = 0.7,
    confidence_source = 'retrosheet_name_match'
WHERE retrosheet_coach_id = 'coach001'
AND confidence_score < 0.7;
```

## Monitoring and Quality Assurance

### Regular Checks

1. **Check low-confidence mappings:**
   ```sql
   SELECT COUNT(*) FROM bridge.low_confidence_mappings;
   ```

2. **Review confidence distribution:**
   ```sql
   SELECT * FROM bridge.confidence_score_distribution;
   ```

3. **Identify tables with poor average confidence:**
   ```sql
   SELECT table_name, AVG(confidence_score) as avg_score
   FROM bridge.confidence_score_distribution
   GROUP BY table_name
   HAVING AVG(confidence_score) < 0.8;
   ```

### Quality Targets

- **Target average confidence:** ≥ 0.8
- **Target low-confidence mappings:** < 5% of total
- **Target high-confidence mappings:** ≥ 70% of total

## Manual Review Process

1. Query low-confidence mappings:
   ```sql
   SELECT * FROM bridge.low_confidence_mappings WHERE confidence_score < 0.5;
   ```

2. Investigate each mapping using external sources (MLB.com, Baseball Reference, etc.)

3. Update confidence score after verification:
   ```sql
   UPDATE bridge.player_xref
   SET confidence_score = 0.9, confidence_source = 'manual_verification'
   WHERE retrosheet_id = 'playerid';
   ```

## Integration with External Data Sources

When integrating new data sources (ESPN, Statcast, etc.), set confidence scores based on:

- **Direct MLB API integration:** 1.0
- **Statcast (via MLB IDs):** 0.9
- **ESPN (via MLB IDs):** 0.9
- **Baseball Reference (via cross-reference):** 0.8
- **Lahman (via retroID):** 0.8
- **Fuzzy name matching:** 0.5-0.7

## Future Enhancements

1. **Automated confidence scoring:** Calculate confidence based on multiple factors (name similarity, date overlap, team consistency)

2. **Confidence history:** Track changes to confidence scores over time for audit trail

3. **Confidence propagation:** When a high-confidence mapping is confirmed, propagate confidence to related mappings

4. **Machine learning:** Use ML to predict confidence scores for new mappings based on historical patterns

## Related Documentation

- `docs/BRIDGE_TABLE_IMPLEMENTATION.md` - Bridge table design and implementation
- `docs/ID_RECONCILIATION.md` - ID reconciliation methods and strategies
- `sql/bridge/910_confidence_scoring.sql` - SQL migration for confidence scoring
