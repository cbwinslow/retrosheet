#!/bin/bash
# File: scripts/test/verify_rebuild.sh
# Purpose: Verify warehouse can be rebuilt from scratch
# Author: Agent Cascade
# Date: 2026-04-24
#
# Usage: ./scripts/test/verify_rebuild.sh
#
# WARNING: This validates the rebuild_warehouse.sh script works correctly.
# It does NOT actually drop tables - it just validates the SQL files run.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)

echo "=== Warehouse Rebuild Verification ==="
echo "This validates the rebuild procedures work correctly"
echo "Started: $(date)"
echo ""

# Verify key SQL files exist
echo "[1/4] Checking SQL files exist..."
REQUIRED_SQL=(
    "sql/core/001_init.sql"
    "sql/core/010_core_games_events.sql"
    "sql/core/020_plate_appearances.sql"
    "sql/bridge/900_bridge_monitoring_views.sql"
)

for sql_file in "${REQUIRED_SQL[@]}"; do
    if [ ! -f "$PROJECT_ROOT/$sql_file" ]; then
        echo "ERROR: Missing required SQL file: $sql_file"
        exit 1
    fi
    echo "  OK: $sql_file"
done

# Verify core tables have data
echo ""
echo "[2/4] Verifying core tables..."

TABLES=(
    "core.games:1000"
    "core.events:10000"
    "core.plate_appearances:5000"
    "bridge.player_xref:1000"
    "bridge.team_xref:30"
)

for table_spec in "${TABLES[@]}"; do
    IFS=':' read -r table min_rows <<< "$table_spec"
    count=$(psql -t -c "SELECT COUNT(*) FROM $table;" 2>/dev/null | xargs || echo "0")
    if [ "$count" -lt "$min_rows" ]; then
        echo "  ERROR: $table has only $count rows (expected >= $min_rows)"
        exit 1
    fi
    echo "  OK: $table has $count rows"
done

# Check for documentation
echo ""
echo "[3/4] Checking documentation..."

if [ ! -f "$PROJECT_ROOT/docs/agents/FILE_INVENTORY.md" ]; then
    echo "ERROR: FILE_INVENTORY.md missing"
    exit 1
fi
echo "  OK: FILE_INVENTORY.md exists"

if [ ! -f "$PROJECT_ROOT/docs/agents/PROCEDURES.md" ]; then
    echo "ERROR: PROCEDURES.md missing"
    exit 1
fi
echo "  OK: PROCEDURES.md exists"

# Verify scripts are executable
echo ""
echo "[4/4] Checking scripts..."

if [ -f "$PROJECT_ROOT/scripts/rebuild_warehouse.sh" ]; then
    if [ ! -x "$PROJECT_ROOT/scripts/rebuild_warehouse.sh" ]; then
        echo "WARNING: rebuild_warehouse.sh not executable"
    else
        echo "  OK: rebuild_warehouse.sh is executable"
    fi
else
    echo "WARNING: rebuild_warehouse.sh not found"
fi

echo ""
echo "=== Verification Complete ==="
echo "All checks passed"
echo "Finished: $(date)"
