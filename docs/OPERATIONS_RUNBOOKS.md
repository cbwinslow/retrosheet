# Operations Runbooks

This document provides runbooks for common operational tasks in the Retrosheet Prediction Warehouse.

## Table of Contents

1. [Database Maintenance](#database-maintenance)
2. [Model Deployment](#model-deployment)
3. [Data Ingestion](#data-ingestion)
4. [Backup and Restore](#backup-and-restore)
5. [Monitoring and Alerting](#monitoring-and-alerting)
6. [Emergency Response](#emergency-response)
7. [Performance Tuning](#performance-tuning)

## Database Maintenance

### Routine Vacuum and Analyze

**Purpose:** Reclaim space and update statistics

**Frequency:** Weekly

**Steps:**
```bash
# Connect to database
psql -d retrosheet

# Vacuum and analyze large tables
VACUUM ANALYZE core.games;
VACUUM ANALYZE core.events;
VACUUM ANALYZE core.plate_appearances;
VACUUM ANALYZE features.plate_appearance_advanced_examples;

# Check table sizes
SELECT schemaname, tablename,
       pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname IN ('core', 'features')
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

**Validation:**
- Query performance should improve
- Disk usage should decrease

### Index Rebuild

**Purpose:** Rebuild fragmented indexes

**Frequency:** Monthly

**Steps:**
```bash
# Connect to database
psql -d retrosheet

# Reindex specific tables
REINDEX TABLE core.games;
REINDEX TABLE core.events;
REINDEX TABLE core.plate_appearances;
REINDEX TABLE features.plate_appearance_advanced_examples;

# Check index usage
SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read, idx_tup_fetch
FROM pg_stat_user_indexes
WHERE schemaname IN ('core', 'features')
ORDER BY idx_scan ASC;
```

**Validation:**
- Index usage should increase
- Query performance should improve

### Statistics Update

**Purpose:** Update query planner statistics

**Frequency:** Daily

**Steps:**
```bash
# Connect to database
psql -d retrosheet

# Update statistics
ANALYZE core.games;
ANALYZE core.events;
ANALYZE core.plate_appearances;
ANALYZE features.plate_appearance_advanced_examples;
```

**Validation:**
- Query plans should be optimal
- No sequential scans on large tables

## Model Deployment

### Deploy New Model

**Purpose:** Deploy a new trained model to production

**Prerequisites:**
- Model trained and validated
- Calibration artifact created
- Model registered in model registry

**Steps:**
```bash
# 1. Verify model registration
psql -d retrosheet -c "SELECT * FROM models.model_registry WHERE model_id = <MODEL_ID>;"

# 2. Test prediction in staging
python3 scripts/predict_pa_outcome_distribution.py \
    --game-id WAS201910260 \
    --plate-appearance-id 1 \
    --model-id <MODEL_ID> \
    --apply-calibration

# 3. Mark model as active
psql -d retrosheet -c "UPDATE models.model_registry SET is_active = false WHERE is_active = true;"
psql -d retrosheet -c "UPDATE models.model_registry SET is_active = true WHERE model_id = <MODEL_ID>;"

# 4. Verify prediction in production
python3 scripts/predict_pa_outcome_distribution.py \
    --game-id WAS201910260 \
    --plate-appearance-id 1 \
    --apply-calibration

# 5. Monitor predictions for errors
# Check logs for prediction errors
# Monitor accuracy metrics
```

**Rollback:**
```bash
# Revert to previous model
psql -d retrosheet -c "UPDATE models.model_registry SET is_active = true WHERE model_id = <PREVIOUS_MODEL_ID>;"
psql -d retrosheet -c "UPDATE models.model_registry SET is_active = false WHERE model_id = <NEW_MODEL_ID>;"
```

**Validation:**
- Predictions succeed without errors
- Latency meets SLA (< 100ms P95)
- Calibration metrics acceptable

## Data Ingestion

### Ingest Retrosheet Data

**Purpose:** Load new Retrosheet data into warehouse

**Prerequisites:**
- Retrosheet data downloaded
- Database initialized

**Steps:**
```bash
# 1. Fetch data
python3 scripts/warehouse.py fetch-retrosheet --years <YEAR>

# 2. Extract with Chadwick
python3 scripts/warehouse.py extract-chadwick --years <YEAR> --outputs all

# 3. Load to database
python3 scripts/warehouse.py load-chadwick --years <YEAR> --outputs all

# 4. Validate data quality
python3 scripts/validate_data_quality.py --fail-on-error

# 5. Refresh feature marts
psql -d retrosheet -f sql/050_feature_marts.sql
```

**Validation:**
- Row counts increase as expected
- Data quality checks pass
- Feature marts refresh successfully

### Ingest Live MLB Data

**Purpose:** Ingest live MLB game data

**Prerequisites:**
- Bridge tables populated
- Live data transform working

**Steps:**
```bash
# 1. Discover games
python3 scripts/fetch_mlb_schedule.py --yesterday

# 2. Ingest games
python3 scripts/ingest_live_games.py --schedule

# 3. Validate data
psql -d retrosheet -c "SELECT COUNT(*) FROM core.live_games WHERE created_at > NOW() - INTERVAL '1 day';"
```

**Validation:**
- Games discovered and ingested
- No errors in ingestion logs
- Live tables populate correctly

## Backup and Restore

### Create Database Backup

**Purpose:** Backup database for disaster recovery

**Frequency:** Daily

**Steps:**
```bash
# 1. Create backup directory
mkdir -p /backups/postgresql/$(date +%Y%m%d)

# 2. Perform backup
pg_dump -d retrosheet -F c -f /backups/postgresql/$(date +%Y%m%d)/retrosheet_$(date +%Y%m%d_%H%M%S).dump

# 3. Compress backup
gzip /backups/postgresql/$(date +%Y%m%d)/retrosheet_*.dump

# 4. Verify backup
pg_restore -l /backups/postgresql/$(date +%Y%m%d)/retrosheet_*.dump.gz | head -20
```

**Validation:**
- Backup file created
- Backup file size reasonable
- Backup file can be listed

### Restore Database from Backup

**Purpose:** Restore database from backup

**Prerequisites:**
- Backup file available
- Database stopped or dropped

**Steps:**
```bash
# 1. Stop application
systemctl stop retrosheet-api

# 2. Drop existing database
psql -c "DROP DATABASE IF EXISTS retrosheet;"

# 3. Create empty database
createdb retrosheet

# 4. Restore from backup
pg_restore -d retrosheet -F c /backups/postgresql/<DATE>/retrosheet_<TIMESTAMP>.dump.gz

# 5. Run migrations
python3 scripts/warehouse.py init-db

# 6. Start application
systemctl start retrosheet-api

# 7. Verify
psql -d retrosheet -c "SELECT COUNT(*) FROM core.games;"
```

**Validation:**
- Database restored
- Tables present
- Row counts reasonable
- Application starts successfully

## Monitoring and Alerting

### Check System Health

**Purpose:** Verify system is healthy

**Frequency:** Daily

**Steps:**
```bash
# 1. Check disk space
df -h

# 2. Check CPU usage
top -bn1 | head -20

# 3. Check memory usage
free -h

# 4. Check database connections
psql -d retrosheet -c "SELECT count(*) FROM pg_stat_activity;"

# 5. Check slow queries
psql -d retrosheet -c "SELECT query, mean_exec_time, calls FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 10;"

# 6. Check recent errors
tail -100 /var/log/retrosheet/error.log
```

**Validation:**
- Disk usage < 80%
- CPU usage < 70%
- Memory usage < 80%
- Database connections < 80% of max
- No slow queries > 5s
- No recent errors

### Check Data Quality

**Purpose:** Verify data quality is acceptable

**Frequency:** Weekly

**Steps:**
```bash
# Run data quality validation
python3 scripts/validate_data_quality.py --output report.json

# Check report for failures
cat report.json | jq '.results[] | select(.passed == false)'
```

**Validation:**
- All critical checks pass
- No new issues introduced
- Trend analysis shows stable quality

## Emergency Response

### Database Down

**Symptoms:**
- Application cannot connect to database
- Connection timeout errors

**Steps:**
```bash
# 1. Check PostgreSQL status
pg_ctl status

# 2. If not running, start PostgreSQL
pg_ctl start

# 3. Check logs
tail -100 /var/log/postgresql/postgresql-*.log

# 4. Check disk space
df -h

# 5. If disk full, clear old logs or WAL archives
# Remove old WAL archives older than 7 days
find /var/lib/postgresql/wal -name "*.wal" -mtime +7 -delete

# 6. Restart PostgreSQL
pg_ctl restart

# 7. Verify connection
psql -d retrosheet -c "SELECT 1;"
```

**Escalation:**
- If cannot resolve within 15 minutes, escalate to DBA
- If data corruption suspected, initiate restore from backup

### High CPU Usage

**Symptoms:**
- CPU usage > 90% for extended period
- Slow application response

**Steps:**
```bash
# 1. Identify CPU-intensive processes
top

# 2. Check database queries
psql -d retrosheet -c "SELECT pid, query, state, wait_event_type FROM pg_stat_activity WHERE state = 'active' ORDER BY query_start;"

# 3. Kill long-running queries if safe
psql -d retrosheet -c "SELECT pg_cancel_backend(<PID>);"

# 4. Check for runaway application processes
# Kill if necessary

# 5. Restart application if needed
systemctl restart retrosheet-api
```

**Escalation:**
- If cannot resolve within 30 minutes, escalate to sysadmin
- If recurring, investigate root cause

### Out of Disk Space

**Symptoms:**
- Disk usage > 90%
- Write errors in logs

**Steps:**
```bash
# 1. Check disk usage
df -h

# 2. Identify large files
du -sh /var/* | sort -hr | head -20

# 3. Clear old logs
find /var/log -name "*.log" -mtime +30 -delete

# 4. Clear old backups
find /backups -mtime +30 -delete

# 5. Vacuum database to reclaim space
psql -d retrosheet -c "VACUUM FULL;"

# 6. Consider expanding storage if needed
```

**Escalation:**
- If cannot free sufficient space, escalate to sysadmin
- If recurring, plan storage expansion

## Performance Tuning

### Optimize Slow Queries

**Purpose:** Improve query performance

**Steps:**
```bash
# 1. Identify slow queries
psql -d retrosheet -c "SELECT query, mean_exec_time, calls FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 10;"

# 2. Explain query plan
EXPLAIN ANALYZE <SLOW_QUERY>;

# 3. Check for missing indexes
# Look for sequential scans on large tables

# 4. Add missing indexes
CREATE INDEX CONCURRENTLY idx_table_column ON table(column);

# 5. Update statistics
ANALYZE table;

# 6. Verify improvement
EXPLAIN ANALYZE <SLOW_QUERY>;
```

**Validation:**
- Query execution time improves
- No sequential scans on large tables
- Index usage increases

### Tune PostgreSQL Configuration

**Purpose:** Optimize PostgreSQL for workload

**Steps:**
```bash
# 1. Review current configuration
cat /etc/postgresql/14/main/postgresql.conf

# 2. Adjust settings based on hardware
# shared_buffers = 25% of RAM
# effective_cache_size = 50% of RAM
# maintenance_work_mem = 1GB
# work_mem = 64MB
# max_connections = 100

# 3. Reload configuration
pg_ctl reload

# 4. Monitor performance
# Check query performance
# Check connection usage
# Check cache hit ratio
```

**Validation:**
- Query performance improves
- Cache hit ratio > 95%
- No connection pool exhaustion

## Change Management

### Deploy Code Changes

**Purpose:** Deploy code changes to production

**Prerequisites:**
- Code reviewed and approved
- Tests passing
- Staging validated

**Steps:**
```bash
# 1. Create backup
pg_dump -d retrosheet -F c -f /backups/pre-deploy_$(date +%Y%m%d_%H%M%S).dump

# 2. Pull latest code
git pull origin main

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run migrations
python3 scripts/warehouse.py init-db

# 5. Restart application
systemctl restart retrosheet-api

# 6. Verify deployment
# Check logs
# Test predictions
# Monitor metrics
```

**Rollback:**
```bash
# 1. Restore database
pg_restore -d retrosheet -F c /backups/pre-deploy_<TIMESTAMP>.dump

# 2. Revert code
git checkout <PREVIOUS_COMMIT>

# 3. Restart application
systemctl restart retrosheet-api
```

**Validation:**
- Deployment succeeds
- No errors in logs
- Predictions work correctly
- Metrics within SLA

## Documentation

### Update Runbooks

**Purpose:** Keep runbooks current

**Frequency:** After any significant change

**Steps:**
1. Review runbook for accuracy
2. Update with new procedures
3. Add new procedures as needed
4. Remove obsolete procedures
5. Test procedures
6. Commit changes

**Validation:**
- Procedures work as documented
- No missing steps
- No obsolete information
