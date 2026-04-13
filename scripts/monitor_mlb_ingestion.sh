#!/bin/bash
# EdgeForge MLB Ingestion Monitor
# Track progress of complete historical data ingestion

echo "📊 EdgeForge MLB Data Ingestion Monitor"
echo "========================================"

while true; do
    echo "$(date '+%Y-%m-%d %H:%M:%S')"
    echo "----------------------------------------"

    # Check if ingestion is still running
    if ! pgrep -f "complete_mlb_ingestion.sh" > /dev/null; then
        echo "⚠️  Ingestion process not running"
        echo "   Checking final status..."
        break
    fi

    # Get current status
    psql -d retrosheet -c "
    SELECT
        'Raw Game Feeds' as metric,
        (SELECT COUNT(*) FROM raw_mlb.live_feed_snapshots) as value
    UNION ALL
    SELECT
        'Processed Games' as metric,
        (SELECT COUNT(*) FROM core.live_games) as value
    UNION ALL
    SELECT
        'Processed Events' as metric,
        (SELECT COUNT(*) FROM core.live_events) as value
    UNION ALL
    SELECT
        'Seasons Downloaded' as metric,
        (SELECT COUNT(DISTINCT season) FROM raw_mlb.live_feed_snapshots WHERE season >= 2000) as value
    UNION ALL
    SELECT
        'Statcast Pitches' as metric,
        (SELECT COUNT(*) FROM mlb_enhanced.statcast_pitches) as value
    UNION ALL
    SELECT
        'Matchup History' as metric,
        (SELECT COUNT(*) FROM mlb_enhanced.batter_pitcher_history) as value
    ORDER BY value DESC;
    " 2>/dev/null | grep -E "(metric|Raw|Processed|Seasons|Statcast|Matchup)" | head -10

    # Check current season being processed
    echo ""
    echo "🎯 Current Activity:"
    ps aux | grep -E "(download_mlb_bulk|ingest_all_mlb)" | grep -v grep | awk '{print "   " $11 " " $12 " " $13}' || echo "   No active downloads"

    # Check recent log activity
    echo ""
    echo "📝 Recent Log Activity:"
    tail -5 /tmp/complete_mlb_ingestion.log 2>/dev/null | sed 's/^/   /' || echo "   No log available"

    # Progress estimate
    TOTAL_SEASONS=27  # 2000-2025
    CURRENT_SEASONS=$(psql -d retrosheet -t -c "
    SELECT COUNT(DISTINCT season)
    FROM raw_mlb.live_feed_snapshots
    WHERE season >= 2000" 2>/dev/null | tr -d ' ')

    if [ ! -z "$CURRENT_SEASONS" ] && [ "$CURRENT_SEASONS" -gt 0 ]; then
        PERCENT_COMPLETE=$((CURRENT_SEASONS * 100 / TOTAL_SEASONS))
        REMAINING=$((TOTAL_SEASONS - CURRENT_SEASONS))
        echo ""
        echo "📈 Progress: $CURRENT_SEASONS/$TOTAL_SEASONS seasons ($PERCENT_COMPLETE% complete, $REMAINING remaining)"
    fi

    echo ""
    echo "⏳ Next update in 5 minutes..."
    echo "=========================================="

    sleep 300  # 5 minutes
done

echo ""
echo "🏁 FINAL STATUS:"
echo "==============="
psql -d retrosheet -c "
SELECT
    (SELECT COUNT(*) FROM raw_mlb.live_feed_snapshots) || ' total game feeds' as status
UNION ALL
SELECT
    (SELECT COUNT(*) FROM core.live_games) || ' processed games' as status
UNION ALL
SELECT
    (SELECT COUNT(*) FROM core.live_events) || ' processed events' as status
UNION ALL
SELECT
    (SELECT COUNT(DISTINCT season) FROM raw_mlb.live_feed_snapshots WHERE season >= 2000) || '/27 seasons downloaded' as status
UNION ALL
SELECT
    'EdgeForge model: ' || CASE WHEN EXISTS(SELECT 1 FROM pg_proc WHERE proname = 'train_edgeforge_model')
    THEN 'Ready for retraining' ELSE 'Available' END as status;
"

echo ""
echo "🎉 MLB Data Ingestion Complete!"
echo "💰 EdgeForge ready for enhanced betting intelligence!"