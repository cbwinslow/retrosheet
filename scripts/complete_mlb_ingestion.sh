#!/bin/bash
# Complete MLB Data Ingestion - Simple Version
# Download all missing MLB seasons sequentially

echo "🎯 EdgeForge: Complete MLB Historical Data Ingestion"
echo "======================================================"
echo "📊 Target: MLB seasons 2000-2019"
echo "🎲 Method: Sequential processing (safer for API limits)"

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

# Process each season
COMPLETED=0
FAILED=0

for season in $MISSING_SEASONS; do
    echo -e "\n🏏 Processing MLB $season Season ($((COMPLETED + FAILED + 1))/$(echo $MISSING_SEASONS | wc -w))"
    echo "========================================"

    # Download schedules
    echo "📅 Downloading $season schedules..."
    if python3 scripts/download_mlb_bulk.py --start-season $season --end-season $season --mode schedules --workers 8 --delay 0.5; then
        echo "✅ Schedules downloaded for $season"
    else
        echo "❌ Failed to download schedules for $season"
        ((FAILED++))
        continue
    fi

    # Download game feeds
    echo "🎮 Downloading $season game feeds..."
    if python3 scripts/download_mlb_bulk.py --start-season $season --end-season $season --mode games --workers 8 --delay 0.5; then
        echo "✅ Game feeds downloaded for $season"
    else
        echo "❌ Failed to download game feeds for $season"
        ((FAILED++))
        continue
    fi

    # Transform data
    echo "🔄 Transforming $season data..."
    if python3 scripts/ingest_all_mlb_data.py --seasons $season --transform-only; then
        echo "✅ Data transformed for $season"
        ((COMPLETED++))
    else
        echo "❌ Failed to transform data for $season"
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

if [ $COMPLETED -gt 0 ]; then
    echo -e "\n🔄 Updating EdgeForge model with new data..."
    python3 scripts/train_edgeforge_model.py
fi

echo -e "\n📈 FINAL STATUS:"
echo "----------------"
psql -d retrosheet -c "
SELECT
    (SELECT COUNT(*) FROM raw_mlb.live_feed_snapshots) as game_feeds,
    (SELECT COUNT(*) FROM core.live_games) as processed_games,
    (SELECT COUNT(DISTINCT season) FROM raw_mlb.live_feed_snapshots WHERE season >= 2000) as seasons_downloaded
"