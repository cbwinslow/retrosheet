# Troubleshooting Procedures

This document provides common issues and solutions for the Retrosheet Prediction Warehouse.

## Database Issues

### Issue: Cannot connect to database

**Symptoms:**
```
psycopg2.OperationalError: could not connect to server
```

**Solutions:**
1. Check PostgreSQL is running:
   ```bash
   pg_ctl status
   ```

2. Start PostgreSQL if not running:
   ```bash
   pg_ctl start
   ```

3. Verify database exists:
   ```bash
   psql -l
   ```

4. Create database if needed:
   ```bash
   createdb retrosheet
   ```

5. Check connection string in environment variables:
   ```bash
   echo $DATABASE_URL
   ```

### Issue: Migration fails halfway through

**Symptoms:**
```
ERROR: relation "table_name" already exists
```

**Solutions:**
1. Check which migrations were applied:
   ```bash
   psql -d retrosheet -c "SELECT filename FROM schema_migrations ORDER BY applied_at;"
   ```

2. Roll back to last successful migration:
   ```bash
   psql -d retrosheet -f sql/<rollback_file>.sql
   ```

3. Re-run migration:
   ```bash
   psql -d retrosheet -f sql/<migration_file>.sql
   ```

### Issue: Out of memory during data load

**Symptoms:**
```
ERROR: out of memory
```

**Solutions:**
1. Process data in smaller batches
2. Increase PostgreSQL memory settings:
   ```bash
   # In postgresql.conf
   shared_buffers = 4GB
   work_mem = 256MB
   ```
3. Restart PostgreSQL:
   ```bash
   pg_ctl restart
   ```

## Data Ingestion Issues

### Issue: Chadwick tool not found

**Symptoms:**
```
cwevent: command not found
```

**Solutions:**
1. Install Chadwick tools from https://chadwick.sourceforge.net/
2. Add to PATH:
   ```bash
   export PATH=$PATH:/path/to/chadwick/bin
   ```
3. Verify installation:
   ```bash
   which cwevent
   ```

### Issue: Retrosheet data not found

**Symptoms:**
```
ERROR: No such file or directory: data/raw/retrosheet/...
```

**Solutions:**
1. Check data directory:
   ```bash
   ls data/raw/retrosheet/
   ```

2. Fetch data if missing:
   ```bash
   python3 scripts/warehouse.py fetch-retrosheet --years 2000-2025
   ```

3. Verify download completed:
   ```bash
   find data/raw/retrosheet/ -name "*.EV*" | wc -l
   ```

### Issue: Extraction very slow

**Symptoms:**
- Extraction taking hours for single year

**Solutions:**
1. Process fewer years at a time
2. Use SSD for data directory
3. Check disk I/O:
   ```bash
   iostat -x 1
   ```
4. Reduce output types:
   ```bash
   python3 scripts/warehouse.py extract-chadwick --years 2000-2005 --outputs events, games
   ```

## Model Training Issues

### Issue: Training out of memory

**Symptoms:**
```
MemoryError: Unable to allocate array
```

**Solutions:**
1. Reduce training data:
   ```bash
   python3 scripts/train_pa_outcome_distribution.py --train-years 2020-2022
   ```

2. Reduce model complexity:
   ```bash
   python3 scripts/train_pa_outcome_distribution.py --max-depth 5 --n-estimators 100
   ```

3. Use simpler feature set:
   ```bash
   python3 scripts/train_pa_outcome_distribution.py --feature-set basic
   ```

4. Use GPU if available:
   ```bash
   python3 scripts/train_pa_outcome_distribution.py --use-gpu
   ```

### Issue: Model overfitting

**Symptoms:**
- Training metrics much better than validation metrics
- Validation log loss increases during training

**Solutions:**
1. Reduce model complexity:
   ```bash
   --max-depth 3 --n-estimators 50
   ```

2. Add regularization:
   ```bash
   --l2-regularization 0.1
   ```

3. Use temporal decay:
   ```bash
   --temporal-policy half_life_5
   ```

4. Increase training data:
   ```bash
   --train-years 2000-2022
   ```

### Issue: Calibration makes performance worse

**Symptoms:**
- Log loss increases after calibration
- ECE increases after calibration

**Solutions:**
1. Ensure calibration years separate from validation:
   ```bash
   --calibration-years 2023-2024 --validation-years 2025
   ```

2. Try different calibration type:
   ```bash
   --calibration-type sigmoid
   ```

3. Ensure sufficient calibration data:
   ```bash
   # Need at least 10K samples
   ```

4. Check for data leakage in features

## Prediction Serving Issues

### Issue: Model not found

**Symptoms:**
```
ERROR: Model not found in registry
```

**Solutions:**
1. Check model is registered:
   ```bash
   psql -d retrosheet -c "SELECT * FROM models.model_registry;"
   ```

2. Register model if needed:
   ```bash
   python3 scripts/register_pa_outcome_calibration.py --model-id <MODEL_ID>
   ```

3. Check model is active:
   ```bash
   psql -d retrosheet -c "SELECT * FROM models.model_registry WHERE is_active = true;"
   ```

### Issue: Features missing

**Symptoms:**
```
ERROR: Feature 'column_name' not found
```

**Solutions:**
1. Check feature table exists:
   ```bash
   psql -d retrosheet -c "\d features.plate_appearance_advanced_examples"
   ```

2. Check feature table has data:
   ```bash
   psql -d retrosheet -c "SELECT COUNT(*) FROM features.plate_appearance_advanced_examples;"
   ```

3. Rebuild feature marts if empty:
   ```bash
   psql -d retrosheet -f sql/050_feature_marts.sql
   ```

### Issue: Slow predictions

**Symptoms:**
- Predictions taking > 1 second

**Solutions:**
1. Use model caching
2. Process predictions in batches
3. Check database indexes:
   ```bash
   psql -d retrosheet -c "SELECT indexname FROM pg_indexes WHERE tablename = 'plate_appearance_advanced_examples';"
   ```
4. Use connection pooling

## Data Quality Issues

### Issue: Null rate too high

**Symptoms:**
- Data quality check fails with high null rate

**Solutions:**
1. Identify problematic columns:
   ```bash
   python3 scripts/validate_data_quality.py --output report.json
   ```

2. Check upstream data quality
3. Fix data extraction if needed
4. Re-ingest cleaned data

### Issue: Referential integrity violation

**Symptoms:**
- Orphaned records found in foreign key checks

**Solutions:**
1. Identify orphaned records:
   ```bash
   SELECT COUNT(*) FROM child_table c
   LEFT JOIN parent_table p ON c.fk = c.fk
   WHERE p.pk IS NULL;
   ```

2. Re-ingest missing parent data
3. Delete orphaned records if appropriate
4. Add foreign key constraints to prevent future violations

## Live Data Issues

### Issue: MLB API rate limit

**Symptoms:**
```
ERROR: 429 Too Many Requests
```

**Solutions:**
1. Add delay between requests:
   ```bash
   python3 scripts/fetch_mlb_schedule.py --delay 1
   ```

2. Use caching for repeated requests
3. Implement exponential backoff
4. Check API quota and adjust usage

### Issue: Bridge table mapping missing

**Symptoms:**
- MLB IDs not mapped to Retrosheet IDs

**Solutions:**
1. Re-populate bridge tables:
   ```bash
   python3 scripts/populate_bridge_tables.py
   ```

2. Check Chadwick Bureau Register data
3. Add manual mappings if needed
4. Document unmapped IDs

## Performance Issues

### Issue: Slow database queries

**Symptoms:**
- Queries taking > 10 seconds

**Solutions:**
1. Run EXPLAIN ANALYZE:
   ```bash
   EXPLAIN ANALYZE SELECT * FROM table WHERE condition;
   ```

2. Add missing indexes
3. Optimize query structure
4. Update PostgreSQL statistics:
   ```bash
   ANALYZE table_name;
   ```

### Issue: High CPU usage

**Symptoms:**
- CPU usage > 90%

**Solutions:**
1. Identify CPU-intensive processes:
   ```bash
   top
   ```

2. Reduce batch sizes
3. Limit concurrent operations
4. Use more efficient algorithms

## Getting Help

If issues persist:

1. Check documentation:
   - `docs/agents/PROCEDURES.md`
   - `docs/agents/CURRENT_SNAPSHOT.md`
   - Training guides in `docs/TRAINING_*.md`

2. Search GitHub issues for similar problems

3. Check error logs:
   ```bash
   tail -f /var/log/postgresql/postgresql-*.log
   ```

4. Create GitHub issue with:
   - Error message
   - Steps to reproduce
   - System information
   - Relevant logs

## Prevention

To prevent common issues:

1. **Always validate data after ingestion**
2. **Run data quality checks regularly**
3. **Monitor system resources**
4. **Keep backups of critical data**
5. **Document custom configurations**
6. **Test changes in development first**
7. **Keep software dependencies updated**
