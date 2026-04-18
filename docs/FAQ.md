# Frequently Asked Questions

## General Questions

### Q: What is the Retrosheet Prediction Warehouse?

A: A reproducible baseball prediction warehouse that uses Retrosheet historical data and MLB Stats API live data to train machine learning models for plate appearance outcome predictions.

### Q: What data sources does it use?

A: 
- **Historical:** Retrosheet event files processed with Chadwick tools
- **Live:** MLB Stats API / GUMBO for schedules and live game feeds
- **Reference:** Chadwick Bureau Register for player/team ID mappings

### Q: What programming languages are used?

A: 
- **Python:** For data processing, model training, prediction serving
- **SQL:** For database schema, migrations, feature queries
- **TypeScript:** For Next.js web interface

### Q: What database does it use?

A: PostgreSQL 14+ is the primary database. DuckDB and Redis are optional for analytics and caching.

## Setup and Installation

### Q: How do I install the dependencies?

A: Run the dependency check:
```bash
python3 scripts/warehouse.py check-deps
```

Install Python dependencies:
```bash
pip install -r requirements.txt
```

Install Chadwick tools from https://chadwick.sourceforge.net/

### Q: How do I set up the database?

A: Create the database:
```bash
createdb retrosheet
```

Initialize schema:
```bash
python3 scripts/warehouse.py init-db
```

### Q: How much disk space do I need?

A: 
- Raw Retrosheet data: ~5GB for 2000-2025
- Processed data: ~10GB
- Database: ~20GB
- Models: ~1GB
- **Total:** ~35GB minimum, 50GB recommended

## Data Ingestion

### Q: How do I download Retrosheet data?

A: 
```bash
python3 scripts/warehouse.py fetch-retrosheet --years 2000-2025
```

### Q: How do I rebuild the entire warehouse?

A: Use the rebuild script:
```bash
./scripts/rebuild_warehouse.sh
```

Or manually:
```bash
python3 scripts/warehouse.py check-deps
python3 scripts/warehouse.py fetch-retrosheet --years 2000-2025
python3 scripts/warehouse.py init-db
python3 scripts/warehouse.py extract-chadwick --years 2000-2025 --outputs all
python3 scripts/warehouse.py load-chadwick --years 2000-2025 --outputs all
```

### Q: Can I rebuild for a specific year?

A: Yes:
```bash
python3 scripts/warehouse.py extract-chadwick --years 2023 --outputs all
python3 scripts/warehouse.py load-chadwick --years 2023 --outputs all
```

### Q: How do I ingest live MLB data?

A: 
```bash
# Discover games
python3 scripts/fetch_mlb_schedule.py --yesterday

# Ingest games
python3 scripts/ingest_live_games.py --schedule
```

## Model Training

### Q: How do I train a model?

A: 
```bash
python3 scripts/train_pa_outcome_distribution.py \
    --feature-set advanced \
    --model-name hist_gradient_boosting_multiclass \
    --train-years 2000-2022 \
    --validation-years 2023-2025
```

### Q: What model families are available?

A: 
- `hist_gradient_boosting_multiclass` (recommended)
- `random_forest_multiclass`
- `logistic_regression_multiclass`

### Q: What feature sets are available?

A: 
- `basic`: Core game state
- `advanced_count`: Advanced with count context
- `advanced`: Full advanced feature set

### Q: How do I calibrate a model?

A: 
```bash
python3 scripts/calibrate_pa_outcome_model.py \
    --model-id <MODEL_ID> \
    --calibration-years 2023-2024 \
    --validation-years 2025
```

### Q: How do I register a model?

A: 
```bash
python3 scripts/register_pa_outcome_calibration.py \
    --model-id <MODEL_ID> \
    --calibration-artifact-path <PATH>
```

## Prediction Serving

### Q: How do I make a prediction?

A: Historical:
```bash
python3 scripts/predict_pa_outcome_distribution.py \
    --game-id WAS201910260 \
    --plate-appearance-id 1
```

Live:
```bash
python3 scripts/predict_live_pa_outcome_distribution.py \
    --game-pk 599374
```

### Q: What does the prediction output include?

A: 
- `class_probabilities`: Raw probabilities for each outcome
- `derived_probabilities`: Aggregated probabilities (hit, out, walk)
- `model_metadata`: Information about the model used
- `state_snapshot`: Game state at prediction time
- `missing_features`: List of missing features

### Q: How do I use calibration?

A: Add `--apply-calibration` flag:
```bash
python3 scripts/predict_pa_outcome_distribution.py \
    --game-id WAS201910260 \
    --plate-appearance-id 1 \
    --apply-calibration
```

Calibration is enabled by default.

## Data Quality

### Q: How do I validate data quality?

A: 
```bash
python3 scripts/validate_data_quality.py
```

Export results:
```bash
python3 scripts/validate_data_quality.py --output report.json
```

### Q: What does data quality check?

A: 
- Schema validation
- Null rate monitoring
- Value range validation
- Referential integrity
- Temporal consistency

### Q: What are the data quality SLAs?

A: See `docs/DATA_QUALITY_SLAs.md` for detailed SLAs:
- Null rate: ≤ 5% for non-critical columns, 0% for critical
- Value ranges: 0 out-of-range values
- Referential integrity: 0% orphan rate for critical relationships

## Troubleshooting

### Q: The database connection failed

A: Check PostgreSQL is running:
```bash
pg_ctl status
```

Verify database exists:
```bash
psql -l
```

Check connection string:
```bash
echo $DATABASE_URL
```

### Q: Training is very slow

A: 
- Reduce `--n-estimators`
- Use `--feature-set basic`
- Reduce training year range
- Use GPU if available

### Q: Model overfits

A: 
- Reduce model complexity (`--max-depth`)
- Add regularization
- Use temporal decay policy
- Increase training data

### Q: Calibration makes performance worse

A: 
- Ensure calibration years separate from validation
- Try different calibration type (sigmoid vs isotonic)
- Ensure sufficient calibration data
- Check for data leakage

### Q: Prediction serving is slow

A: 
- Use model caching
- Process predictions in batches
- Check database indexes
- Use connection pooling

## Architecture

### Q: What are the data layers?

A: 
- `raw_retrosheet`: Source-preserved Chadwick outputs
- `raw_mlb`: Source-preserved MLB API data
- `bridge`: MLB ↔ Retrosheet ID mappings
- `core`: Canonical baseball entities
- `features`: ML-ready feature marts
- `models`: Model registry and metadata
- `predictions`: Stored outputs and reports
- `analysis`: Historical + live combined views

### Q: Should I use EdgeForge/mlb_features?

A: No, those are experimental prototypes. Use the canonical layers listed above. See `docs/EDGEFORGE_TRIAGE.md` for details.

### Q: Where should I put new code?

A: Check `docs/agents/FILE_INVENTORY.md` for the canonical file locations. Don't create new schemas without checking documentation first.

## Contributing

### Q: How do I contribute?

A: See `docs/CONTRIBUTOR_ONBOARDING.md` for the contributor guide.

### Q: What are the coding standards?

A: 
- Follow PEP 8 for Python
- Use type hints where appropriate
- Add docstrings to all functions
- Write unit tests for new code

### Q: How do I run tests?

A: 
```bash
# Unit tests
pytest retrosheet/prediction/test_*.py

# Integration tests
pytest scripts/test_integration_*.py

# Validation tests
pytest scripts/test_validation_*.py
```

## Advanced

### Q: How do I set up GPU training?

A: Install GPU-enabled libraries and use `--use-gpu` flag. See `docs/PERFORMANCE_OPTIMIZATION.md` for details.

### Q: How do I set up Redis caching?

A: See `docs/FEATURE_STORE_ARCHITECTURE.md` for Redis integration design.

### Q: How do I set up DuckDB analytics?

A: See `docs/FEATURE_STORE_ARCHITECTURE.md` for DuckDB integration design.

### Q: How do I set up market data integration?

A: See `docs/MARKET_INTEGRATION.md` for market integration architecture.

## Support

### Q: Where can I get help?

A: 
- Check documentation in `docs/` directory
- Search GitHub issues
- Check `docs/agents/CURRENT_SNAPSHOT.md` for current state
- Create GitHub issue with detailed information

### Q: How do I report a bug?

A: Create a GitHub issue with:
- Error message
- Steps to reproduce
- System information
- Relevant logs
