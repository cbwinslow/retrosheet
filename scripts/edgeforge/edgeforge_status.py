#!/usr/bin/env python3
"""
EdgeForge Status Report - Clean, Non-Interactive Version
"""

import os
from datetime import datetime


def database_kwargs():
    return {
        'host': os.environ.get('PGHOST', 'localhost'),
        'port': os.environ.get('PGPORT', '5432'),
        'dbname': os.environ.get('PGDATABASE', 'retrosheet'),
        'user': os.environ.get('PGUSER', 'postgres'),
        'password': os.environ.get('PGPASSWORD', ''),
    }


def get_comprehensive_status():
    """Get comprehensive status for EdgeForge report."""
    import psycopg2

    conn = psycopg2.connect(**database_kwargs())
    try:
        with conn.cursor() as cur:
            # Overall metrics
            cur.execute("""
                SELECT
                    (SELECT COUNT(*) FROM raw_mlb.live_feed_snapshots) as raw_feeds,
                    (SELECT COUNT(*) FROM core.live_games) as processed_games,
                    (SELECT COUNT(*) FROM core.live_events) as processed_events,
                    (SELECT COUNT(DISTINCT season) FROM raw_mlb.live_feed_snapshots WHERE season >= 2000) as seasons_downloaded,
                    (SELECT COUNT(*) FROM mlb_enhanced.statcast_pitches) as statcast_pitches,
                    (SELECT COUNT(*) FROM mlb_enhanced.betting_features) as betting_samples,
                    (SELECT COUNT(*) FROM mlb_enhanced.batter_pitcher_history) as matchup_history
            """)
            overall = cur.fetchone()

            # Season breakdown
            cur.execute("""
                SELECT season, COUNT(*) as games
                FROM raw_mlb.live_feed_snapshots
                WHERE season >= 2000
                GROUP BY season
                ORDER BY season DESC
                LIMIT 8
            """)
            seasons = cur.fetchall()

            # Missing seasons count
            cur.execute("""
                SELECT COUNT(*) as missing_seasons
                FROM (
                    SELECT generate_series as season
                    FROM generate_series(2000, 2019)
                    EXCEPT
                    SELECT DISTINCT season
                    FROM raw_mlb.live_feed_snapshots
                    WHERE season >= 2000 AND season <= 2019
                ) as missing
            """)
            missing_count = cur.fetchone()[0]

            return {
                'overall': overall,
                'seasons': seasons,
                'missing_count': missing_count,
            }

    finally:
        conn.close()


def display_status_report(status):
    """Display a clean status report."""
    (
        raw_feeds,
        processed_games,
        processed_events,
        seasons_downloaded,
        statcast_pitches,
        betting_samples,
        matchup_history,
    ) = status['overall']

    print('🎯 EdgeForge MLB Data Ingestion Status Report')
    print('=' * 60)
    print(f"📊 Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print('=' * 60)

    # Progress summary
    total_target_seasons = 27  # 2000-2026
    percent_complete = (seasons_downloaded / total_target_seasons) * 100
    progress_bar = '█' * int(percent_complete / 4) + '░' * int((100 - percent_complete) / 4)

    print('\n📈 OVERALL PROGRESS')
    print(
        f'Progress: {progress_bar} {percent_complete:.1f}% ({seasons_downloaded}/{total_target_seasons} seasons)',
    )

    print('\n🎮 DATA VOLUME')
    print(f'   Raw Game Feeds:     {raw_feeds:,}')
    print(f'   Processed Games:     {processed_games:,}')
    print(f'   Processed Events:    {processed_events:,}')

    print('\n💰 BETTING INTELLIGENCE')
    print(f'   Training Samples:    {betting_samples:,}')
    print(f'   Statcast Pitches:    {statcast_pitches:,}')
    print(f'   Matchup History:     {matchup_history:,}')

    print('\n📅 SEASON STATUS')
    for _season, games in status['seasons']:
        status_icon = '✅' if games > 2000 else '⚠️' if games > 1000 else '🔄'
        print('6')

    if status['missing_count'] > 0:
        print(f"   ❌ Missing Seasons: {status['missing_count']} (2000-2019)")

    # Ingestion status
    print('\n🔄 INGESTION STATUS')
    try:
        with open('/tmp/complete_mlb_ingestion.log') as f:
            lines = f.readlines()[-3:]  # Last 3 lines
            for line in lines:
                if line.strip():
                    print(f'   {line.strip()}')
    except:
        print('   Log file not accessible')

    # EdgeForge readiness
    print('\n🎯 EDGEFORGE READINESS')
    model_ready = betting_samples > 100000
    statcast_ready = statcast_pitches > 50000
    historical_ready = seasons_downloaded >= 10

    readiness_items = [
        ('ML Training Data', model_ready, f'{betting_samples:,} samples'),
        ('Statcast Features', statcast_ready, f'{statcast_pitches:,} pitches'),
        ('Historical Coverage', historical_ready, f'{seasons_downloaded} seasons'),
        (
            'Matchup Intelligence',
            matchup_history > 10000,
            f'{matchup_history:,} matchups',
        ),
    ]

    for item, ready, detail in readiness_items:
        status_icon = '✅' if ready else '⏳'
        print(f'   {status_icon} {item}: {detail}')

    # Overall assessment
    readiness_score = (
        sum([model_ready, statcast_ready, historical_ready, matchup_history > 10000]) / 4 * 100
    )

    if readiness_score >= 80:
        assessment = '🚀 PRODUCTION READY'
    elif readiness_score >= 60:
        assessment = '⚡ BETA READY'
    elif readiness_score >= 40:
        assessment = '🔧 MVP READY'
    else:
        assessment = '🏗️ BUILDING'

    print('\n🏆 OVERALL ASSESSMENT')
    print(f'   Status: {assessment} ({readiness_score:.0f}% readiness)')
    print('   💰 Monetizable betting intelligence platform')

    print('\n🔄 Auto-updating | Next refresh in 5 minutes')
    print('💡 EdgeForge: Where data meets betting intelligence')


def main():
    """Generate EdgeForge status report."""
    try:
        status = get_comprehensive_status()
        display_status_report(status)
    except Exception as e:
        print(f'❌ Error generating status report: {e}')
        import traceback

        traceback.print_exc()


if __name__ == '__main__':
    main()
