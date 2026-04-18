# Archived SQL Files

This directory contains SQL files that have been archived from the main `sql/` directory.

## Archived Files

### sql/092_live_odds_views.sql
**Archived:** 2026-04-17

**Purpose:** Prototype materialized views for hit and strikeout odds derived from `features.play_snapshot`.

**Reason for archival:**
- These views were experimental odds calculations that predate the canonical prediction infrastructure
- The canonical path for odds calculations should use the calibrated prediction outputs from `predict_pa_outcome_distribution.py`
- These views were never validated against historical data or integrated into the live prediction logging system

**Reactivation steps:**
1. Validate odds calculations against historical Retrosheet data
2. Integrate with canonical live prediction logging (sql/083_live_prediction_logging.sql)
3. Replace with calibrated probability outputs from the canonical prediction serving path
4. Document in docs/agents/PROCEDURES.md before use in production

### sql/121_inference_functions_legacy.sql
**Archived:** 2026-04-17

**Purpose:** Placeholder inference functions for fast batch predictions and simulation state management.

**Reason for archival:**
- `predict_plate_appearance_batch()` returns mock data instead of real predictions
- Simulation state management was never validated against Retrosheet data
- Functions predate the canonical live prediction logging infrastructure
- Python-based prediction scripts (predict_pa_outcome_distribution.py) are the canonical serving path

**Reactivation steps:**
1. Replace mock predictions with actual Python model integration
2. Validate simulation state transitions against historical Retrosheet data
3. Integrate with canonical live prediction logging (sql/083_live_prediction_logging.sql)
4. Document in docs/agents/PROCEDURES.md before use in production

**Archived Date:** 2026-04-17
**Archived By:** Phase 6.1 of MLB PBP Pipeline Refactor
