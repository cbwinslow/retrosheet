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

## Consolidation Summary

The following documentation consolidation was performed in April 2026:

- 2 files archived (outdated/superseded)
- 2 files retained with notes (historical context/operational value)
- No files deleted (all archived files remain in repository for historical reference)

## Guidelines for Future Documentation

When creating new documentation:

1. Check if the content fits into existing canonical docs (especially docs/agents/)
2. Use docs/agents/PROCEDURES.md for canonical workflows
3. Use docs/agents/FILE_INVENTORY.md for file inventory
4. Archive outdated docs rather than deleting them
5. Update this ARCHIVED_DOCUMENTATION.md when archiving files
