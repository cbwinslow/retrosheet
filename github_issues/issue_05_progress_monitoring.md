# Issue 5 – Real‑Time Query Progress Monitoring

**Goal**: Provide live visibility into long‑running SQL queries during data ingestion and model training.

## Tasks
1. Deploy FastAPI endpoint (`scripts/query_monitor.py`).
2. Install and configure `pg_progress` extension (optional but recommended).
3. Add dashboard widget to `baseball-chatbot-ui` that polls `/progress`.
4. Write unit tests for the endpoint and integration tests for the UI widget.
5. Document usage in `docs/agents/next_steps.md`.

## Definition of Done
- Endpoint returns JSON with active queries and elapsed time.
- UI shows a progress bar for each running ingestion step.
- All tests pass (`pytest tests/test_query_monitor.py`).

## Links & Context
- **Documentation**: [Next Steps](../docs/agents/next_steps.md)
- **SQL Migration**: [MLB Data Completeness](../sql/150_mlb_data_completeness.sql)
- **Related Issue**: #05_documentation_and_issue_linking