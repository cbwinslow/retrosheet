#!/usr/bin/env python3
"""
Download Statcast pitch-level data using pybaseball.statcast().

This script downloads actual Statcast pitch-level data for specified date ranges
using the pybaseball library, which wraps the Baseball Savant Statcast API.

Usage:
    python3 scripts/download_statcast_pitch_level.py --start-date 2024-04-01 --end-date 2024-04-30
    python3 scripts/download_statcast_pitch_level.py --season 2024
"""

import argparse
import pandas as pd
from pathlib import Path
import sys
from datetime import datetime, timedelta

try:
    from pybaseball import statcast
except ImportError:
    print("Error: pybaseball library not installed.")
    print("Install with: pip install pybaseball")
    sys.exit(1)

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "statcast"
DATA_DIR.mkdir(parents=True, exist_ok=True)


def download_statcast_date_range(start_date: str, end_date: str) -> bool:
    """Download Statcast data for a date range."""
    print(f"Downloading Statcast data from {start_date} to {end_date}...")
    
    try:
        df = statcast(start_dt=start_date, end_dt=end_date)
        
        if df.empty:
            print(f"  ⚠️  No Statcast data returned for {start_date} to {end_date}")
            return False
        
        # Save to CSV
        output_file = DATA_DIR / f"statcast_{start_date}_{end_date}.csv"
        df.to_csv(output_file, index=False)
        
        print(f"  ✅ Downloaded {len(df)} Statcast rows to {output_file}")
        return True
        
    except Exception as e:
        print(f"  ❌ Error downloading Statcast data: {e}")
        return False


def download_statcast_season(season: int) -> bool:
    """Download Statcast data for an entire season."""
    print(f"Downloading Statcast data for {season} season...")
    
    # Statcast data available from 2015 onwards
    if season < 2015:
        print(f"  ⚠️  Statcast data only available from 2015 onwards")
        return False
    
    # Download in monthly chunks to avoid timeouts
    start_date = f"{season}-03-01"  # Season typically starts in March
    end_date = f"{season}-11-01"    # Season typically ends in November
    
    # Download in 30-day chunks
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    
    all_dfs = []
    current_dt = start_dt
    
    while current_dt < end_dt:
        chunk_end = min(current_dt + timedelta(days=30), end_dt)
        chunk_start_str = current_dt.strftime("%Y-%m-%d")
        chunk_end_str = chunk_end.strftime("%Y-%m-%d")
        
        print(f"  Downloading chunk: {chunk_start_str} to {chunk_end_str}...")
        try:
            df = statcast(start_dt=chunk_start_str, end_dt=chunk_end_str)
            if not df.empty:
                all_dfs.append(df)
                print(f"    ✅ Downloaded {len(df)} rows")
        except Exception as e:
            print(f"    ❌ Error downloading chunk: {e}")
        
        current_dt = chunk_end
    
    if not all_dfs:
        print(f"  ⚠️  No Statcast data returned for {season}")
        return False
    
    # Combine all chunks
    combined_df = pd.concat(all_dfs, ignore_index=True)
    
    # Save to CSV
    output_file = DATA_DIR / f"statcast_{season}.csv"
    combined_df.to_csv(output_file, index=False)
    
    print(f"  ✅ Downloaded {len(combined_df)} total Statcast rows to {output_file}")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Download Statcast pitch-level data using pybaseball"
    )
    parser.add_argument(
        "--start-date",
        type=str,
        help="Start date (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--end-date",
        type=str,
        help="End date (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--season",
        type=int,
        help="Download entire season (2015+)"
    )
    args = parser.parse_args()
    
    if args.season:
        success = download_statcast_season(args.season)
    elif args.start_date and args.end_date:
        success = download_statcast_date_range(args.start_date, args.end_date)
    else:
        print("Error: Must specify either --season or --start-date and --end-date")
        sys.exit(1)
    
    if success:
        print("\n✅ Statcast download completed successfully")
        print(f"Data saved to: {DATA_DIR}")
        print("\nNext step: Load into database with:")
        print(f"  python3 scripts/external_data/load_statcast.py --file <csv_file>")
    else:
        print("\n❌ Statcast download failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
