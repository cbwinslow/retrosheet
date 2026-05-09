# Recommendations Log (UTC)

## Immediate Improvements
1. Add an extras-based dependency strategy in `pyproject.toml` (e.g., `cli`, `models`, `live`) so minimal installs can run core commands while advanced features remain optional.
2. Add a preflight CLI command (`baseball doctor`) that checks required binaries, Python packages, DB connectivity, and API tokens.
3. Split CLI command registration into lazy-loaded groups so `--help` works without importing all integrations.
4. Add CI matrix jobs for minimal install vs full install to catch import regressions early.
5. Standardize a "universal test harness" wrapper that captures stack traces, environment metadata, and artifact logs for every test module.

## Mid-Term Architecture Suggestions
1. Introduce ingestion interface contracts (`BaseSource.download`, `ingest`, `bootstrap`) with mandatory integration tests per source.
2. Build database bootstrap SQL as idempotent migration layers:
   - `sql/00_admin` for roles/schemas
   - `sql/raw/*` for source-specific landing tables
   - `sql/bridge/*` for xref tables
   - `sql/core/*` for canonical models
   - `sql/features/*` for materialized views and feature tables
3. Implement model registry metadata table tracking: model family, feature snapshot, calibration status, latency, and deployment eligibility.
4. Add real-time orchestration tests with mocked live feed + mocked odds feed to validate prediction refresh cadence and arbitrage signal generation.
