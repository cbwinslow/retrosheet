#!/usr/bin/env python3
"""
Download Fangraphs data using baseball-scraper library.

This script downloads Fangraphs data for specified seasons using the baseball-scraper
Python library, which scrapes Fangraphs leaderboards.

Usage:
    python3 scripts/download_fangraphs.py --season 2024
    python3 scripts/download_fangraphs.py --seasons 2020 2021 2022 2023 2024
"""

import argparse
import sys
from pathlib import Path


try:
    import pybaseball
except ImportError:
    print('Error: pybaseball library not installed.')
    print('Install with: pip install pybaseball')
    sys.exit(1)

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / 'data' / 'fangraphs'
DATA_DIR.mkdir(parents=True, exist_ok=True)


def download_fangraphs_batting(season: int) -> bool:
    """Download Fangraphs batting data for a single season."""
    print(f'Downloading Fangraphs batting data for {season} season...')

    try:
        # Download batting stats from Fangraphs using pybaseball
        df = pybaseball.batting_stats(season, season, qual=0)

        if df.empty:
            print(f'  ⚠️  No batting data returned for {season}')
            return False

        # Save to CSV
        output_file = DATA_DIR / f'fangraphs_batting_{season}.csv'
        df.to_csv(output_file, index=False)

        print(f'  ✅ Downloaded {len(df)} batting rows to {output_file}')
        return True

    except Exception as e:
        print(f'  ❌ Error downloading batting data for {season}: {e}')
        return False


def download_fangraphs_pitching(season: int) -> bool:
    """Download Fangraphs pitching data for a single season."""
    print(f'Downloading Fangraphs pitching data for {season} season...')

    try:
        # Download pitching stats from Fangraphs using pybaseball
        df = pybaseball.pitching_stats(season, season, qual=0)

        if df.empty:
            print(f'  ⚠️  No pitching data returned for {season}')
            return False

        # Save to CSV
        output_file = DATA_DIR / f'fangraphs_pitching_{season}.csv'
        df.to_csv(output_file, index=False)

        print(f'  ✅ Downloaded {len(df)} pitching rows to {output_file}')
        return True

    except Exception as e:
        print(f'  ❌ Error downloading pitching data for {season}: {e}')
        return False


def main():
    parser = argparse.ArgumentParser(description='Download Fangraphs data using baseball-scraper')
    parser.add_argument('--season', type=int, help='Single season to download')
    parser.add_argument('--seasons', nargs='+', type=int, help='Multiple seasons to download')
    parser.add_argument('--batting', action='store_true', help='Download batting stats')
    parser.add_argument('--pitching', action='store_true', help='Download pitching stats')
    args = parser.parse_args()

    # Determine seasons to download
    if args.season:
        seasons = [args.season]
    elif args.seasons:
        seasons = args.seasons
    else:
        # Default to recent seasons
        seasons = [2020, 2021, 2022, 2023, 2024]

    print(f'Downloading Fangraphs data for seasons: {seasons}')
    print(f'Data directory: {DATA_DIR}')
    print('=' * 60)

    results = {}

    for season in seasons:
        # Download batting stats if requested or by default
        if args.batting or not args.pitching:
            success = download_fangraphs_batting(season)
            results[f'batting_{season}'] = success

        # Download pitching stats if requested or by default
        if args.pitching or not args.batting:
            success = download_fangraphs_pitching(season)
            results[f'pitching_{season}'] = success

    print('\n' + '=' * 60)
    print('DOWNLOAD SUMMARY')
    print('=' * 60)
    for source, success in results.items():
        status = '✅' if success else '❌'
        print(f'{status} {source}')
    print('=' * 60)


if __name__ == '__main__':
    main()
