#!/usr/bin/env bash
set -euo pipefail

# Load environment (if any)
# source /home/cbwinslow/workspace/retrosheet/.env  # uncomment if .env exists

# Step 1: Initialize DB (idempotent)
python3 scripts/warehouse.py init-db

# Step 2: Load backtest view (if not already loaded)
psql -f sql/080_backtest_results.sql

# Step 3: Run model training with enriched feature set
python3 scripts/train_models.py --feature-set enriched

# Step 4: Verify that backtest view has data
row_count=$(psql -t -c "SELECT COUNT(*) FROM features.backtest_results;" | xargs)
if [[ "$row_count" -eq 0 ]]; then
  echo "E2E test failed: backtest_results view is empty"
  exit 1
fi

echo "E2E test passed: $row_count rows in backtest_results"
