#!/usr/bin/env bash
#
# File: scripts/populate_all_missing_data.sh
# Purpose: Master script to populate ALL empty tables
# Author: Agent Cascade
# Date: 2026-04-25
# Usage: ./scripts/populate_all_missing_data.sh --season 2025
#
# This populates:
# - mlb.players (from MLB API)
# - mlb.venues (from MLB API) - CRITICAL for park context
# - core.live_plate_appearances (from live_feed)
# - raw_espn.player_stats_snapshots
# - raw_espn.team_stats_snapshots
# - raw_espn.plays_snapshots
# - raw_baseball_reference.game_logs
# - raw_mlb.*_snapshots (boxscore, PBP, pitch_metrics, etc.)
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SEASON=${SEASON:-2025}
DRY_RUN=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --season)
            SEASON="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN="--dry-run"
            shift
            ;;
        --help)
            echo "Usage: $0 [--season YEAR] [--dry-run]"
            echo ""
            echo "Options:"
            echo "  --season YEAR   Season to fetch (default: 2025)"
            echo "  --dry-run       Show what would be done without doing it"
            echo "  --help          Show this help"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

echo "======================================================================"
echo "POPULATING ALL MISSING DATA - Season ${SEASON}"
echo "======================================================================"
if [[ -n "$DRY_RUN" ]]; then
    echo "MODE: DRY RUN (no changes will be made)"
fi
echo ""

# Step 1: Populate mlb.players and mlb.venues (CRITICAL for park context)
echo "[1/7] Populating mlb.players and mlb.venues..."
echo "      This is CRITICAL for features_pitch.mv_park_context to work!"
uv run python "${SCRIPT_DIR}/bridge/populate_mlb_players_venues_complete.py" \
    --season "${SEASON}" \
    ${DRY_RUN}

# Step 2: Link MLB venues to Retrosheet parks
echo ""
echo "[2/7] Linking MLB venues to Retrosheet parks..."
if [[ -z "$DRY_RUN" ]]; then
    uv run python "${SCRIPT_DIR}/bridge/populate_mlb_players_venues_complete.py" \
        --season "${SEASON}" \
        --skip-players \
        --skip-venues \
        --link-parks
fi

# Step 3: Populate live_plate_appearances
echo ""
echo "[3/7] Populating core.live_plate_appearances..."
uv run python "${SCRIPT_DIR}/bridge/populate_live_plate_appearances.py" \
    --season "${SEASON}" \
    ${DRY_RUN}

# Step 4: Fetch ESPN data
echo ""
echo "[4/7] Fetching ESPN player/team stats and plays..."
uv run python "${SCRIPT_DIR}/data_ingestion/fetch_espn_complete.py" \
    --season "${SEASON}" \
    ${DRY_RUN}

# Step 5: Fetch MLB Stats API data
echo ""
echo "[5/7] Fetching MLB Stats API data (boxscore, PBP, pitch metrics, etc.)..."
uv run python "${SCRIPT_DIR}/data_ingestion/fetch_mlb_stats_api_complete.py" \
    --season "${SEASON}" \
    ${DRY_RUN}

# Step 6: Fetch Baseball-Reference data (if pybaseball available)
echo ""
echo "[6/7] Fetching Baseball-Reference game logs..."
if command -v python &> /dev/null; then
    if python -c "import pybaseball" 2>/dev/null; then
        uv run python "${SCRIPT_DIR}/data_ingestion/fetch_baseball_reference_complete.py" \
            --season "${SEASON}" \
            ${DRY_RUN}
    else
        echo "      SKIPPED: pybaseball not installed"
        echo "      Install: uv add pybaseball"
    fi
else
    echo "      SKIPPED: Python not available"
fi

# Step 7: Load Lahman data (if not already loaded)
echo ""
echo "[7/7] Loading Lahman Baseball Database..."
if [[ -d "${SCRIPT_DIR}/../data/lahman_csv" ]]; then
    uv run python "${SCRIPT_DIR}/external_data/load_lahman_complete.py" \
        --dir "${SCRIPT_DIR}/../data/lahman_csv" \
        ${DRY_RUN}
else
    echo "      SKIPPED: data/lahman_csv directory not found"
    echo "      Download: python scripts/data_ingestion/download_lahman_data.py"
fi

# Summary
echo ""
echo "======================================================================"
echo "SUMMARY - All tables should now have data"
echo "======================================================================"

if [[ -z "$DRY_RUN" ]]; then
    psql retrosheet -c "
        SELECT 
            schemaname,
            relname as table_name,
            n_live_tup as row_count
        FROM pg_stat_user_tables
        WHERE schemaname IN ('mlb', 'core', 'raw_espn', 'raw_mlb', 'raw_baseball_reference')
        AND relname IN (
            'players', 'venues', 'live_plate_appearances',
            'player_stats_snapshots', 'team_stats_snapshots', 'plays_snapshots',
            'game_logs', 'boxscore_snapshots', 'play_by_play_snapshots'
        )
        ORDER BY schemaname, relname;
    "
fi

echo ""
echo "======================================================================"
echo "Next steps:"
echo "  1. Verify mv_park_context has data (should now work with venues)"
echo "  2. Check all empty tables are now populated"
echo "  3. Run feature population scripts if needed"
echo "======================================================================"
