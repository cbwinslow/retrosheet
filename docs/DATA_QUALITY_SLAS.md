# Data Quality SLAs

This document defines the Service Level Agreements (SLAs) for data quality in the Retrosheet Prediction Warehouse.

## Overview

Data quality SLAs define acceptable thresholds for various data quality metrics. These SLAs ensure that the warehouse maintains high data quality for reliable model training and inference.

## SLA Categories

### 1. Schema Validation

**Definition:** Tables must have all required columns with correct data types.

**SLA:**
- **Required Columns:** 100% of required columns present
- **Data Types:** All columns match expected data types
- **Constraints:** All NOT NULL constraints enforced

**Measurement:**
```sql
SELECT COUNT(*) AS missing_columns
FROM information_schema.columns
WHERE table_schema = 'core'
  AND table_name = 'games'
  AND column_name IN ('game_id', 'game_date', 'season', 'home_team_id', 'away_team_id')
  AND column_name IS NULL;
```

**Threshold:** 0 missing columns (100% compliance)

### 2. Null Rate Monitoring

**Definition:** Percentage of null values in critical columns must stay below threshold.

**SLA by Table:**

| Table | Critical Columns | Null Rate Threshold |
|-------|------------------|---------------------|
| core.games | game_id, game_date, season, home_team_id, away_team_id | 0% |
| core.events | event_id, game_id, inning, outs_before, start_bases | 0% |
| core.plate_appearances | plate_appearance_id, game_id, batter_id, pitcher_id | 0% |
| features.plate_appearance_advanced_examples | plate_appearance_id, feature_season, inning, outs_before | 0% |
| features.* (non-critical) | All columns | ≤ 5% |

**Measurement:**
```sql
SELECT column_name,
       COUNT(*) FILTER (WHERE column_name IS NULL) * 100.0 / COUNT(*) AS null_rate
FROM core.games
GROUP BY column_name;
```

**Threshold:** ≤ 5% null rate for non-critical columns, 0% for critical columns

### 3. Value Range Validation

**Definition:** Numeric columns must stay within expected value ranges.

**SLA by Column:**

| Table | Column | Min Value | Max Value |
|-------|--------|-----------|-----------|
| core.games | inning | 1 | 20 |
| core.games | home_score | 0 | 50 |
| core.games | away_score | 0 | 50 |
| core.events | inning | 1 | 20 |
| core.events | outs_before | 0 | 3 |
| core.events | balls | 0 | 4 |
| core.events | strikes | 0 | 3 |
| core.plate_appearances | season | 1900 | 2100 |

**Measurement:**
```sql
SELECT COUNT(*) FILTER (WHERE inning < 1 OR inning > 20) AS out_of_range_count
FROM core.games;
```

**Threshold:** 0 out-of-range values (100% compliance)

### 4. Referential Integrity

**Definition:** Foreign key relationships must be maintained.

**SLA by Relationship:**

| Child Table | Child Column | Parent Table | Parent Column | Orphan Rate Threshold |
|-------------|--------------|--------------|---------------|----------------------|
| core.events | game_id | core.games | game_id | 0% |
| core.plate_appearances | game_id | core.games | game_id | 0% |
| core.plate_appearances | batter_id | core.players | player_id | ≤ 1% |
| core.plate_appearances | pitcher_id | core.players | player_id | ≤ 1% |

**Measurement:**
```sql
SELECT COUNT(*) AS orphan_count
FROM core.events c
LEFT JOIN core.games g ON c.game_id = g.game_id
WHERE g.game_id IS NULL;
```

**Threshold:** 0% orphan rate for critical relationships, ≤ 1% for non-critical

### 5. Temporal Consistency

**Definition:** Date columns must be consistent with season/year columns.

**SLA by Table:**

| Table | Date Column | Season Column | Consistency Threshold |
|-------|-------------|---------------|----------------------|
| core.games | game_date | season | 100% |
| core.events | game_date | season | 100% |
| features.* | feature_season | season | 100% |

**Measurement:**
```sql
SELECT COUNT(*) AS inconsistent_count
FROM core.games
WHERE EXTRACT(YEAR FROM game_date)::integer != season;
```

**Threshold:** 0 inconsistent rows (100% compliance)

## Monitoring and Alerting

### Alert Levels

**Critical Alert:**
- Schema validation failure
- Null rate > 10% in critical columns
- Orphan rate > 1% in critical relationships
- Temporal consistency < 95%

**Warning Alert:**
- Null rate > 5% in non-critical columns
- Value range violations > 1%
- Orphan rate > 0% in non-critical relationships

**Info Alert:**
- Data quality check completed
- SLA compliance report generated

### Monitoring Frequency

| Check Type | Frequency |
|------------|-----------|
| Schema validation | After schema migrations |
| Null rate monitoring | Daily |
| Value range validation | Daily |
| Referential integrity | Daily |
| Temporal consistency | Daily |

### Reporting

**Daily Report:**
- Summary of all data quality checks
- SLA compliance metrics
- Failed checks with details
- Trend analysis (7-day, 30-day)

**Weekly Report:**
- SLA compliance trends
- Root cause analysis for failures
- Recommendations for improvements

**Monthly Report:**
- SLA compliance summary
- Data quality scorecard
- Improvement roadmap

## Implementation

### Validation Script

Use `scripts/validate_data_quality.py` to run data quality checks:

```bash
# Run all checks
python3 scripts/validate_data_quality.py

# Export results to JSON
python3 scripts/validate_data_quality.py --output data_quality_report.json

# Exit with error if any check fails
python3 scripts/validate_data_quality.py --fail-on-error
```

### Integration with Rebuild Pipeline

Add data quality validation to `scripts/rebuild_warehouse.sh`:

```bash
# After loading data
echo "Running data quality validation..."
python3 scripts/validate_data_quality.py --fail-on-error
```

### Dashboard Integration

Display data quality metrics in the reliability dashboard:
- SLA compliance percentage
- Failed checks count
- Null rate heatmap
- Referential integrity status

## Remediation

### Immediate Actions

**Schema Validation Failure:**
1. Rollback schema migration
2. Investigate missing columns
3. Re-run migration with correct schema

**Null Rate Breach:**
1. Identify source of null values
2. Check upstream data quality
3. Implement data cleaning if needed
4. Re-ingest cleaned data

**Referential Integrity Failure:**
1. Identify orphaned records
2. Investigate missing parent records
3. Re-ingest missing parent data
4. Delete or fix orphaned records

### Long-term Improvements

**Preventive Measures:**
- Add NOT NULL constraints to critical columns
- Implement foreign key constraints
- Add CHECK constraints for value ranges
- Implement data validation at ingestion

**Process Improvements:**
- Add data quality checks to ingestion pipeline
- Implement automated data cleaning
- Add data quality monitoring to CI/CD
- Regular data quality reviews

## SLA Compliance Targets

### Overall Target

**Annual SLA Compliance:** ≥ 99.5%

**Monthly SLA Compliance:** ≥ 99%

**Weekly SLA Compliance:** ≥ 98%

### Per-Category Targets

| Category | Annual Target | Monthly Target | Weekly Target |
|----------|---------------|----------------|---------------|
| Schema Validation | 100% | 100% | 100% |
| Null Rate Monitoring | ≥ 99.5% | ≥ 99% | ≥ 98% |
| Value Range Validation | ≥ 99.5% | ≥ 99% | ≥ 98% |
| Referential Integrity | ≥ 99.5% | ≥ 99% | ≥ 98% |
| Temporal Consistency | 100% | 100% | 100% |

## Governance

### Roles and Responsibilities

**Data Engineer:**
- Implement data quality checks
- Monitor SLA compliance
- Remediate data quality issues
- Maintain validation scripts

**Data Scientist:**
- Define data quality requirements
- Review SLA compliance reports
- Provide feedback on data quality needs
- Validate data quality for model training

**Warehouse Owner:**
- Approve SLA definitions
- Review compliance reports
- Escalate critical issues
- Approve remediation plans

### Change Management

**SLA Changes:**
- Proposed changes reviewed by data team
- Impact analysis performed
- Stakeholders notified
- Changes documented in PROJECT_LOG.md

**Schema Changes:**
- Impact on SLAs assessed
- Validation scripts updated
- Migration includes SLA validation
- Post-migration SLA verification

## Review and Update

**SLA Review:** Quarterly
**SLA Update:** Annually or as needed
**Documentation Update:** With each SLA change
