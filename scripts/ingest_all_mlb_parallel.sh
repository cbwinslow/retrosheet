#!/bin/bash
# MLB Data Ingestion Scheduler - Wrapper for baseball CLI
# Downloads and transforms MLB data for multiple seasons in parallel
#
# This script is a wrapper around: baseball pipeline run mlb_parallel

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

# Seasons to process
SEASONS=(2020 2021 2022 2024 2025)

# Maximum parallel processes
MAX_PARALLEL=3

echo "🚀 MLB Data Ingestion (Parallel) - baseball CLI Wrapper"
echo "📅 Seasons: ${SEASONS[*]}"
echo "⚡ Max parallel processes: $MAX_PARALLEL"
echo "=========================================="
echo "Note: This wrapper calls baseball mlb download/ingest commands"
echo ""

# Check if baseball CLI is available
if ! command -v baseball &> /dev/null; then
    echo "❌ baseball CLI not found. Installing..."
    if [ -f "pyproject.toml" ]; then
        pip install -e .
    else
        echo "❌ Cannot install baseball CLI. Please run: pip install -e ."
        exit 1
    fi
fi

# Function to process a single season via baseball CLI
process_season() {
    local season=$1
    echo "🏏 Starting season $season at $(date)"

    # Download data via baseball CLI
    echo "📅 Downloading data for $season..."
    if baseball mlb download --season $season; then
        echo "✅ Data downloaded for $season"
    else
        echo "❌ Failed to download data for $season"
        return 1
    fi

    # Ingest data via baseball CLI
    echo "🔄 Ingesting data for $season..."
    if baseball mlb ingest --season $season; then
        echo "✅ Data ingested for $season"
    else
        echo "❌ Failed to ingest data for $season"
        return 1
    fi

    echo "🎉 Season $season completed at $(date)"
    return 0
}

# Process seasons with limited parallelism
active_processes=0
season_index=0

while [ $season_index -lt ${#SEASONS[@]} ]; do
    # Check if we can start more processes
    while [ $active_processes -lt $MAX_PARALLEL ] && [ $season_index -lt ${#SEASONS[@]} ]; do
        season=${SEASONS[$season_index]}
        echo "🎯 Starting background process for season $season"

        # Start process in background
        (
            if process_season $season; then
                echo "✅ Season $season finished successfully"
            else
                echo "❌ Season $season failed"
            fi
        ) &

        active_processes=$((active_processes + 1))
        season_index=$((season_index + 1))

        # Small delay between starting processes
        sleep 2
    done

    # Wait for any process to finish
    if [ $active_processes -gt 0 ]; then
        wait -n 2>/dev/null || true
        active_processes=$((active_processes - 1))
    fi

    # Progress update
    completed=$((season_index - active_processes))
    echo "📊 Progress: $completed/${#SEASONS[@]} seasons completed, $active_processes active"

    # Brief pause
    sleep 5
done

# Wait for all remaining processes
echo "⏳ Waiting for final processes to complete..."
wait

echo "🎉 All MLB data ingestion completed!"
echo "📈 Final statistics:"
psql -d retrosheet -c "
SELECT
    (SELECT COUNT(*) FROM raw_mlb.schedule_snapshots) as total_schedules,
    (SELECT COUNT(*) FROM raw_mlb.live_feed_snapshots) as total_game_feeds,
    (SELECT COUNT(*) FROM core.live_games) as total_live_games,
    (SELECT COUNT(*) FROM core.live_events) as total_live_events,
    (SELECT COUNT(DISTINCT season) FROM raw_mlb.live_feed_snapshots WHERE season >= 2000) as seasons_with_data
"