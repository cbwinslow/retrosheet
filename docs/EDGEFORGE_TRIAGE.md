# EdgeForge Triage

This document records the current status of the untracked `EdgeForge` / MLB-enhanced files that appeared outside the documented canonical warehouse workflow.

## Decision

The project will keep a single canonical warehouse and modeling architecture:

\[
\text{raw\_retrosheet} \rightarrow \text{core} \rightarrow \text{features}
\]

\[
\text{raw\_mlb} \rightarrow \text{bridge} \rightarrow \text{core.live\_*} \rightarrow \text{analysis/features}
\]

The files reviewed here are **not canonical project state yet**. They are either:

1. product-direction notes worth keeping as documentation
2. experimental scripts worth mining for ideas
3. duplicate/parallel pipeline work that should not be adopted directly

Until rewritten into the documented architecture, none of these files should be treated as the official ingestion, feature-engineering, training, or deployment path.

## Classification Rules

### Canonical

A file is canonical only if it does all of the following:

- fits the documented schema layers in `AGENTS.md`
- is compatible with `scripts/rebuild_warehouse.sh` or an explicitly documented runtime workflow
- avoids creating a parallel warehouse or model registry
- is listed in `docs/agents/FILE_INVENTORY.md`

### Experimental

A file is experimental if it contains useful ideas but currently violates one or more of:

- schema ownership
- documented rebuild order
- reproducibility
- code quality / placeholder-output standards

### Product / Strategy Note

A file is a product note if it describes a future interface, agent persona, or commercialization direction without asserting itself as executable system truth.

## File-by-File Status

### Keep As Product / Strategy Notes

| File | Status | Reason |
|---|---|---|
| `docs/agents/EdgeForge.agent.md` | Product note | Useful as a future product persona for a commercial betting-intelligence layer, but not a warehouse or model-design source of truth. |

### Keep As Experimental Inputs, Not Canonical

| File | Status | Reason |
|---|---|---|
| `sql/mlb_win_probability_features.sql` | Experimental design | Contains useful ideas for MLB-only enhanced features, but creates a parallel `mlb_features` stack outside the canonical `features`/`analysis` layers. |
| `scripts/enhance_win_probability_model.py` | Experimental prototype | Useful feature ideas, but depends on parallel schemas and uses ad hoc table-building flow. |
| `scripts/edgeforge_enhanced_features.py` | Experimental prototype | Contains potentially useful Statcast/matchup feature concepts, but writes to `mlb_enhanced` and bypasses canonical schema ownership. |
| `scripts/extract_enhanced_features.py` | Experimental prototype | Same issue: feature concepts may be useful, implementation path is not canonical. |
| `scripts/train_edgeforge_model.py` | Experimental prototype | Separate model path outside `models.model_registry` and current trainer conventions. |
| `scripts/train_win_probability_model.py` | Experimental prototype | Separate win-probability trainer outside current model registry and evaluation conventions. |
| `scripts/complete_mlb_ingestion.py` | Experimental orchestration | Automates MLB historical ingestion, but outside `scripts/warehouse.py` and current documented live-bridge workflow. |
| `scripts/complete_mlb_ingestion.sh` | Experimental orchestration | Same issue as above. |
| `scripts/monitor_mlb_ingestion.sh` | Experimental monitoring | Potentially useful runbook/dashboard ideas, but tied to non-canonical schemas. |
| `scripts/populate_mlb_reference_data.py` | Experimental loader | Reference-data concept is useful, but target schemas and ownership are not aligned yet. |
| `scripts/setup_mlb_analytics.py` | Experimental analytics setup | Some views may be useful later, but currently assumes additional schemas and undocumented flows. |
| `scripts/edgeforge_dashboard.py` | Experimental dashboard | Interface idea is useful; current implementation depends on non-canonical objects. |
| `scripts/edgeforge_alerts.py` | Experimental operations tool | Useful product concept, but not tied to the documented warehouse status model. |
| `scripts/edgeforge_status.py` | Experimental operations tool | Same issue as above. |
| `scripts/demonstrate_enhanced_model.py` | Demo / throwaway experiment | Not a canonical training or evaluation asset. |
| `scripts/test_dashboard.py` | Experimental smoke test | Depends on non-canonical `mlb_enhanced` objects. |
| `scripts/download_missing_2023.py` | Experimental utility | May be useful for raw backfill logic, but should be folded into canonical `warehouse.py` / live ingestion workflows instead of kept separate. |

### Special Attention

| File | Status | Reason |
|---|---|---|
| `scripts/download_mlb_bulk.py` | Canonical utility | Promoted as the canonical historical MLB raw backfill tool after provenance/failure logging review. It belongs to the raw backfill workflow, not the EdgeForge parallel stack. |

## What To Reuse From These Files

The following ideas are worth extracting into the canonical architecture:

- MLB bulk historical backfill workflow
- raw schedule snapshot backfill utilities
- Statcast pitch-level enrichment from `raw_mlb.live_feed_snapshots`
- MLB reference entity backfill from raw payloads
- win-probability feature concepts that can map into canonical `features` objects
- operational dashboard / alert concepts for warehouse health

These ideas should be rewritten into:

- `raw_mlb`
- `bridge`
- `core.live_*`
- `analysis.*`
- `features.*`
- `models.model_registry`
- `predictions.*`

## What Not To Do

Do not do any of the following without an explicit architecture update:

- adopt `mlb_features`, `mlb_models`, or `mlb_enhanced` as official parallel stacks
- train production-style models outside `models.model_registry`
- create a second orchestration path that bypasses `scripts/warehouse.py` or the documented procedures
- present EdgeForge prototype outputs as validated model or warehouse truth

## Recommended Next Move

The next canonical integration step should be:

1. define one additive MLB advanced-feature design under the current warehouse layers
2. port only the useful concepts from the experimental EdgeForge files
3. discard or archive the rest after the canonical replacements exist

Separately, the current modeling-critical next step remains:

1. run the formal temporal sweep for `pa_outcome_distribution`
2. compare windows and half-lives on `2023-2025` validation
3. only then decide the default production-style temporal policy
