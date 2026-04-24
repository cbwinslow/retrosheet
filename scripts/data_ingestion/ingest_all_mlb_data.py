#!/usr/bin/env python3
"""
Comprehensive MLB Historical Data Ingestion Script
Downloads and transforms all MLB data from 2000-2025.
"""

import argparse
import subprocess
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run_command(cmd: str, description: str) -> bool:
    """Run a command and return success status."""
    print(f'🔄 {description}')
    try:
        result = subprocess.run(cmd, shell=True, cwd=ROOT, capture_output=True, text=True)
        if result.returncode == 0:
            print(f'✅ {description} completed')
            return True
        print(f'❌ {description} failed: {result.stderr}')
        return False
    except Exception as e:
        print(f'❌ {description} error: {e}')
        return False


def download_season_data(season: int) -> bool:
    """Download both schedules and game feeds for a season."""
    print(f"\n{'=' * 60}")
    print(f'🏏 Processing MLB {season} Season')
    print(f"{'=' * 60}")

    # Download schedules
    success = run_command(
        f'python3 scripts/download_mlb_bulk.py --start-season {season} --end-season {season} --mode schedules --workers 8 --delay 0.5',
        f'Download {season} schedules',
    )
    if not success:
        return False

    # Download game feeds
    success = run_command(
        f'python3 scripts/download_mlb_bulk.py --start-season {season} --end-season {season} --mode games --workers 8 --delay 0.5',
        f'Download {season} game feeds',
    )
    return success


def transform_season_data(season: int) -> bool:
    """Transform all downloaded game feeds for a season."""
    print(f'\n🔄 Transforming {season} season data...')

    # Get untransformed game PKs for the season
    cmd = f"""
    psql -d retrosheet -t -c "
    SELECT game_pk
    FROM raw_mlb.live_feed_snapshots
    WHERE season = {season}
    EXCEPT
    SELECT mlb_game_pk::bigint
    FROM core.live_games
    ORDER BY game_pk
    "
    """

    try:
        result = subprocess.run(cmd, shell=True, cwd=ROOT, capture_output=True, text=True)
        if result.returncode != 0:
            print(f'❌ Failed to get game PKs for {season}: {result.stderr}')
            return False

        game_pks = [line.strip() for line in result.stdout.strip().split('\n') if line.strip()]

        if not game_pks:
            print(f'✅ No games to transform for {season}')
            return True

        print(f'📊 Found {len(game_pks)} games to transform for {season}')

        # Transform in batches of 10
        batch_size = 10
        transformed = 0

        for i in range(0, len(game_pks), batch_size):
            batch = game_pks[i : i + batch_size]
            print(
                f'   Transforming batch {i // batch_size + 1}/{(len(game_pks) + batch_size - 1) // batch_size}',
            )

            for pk in batch:
                if run_command(
                    f'python3 scripts/transform_live_game.py --game-pk {pk}',
                    f'Transform game {pk}',
                ):
                    transformed += 1

        print(f'✅ Transformed {transformed}/{len(game_pks)} games for {season}')
        return True

    except Exception as e:
        print(f'❌ Error transforming {season}: {e}')
        return False


def get_missing_seasons() -> list[int]:
    """Get list of seasons that need data downloaded."""
    # Target seasons: 2000-2025
    target_seasons = list(range(2000, 2026))

    # Check which seasons have complete data
    # For now, we'll check which have any game feeds
    cmd = """
    psql -d retrosheet -t -c "
    SELECT DISTINCT season
    FROM raw_mlb.live_feed_snapshots
    WHERE season >= 2000 AND season <= 2025
    ORDER BY season
    "
    """

    try:
        result = subprocess.run(cmd, shell=True, cwd=ROOT, capture_output=True, text=True)
        existing_seasons = [
            int(line.strip()) for line in result.stdout.strip().split('\n') if line.strip()
        ]

        missing_seasons = [s for s in target_seasons if s not in existing_seasons]
        return missing_seasons

    except Exception as e:
        print(f'❌ Error getting missing seasons: {e}')
        return target_seasons  # Assume all missing if error


def main():
    parser = argparse.ArgumentParser(description='Comprehensive MLB data ingestion')
    parser.add_argument(
        '--seasons',
        nargs='*',
        type=int,
        help='Specific seasons to process (default: missing seasons)',
    )
    parser.add_argument(
        '--download-only',
        action='store_true',
        help="Only download data, don't transform",
    )
    parser.add_argument(
        '--transform-only', action='store_true', help='Only transform existing data',
    )
    parser.add_argument('--workers', type=int, default=8, help='Number of parallel workers')
    parser.add_argument('--delay', type=float, default=0.5, help='Delay between requests')

    args = parser.parse_args()

    print('🚀 MLB Historical Data Ingestion')
    print('=' * 50)

    if args.seasons:
        seasons_to_process = args.seasons
    else:
        seasons_to_process = get_missing_seasons()

    if not seasons_to_process:
        print('✅ All seasons appear to have data. Use --seasons to specify specific seasons.')
        return

    print(f'📅 Seasons to process: {seasons_to_process}')

    total_seasons = len(seasons_to_process)
    completed_seasons = 0

    for season in seasons_to_process:
        print(f'\n🎯 Processing season {season} ({completed_seasons + 1}/{total_seasons})')

        if not args.transform_only:
            if not download_season_data(season):
                print(f'❌ Failed to download {season} data')
                continue

        if not args.download_only:
            if not transform_season_data(season):
                print(f'❌ Failed to transform {season} data')
                continue

        completed_seasons += 1
        print(f'✅ Season {season} completed')

        # Brief pause between seasons
        if season != seasons_to_process[-1]:
            time.sleep(5)

    print(f'\n🎉 Completed {completed_seasons}/{total_seasons} seasons')

    # Final summary
    run_command(
        """
        psql -d retrosheet -c "
        SELECT
            (SELECT COUNT(*) FROM raw_mlb.schedule_snapshots) as schedules,
            (SELECT COUNT(*) FROM raw_mlb.live_feed_snapshots) as game_feeds,
            (SELECT COUNT(*) FROM core.live_games) as live_games,
            (SELECT COUNT(*) FROM core.live_events) as live_events
        "
        """,
        'Final data summary',
    )


if __name__ == '__main__':
    main()
