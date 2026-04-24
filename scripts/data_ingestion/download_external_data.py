#!/usr/bin/env python3
"""
Download all external data sources for the baseball prediction warehouse.

Downloads:
1. Lahman Baseball Databank from SABR
2. Fangraphs data
3. Statcast data from Baseball Savant

Usage:
    python3 scripts/download_external_data.py --lahman --fangraphs --statcast --baseball-savant
    python3 scripts/download_external_data.py --all
"""

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / 'data'


def download_lahman() -> bool:
    """Download Lahman Baseball Databank from SABR."""
    print('Lahman Baseball Databank requires manual download from:')
    print('  - https://sabr.org/lahman-database/')
    print('  - Download the CSV version (1871-2025)')
    print('  - Extract to data/lahman_csv/')
    print('')
    print('Alternative: Download from GitHub (may timeout due to size):')
    print('  - https://github.com/chadwickbureau/baseballdatabank')
    print('')
    print('After download, run:')
    print('  python3 scripts/external_data/load_lahman.py --dir data/lahman_csv')
    print('')
    print('⚠️  Lahman requires manual download (large file, no stable API)')
    return False


def download_fangraphs() -> bool:
    """Download Fangraphs data."""
    print('Fangraphs data requires manual download from:')
    print('  - https://www.fangraphs.com/leaders.aspx')
    print('  - Export as CSV and save to data/fangraphs_player_season.csv')
    print(
        '  - https://www.fangraphs.com/leaders.aspx?pos=all&stats=bat&lg=all&qual=0&type=8&season=2025&month=0&season1=2000&ind=0',
    )
    print('  - Export team data to data/fangraphs_team_season.csv')
    print('⚠️  Fangraphs requires manual download (no public API)')
    return False


def download_statcast() -> bool:
    """Download Statcast data from Baseball Savant."""
    print('Statcast data requires manual download from:')
    print('  - https://baseballsavant.mlb.com/statcast_search')
    print('  - Set date range and export as CSV')
    print('  - Save to data/statcast/ directory')
    print('⚠️  Statcast requires manual download (no public API for bulk data)')
    return False


def main():
    parser = argparse.ArgumentParser(description='Download all external data sources')
    parser.add_argument('--lahman', action='store_true', help='Download Lahman data')
    parser.add_argument('--fangraphs', action='store_true', help='Download Fangraphs data')
    parser.add_argument('--statcast', action='store_true', help='Download Statcast data')
    parser.add_argument('--all', action='store_true', help='Download all data sources')
    args = parser.parse_args()

    if not any([args.lahman, args.fangraphs, args.statcast, args.baseball_savant, args.all]):
        print('Error: Must specify --lahman, --fangraphs, --statcast, --baseball-savant, or --all')
        sys.exit(1)

    results = {}

    if args.all or args.lahman:
        results['lahman'] = download_lahman()

    if args.all or args.fangraphs:
        results['fangraphs'] = download_fangraphs()

    if args.all or args.statcast:
        results['statcast'] = download_statcast()

    if args.all or args.baseball_savant:
        results['baseball_savant'] = download_baseball_savant()

    print('\n' + '=' * 60)
    print('DOWNLOAD SUMMARY')
    print('=' * 60)
    for source, success in results.items():
        status = '✅' if success else '⚠️'
        print(f'{status} {source}')

    print('=' * 60)


if __name__ == '__main__':
    main()
