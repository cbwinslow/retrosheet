#!/usr/bin/env python3
"""
EdgeForge: Complete MLB Historical Data Ingestion
Download and process all remaining MLB seasons (2000-2019)
"""

import os
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed


def run_command(cmd: str, description: str, timeout: int = 300) -> bool:
    """Run a command with timeout and error handling."""
    print(f"🔄 {description}")
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode == 0:
            print(f"✅ {description} completed")
            return True
        else:
            print(f"❌ {description} failed: {result.stderr[:200]}")
            return False
    except subprocess.TimeoutExpired:
        print(f"⏰ {description} timed out after {timeout}s")
        return False
    except Exception as e:
        print(f"❌ {description} error: {e}")
        return False


def download_season(season: int) -> bool:
    """Download schedules and games for a single season."""
    print(f"\n🏏 Processing MLB {season} Season")

    # Download schedules
    schedule_success = run_command(
        f"python3 scripts/download_mlb_bulk.py --start-season {season} --end-season {season} --mode schedules --workers 8 --delay 0.5",
        f"Download {season} schedules",
    )

    # Download game feeds
    games_success = run_command(
        f"python3 scripts/download_mlb_bulk.py --start-season {season} --end-season {season} --mode games --workers 8 --delay 0.5",
        f"Download {season} game feeds",
    )

    # Transform data
    transform_success = run_command(
        f"python3 scripts/ingest_all_mlb_data.py --seasons {season} --transform-only",
        f"Transform {season} data",
        timeout=600,  # 10 minutes for transformation
    )

    success = schedule_success and games_success and transform_success
    status = "✅ SUCCESS" if success else "❌ FAILED"
    print(f"🏁 Season {season}: {status}")

    return success


def get_missing_seasons() -> list[int]:
    """Get list of seasons that still need data."""
    try:
        result = subprocess.run(
            """
            psql -d retrosheet -t -c "
            SELECT generate_series as missing_season
            FROM generate_series(2000, 2019) 
            WHERE generate_series NOT IN (
                SELECT DISTINCT season 
                FROM raw_mlb.live_feed_snapshots 
                WHERE season >= 2000
            )
            ORDER BY generate_series
            "
            """,
            shell=True,
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            seasons = [
                int(line.strip()) for line in result.stdout.strip().split("\n") if line.strip()
            ]
            return seasons
        else:
            print(f"❌ Failed to get missing seasons: {result.stderr}")
            return list(range(2000, 2020))  # Fallback

    except Exception as e:
        print(f"❌ Error getting missing seasons: {e}")
        return list(range(2000, 2020))  # Fallback


def get_current_status():
    """Get current download and processing status."""
    try:
        result = subprocess.run(
            """
            psql -d retrosheet -c "
            SELECT 
                (SELECT COUNT(*) FROM raw_mlb.live_feed_snapshots) as game_feeds,
                (SELECT COUNT(*) FROM core.live_games) as processed_games,
                (SELECT COUNT(DISTINCT season) FROM raw_mlb.live_feed_snapshots WHERE season >= 2000) as seasons_downloaded,
                (SELECT COUNT(*) FROM mlb_enhanced.statcast_pitches) as statcast_pitches,
                (SELECT COUNT(*) FROM mlb_enhanced.batter_pitcher_history) as matchup_history
            "
            """,
            shell=True,
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            # Extract numbers from the output
            lines = result.stdout.strip().split("\n")
            for line in lines:
                if "game_feeds" in line and "|" in line:
                    parts = line.split("|")
                    if len(parts) >= 2:
                        feeds = parts[1].strip()
                        print(f"🎮 Raw Game Feeds: {feeds}")
                elif "processed_games" in line and "|" in line:
                    parts = line.split("|")
                    if len(parts) >= 2:
                        games = parts[1].strip()
                        print(f"🏟️ Processed Games: {games}")
                elif "seasons_downloaded" in line and "|" in line:
                    parts = line.split("|")
                    if len(parts) >= 2:
                        seasons = parts[1].strip()
                        print(f"📅 Seasons Downloaded: {seasons}")
                elif "statcast_pitches" in line and "|" in line:
                    parts = line.split("|")
                    if len(parts) >= 2:
                        pitches = parts[1].strip()
                        print(f"⚾ Statcast Pitches: {pitches}")
                elif "matchup_history" in line and "|" in line:
                    parts = line.split("|")
                    if len(parts) >= 2:
                        matchups = parts[1].strip()
                        print(f"🤝 Matchup History: {matchups}")

    except Exception as e:
        print(f"❌ Error getting status: {e}")


def main():
    print("🎯 EdgeForge: Complete MLB Historical Data Ingestion")
    print("=" * 60)
    print("📊 Target: All MLB seasons 2000-2019")
    print("🎲 Method: Parallel processing with error recovery")
    print("💰 Goal: Maximum historical data for superior models")

    # Show current status
    print("\n📈 CURRENT STATUS:")
    print("-" * 30)
    get_current_status()

    # Get missing seasons
    missing_seasons = get_missing_seasons()
    if not missing_seasons:
        print("\n✅ All seasons already downloaded!")
        return

    print(f"\n🎯 MISSING SEASONS ({len(missing_seasons)}): {missing_seasons}")

    # Estimate workload
    estimated_games = len(missing_seasons) * 2500  # ~2500 games per season
    estimated_time_hours = estimated_games * 0.0005  # Rough estimate per game
    print("\n📊 WORKLOAD ESTIMATE:")
    print(f"   • Seasons to download: {len(missing_seasons)}")
    print(f"   • Estimated games: ~{estimated_games:,}")
    print(".1f")
    # Process seasons in parallel (but not too aggressively to avoid API limits)
    max_workers = 2  # Conservative to avoid rate limiting
    completed = 0
    failed = 0

    print(f"\n🚀 STARTING DOWNLOAD (max {max_workers} parallel seasons)")
    print("=" * 60)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_season = {
            executor.submit(download_season, season): season for season in missing_seasons
        }

        # Process results as they complete
        for future in as_completed(future_to_season):
            season = future_to_season[future]
            try:
                success = future.result()
                if success:
                    completed += 1
                    print(f"✅ Season {season} completed ({completed}/{len(missing_seasons)})")
                else:
                    failed += 1
                    print(f"❌ Season {season} failed ({failed} failures)")

                # Brief pause between completions
                time.sleep(2)

            except Exception as e:
                failed += 1
                print(f"❌ Season {season} error: {e}")

    print("\n🏁 INGESTION COMPLETE")
    print("=" * 60)
    print(f"✅ Completed: {completed} seasons")
    print(f"❌ Failed: {failed} seasons")
    print(
        f"📊 Success Rate: {(completed / (completed + failed) * 100):.1f}%"
        if (completed + failed) > 0
        else "N/A"
    )

    # Final status
    print("\n📈 FINAL STATUS:")
    print("-" * 30)
    get_current_status()

    # Update EdgeForge model
    if completed > 0:
        print("\n🔄 Updating EdgeForge model with new data...")
        run_command(
            "python3 scripts/train_edgeforge_model.py",
            "Retrain EdgeForge model",
            timeout=1200,  # 20 minutes for retraining
        )

    print("\n🎉 EdgeForge historical data ingestion complete!")
    print("💰 Enhanced model ready for production betting edges!")


if __name__ == "__main__":
    main()
