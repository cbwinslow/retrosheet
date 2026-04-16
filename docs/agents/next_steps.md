# Next Steps for EdgeForge Project

## 1. Complete MLB Data Ingestion & Validation (updated)
	- Run `scripts/complete_mlb_ingestion.sh` to ensure all seasons 2000‑2025 are present.
	- Verify completeness with the new view `raw_mlb.latest_feed` and the validation script `scripts/validate_mlb_ingestion.py`.
	- Add any missing schedules or game feeds via `scripts/download_mlb_bulk.py` (now includes jitter and retry logic).
	- **Optional RAG setup** – after the KB is populated, run `python3 scripts/ingest_kb_llamaindex.py` to build a LlamaIndex vector store for semantic search over the knowledge base.
	- **Optional RAG setup** – after the KB is populated, run `make kb` (or the individual scripts) to build a LlamaIndex vector store for semantic search over the knowledge base.
	- **Optional RAG setup** – after the KB is populated, run `make kb` (or the individual scripts) to build a LlamaIndex vector store for semantic search over the knowledge base.
	- For bulk/parallel execution, use `make kb_parallel` which runs the scrape, download, and web‑search steps concurrently before optional ingestion.

## 2. Implement Real‑Time Query Progress Monitoring
- Deploy the FastAPI endpoint (`scripts/query_monitor.py`) that surfaces `pg_stat_activity` and `mlb.query_progress`.
- (Optional) Install the `pg_progress` extension and wrap long‑running PL/pgSQL functions with `pg_progress_start/end`.
- Add a dashboard widget in `baseball-chatbot-ui` to poll `/progress` and display a progress bar.

## 3. Finalise EdgeForge Modeling Pipeline
- Train the ensemble model (`scripts/train_edgeforge_model.py`).
- Run backtesting (`scripts/edgeforge_backtest.py`) and store results in `features` tables.
- Create stored procedures for batch predictions (`sql/160_edgeforge_predict.sql`).

## 4. Content Monetisation Studio
- Implement the content generation chain (`scripts/generate_content.py`).
- Add API routes for newsletters, Discord posts, and dashboard exports.
- Define pricing tiers and subscription management in the `subscriptions` schema.

## 5. Documentation & Issue Tracking
- Keep the `github_issues/` folder up‑to‑date with concrete issue tickets.
- Link each issue to the relevant documentation section.
- Review and close issues as work is completed.
- **Model Training Pipeline**: Hyper‑parameter sweep for `pa_batter_hit` completed; see [`github_issues/issue_06_model_training_pipeline.md`](github_issues/issue_06_model_training_pipeline.md).

---
*This document serves as a living roadmap; update it as priorities shift.*
