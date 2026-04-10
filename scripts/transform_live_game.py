#!/usr/bin/env python3
"""
Transform MLB live feed data into core schema for live prediction.

This script takes MLB live game feed snapshots and transforms them into
the same core.events and core.games schema used for historical data,
enabling live prediction with trained models.
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

import psycopg2
import pandas as pd
from sqlalchemy import URL, create_engine


ROOT = Path(__file__).resolve().parents[1]


def database_kwargs() -> dict[str, str]:
    return {
        "host": os.environ.get("PGHOST", "localhost"),
        "port": os.environ.get("PGPORT", "5432"),
        "dbname": os.environ.get("PGDATABASE", "retrosheet"),
        "user": os.environ.get("PGUSER", "postgres"),
        "password": os.environ.get("PGPASSWORD", ""),
    }


def database_url() -> str | URL:
    if os.environ.get("DATABASE_URL"):
        return os.environ["DATABASE_URL"]
    kwargs = database_kwargs()
    return URL.create(
        "postgresql+psycopg2",
        username=kwargs["user"],
        password=kwargs["password"] or None,
        host=kwargs["host"],
        port=int(kwargs["port"]),
        database=kwargs["dbname"],
    )


def get_live_feed(game_pk: int) -> Dict[str, Any]:
    """Get the most recent live feed snapshot for a game."""
    conn = psycopg2.connect(**database_kwargs())
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT payload
                FROM raw_mlb.live_feed_snapshots
                WHERE game_pk = %s
                ORDER BY fetched_at DESC
                LIMIT 1
                """,
                (game_pk,),
            )
            row = cur.fetchone()
            if not row:
                raise ValueError(f"No live feed data found for game_pk {game_pk}")
            return row[0]
    finally:
        conn.close()


def lookup_retrosheet_team_id(mlb_team_id: int, conn) -> str:
    """Look up Retrosheet team ID from MLB team ID."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT retrosheet_team_id FROM bridge.team_xref WHERE mlb_team_id = %s",
            (mlb_team_id,),
        )
        row = cur.fetchone()
        return row[0] if row else f"MLB{mlb_team_id}"


def lookup_retrosheet_player_id(mlb_player_id: int, conn) -> str:
    """Look up Retrosheet player ID from MLB player ID."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT retrosheet_id FROM bridge.player_xref WHERE mlb_id = %s",
            (mlb_player_id,),
        )
        row = cur.fetchone()
        return row[0] if row else f"MLB{mlb_player_id}"


def transform_live_game(feed: Dict[str, Any]) -> Dict[str, Any]:
    """Transform MLB live feed into core.games format."""
    conn = psycopg2.connect(**database_kwargs())
    try:
        game_data = feed.get("gameData", {})
        live_data = feed.get("liveData", {})

        # Extract basic game info
        game_pk = game_data.get("game", {}).get("pk")
        season = game_data.get("game", {}).get("season")
        game_date = game_data.get("datetime", {}).get("dateTime")

        # Team info
        teams = game_data.get("teams", {})
        home_team = teams.get("home", {})
        away_team = teams.get("away", {})

        # Look up Retrosheet team IDs from bridge tables
        home_team_id = lookup_retrosheet_team_id(home_team.get("id"), conn)
        away_team_id = lookup_retrosheet_team_id(away_team.get("id"), conn)

        # Score info
        linescore = live_data.get("linescore", {})
        home_score = linescore.get("teams", {}).get("home", {}).get("runs", 0)
        away_score = linescore.get("teams", {}).get("away", {}).get("runs", 0)

        # Game status
        status = live_data.get("gameData", {}).get("status", {})
        is_complete = status.get("abstractGameState") == "Final"

        return {
            "game_id": f"MLB{game_pk}",
            "season": season,
            "game_date": game_date.split("T")[0] if game_date else None,
            "home_team_id": home_team_id,
            "away_team_id": away_team_id,
            "home_team_name": home_team.get("name"),
            "away_team_name": away_team.get("name"),
            "park_id": f"MLB{game_data.get('venue', {}).get('id', 'UNK')}",
            "home_score": home_score,
            "away_score": away_score,
            "is_complete": is_complete,
            "source_type": "mlb_live",
            "raw_payload": feed,
        }
    finally:
        conn.close()


def transform_live_events(feed: Dict[str, Any], game_id: str) -> List[Dict[str, Any]]:
    """Transform MLB live feed plays into core.events format."""
    conn = psycopg2.connect(**database_kwargs())
    try:
        live_data = feed.get("liveData", {})
        plays = live_data.get("plays", {}).get("allPlays", [])

        events = []
        for play_idx, play in enumerate(plays):
            # Each play can have multiple events (pitches, etc.)
            # For simplicity, we'll create one event per play result

            result = play.get("result", {})
            about = play.get("about", {})

            inning = about.get("inning")
            is_top = about.get("isTopInning", True)
            event_idx = about.get("atBatIndex", play_idx)

            # Batter info - look up Retrosheet IDs
            batter = play.get("matchup", {}).get("batter", {})
            pitcher = play.get("matchup", {}).get("pitcher", {})

            batter_id = (
                lookup_retrosheet_player_id(batter.get("id"), conn)
                if batter.get("id")
                else "UNK"
            )
            pitcher_id = (
                lookup_retrosheet_player_id(pitcher.get("id"), conn)
                if pitcher.get("id")
                else "UNK"
            )

            # Count info
            count = play.get("count", {})
            balls = count.get("balls", 0)
            strikes = count.get("strikes", 0)

            # Base state
            runners = play.get("runners", [])
            bases = 0
            for runner in runners:
                if (
                    runner.get("movement", {}).get("end")
                    and runner.get("movement", {}).get("end") != "OUT"
                ):
                    base = runner.get("movement", {}).get("end")
                    if base == "1B":
                        bases |= 1
                    elif base == "2B":
                        bases |= 2
                    elif base == "3B":
                        bases |= 4

            # Outs
            outs = about.get("halfInningOuts", 0)

            # Event details
            event_type = result.get("type", "unknown")
            event_desc = result.get("description", "")
            rbi = result.get("rbi", 0)
            runs_on_play = len(
                [
                    r
                    for r in runners
                    if r.get("movement", {}).get("run", {}).get("isScoringEvent")
                ]
            )

            # Determine event code (simplified mapping)
            if "single" in event_desc.lower():
                event_code = 20  # Single
                hit_value = 1
            elif "double" in event_desc.lower():
                event_code = 21  # Double
                hit_value = 2
            elif "triple" in event_desc.lower():
                event_code = 22  # Triple
                hit_value = 3
            elif "home run" in event_desc.lower():
                event_code = 23  # Home run
                hit_value = 4
            elif "strikeout" in event_desc.lower():
                event_code = 3  # Strikeout
                hit_value = 0
            elif "walk" in event_desc.lower():
                event_code = 14  # Walk
                hit_value = 0
            else:
                event_code = 0  # Unknown/other
                hit_value = 0

            # Plate appearance flags
            is_at_bat = event_type in ["atBat", "action"]
            is_hit = hit_value > 0
            is_walk = event_code == 14
            is_strikeout = event_code == 3
            is_home_run = hit_value == 4

            events.append(
                {
                    "game_id": game_id,
                    "event_id": event_idx + 1,
                    "season": feed.get("gameData", {}).get("game", {}).get("season"),
                    "inning": inning,
                    "is_bottom_inning": not is_top,
                    "event_sequence": event_idx + 1,
                    "batter_id": batter_id,
                    "pitcher_id": pitcher_id,
                    "batter_hand": batter.get("batSide", {}).get("code", "U"),
                    "pitcher_hand": pitcher.get("pitchHand", {}).get("code", "U"),
                    "outs_before": outs,
                    "balls": balls,
                    "strikes": strikes,
                    "start_bases": bases,
                    "event_code": event_code,
                    "event_text": event_desc,
                    "is_at_bat": is_at_bat,
                    "is_plate_appearance": is_at_bat,
                    "hit_value": hit_value,
                    "is_hit": is_hit,
                    "is_walk": is_walk,
                    "is_strikeout": is_strikeout,
                    "is_home_run": is_home_run,
                    "runs_on_play": runs_on_play,
                    "rbi": rbi,
                    "source_type": "mlb_live",
                    "raw_play": play,
                }
            )

        return events
    finally:
        conn.close()


def store_live_game_data(
    game_data: Dict[str, Any], events: List[Dict[str, Any]]
) -> None:
    """Store transformed live game data in core tables."""
    engine = create_engine(database_url())
    try:
        # Store game data (exclude raw_payload for now)
        game_data_copy = game_data.copy()
        game_data_copy.pop("raw_payload", None)
        game_df = pd.DataFrame([game_data_copy])
        game_df.to_sql(
            "live_games", engine, schema="core", if_exists="replace", index=False
        )

        # Store event data
        if events:
            # Remove raw_play from events to avoid JSON serialization issues
            clean_events = []
            for event in events:
                event_copy = event.copy()
                event_copy.pop("raw_play", None)
                clean_events.append(event_copy)

            events_df = pd.DataFrame(clean_events)
            events_df.to_sql(
                "live_events", engine, schema="core", if_exists="replace", index=False
            )

        print(f"Stored {len(events)} live events for game {game_data['game_id']}")

    finally:
        engine.dispose()


def main():
    parser = argparse.ArgumentParser(
        description="Transform MLB live feed into core schema"
    )
    parser.add_argument(
        "--game-pk", type=int, required=True, help="MLB game primary key"
    )

    args = parser.parse_args()

    try:
        # Get live feed data
        feed = get_live_feed(args.game_pk)
        print(f"Processing live feed for game {args.game_pk}")

        # Transform data
        game_data = transform_live_game(feed)
        events = transform_live_events(feed, game_data["game_id"])

        # Store in database
        store_live_game_data(game_data, events)

        print(
            f"Successfully transformed {len(events)} events for live game {game_data['game_id']}"
        )

    except Exception as e:
        print(f"Error: {e}")
        exit(1)


if __name__ == "__main__":
    main()
