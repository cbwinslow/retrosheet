#!/usr/bin/env python3
"""
Replay stored MLB live-feed snapshots through the repaired transform path.

This script is intentionally additive:
- it reads the latest successful raw snapshot per game from `raw_mlb`
- it reuses `scripts/transform_live_game.py` upsert logic
- it can target only rows that still carry legacy `MLB###` fallback ids
"""

from __future__ import annotations

import argparse
import os
from collections.abc import Sequence

import psycopg2

from transform_live_game import transform_live_game


def database_kwargs() -> dict[str, str]:
    return {
        "host": os.environ.get("PGHOST", "localhost"),
        "port": os.environ.get("PGPORT", "5432"),
        "dbname": os.environ.get("PGDATABASE", "retrosheet"),
        "user": os.environ.get("PGUSER", "postgres"),
        "password": os.environ.get("PGPASSWORD", ""),
    }


def candidate_game_pks(
    conn,
    *,
    season_from: int | None,
    season_to: int | None,
    only_fallback_rows: bool,
    limit: int | None,
) -> list[int]:
    snapshot_filters: list[str] = ["snap.http_status = 200"]
    outer_filters: list[str] = []
    params: list[object] = []

    if season_from is not None:
        snapshot_filters.append("COALESCE(snap.season, 0) >= %s")
        params.append(season_from)
    if season_to is not None:
        snapshot_filters.append("COALESCE(snap.season, 0) <= %s")
        params.append(season_to)
    if only_fallback_rows:
        outer_filters.append(
            """
            (
                lg.game_id IS NULL
                OR lg.home_team_id LIKE 'MLB%%'
                OR lg.away_team_id LIKE 'MLB%%'
                OR lg.park_id LIKE 'MLB%%'
                OR lg.game_id LIKE 'MLB%%'
            )
            """
        )

    sql = f"""
        WITH latest_success AS (
            SELECT DISTINCT ON (snap.game_pk)
                snap.game_pk,
                snap.season,
                snap.fetched_at
            FROM raw_mlb.live_feed_snapshots snap
            WHERE {" AND ".join(snapshot_filters)}
            ORDER BY snap.game_pk, snap.fetched_at DESC, snap.snapshot_id DESC
        )
        SELECT latest_success.game_pk
        FROM latest_success
        LEFT JOIN core.live_games lg
          ON lg.mlb_game_pk = latest_success.game_pk
        {"WHERE " + " AND ".join(outer_filters) if outer_filters else ""}
        ORDER BY latest_success.season NULLS LAST, latest_success.game_pk
    """
    if limit is not None:
        sql += " LIMIT %s"
        params.append(limit)

    with conn.cursor() as cur:
        cur.execute(sql, params)
        return [row[0] for row in cur.fetchall()]


def replay_games(game_pks: Sequence[int]) -> tuple[int, int]:
    processed = 0
    total_events = 0
    for game_pk in game_pks:
        game_row, event_rows = transform_live_game(game_pk)
        processed += 1
        total_events += len(event_rows)
        print(
            f"Replayed game_pk {game_pk} -> {game_row['game_id']} with {len(event_rows)} live events."
        )
    return processed, total_events


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Replay stored MLB live snapshots through the repaired bridge-aware transform path."
    )
    parser.add_argument("--season-from", type=int, default=None)
    parser.add_argument("--season-to", type=int, default=None)
    parser.add_argument(
        "--only-fallback-rows",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Only replay games whose current core.live_games row is missing or still uses MLB### fallback ids.",
    )
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    conn = psycopg2.connect(**database_kwargs())
    try:
        game_pks = candidate_game_pks(
            conn,
            season_from=args.season_from,
            season_to=args.season_to,
            only_fallback_rows=args.only_fallback_rows,
            limit=args.limit,
        )
    finally:
        conn.close()

    print(f"Selected {len(game_pks)} game_pks for replay.")
    processed, total_events = replay_games(game_pks)
    print(f"Replay complete: {processed} games, {total_events} live events upserted.")


if __name__ == "__main__":
    main()
