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
python3 scripts/warehouse.py fetch-retrosheet
python3 scripts/warehouse.py init-db
python3 scripts/warehouse.py extract-chadwick --years "$YEARS" --outputs all
python3 scripts/warehouse.py load-chadwick --years "$YEARS" --outputs all

psql -h "$PGHOST" -p "$PGPORT" -d "$PGDATABASE" -v ON_ERROR_STOP=1 -f sql/010_core_games_events.sql
psql -h "$PGHOST" -p "$PGPORT" -d "$PGDATABASE" -v ON_ERROR_STOP=1 -f sql/020_plate_appearances.sql
psql -h "$PGHOST" -p "$PGPORT" -d "$PGDATABASE" -v ON_ERROR_STOP=1 -f sql/090_mlb_live_data.sql
psql -h "$PGHOST" -p "$PGPORT" -d "$PGDATABASE" -v ON_ERROR_STOP=1 -f sql/100_bridge_tables.sql
psql -h "$PGHOST" -p "$PGPORT" -d "$PGDATABASE" -v ON_ERROR_STOP=1 -f sql/110_live_core_tables.sql
python3 scripts/load_reference_metadata.py
python3 scripts/load_auxiliary_retrosheet.py

psql -h "$PGHOST" -p "$PGPORT" -d "$PGDATABASE" -v ON_ERROR_STOP=1 -f sql/050_feature_marts.sql
psql -h "$PGHOST" -p "$PGPORT" -d "$PGDATABASE" -v ON_ERROR_STOP=1 -f sql/060_advanced_feature_marts.sql
psql -h "$PGHOST" -p "$PGPORT" -d "$PGDATABASE" -v ON_ERROR_STOP=1 -f sql/070_temporal_and_production_marts.sql
psql -h "$PGHOST" -p "$PGPORT" -d "$PGDATABASE" -v ON_ERROR_STOP=1 -f sql/076_plate_appearance_outcome_model.sql
psql -h "$PGHOST" -p "$PGPORT" -d "$PGDATABASE" -v ON_ERROR_STOP=1 -f sql/080_half_inning_examples.sql
psql -h "$PGHOST" -p "$PGPORT" -d "$PGDATABASE" -v ON_ERROR_STOP=1 -f sql/120_inference_optimization.sql
psql -h "$PGHOST" -p "$PGPORT" -d "$PGDATABASE" -v ON_ERROR_STOP=1 -f sql/121_inference_functions.sql

echo "Warehouse rebuild complete."
