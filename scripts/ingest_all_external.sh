#!/usr/bin/env bash
# =============================================================================
# Master script to ingest all free external data sources.
# =============================================================================
# Usage:
#   ./scripts/ingest_all_external.sh
# =============================================================================

set -euo pipefail

echo "=== Ingest Lahman CSVs ==="
# Adjust the path to where you have the Lahman CSVs downloaded
LAHMAN_DIR="${HOME}/data/lahman_csv"
python3 scripts/external_data/load_lahman.py --dir "$LAHMAN_DIR"

echo "=== Ingest Baseball‑Reference game logs ==="
BR_DIR="${HOME}/data/br_game_logs"
python3 scripts/external_data/load_baseball_reference.py --dir "$BR_DIR"

# Skipping Fangraphs ingestion pending valid CSV files
# echo "=== Ingest Fangraphs CSVs ==="
# FG_PLAYER="${HOME}/data/fangraphs_player_season.csv"
# FG_TEAM="${HOME}/data/fangraphs_team_season.csv"
# python3 scripts/external_data/load_fangraphs.py --player "$FG_PLAYER" --team "$FG_TEAM"

echo "=== Ingest Statcast park factors ==="
PF_CSV="${HOME}/data/park_factors.csv"
python3 scripts/external_data/load_park_factors.py --file "$PF_CSV"

echo "=== Fetch current MLB rosters (snapshot today) ==="
TODAY=$(date +%F)
python3 scripts/fetch_mlb_rosters.py --date "$TODAY"

echo "=== Skipping weather fetch (network timeout) ==="

echo "=== All external data sources ingested ==="