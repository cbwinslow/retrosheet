#!/usr/bin/env python3
"""
Download Lahman Baseball Databank CSV files from official source.

Lahman Baseball Databank: https://github.com/chadwickbureau/baseballdatabank
Contains comprehensive historical baseball statistics from 1871-present.

Usage:
    python3 scripts/download_lahman_data.py --dir data/lahman_csv
"""

import argparse
import sys
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlretrieve


LAHMAN_ZIP_URL = 'https://www.dropbox.com/scl/fi/hy0sxw6gaai7ghemrshi8/lahman_1871-2023_csv.7z?rlkey=edw1u63zzxg48gvpcmr3qpnhz&dl=1'


def download_lahman_zip(output_dir: Path) -> Path:
    """Download Lahman database zip file."""
    zip_path = output_dir / 'lahman_master.7z'

    if zip_path.exists():
        print(f'Archive file already exists at {zip_path}')
        return zip_path

    print(f'Downloading Lahman Baseball Databank from {LAHMAN_ZIP_URL}')
    print('This may take a few minutes...')

    try:
        urlretrieve(LAHMAN_ZIP_URL, zip_path)
        print(f'Downloaded to {zip_path}')
        return zip_path
    except URLError as e:
        print(f'Error downloading: {e}')
        sys.exit(1)


def extract_csv_files(zip_path: Path, output_dir: Path) -> None:
    """Extract CSV files from zip to output directory."""
    print(f'Extracting CSV files to {output_dir}')

    # Create output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)

    # CSV files we want to extract
    target_files = [
        'People.csv',
        'Teams.csv',
        'Salaries.csv',
        'Pitching.csv',
        'Batting.csv',
        'Fielding.csv',
        'Managers.csv',
        'AwardsManagers.csv',
        'AwardsPlayers.csv',
        'AwardsSharePlayers.csv',
        'Appearances.csv',
        'HallOfFame.csv',
        'AllstarFull.csv',
        'Parks.csv',
        'CollegePlaying.csv',
    ]

    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        # Find the baseballdatabank-master directory
        base_dir = None
        for name in zip_ref.namelist():
            if name.startswith('baseballdatabank-master/') and name.endswith('/'):
                base_dir = name
                break

        if not base_dir:
            print('Error: Could not find baseballdatabank-master directory in zip')
            sys.exit(1)

        # Extract target CSV files
        extracted_count = 0
        for target in target_files:
            file_path = f'{base_dir}core/{target}'
            try:
                zip_ref.extract(file_path, output_dir)
                # Move from nested directory to output directory
                src = output_dir / file_path
                dst = output_dir / target
                if src.exists():
                    src.rename(dst)
                    extracted_count += 1
                    print(f'  ✓ Extracted {target}')
            except KeyError:
                print(f'  ⚠ {target} not found in archive')

        print(f'\nExtracted {extracted_count} CSV files')


def main():
    parser = argparse.ArgumentParser(description='Download Lahman Baseball Databank CSV files')
    parser.add_argument(
        '--dir',
        type=Path,
        default=Path('data/lahman_csv'),
        help='Output directory for CSV files (default: data/lahman_csv)',
    )
    args = parser.parse_args()

    # Download zip file
    zip_path = download_lahman_zip(args.dir.parent)

    # Extract CSV files
    extract_csv_files(zip_path, args.dir)

    print(f'\n✅ Lahman data downloaded to {args.dir}')


if __name__ == '__main__':
    main()
