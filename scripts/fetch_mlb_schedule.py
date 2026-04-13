#!/usr/bin/env python3
"""
Fetch MLB schedule and identify active/in-progress games for live data ingestion.

This script queries the MLB Stats API for the current day's schedule and identifies
games that are currently in progress or recently completed, making them candidates
for live data ingestion.
"""

from __future__ import annotations

import argparse
import json
import urllib.request
from datetime import datetime, timedelta
from typing import List, Dict, Any


def fetch_mlb_schedule(date: str) -> Dict[str, Any]:
    """Fetch MLB schedule for a specific date."""
    url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={date}"
    print(f"Fetching schedule from: {url}")

    with urllib.request.urlopen(url, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def get_active_games(schedule_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract games that are currently active (in progress or recently completed)."""
    active_games = []

    dates = schedule_data.get("dates", [])
    for date_info in dates:
        games = date_info.get("games", [])
        for game in games:
            status = game.get("status", {})
            abstract_state = status.get("abstractGameState", "")

            # Consider games that are live, in progress, or recently final
            if abstract_state in ["Live", "In Progress", "Final"]:
                active_games.append(
                    {
                        "game_pk": game["gamePk"],
                        "status": abstract_state,
                        "home_team": game["teams"]["home"]["team"]["name"],
                        "away_team": game["teams"]["away"]["team"]["name"],
                        "home_score": game.get("teams", {})
                        .get("home", {})
                        .get("score", 0),
                        "away_score": game.get("teams", {})
                        .get("away", {})
                        .get("score", 0),
                        "inning": game.get("inning", 0),
                        "is_top_inning": game.get("isTopInning", True),
                        "game_date": game.get("gameDate"),
                    }
                )

    return active_games


def main():
    parser = argparse.ArgumentParser(description="Fetch MLB schedule and active games")
    parser.add_argument(
        "--date",
        default=datetime.now().strftime("%Y-%m-%d"),
        help="Date to fetch schedule for (YYYY-MM-DD format, default: today)",
    )
    parser.add_argument(
        "--yesterday",
        action="store_true",
        help="Also check yesterday's games for recently completed ones",
    )

    args = parser.parse_args()

    dates_to_check = [args.date]
    if args.yesterday:
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        dates_to_check.append(yesterday)

    all_active_games = []

    for date in dates_to_check:
        try:
            schedule = fetch_mlb_schedule(date)
            active_games = get_active_games(schedule)
            print(f"Found {len(active_games)} active games for {date}")

            for game in active_games:
                status_indicator = "🔴" if game["status"] == "Live" else "⚫"
                inning_info = ""
                if game["status"] == "Live":
                    inning_info = f" (inning {game['inning']}, {'top' if game['is_top_inning'] else 'bottom'})"

                print(
                    f"  {status_indicator} {game['game_pk']}: {game['away_team']} @ {game['home_team']} "
                    f"({game['away_score']}-{game['home_score']}){inning_info}"
                )

            all_active_games.extend(active_games)

        except Exception as e:
            print(f"Error fetching schedule for {date}: {e}")

    if all_active_games:
        print(f"\nTotal active games found: {len(all_active_games)}")
        print("\nTo ingest live data for these games, run:")
        for game in all_active_games[:5]:  # Show first 5 as examples
            print(
                f"  python3 scripts/warehouse.py fetch-live-game --game-pk {game['game_pk']}"
            )
        if len(all_active_games) > 5:
            print(f"  ... and {len(all_active_games) - 5} more")
    else:
        print("\nNo active games found.")


if __name__ == "__main__":
    main()
