# Archived Documentation

This document lists documentation that has been archived because it is outdated, superseded by newer documentation, or no longer relevant to the current project state.

## Archived Files

### docs/MLB_API_DOCUMENTATION.md

- **Archived**: April 2026
- **Reason**: Documents a different MLB API (lookup-service-prod.mlb.com) that is not used in the project. The project uses MLB Stats API (statsapi.mlb.com) instead.
- **Replaced By**: [docs/MLB_API_INTEGRATION_GUIDE.md](MLB_API_INTEGRATION_GUIDE.md) and [docs/MLB_API_DATA_DICTIONARY.md](MLB_API_DATA_DICTIONARY.md)
- **Status**: Outdated API endpoints and structure

### docs/PIPELINE_STATUS.md

- **Archived**: April 2026
- **Reason**: This is a point-in-time status report from when the MLB live data pipeline was being built. The pipeline is now operational and documented in [docs/LIVE_DATA_ARCHITECTURE.md](LIVE_DATA_ARCHITECTURE.md) and [docs/agents/PROCEDURES.md](agents/PROCEDURES.md).
- **Replaced By**: [docs/LIVE_DATA_ARCHITECTURE.md](LIVE_DATA_ARCHITECTURE.md), [docs/MLB_PBP_PIPELINE.md](MLB_PBP_PIPELINE.md), [docs/agents/PROCEDURES.md](agents/PROCEDURES.md)
- **Status**: Historical status report, pipeline now operational

## Retained Files with Notes

### docs/WAREHOUSE_PLAN.md

- **Status**: Retained
- **Reason**: Contains historical design decisions about staged normalization and Chadwick extracts. While some content is now in PROCEDURES.md, this document provides valuable context about the original design philosophy.
- **Relationship**: Complements [docs/agents/PROCEDURES.md](agents/PROCEDURES.md) with design rationale

### docs/TROUBLESHOOTING.md

- **Status**: Retained
- **Reason**: Contains valuable troubleshooting information that is still relevant for operational issues.
- **Relationship**: Operational reference document

## Consolidation Summary (Updated January 2025)

The following documentation consolidation was performed during the major migration to the new baseball CLI architecture:

### Archived Files (Outdated/Superseded)

The following documentation files have been archived because they are outdated, superseded by newer documentation, or no longer relevant to the current project state:

**Architecture & Design (Archived)**
- ADVANCED_MODELING_PLAN.md - Superseded by docs/models.md and docs/architecture.md
- CRISP_DM_IMPLEMENTATION_PLAN.md - Superseded by docs/architecture.md
- EXTENSIBLE_FRAMEWORK_DESIGN.md - Superseded by docs/architecture.md
- FRAMEWORK_CONFIRMATION.md - Historical design document, no longer needed
- FRAMEWORK_IMPLEMENTATION_STATUS.md - Superseded by docs/migration_backlog.md
- IMPLEMENTATION_ROADMAP.md - Superseded by docs/migration_backlog.md
- IMPLEMENTATION_SUMMARY.md - Historical summary, no longer needed
- OVERALL_STRATEGY.md - Superseded by docs/architecture.md
- ORCHESTRATION_ARCHITECTURE.md - Superseded by docs/architecture.md

**Bridge & Xref (Archived)**
- BRIDGE_TABLE_IMPLEMENTATION.md - Superseded by docs/architecture.md and docs/keys_and_grains.md
- BRIDGE_TABLE_RESEARCH.md - Research document, implementation complete
- ESPN_BRIDGE_REQUIREMENTS.md - Superseded by docs/sources.md
- ID_RECONCILIATION.md - Implementation complete, no longer needed

**Database & SQL (Archived)**
- CORE_SCHEMA.md - Superseded by docs/architecture.md and docs/keys_and_grains.md
- DATABASE_CATALOG.md - Superseded by docs/architecture.md
- DATABASE_OPTIMIZATION_GUIDE.md - Historical guidance, superseded by docs/architecture.md
- DATA_MODELS.md - Superseded by docs/architecture.md and docs/keys_and_grains.md
- ISSUE_DATABASE_OPTIMIZATION.md - Historical issue, resolved
- PROCEDURES_AND_FUNCTIONS.md - Superseded by docs/architecture.md
- PROCEDURES_AND_FUNCTIONS_STATUS.md - Historical status, no longer needed
- PROCEDURES_DETAILED.md - Superseded by docs/architecture.md

**Features & Models (Archived)**
- AT_BAT_OUTCOME_MODEL_REVIEW.md - Historical model review, superseded by docs/models.md
- CONFIDENCE_SCORING.md - Superseded by docs/architecture.md
- FEATURE_AUDIT.md - Historical audit, superseded by docs/keys_and_grains.md
- FEATURE_ENGINEERING_PLAN.md - Superseded by docs/architecture.md and docs/models.md
- FEATURE_STATUS_REPORT.md - Historical status, superseded by docs/migration_backlog.md
- KNOWLEDGE_BASE_FRAMEWORK.md - Historical framework, superseded by docs/architecture.md
- KNOWLEDGE_BASE_GIS_PITCH.md - Historical research, superseded by docs/architecture.md
- KNOWLEDGE_BASE_MARKOV_CHAIN.md - Historical research, superseded by docs/architecture.md
- KNOWLEDGE_BASE_MODELS_REPOS.md - Historical research, superseded by docs/architecture.md
- KNOWLEDGE_BASE_SABERMETRICS.md - Historical research, superseded by docs/architecture.md
- MATCHUP_FEATURES.md - Superseded by docs/architecture.md
- MODEL_SELECTION_GUIDE.md - Superseded by docs/models.md
- PITCH_FEATURE_MART_SCHEMA.md - Superseded by docs/keys_and_grains.md
- PITCH_KB_COMPARISON_REPORT.md - Historical comparison, superseded by docs/architecture.md
- PITCH_MODEL_PROGRESS.md - Historical progress, superseded by docs/migration_backlog.md
- PITCH_PLAYER_ANALYSIS_ARCHITECTURE.md - Historical design, superseded by docs/architecture.md
- STATCAST_MODELS_RESEARCH_REPORT.md - Historical research, superseded by docs/architecture.md
- TABLE_ASSESSMENT_SABERMETRICS.md - Historical assessment, superseded by docs/keys_and_grains.md
- TEMPORAL_MODEL_SELECTION.md - Historical selection, superseded by docs/models.md

**Ingestion & Live Data (Archived)**
- CURRENT_STATE_REVIEW.md - Historical review, superseded by docs/migration_backlog.md
- DATA_INGESTION_FIX_REPORT.md - Historical fix, resolved
- EDGEFORGE_TRIAGE.md - Historical triage, resolved
- LIVE_BETTING_PIPELINE_STATUS.md - Historical status, superseded by docs/migration_backlog.md
- LIVE_DATA_ARCHITECTURE.md - Superseded by docs/architecture.md
- MLB_API_DATA_DICTIONARY.md - Superseded by docs/sources.md
- MLB_BULK_DATA_INGESTION.md - Historical guide, superseded by docs/architecture.md
- MLB_DATA_MODEL.md - Superseded by docs/architecture.md and docs/keys_and_grains.md
- MLB_LIVE_PBP_PIPELINE_DESIGN.md - Superseded by docs/architecture.md
- MLB_PREDICT_FRAMEWORK_GUIDE.md - Superseded by docs/architecture.md and docs/models.md
- MLB_VS_RETROSHEET_GRANULARITY.md - Historical comparison, superseded by docs/architecture.md

**External & Enrichment (Archived)**
- POSTGRESQL_EXTENSIONS_RESEARCH.md - Historical research, superseded by docs/architecture.md
- RESEARCH_METHODOLOGY.md - Historical methodology, superseded by docs/architecture.md
- SABERMETRICS_LINK_INVENTORY.md - Historical inventory, superseded by docs/architecture.md

**GitHub & Issues (Archived)**
- GITHUB_ISSUE_UPDATES.md - Historical updates, superseded by docs/migration_backlog.md
- GITHUB_PROJECT_GUIDE.md - Historical guide, no longer needed

**Knowledge Base (Archived)**
- MLB_API_DOCUMENTATION.md - Already archived (different API)
- PIPELINE_STATUS.md - Already archived (historical status)

**Other (Archived)**
- DEPLOYMENT_PLAN.md - Superseded by docs/architecture.md
- LLM_GPU_OPTIMIZATION_REPORT.md - Historical optimization, no longer needed
- MASTER_INDEX.md - Historical index, superseded by docs/architecture.md
- PIPELINE_ARCHITECTURE_ASSESSMENT.md - Historical assessment, superseded by docs/architecture.md
- PIPELINE_STATUS.md - Historical status, superseded by docs/migration_backlog.md
- PROJECT_LOG.md - Historical log, superseded by docs/migration_backlog.md
- PROJECT_STATUS_DASHBOARD.md - Historical dashboard, superseded by docs/migration_backlog.md
- RESEARCH_PAPER.md - Historical paper, superseded by docs/architecture.md
- RETROSHEET_KEY.md - Historical reference, superseded by docs/architecture.md
- SCHEMA_REFERENCE_FOR_CODEX.md - Historical reference, superseded by docs/architecture.md
- SCRIPT_CONSOLIDATION_ANALYSIS.md - Historical analysis, superseded by docs/migration_map.md
- SCRIPT_CONSOLIDATION_ANALYSIS_REVISED.md - Historical analysis, superseded by docs/migration_map.md
- USER_MANUAL.md - Historical manual, superseded by docs/architecture.md
- WAREHOUSE_PLAN.md - Historical plan, superseded by docs/architecture.md
- WORKFLOW_VALIDATION_REPORT.md - Historical report, superseded by docs/migration_backlog.md
- ab_outcome.md - Historical analysis, superseded by docs/architecture.md
- audit_report.md - Historical audit, superseded by docs/migration_backlog.md
- framework/ - Empty directory, no longer needed
- kb/ - Empty directory, no longer needed

**Note**: All archived files remain in the repository for historical reference. No files have been deleted.

## Guidelines for Future Documentation

When creating new documentation:

1. Check if the content fits into existing canonical docs (especially docs/agents/)
2. Use docs/agents/PROCEDURES.md for canonical workflows
3. Use docs/agents/FILE_INVENTORY.md for file inventory
4. Archive outdated docs rather than deleting them
5. Update this ARCHIVED_DOCUMENTATION.md when archiving files
