# Python Agent Guidance

**Role**: Source adapters, CLI implementation, services, models, and all Python code.

---

## Scope

You are responsible for:
- `baseball/` package implementation
- Source adapters (`baseball/sources/`)
- CLI commands (`baseball/cli.py`)
- Core services (`baseball/services/`)
- Feature engineering (`baseball/features/`)
- ML pipeline (`baseball/models/`)
- Tests (`tests/`)

---

## Key Documents

| Document | When to Use |
|----------|-------------|
| `docs/migration_map.md` | Where to place new code |
| `docs/architecture.md` | Component patterns |
| `pyproject.toml` | Dependencies and project config |

---

## Code Organization

```
baseball/
  __init__.py           # Package version
  cli.py                # Typer CLI entry point
  app.py                # Application container
  settings.py           # Pydantic settings
  logging.py            # Structured logging
  core/                 # Shared infrastructure
    db.py               # Database connections
    sql_runner.py       # SQL execution
    checkpoints.py     # Pipeline checkpoints
    types.py            # Type definitions
  sources/              # Data source adapters
    base.py             # BaseSource abstract class
    retrosheet.py       # Retrosheet adapter
    mlb.py              # MLB API adapter
    espn.py             # ESPN adapter
    statcast.py         # Statcast adapter
  features/             # Feature engineering
    base.py             # BaseFeature class
    run_expectancy.py
    win_expectancy.py
  models/               # ML pipeline
    base.py             # BaseModel class
    registry.py         # Model registry
    training.py         # Training pipeline
    inference.py        # Inference pipeline
  services/             # Business logic
    bridge.py           # Bridge/xref service
    validation.py       # Data validation
    serving.py          # Serving layer
```

---

## Code Standards

### Headers

Every Python file must have this header:

```python
#!/usr/bin/env python3
"""
File: baseball/sources/mlb.py
Purpose: MLB Stats API source adapter
Author: Agent [identifier]
Date: 2026-04-26
Dependencies: requests, pydantic
Notes: Implements BaseSource interface for MLB live data
"""
```

### Type Hints

Use type hints everywhere:

```python
def download(self, config: DownloadConfig) -> SourceResult:
    ...
```

### Error Handling

Use custom exceptions:

```python
class SourceError(Exception):
    """Base exception for source adapters."""
    pass

class DownloadError(SourceError):
    """Failed to download from source."""
    pass
```

### Logging

Use structured logging:

```python
from baseball.logging import get_logger

logger = get_logger(__name__)
logger.info("downloading_games", date=game_date, count=len(games))
```

---

## CLI Patterns

### Command Structure

```python
import typer
from baseball import settings

app = typer.Typer(help="MLB data ingestion")

@app.command()
def download(
    date: str = typer.Option(..., "--date", "-d", help="Game date (YYYY-MM-DD)"),
    team: str = typer.Option(None, "--team", "-t", help="Team abbreviation")
):
    """Download MLB games for a date."""
    config = settings.load()
    source = MlbSource(config)
    result = source.download(DownloadConfig(date=date, team=team))
    typer.echo(f"Downloaded {result.count} games")

if __name__ == "__main__":
    app()
```

### Progress Reporting

Use `rich` for progress bars:

```python
from rich.progress import Progress

with Progress() as progress:
    task = progress.add_task("[cyan]Ingesting...", total=total)
    for game in games:
        ingest_game(game)
        progress.advance(task)
```

---

## Testing

### Unit Tests

```python
def test_mlb_source_download():
    source = MlbSource(test_config)
    result = source.download(DownloadConfig(date="2024-04-01"))
    assert result.count > 0
    assert result.status == "success"
```

### Integration Tests

```python
def test_mlb_end_to_end():
    # Download
    result = run_cli(["mlb", "download", "--date", "2024-04-01"])
    assert result.exit_code == 0
    
    # Ingest
    result = run_cli(["mlb", "ingest", "--date", "2024-04-01"])
    assert result.exit_code == 0
    
    # Validate
    result = run_cli(["mlb", "validate", "--date", "2024-04-01"])
    assert "valid" in result.output
```

---

## Dependencies

### Adding New Dependencies

```bash
uv add package_name
# For dev dependencies:
uv add --dev package_name
```

### Preferred Libraries

| Purpose | Library |
|---------|---------|
| CLI | typer |
| HTTP | requests / aiohttp |
| Database | psycopg2-binary / asyncpg |
| Data | pandas, numpy |
| ML | scikit-learn, xgboost, lightgbm |
| Validation | pydantic |
| Logging | structlog |
| Testing | pytest, pytest-asyncio |

---

## Migration Rules

When refactoring existing code:

1. **Preserve working logic** - wrap, don't rewrite
2. **Update imports** - after moving files
3. **Maintain tests** - ensure they still pass
4. **Document moves** - in `docs/migration_map.md`

---

## Review Checklist

Before submitting Python changes:

- [ ] File has proper header
- [ ] Type hints used throughout
- [ ] Error handling appropriate
- [ ] Logging added for important operations
- [ ] Tests added/updated
- [ ] `ruff check --fix .` passes
- [ ] `ruff format .` applied
- [ ] No hardcoded credentials
- [ ] Environment variables used for config

---

## Document Control

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-04-26 | Migration Agent | Initial Python agent guidance |
