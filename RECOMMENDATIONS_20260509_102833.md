# Recommendations Log (UTC)

## Immediate Reliability Improvements
1. Define dependency extras in packaging:
   - `base` (cli + db)
   - `ingest` (requests, pandas)
   - `live` (websockets)
   - `models` (numpy, sklearn/xgboost)
   - `monitor` (prometheus_client)
2. Remove legacy `@app.command(name='train')` wrapper in `baseball/cli/main.py` to avoid naming conflict with `train` sub-app.
3. Add CLI integration tests that execute:
   - `python -m baseball --help`
   - `python -m baseball bootstrap plan`
   - `python -m baseball bootstrap run --dry-run`
4. Add SQL validation CI stage:
   - parse all `sql/**/*.sql`
   - run idempotency smoke test in ephemeral Postgres container.

## Database Workflow Consolidation
1. Add `sql/README.md` with authoritative execution order and object grain/key references.
2. Split maintenance-only scripts from required bootstrap scripts so production bootstrap path is deterministic.
3. Add bootstrap manifest file (YAML or TOML) to explicitly control execution order instead of filename ordering only.

## Handoff Notes
- If command groups still skip due import errors, install extras first and re-run help/status/bootstrap checks before deeper refactoring.
