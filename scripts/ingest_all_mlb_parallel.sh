#!/bin/bash
# MLB Data Ingestion Scheduler
# Downloads and transforms MLB data for multiple seasons in parallel

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

# Seasons to process (2020-2022, 2024-2025 for initial batch)
SEASONS=(2020 2021 2022 2024 2025)

# Maximum parallel processes
MAX_PARALLEL=3

echo "🚀 Starting MLB Data Ingestion for ${#SEASONS[@]} seasons"
echo "📅 Seasons: ${SEASONS[*]}"
echo "⚡ Max parallel processes: $MAX_PARALLEL"
echo "=========================================="

# Function to process a single season
process_season() {
    local season=$1
    echo "🏏 Starting season $season at $(date)"

    # Download schedules
    echo "📅 Downloading schedules for $season..."
    if python3 scripts/download_mlb_bulk.py --start-season $season --end-season $season --mode schedules --workers 8 --delay 0.5; then
        echo "✅ Schedules downloaded for $season"
    else
        echo "❌ Failed to download schedules for $season"
        return 1
    fi

    # Download game feeds
    echo "🎮 Downloading game feeds for $season..."
    if python3 scripts/download_mlb_bulk.py --start-season $season --end-season $season --mode games --workers 8 --delay 0.5; then
        echo "✅ Game feeds downloaded for $season"
    else
        echo "❌ Failed to download game feeds for $season"
        return 1
    fi

    # Transform data
    echo "🔄 Transforming data for $season..."
    if python3 scripts/ingest_all_mlb_data.py --seasons $season --transform-only; then
        echo "✅ Data transformed for $season"
    else
        echo "❌ Failed to transform data for $season"
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