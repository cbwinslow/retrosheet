#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

YEARS="${YEARS:-2000-2025}"
PGHOST="${PGHOST:-localhost}"
PGPORT="${PGPORT:-5432}"
PGDATABASE="${PGDATABASE:-retrosheet}"

echo "Rebuilding Retrosheet warehouse for years: ${YEARS}"
echo "Database: ${PGHOST}:${PGPORT}/${PGDATABASE}"

python3 scripts/warehouse.py check-deps
# By default, skip the large Retrosheet download to preserve existing raw data.
# To force a fresh download, set FETCH_RETROSHEET=1 before running.
if [ -n "${FETCH_RETROSHEET:-}" ]; then
  echo "[info] FETCH_RETROSHEET is set – downloading Retrosheet data."
  python3 scripts/warehouse.py fetch-retrosheet
else
  echo "[info] Skipping Retrosheet download (default). Set FETCH_RETROSHEET=1 to re-download."
fi
python3 scripts/warehouse.py init-db
python3 scripts/warehouse.py extract-chadwick --years "$YEARS" --outputs all
python3 scripts/warehouse.py load-chadwick --years "$YEARS" --outputs all

psql -h "$PGHOST" -p "$PGPORT" -d "$PGDATABASE" -v ON_ERROR_STOP=1 -f sql/010_core_games_events.sql
psql -h "$PGHOST" -p "$PGPORT" -d "$PGDATABASE" -v ON_ERROR_STOP=1 -f sql/020_plate_appearances.sql
psql -h "$PGHOST" -p "$PGPORT" -d "$PGDATABASE" -v ON_ERROR_STOP=1 -f sql/090_mlb_live_data.sql
psql -h "$PGHOST" -p "$PGPORT" -d "$PGDATABASE" -v ON_ERROR_STOP=1 -f sql/091_mlb_reference_raw.sql
psql -h "$PGHOST" -p "$PGPORT" -d "$PGDATABASE" -v ON_ERROR_STOP=1 -f sql/095_mlb_reference_views.sql
psql -h "$PGHOST" -p "$PGPORT" -d "$PGDATABASE" -v ON_ERROR_STOP=1 -f sql/100_bridge_tables.sql
psql -h "$PGHOST" -p "$PGPORT" -d "$PGDATABASE" -v ON_ERROR_STOP=1 -f sql/110_live_core_tables.sql
python3 scripts/load_reference_metadata.py
python3 scripts/load_auxiliary_retrosheet.py

psql -h "$PGHOST" -p "$PGPORT" -d "$PGDATABASE" -v ON_ERROR_STOP=1 -f sql/050_feature_marts.sql
psql -h "$PGHOST" -p "$PGPORT" -d "$PGDATABASE" -v ON_ERROR_STOP=1 -f sql/060_advanced_feature_marts.sql
psql -h "$PGHOST" -p "$PGPORT" -d "$PGDATABASE" -v ON_ERROR_STOP=1 -f sql/070_temporal_and_production_marts.sql
psql -h "$PGHOST" -p "$PGPORT" -d "$PGDATABASE" -v ON_ERROR_STOP=1 -f sql/075_interface_workflows.sql
psql -h "$PGHOST" -p "$PGPORT" -d "$PGDATABASE" -v ON_ERROR_STOP=1 -f sql/076_plate_appearance_outcome_model.sql
psql -h "$PGHOST" -p "$PGPORT" -d "$PGDATABASE" -v ON_ERROR_STOP=1 -f sql/077_pitch_sequence_model.sql
psql -h "$PGHOST" -p "$PGPORT" -d "$PGDATABASE" -v ON_ERROR_STOP=1 -f sql/078_plate_appearance_outcome_grouped.sql
psql -h "$PGHOST" -p "$PGPORT" -d "$PGDATABASE" -v ON_ERROR_STOP=1 -f sql/079_probability_evaluation_reports.sql
psql -h "$PGHOST" -p "$PGPORT" -d "$PGDATABASE" -v ON_ERROR_STOP=1 -f sql/081_probability_calibration_artifacts.sql
psql -h "$PGHOST" -p "$PGPORT" -d "$PGDATABASE" -v ON_ERROR_STOP=1 -f sql/082_count_state_feature_marts.sql
psql -h "$PGHOST" -p "$PGPORT" -d "$PGDATABASE" -v ON_ERROR_STOP=1 -f sql/080_half_inning_examples.sql
psql -h "$PGHOST" -p "$PGPORT" -d "$PGDATABASE" -v ON_ERROR_STOP=1 -f sql/120_inference_optimization.sql
psql -h "$PGHOST" -p "$PGPORT" -d "$PGDATABASE" -v ON_ERROR_STOP=1 -f sql/121_inference_functions.sql
psql -h "$PGHOST" -p "$PGPORT" -d "$PGDATABASE" -v ON_ERROR_STOP=1 -f sql/122_live_pa_feature_parity.sql
psql -h "$PGHOST" -p "$PGPORT" -d "$PGDATABASE" -v ON_ERROR_STOP=1 -f sql/130_analysis_views.sql

echo "Warehouse rebuild complete."

# Start the FastAPI query monitor in the background (non‑blocking).
# This provides real‑time visibility into any long‑running queries that may be
# triggered by subsequent operations (e.g., model training, data ingestion).
# The monitor runs on port 8000 and binds to all interfaces.
nohup uvicorn scripts.query_monitor:app --host 0.0.0.0 --port 8000 >/dev/null 2>&1 &
