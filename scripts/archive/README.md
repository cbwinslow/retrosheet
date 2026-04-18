# Archived Prototype Scripts

This directory contains prototype scripts that have been frozen and are not part of the canonical warehouse workflow.

## simulate_half_inning.py

**Status:** Archived - Frozen Prototype

**Reason for Archiving:**
- This half-inning Monte Carlo simulator is a prototype that has not been validated for correct baseball state transitions
- Per AGENTS.md and docs/EDGEFORGE_TRIAGE.md, prototype code must be frozen until it is properly validated and integrated into canonical layers
- The canonical simulation approach should be built using validated baseball state transition rules and integrated through the `predictions` layer

**Next Steps for Reactivation:**
1. Validate baseball state transition logic against official Retrosheet/MLB rules
2. Add comprehensive unit tests for all state transitions
3. Integrate with canonical `predictions` schema and logging infrastructure
4. Document the approach in docs/agents/PROCEDURES.md
5. Get approval from the canonical architecture review before re-integrating

**Archived Date:** 2026-04-17
**Archived By:** Phase 4.1 of MLB PBP Pipeline Refactor

## fast_prediction_service.py

**Status:** Archived - Frozen Prototype

**Reason for Archiving:**
- This prediction service is a prototype that predates the canonical live prediction logging infrastructure
- Per AGENTS.md and Phase 3.1 completion, all live predictions must now go through `predictions.live_pa_predictions` with proper feature snapshots, state snapshots, and request tracking
- The canonical live inference path uses `predict_live_pa_outcome_distribution.py` with normalized output and durable logging

**Next Steps for Reactivation:**
1. Integrate with canonical `predictions.live_pa_predictions` logging schema
2. Use normalized output format from `predict_live_pa_outcome_distribution.py`
3. Add proper request tracking via `predictions.api_prediction_requests`
4. Document the service architecture in docs/agents/PROCEDURES.md
5. Get approval from the canonical architecture review before re-integrating

**Archived Date:** 2026-04-17
**Archived By:** Phase 4.2 of MLB PBP Pipeline Refactor
