# Contributor Onboarding Guide

Welcome to the Retrosheet Prediction Warehouse project! This guide will help you get started contributing to the codebase.

## Project Overview

This project builds a reproducible baseball prediction warehouse from free/open data sources. It uses Retrosheet historical data and MLB Stats API live data to train ML models for plate appearance outcome predictions.

## Quick Start

### Prerequisites

- Python 3.9+
- PostgreSQL 14+
- Git

### Setup

1. **Clone the repository:**
```bash
git clone https://github.com/your-org/retrosheet.git
cd retrosheet
```

2. **Set up the database:**
```bash
# Create database
createdb retrosheet

# Run migrations
python3 scripts/warehouse.py init-db
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

## Architecture Overview

### Data Layers

- `raw_retrosheet`: Source-preserved Chadwick/Retrosheet outputs
- `raw_mlb`: Source-preserved MLB schedules, live feeds, and reference snapshots
- `bridge`: MLB ↔ Retrosheet identifier mappings
- `core`: Typed baseball entities and canonical facts
- `features`: Model-ready examples and marts
- `models`: Model registry and metadata
- `predictions`: Stored outputs, reports, backtests
- `analysis`: Historical + live combined read layer

### Key Scripts

- `scripts/warehouse.py`: Main warehouse orchestration script
- `scripts/train_pa_outcome_distribution.py`: Train PA outcome models
- `scripts/predict_pa_outcome_distribution.py`: Historical prediction serving
- `scripts/predict_live_pa_outcome_distribution.py`: Live prediction serving
- `scripts/validate_data_quality.py`: Data quality validation

### Documentation

- `docs/agents/AGENTS.md`: Agent operating guide and non-negotiables
- `docs/agents/CURRENT_SNAPSHOT.md`: Current project state and next steps
- `docs/agents/FILE_INVENTORY.md`: Inventory of SQL, scripts, and docs
- `docs/agents/PROCEDURES.md`: Canonical workflows
- `docs/MLB_SIMULATION.md`: Baseball state machine documentation
- `docs/MARKET_INTEGRATION.md`: Market integration architecture

## Common Workflows

### Rebuilding the Warehouse

```bash
# Full warehouse rebuild
./scripts/rebuild_warehouse.sh

# Partial rebuild (specific years)
python3 scripts/warehouse.py extract-chadwick --years 2020-2025 --outputs all
python3 scripts/warehouse.py load-chadwick --years 2020-2025 --outputs all
```

### Training a Model

```bash
# Train PA outcome distribution model
python3 scripts/train_pa_outcome_distribution.py \
    --feature-set advanced \
    --model-name hist_gradient_boosting_multiclass \
    --train-years 2000-2022 \
    --validation-years 2023-2025

# Register the best model
python3 scripts/register_pa_outcome_calibration.py \
    --model-id <MODEL_ID> \
    --report-name "calibration_report"
```

### Making Predictions

```bash
# Historical prediction
python3 scripts/predict_pa_outcome_distribution.py \
    --game-id WAS201910260 \
    --plate-appearance-id 1 \
    --apply-calibration

# Live prediction
python3 scripts/predict_live_pa_outcome_distribution.py \
    --game-pk 599374 \
    --apply-calibration
```

### Validating Data Quality

```bash
# Run all data quality checks
python3 scripts/validate_data_quality.py

# Export results to JSON
python3 scripts/validate_data_quality.py --output data_quality_report.json

# Exit with error if any check fails
python3 scripts/validate_data_quality.py --fail-on-error
```

## Development Guidelines

### Code Style

- Follow PEP 8 for Python code
- Use type hints where appropriate
- Add docstrings to all functions and classes
- Keep functions focused and modular

### Database Changes

- Always create new migrations in the `sql/` directory
- Use descriptive migration numbers (e.g., `080_new_feature.sql`)
- Test migrations on a copy of the database first
- Document breaking changes in `docs/agents/PROJECT_LOG.md`

### Testing

- Write unit tests for new Python modules
- Create integration tests for database migrations
- Test with sample data before full warehouse rebuild
- Use fixed seeds for reproducibility in simulation tests

### Documentation

- Update `docs/agents/FILE_INVENTORY.md` when adding new files
- Update `docs/agents/PROCEDURES.md` for new workflows
- Update `docs/agents/CURRENT_SNAPSHOT.md` after major milestones
- Add inline comments for complex logic

## Common Issues

### Database Connection Errors

**Issue:** `psycopg2.OperationalError: could not connect to server`

**Solution:**
1. Check PostgreSQL is running: `pg_ctl status`
2. Verify database exists: `psql -l`
3. Check connection string in environment variables

### Model Loading Errors

**Issue:** `FileNotFoundError: Model artifact not found`

**Solution:**
1. Check model is registered in `models.model_registry`
2. Verify artifact path exists in `data/models/`
3. Re-register model if needed

### Feature Query Errors

**Issue:** `ProgrammingError: column does not exist`

**Solution:**
1. Check schema migration has been applied
2. Verify feature table exists: `\d features.plate_appearance_advanced_examples`
3. Run missing migrations

## Getting Help

### Resources

- **Documentation:** Check `docs/` directory for detailed guides
- **GitHub Issues:** Search existing issues before creating new ones
- **AGENTS.md:** Read `docs/agents/AGENTS.md` for project conventions

### Asking Questions

1. Search the documentation first
2. Check GitHub Issues for similar problems
3. Include relevant code snippets and error messages
4. Describe what you've already tried

## Contributing Workflow

1. **Fork the repository**
2. **Create a feature branch:** `git checkout -b feature/my-feature`
3. **Make changes and commit:** `git commit -m "Description of changes"`
4. **Push to fork:** `git push origin feature/my-feature`
5. **Create pull request** with:
   - Clear description of changes
   - Links to relevant documentation
   - Testing performed

## Code Review Process

- Reviewer will check for:
  - Adherence to project conventions
  - Code quality and style
  - Documentation updates
  - Test coverage
- Address review feedback promptly
- Keep discussions focused and constructive

## Next Steps

After completing this guide:

1. Read `docs/agents/AGENTS.md` for project conventions
2. Review `docs/agents/CURRENT_SNAPSHOT.md` for current state
3. Explore `docs/agents/FILE_INVENTORY.md` to understand the codebase
4. Try the common workflows above
5. Pick a small task from the GitHub issues to get started

## Additional Resources

- [Retrosheet Documentation](https://www.retrosheet.org/)
- [MLB Stats API Documentation](https://github.com/MLB-Stats-API)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Python Best Practices](https://docs.python-guide.org/)

Thank you for contributing to the Retrosheet Prediction Warehouse!
