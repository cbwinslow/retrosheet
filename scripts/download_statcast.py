#!/usr/bin/env python3
"""
Download Statcast data using pybaseball library.

This script downloads Statcast data for specified seasons using the pybaseball
Python library, which wraps the Baseball Savant API.

Usage:
    python3 scripts/download_statcast.py --season 2024
    python3 scripts/download_statcast.py --seasons 2020 2021 2022 2023 2024
"""

import argparse
import pandas as pd
from pathlib import Path
import sys

try:
    import pybaseball
except ImportError:
    print("Error: pybaseball library not installed.")
    print("Install with: pip install pybaseball")
    sys.exit(1)

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "statcast"
DATA_DIR.mkdir(parents=True, exist_ok=True)


def download_statcast_season(season: int) -> bool:
    """Download Statcast data for a single season using batting/pitching stats."""
    print(f"Downloading Statcast batting data for {season} season...")
    
    try:
        # Download batting stats using pybaseball (more stable than statcast)
        df = pybaseball.batting_stats_bref(season)
        
        if df.empty:
            print(f"  ⚠️  No batting data returned for {season}")
            return False
        
        # Save to CSV
        output_file = DATA_DIR / f"statcast_batting_{season}.csv"
        df.to_csv(output_file, index=False)
        
        print(f"  ✅ Downloaded {len(df)} batting rows to {output_file}")
        return True
        
    except Exception as e:
        print(f"  ❌ Error downloading batting data for {season}: {e}")
        return False


def download_statcast_pitching(season: int) -> bool:
    """Download Statcast pitching data for a single season."""
    print(f"Downloading Statcast pitching data for {season} season...")
    
    try:
        # Download pitching statcast data
        df = pybaseball.pitching_stats_bref(season)
        
        if df.empty:
            print(f"  ⚠️  No pitching data returned for {season}")
            return False
        
        # Save to CSV
        output_file = DATA_DIR / f"pitching_stats_{season}.csv"
        df.to_csv(output_file, index=False)
        
        print(f"  ✅ Downloaded {len(df)} pitching rows to {output_file}")
        return True
        
    except Exception as e:
        print(f"  ❌ Error downloading pitching data for {season}: {e}")
        return False


def download_statcast_batting(season: int) -> bool:
    """Download Statcast batting data for a single season."""
    print(f"Downloading Statcast batting data for {season} season...")
    
    try:
        # Download batting statcast data
        df = pybaseball.batting_stats_bref(season)
        
        if df.empty:
            print(f"  ⚠️  No batting data returned for {season}")
            return False
        
        # Save to CSV
        output_file = DATA_DIR / f"batting_stats_{season}.csv"
        df.to_csv(output_file, index=False)
        
        print(f"  ✅ Downloaded {len(df)} batting rows to {output_file}")
        return True
        
    except Exception as e:
        print(f"  ❌ Error downloading batting data for {season}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Download Statcast data using pybaseball"
    )
    parser.add_argument(
        "--season",
        type=int,
        help="Single season to download"
    )
    parser.add_argument(
        "--seasons",
        nargs="+",
        type=int,
        help="Multiple seasons to download"
    )
    parser.add_argument(
        "--pitching",
        action="store_true",
        help="Download pitching stats"
    )
    parser.add_argument(
        "--batting",
        action="store_true",
        help="Download batting stats"
    )
    args = parser.parse_args()
    
    # Determine seasons to download
    if args.season:
        seasons = [args.season]
    elif args.seasons:
        seasons = args.seasons
    else:
        # Default to recent seasons
        seasons = [2020, 2021, 2022, 2023, 2024]
    
    print(f"Downloading Statcast data for seasons: {seasons}")
    print(f"Data directory: {DATA_DIR}")
    print("="*60)
    
    results = {}
    
    for season in seasons:
        # Download batting stats by default
        success = download_statcast_batting(season)
        results[f"batting_{season}"] = success
        
        # Download pitching stats by default
        success = download_statcast_pitching(season)
        results[f"pitching_{season}"] = success
    
    print("\n" + "="*60)
    print("DOWNLOAD SUMMARY")
    print("="*60)
    for source, success in results.items():
        status = "✅" if success else "❌"
        print(f"{status} {source}")
    print("="*60)


if __name__ == "__main__":
    main()
