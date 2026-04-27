#!/bin/bash
# Complete MLB Data Ingestion - Wrapper for baseball CLI
# Download all missing MLB seasons sequentially
#
# This script is a wrapper around: baseball pipeline run mlb_ingest

set -e

echo "🎯 Complete MLB Historical Data Ingestion"
echo "=========================================="
echo "📊 Target: MLB seasons 2000-2019"
echo "🎲 Method: Sequential processing via baseball CLI"
echo ""
echo "Note: This wrapper calls: baseball pipeline run mlb_historical"
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

# Get missing seasons
echo -e "\n📋 Checking missing seasons..."
MISSING_SEASONS=$(psql -d retrosheet -t -c "
SELECT string_agg(missing_season::text, ' ')
FROM (
    SELECT generate_series as missing_season
    FROM generate_series(2000, 2019)
    WHERE generate_series NOT IN (
        SELECT DISTINCT season
        FROM raw_mlb.live_feed_snapshots
        WHERE season >= 2000 AND season <= 2019
    )
    ORDER BY generate_series
) as missing")

if [ -z "$MISSING_SEASONS" ]; then
    echo "✅ All seasons already downloaded!"
    exit 0
fi

echo "🎯 Missing seasons: $MISSING_SEASONS"
echo "📊 Total seasons to download: $(echo $MISSING_SEASONS | wc -w)"

# Process each season via baseball CLI
COMPLETED=0
FAILED=0

for season in $MISSING_SEASONS; do
    echo -e "\n🏏 Processing MLB $season Season ($((COMPLETED + FAILED + 1))/$(echo $MISSING_SEASONS | wc -w))"
    echo "========================================"

    # Use baseball CLI mlb download command
    echo "📅 Downloading $season data..."
    if baseball mlb download --season $season; then
        echo "✅ Data downloaded for $season"
    else
        echo "❌ Failed to download data for $season"
        ((FAILED++))
        continue
    fi

    # Transform data
    echo "🔄 Transforming $season data..."
    if baseball mlb ingest --season $season; then
        echo "✅ Data ingested for $season"
        ((COMPLETED++))
    else
        echo "❌ Failed to ingest data for $season"
        ((FAILED++))
        continue
    fi

    echo "🎉 Season $season completed successfully!"

    # Brief pause between seasons
    sleep 5
done

echo -e "\n🏁 INGESTION COMPLETE"
echo "======================"
echo "✅ Completed: $COMPLETED seasons"
echo "❌ Failed: $FAILED seasons"

echo -e "\n📈 FINAL STATUS:"
echo "----------------"
baseball status || psql -d retrosheet -c "
SELECT
    (SELECT COUNT(*) FROM raw_mlb.live_feed_snapshots) as game_feeds,
    (SELECT COUNT(*) FROM core.live_games) as processed_games,
    (SELECT COUNT(DISTINCT season) FROM raw_mlb.live_feed_snapshots WHERE season >= 2000) as seasons_downloaded
"