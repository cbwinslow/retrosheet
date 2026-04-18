# CI/CD Pipeline Design

This document describes the design for the CI/CD pipeline for the Retrosheet Prediction Warehouse.

## Overview

The CI/CD pipeline automates testing, deployment, and validation to ensure reliable and repeatable deployments.

## Pipeline Architecture

### Stages

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Build     │ -> │   Test      │ -> │   Deploy    │ -> │  Validate   │ -> │   Monitor   │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

### Environments

- **Development:** Feature branches
- **Staging:** Main branch pre-production
- **Production:** Tagged releases

## Build Stage

### Purpose

Build application artifacts and prepare for deployment.

### Steps

1. **Checkout Code**
   - Clone repository
   - Checkout specific branch or tag

2. **Install Dependencies**
   - Install Python dependencies
   - Install Chadwick tools
   - Verify PostgreSQL client

3. **Build Artifacts**
   - Create Python package
   - Generate documentation
   - Create deployment manifests

4. **Versioning**
   - Generate version number
   - Tag release
   - Update CHANGELOG

### Configuration

```yaml
# .github/workflows/build.yml
build:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v3
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.9'
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
    - name: Build package
      run: |
        python -m build
    - name: Upload artifacts
      uses: actions/upload-artifact@v3
      with:
        name: package
        path: dist/
```

## Test Stage

### Purpose

Run automated tests to ensure code quality.

### Steps

1. **Unit Tests**
   - Run pytest on test suite
   - Generate coverage report
   - Fail if coverage < 80%

2. **Integration Tests**
   - Run integration tests
   - Test database operations
   - Test prediction serving

3. **Validation Tests**
   - Run data quality validation
   - Validate model predictions
   - Validate simulation outputs

4. **Security Scans**
   - Run dependency vulnerability scan
   - Run code security scan
   - Fail if high-severity issues found

### Configuration

```yaml
# .github/workflows/test.yml
test:
  runs-on: ubuntu-latest
  needs: build
  services:
    postgres:
      image: postgres:14
      env:
        POSTGRES_PASSWORD: postgres
      options: >-
        --health-cmd pg_isready
        --health-interval 10s
  steps:
    - uses: actions/checkout@v3
    - name: Download artifacts
      uses: actions/download-artifact@v3
      with:
        name: package
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.9'
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest pytest-cov
    - name: Run unit tests
      run: |
        pytest retrosheet/prediction/test_*.py --cov=retrosheet --cov-report=xml
    - name: Run integration tests
      run: |
        pytest scripts/test_integration_*.py
    - name: Upload coverage
      uses: codecov/codecov-action@v3
```

## Deploy Stage

### Purpose

Deploy application to target environment.

### Steps

1. **Pre-deployment Checks**
   - Verify all tests passed
   - Verify approval received (for production)
   - Create backup

2. **Database Migrations**
   - Run pending migrations
   - Validate migration success
   - Rollback on failure

3. **Application Deployment**
   - Deploy application code
   - Restart services
   - Verify health checks

4. **Feature Marts Refresh**
   - Refresh materialized views
   - Validate feature data
   - Update statistics

### Configuration

```yaml
# .github/workflows/deploy.yml
deploy:
  runs-on: ubuntu-latest
  needs: test
  environment:
    name: staging
    url: https://staging.example.com
  steps:
    - uses: actions/checkout@v3
    - name: Download artifacts
      uses: actions/download-artifact@v3
      with:
        name: package
    - name: Deploy to staging
      run: |
        # SSH to server
        ssh user@staging.example.com << 'EOF'
          cd /opt/retrosheet
          git pull origin main
          pip install -r requirements.txt
          python scripts/warehouse.py init-db
          systemctl restart retrosheet-api
        EOF
    - name: Health check
      run: |
        curl -f https://staging.example.com/health || exit 1
```

### Production Deployment

Production deployments require manual approval:

```yaml
deploy-production:
  runs-on: ubuntu-latest
  needs: test
  environment:
    name: production
    url: https://api.example.com
  steps:
    - uses: actions/checkout@v3
    - name: Create backup
      run: |
        ssh user@production.example.com "pg_dump -d retrosheet > /backups/pre-deploy.dump"
    - name: Deploy to production
      run: |
        ssh user@production.example.com << 'EOF'
          cd /opt/retrosheet
          git pull origin main
          pip install -r requirements.txt
          python scripts/warehouse.py init-db
          systemctl restart retrosheet-api
        EOF
```

## Validation Stage

### Purpose

Validate deployment success and system health.

### Steps

1. **Smoke Tests**
   - Test prediction endpoint
   - Test database queries
   - Test feature extraction

2. **Data Quality Checks**
   - Run data quality validation
   - Check for null rates
   - Check referential integrity

3. **Performance Tests**
   - Test prediction latency
   - Test query performance
   - Verify SLAs met

4. **Rollback on Failure**
   - If validation fails, trigger rollback
   - Restore from backup
   - Notify team

### Configuration

```yaml
# .github/workflows/validate.yml
validate:
  runs-on: ubuntu-latest
  needs: deploy
  steps:
    - uses: actions/checkout@v3
    - name: Run smoke tests
      run: |
        python scripts/test_smoke.py --environment staging
    - name: Run data quality checks
      run: |
        python scripts/validate_data_quality.py --fail-on-error
    - name: Performance test
      run: |
        python scripts/benchmark_prediction.py --threshold 100
    - name: Rollback on failure
      if: failure()
      run: |
        ssh user@staging.example.com "systemctl restart retrosheet-api"
```

## Rollback Procedures

### Automatic Rollback

Triggered on validation failure:

```yaml
rollback:
  runs-on: ubuntu-latest
  needs: validate
  if: failure()
  steps:
    - name: Rollback deployment
      run: |
        ssh user@production.example.com << 'EOF'
          cd /opt/retrosheet
          git checkout <previous-commit>
          pip install -r requirements.txt
          systemctl restart retrosheet-api
        EOF
    - name: Restore database
      run: |
        ssh user@production.example.com "pg_restore -d retrosheet /backups/pre-deploy.dump"
    - name: Notify team
      uses: slackapi/slack-github-action@v1
      with:
        payload: |
          {"text": "Production deployment rolled back"}
```

### Manual Rollback

Triggered manually via GitHub Actions:

```bash
# Trigger rollback workflow
gh workflow run rollback.yml --ref main
```

## Database Migration Automation

### Migration Tracking

Track migrations in database:

```sql
CREATE TABLE IF NOT EXISTS schema_migrations (
    id SERIAL PRIMARY KEY,
    filename TEXT NOT NULL,
    checksum TEXT NOT NULL,
    applied_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);
```

### Migration Runner

```python
# scripts/migrate.py
import os
import hashlib
from pathlib import Path
from sqlalchemy import create_engine, text

def run_migrations(engine, migrations_dir):
    """Run pending migrations."""
    with engine.begin() as conn:
        for migration_file in sorted(Path(migrations_dir).glob("*.sql")):
            # Check if already applied
            result = conn.execute(text(
                "SELECT COUNT(*) FROM schema_migrations WHERE filename = :filename"
            ), {"filename": migration_file.name})
            
            if result.scalar() == 0:
                # Read and execute migration
                with open(migration_file) as f:
                    sql = f.read()
                
                # Calculate checksum
                checksum = hashlib.md5(sql.encode()).hexdigest()
                
                # Execute migration
                conn.execute(text(sql))
                
                # Record migration
                conn.execute(text(
                    "INSERT INTO schema_migrations (filename, checksum) VALUES (:filename, :checksum)"
                ), {"filename": migration_file.name, "checksum": checksum})
                
                print(f"Applied migration: {migration_file.name}")
```

### CI/CD Integration

```yaml
# .github/workflows/migrate.yml
migrate:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v3
    - name: Run migrations
      run: |
        python scripts/migrate.py --migrations-dir sql/
```

## Deployment Validation

### Pre-deployment Checklist

- [ ] All tests passing
- [ ] Code reviewed
- [ ] Documentation updated
- [ ] Migration plan reviewed
- [ ] Rollback plan documented
- [ ] Stakeholders notified

### Post-deployment Validation

- [ ] Health checks passing
- [ ] Smoke tests passing
- [ ] Data quality checks passing
- [ ] Performance within SLA
- [ ] No errors in logs
- [ ] Monitoring configured

### Automated Validation Script

```python
# scripts/validate_deployment.py
import requests
import sys

def validate_deployment(base_url):
    """Validate deployment is healthy."""
    # Health check
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        response.raise_for_status()
    except Exception as e:
        print(f"Health check failed: {e}")
        return False
    
    # Prediction test
    try:
        response = requests.post(f"{base_url}/predict", json={
            "game_id": "WAS201910260",
            "plate_appearance_id": 1,
        }, timeout=10)
        response.raise_for_status()
    except Exception as e:
        print(f"Prediction test failed: {e}")
        return False
    
    print("Deployment validation passed")
    return True

if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    sys.exit(0 if validate_deployment(url) else 1)
```

## Deployment Documentation

### Deployment Runbook

See `docs/OPERATIONS_RUNBOOKS.md` for detailed deployment procedures.

### Change Log

Maintain CHANGELOG.md with deployment history:

```markdown
# Changelog

## [1.2.0] - 2026-04-17

### Added
- New calibration method
- Performance optimization

### Changed
- Updated model version
- Improved error handling

### Fixed
- Fixed prediction latency issue
```

## Best Practices

### Branch Strategy

- **main:** Production-ready code
- **develop:** Integration branch
- **feature/*:** Feature branches
- **hotfix/*:** Emergency fixes

### Commit Messages

Follow conventional commits:
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation
- `test:` Tests
- `refactor:` Refactoring

### Versioning

Use semantic versioning:
- `MAJOR.MINOR.PATCH`
- Increment MAJOR for breaking changes
- Increment MINOR for new features
- Increment PATCH for bug fixes

### Testing

- Test coverage > 80%
- All tests must pass before merge
- Integration tests on every PR
- Performance tests on release

### Security

- Scan dependencies for vulnerabilities
- Use secrets management
- No secrets in code
- Review security changes

## Monitoring

### Pipeline Metrics

- Build duration
- Test duration
- Deployment duration
- Success rate
- Failure rate

### Alerts

- Pipeline failure
- Deployment failure
- Validation failure
- Rollback triggered

## Next Steps

1. Set up GitHub Actions or similar CI/CD tool
2. Configure secrets for database and API access
3. Set up staging environment
4. Configure automatic testing
5. Set up deployment automation
6. Configure monitoring and alerting
7. Document rollback procedures
8. Test rollback procedures
9. Train team on CI/CD process
10. Monitor pipeline performance
