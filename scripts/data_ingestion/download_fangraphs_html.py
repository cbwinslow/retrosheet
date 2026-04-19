#!/usr/bin/env python3
"""
Download Fangraphs data by parsing HTML directly.

This script fetches HTML from Fangraphs leaderboards and parses the table data.
"""

import argparse
import sys
from pathlib import Path
import time

try:
    import requests
    from bs4 import BeautifulSoup
    import pandas as pd
except ImportError:
    print("Error: Required libraries not installed.")
    print("Install with: pip install requests beautifulsoup4 pandas")
    sys.exit(1)


def download_fangraphs_batting_html(season_start: int, season_end: int) -> bool:
    """Download Fangraphs batting data by parsing HTML."""
    
    # Fangraphs leaderboard URL for batting stats
    url = f"https://www.fangraphs.com/leaders/major-league?pos=all&stats=bat&lg=all&qual=0&type=8&month=0&ind=1&rost=&age=&filter=&players=0&startdate=&enddate=&season1={season_start}&season={season_end}&team=0&pageitems=2000000000"
    
    print(f"Fetching Fangraphs batting data from {url}")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=120)
        response.raise_for_status()
        
        print(f"  HTML fetched (size: {len(response.text)} bytes)")
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find the data table
        table = soup.find('table', {'class': 'leaders-standard'})
        
        if not table:
            print("  ❌ Could not find data table in HTML")
            return False
        
        # Parse table rows
        rows = []
        headers_row = []
        
        # Get headers
        thead = table.find('thead')
        if thead:
            header_cells = thead.find_all('th')
            headers_row = [cell.get_text(strip=True) for cell in header_cells]
            print(f"  Found {len(headers_row)} columns")
        
        # Get data rows
        tbody = table.find('tbody')
        if tbody:
            for tr in tbody.find_all('tr'):
                cells = tr.find_all('td')
                if cells:
                    row_data = [cell.get_text(strip=True) for cell in cells]
                    rows.append(row_data)
        
        print(f"  Parsed {len(rows)} data rows")
        
        if not rows:
            print("  ⚠️  No data rows found")
            return False
        
        # Create DataFrame
        df = pd.DataFrame(rows, columns=headers_row if headers_row else None)
        
        # Save to CSV
        output_dir = Path(__file__).resolve().parents[1] / "data" / "fangraphs"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_file = output_dir / f"fangraphs_batting_{season_start}_{season_end}.csv"
        df.to_csv(output_file, index=False)
        
        print(f"  ✅ Saved {len(df)} rows to {output_file}")
        return True
        
    except requests.exceptions.Timeout:
        print(f"  ❌ Request timed out (page too large)")
        return False
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False


def download_fangraphs_pitching_html(season_start: int, season_end: int) -> bool:
    """Download Fangraphs pitching data by parsing HTML."""
    
    # Fangraphs leaderboard URL for pitching stats
    url = f"https://www.fangraphs.com/leaders/major-league?pos=all&stats=pit&lg=all&qual=0&type=8&month=0&ind=1&rost=&age=&filter=&players=0&startdate=&enddate=&season1={season_start}&season={season_end}&team=0&pageitems=2000000000"
    
    print(f"Fetching Fangraphs pitching data from {url}")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=120)
        response.raise_for_status()
        
        print(f"  HTML fetched (size: {len(response.text)} bytes)")
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find the data table
        table = soup.find('table', {'class': 'leaders-standard'})
        
        if not table:
            print("  ❌ Could not find data table in HTML")
            return False
        
        # Parse table rows
        rows = []
        headers_row = []
        
        # Get headers
        thead = table.find('thead')
        if thead:
            header_cells = thead.find_all('th')
            headers_row = [cell.get_text(strip=True) for cell in header_cells]
            print(f"  Found {len(headers_row)} columns")
        
        # Get data rows
        tbody = table.find('tbody')
        if tbody:
            for tr in tbody.find_all('tr'):
                cells = tr.find_all('td')
                if cells:
                    row_data = [cell.get_text(strip=True) for cell in cells]
                    rows.append(row_data)
        
        print(f"  Parsed {len(rows)} data rows")
        
        if not rows:
            print("  ⚠️  No data rows found")
            return False
        
        # Create DataFrame
        df = pd.DataFrame(rows, columns=headers_row if headers_row else None)
        
        # Save to CSV
        output_dir = Path(__file__).resolve().parents[1] / "data" / "fangraphs"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_file = output_dir / f"fangraphs_pitching_{season_start}_{season_end}.csv"
        df.to_csv(output_file, index=False)
        
        print(f"  ✅ Saved {len(df)} rows to {output_file}")
        return True
        
    except requests.exceptions.Timeout:
        print(f"  ❌ Request timed out (page too large)")
        return False
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Download Fangraphs data by parsing HTML")
    parser.add_argument("--season-start", type=int, default=2000, help="Start season")
    parser.add_argument("--season-end", type=int, default=2026, help="End season")
    parser.add_argument("--type", choices=["batting", "pitching", "both"], default="both", help="Data type")
    args = parser.parse_args()
    
    results = {}
    
    if args.type in ["batting", "both"]:
        success = download_fangraphs_batting_html(args.season_start, args.season_end)
        results["batting"] = success
        time.sleep(2)  # Rate limiting
    
    if args.type in ["pitching", "both"]:
        success = download_fangraphs_pitching_html(args.season_start, args.season_end)
        results["pitching"] = success
    
    print("\n" + "="*60)
    print("DOWNLOAD SUMMARY")
    print("="*60)
    for data_type, success in results.items():
        status = "✅" if success else "❌"
        print(f"{status} {data_type}")
    print("="*60)


if __name__ == "__main__":
    main()
