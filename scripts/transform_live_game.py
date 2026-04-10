#!/usr/bin/env python3
"""
Transform source-preserved MLB live feed snapshots into canonical live tables.

This keeps raw JSON in `raw_mlb`, maps IDs through `bridge`, and upserts a
typed live layer in `core.live_games` and `core.live_events`.
"""

from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from typing import Any

import psycopg2
from psycopg2.extras import Json, execute_values


def database_kwargs() -> dict[str, str]:
    return {
        "host": os.environ.get("PGHOST", "localhost"),
        "port": os.environ.get("PGPORT", "5432"),
        "dbname": os.environ.get("PGDATABASE", "retrosheet"),
        "user": os.environ.get("PGUSER", "postgres"),
        "password": os.environ.get("PGPASSWORD", ""),
    }


@dataclass
class Snapshot:
    snapshot_id: int
    game_pk: int
    fetched_at: Any
    endpoint: str
    payload: dict[str, Any]


def table_columns(conn, schema: str, table: str) -> set[str]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = %s AND table_name = %s
            """,
            (schema, table),
        )
        return {row[0] for row in cur.fetchall()}


def fetch_latest_snapshot(conn, game_pk: int) -> Snapshot:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT snapshot_id, game_pk, fetched_at, endpoint, payload
            FROM raw_mlb.live_feed_snapshots
            WHERE game_pk = %s
            ORDER BY fetched_at DESC, snapshot_id DESC
            LIMIT 1
            """,
            (game_pk,),
        )
        row = cur.fetchone()
    if not row:
        raise ValueError(f"No live feed snapshot found for game_pk {game_pk}")
    return Snapshot(
        snapshot_id=row[0],
        game_pk=row[1],
        fetched_at=row[2],
        endpoint=row[3],
        payload=row[4],
    )


def query_optional_text(conn, sql: str, value: int | None, fallback: str) -> str:
    if value is None:
        return fallback
    with conn.cursor() as cur:
        cur.execute(sql, (value,))
        row = cur.fetchone()
    return row[0] if row and row[0] else fallback


def lookup_retrosheet_team_id(conn, mlb_team_id: int | None) -> str:
    return query_optional_text(
        conn,
        "SELECT retrosheet_team_id FROM bridge.team_xref WHERE mlb_team_id = %s",
        mlb_team_id,
        f"MLB{mlb_team_id}" if mlb_team_id is not None else "UNK",
    )


def lookup_retrosheet_player_id(conn, mlb_player_id: int | None) -> str:
    columns = table_columns(conn, "bridge", "player_xref")
    retrosheet_column = (
        "retrosheet_player_id" if "retrosheet_player_id" in columns else "retrosheet_id"
    )
    mlb_column = "mlb_player_id" if "mlb_player_id" in columns else "mlb_id"
    return query_optional_text(
        conn,
        f"SELECT {retrosheet_column} FROM bridge.player_xref WHERE {mlb_column} = %s",
        mlb_player_id,
        f"MLB{mlb_player_id}" if mlb_player_id is not None else "UNK",
    )


def lookup_retrosheet_park_id(conn, mlb_venue_id: int | None) -> str:
    return query_optional_text(
        conn,
        "SELECT retrosheet_park_id FROM bridge.park_xref WHERE mlb_venue_id = %s",
        mlb_venue_id,
        f"MLB{mlb_venue_id}" if mlb_venue_id is not None else "UNK",
    )


def lookup_game_id(
    conn,
    *,
    game_pk: int,
    home_team_id: str,
    away_team_id: str,
    game_date: str | None,
) -> str:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT retrosheet_game_id
            FROM bridge.game_xref
            WHERE mlb_game_pk = %s
            """,
            (game_pk,),
        )
        row = cur.fetchone()
    if row and row[0]:
        return row[0]

    if game_date and home_team_id != "UNK" and away_team_id != "UNK":
        compact_date = game_date.replace("-", "")
        return f"{home_team_id}{compact_date}0"
    return f"MLB{game_pk}"


def bases_mask_from_runners(runners: list[dict[str, Any]], key: str) -> int:
    mask = 0
    for runner in runners:
        base = runner.get("movement", {}).get(key)
        if base == "1B":
            mask |= 1
        elif base == "2B":
            mask |= 2
        elif base == "3B":
            mask |= 4
    return mask


def parse_runs_on_play(runners: list[dict[str, Any]]) -> int:
    return sum(
        1
        for runner in runners
        if runner.get("details", {}).get("isScoringEvent")
        or runner.get("movement", {}).get("isOut") is False
        and runner.get("movement", {}).get("end") == "score"
    )


def map_event_code(play: dict[str, Any]) -> tuple[int, int]:
    result = play.get("result", {})
    event_type = (result.get("eventType") or "").lower()
    details_event = (result.get("event") or "").lower()
    trajectory = (
        play.get("playEvents", [])[-1].get("hitData", {}).get("trajectory")
        if play.get("playEvents")
        else None
    )
    trajectory = (trajectory or "").lower()

    mapping = {
        "single": (20, 1),
        "double": (21, 2),
        "triple": (22, 3),
        "home_run": (23, 4),
        "walk": (14, 0),
        "intent_walk": (15, 0),
        "hit_by_pitch": (16, 0),
        "strikeout": (3, 0),
        "field_error": (18, 0),
        "error": (18, 0),
        "fielders_choice": (19, 0),
        "catcher_interf": (17, 0),
        "sac_bunt": (2, 0),
        "sac_fly": (2, 0),
        "force_out": (2, 0),
        "field_out": (2, 0),
        "grounded_into_double_play": (2, 0),
        "double_play": (2, 0),
        "triple_play": (2, 0),
    }
    if event_type in mapping:
        return mapping[event_type]

    if "walk" in details_event:
        return (14, 0)
    if "strikeout" in details_event:
        return (3, 0)
    if "single" in details_event:
        return (20, 1)
    if "double" in details_event:
        return (21, 2)
    if "triple" in details_event:
        return (22, 3)
    if "home run" in details_event:
        return (23, 4)
    if trajectory in {"ground_ball", "fly_ball", "line_drive", "popup"}:
        return (2, 0)
    return (0, 0)


def hands_from_play(play: dict[str, Any]) -> tuple[str, str]:
    matchup = play.get("matchup", {})
    batter_hand = matchup.get("batSide", {}).get("code") or "U"
    pitcher_hand = matchup.get("pitchHand", {}).get("code") or "U"
    return batter_hand, pitcher_hand


def transform_game(conn, snapshot: Snapshot) -> dict[str, Any]:
    payload = snapshot.payload
    game_data = payload.get("gameData", {})
    live_data = payload.get("liveData", {})
    teams = game_data.get("teams", {})
    home_team = teams.get("home", {})
    away_team = teams.get("away", {})
    venue = game_data.get("venue", {})
    linescore = live_data.get("linescore", {})
    status = game_data.get("status", {})

    home_team_id = lookup_retrosheet_team_id(conn, home_team.get("id"))
    away_team_id = lookup_retrosheet_team_id(conn, away_team.get("id"))
    park_id = lookup_retrosheet_park_id(conn, venue.get("id"))
    game_date = (game_data.get("datetime", {}).get("originalDate") or "")[:10] or None
    game_id = lookup_game_id(
        conn,
        game_pk=snapshot.game_pk,
        home_team_id=home_team_id,
        away_team_id=away_team_id,
        game_date=game_date,
    )

    return {
        "game_id": game_id,
        "mlb_game_pk": snapshot.game_pk,
        "season": int(game_data.get("game", {}).get("season") or 0) or None,
        "game_date": game_date,
        "home_team_id": home_team_id,
        "away_team_id": away_team_id,
        "home_team_name": home_team.get("name"),
        "away_team_name": away_team.get("name"),
        "park_id": park_id,
        "venue_name": venue.get("name"),
        "home_score": linescore.get("teams", {}).get("home", {}).get("runs", 0),
        "away_score": linescore.get("teams", {}).get("away", {}).get("runs", 0),
        "is_complete": status.get("abstractGameState") == "Final",
        "status_code": status.get("statusCode"),
        "detailed_state": status.get("detailedState"),
        "source_type": "mlb_live",
        "snapshot_id": snapshot.snapshot_id,
        "snapshot_fetched_at": snapshot.fetched_at,
        "raw_payload": payload,
    }


def transform_events(conn, snapshot: Snapshot, game_row: dict[str, Any]) -> list[dict[str, Any]]:
    payload = snapshot.payload
    plays = payload.get("liveData", {}).get("plays", {}).get("allPlays", [])
    season = game_row["season"]
    game_id = game_row["game_id"]

    rows: list[dict[str, Any]] = []
    for play in plays:
        about = play.get("about", {})
        result = play.get("result", {})
        matchup = play.get("matchup", {})
        runners = play.get("runners", [])
        batter = matchup.get("batter", {})
        pitcher = matchup.get("pitcher", {})
        batter_hand, pitcher_hand = hands_from_play(play)
        event_code, hit_value = map_event_code(play)
        event_type = (result.get("eventType") or "").lower()
        event_text = result.get("description", "")
        trajectory = (
            play.get("playEvents", [])[-1].get("hitData", {}).get("trajectory")
            if play.get("playEvents")
            else None
        )
        is_plate_appearance = bool(about.get("isComplete", True))
        is_at_bat = event_code not in (14, 15, 16, 17) and is_plate_appearance
        rows.append(
            {
                "game_id": game_id,
                "event_id": int(about.get("atBatIndex", 0)) + 1,
                "season": season,
                "inning": about.get("inning"),
                "is_bottom_inning": not about.get("isTopInning", True),
                "event_sequence": int(about.get("atBatIndex", 0)) + 1,
                "plate_appearance_index": about.get("atBatIndex"),
                "batter_id": lookup_retrosheet_player_id(conn, batter.get("id")),
                "pitcher_id": lookup_retrosheet_player_id(conn, pitcher.get("id")),
                "batter_hand": batter_hand,
                "pitcher_hand": pitcher_hand,
                "outs_before": about.get("halfInningOuts", 0),
                "balls": play.get("count", {}).get("balls", 0),
                "strikes": play.get("count", {}).get("strikes", 0),
                "start_bases": bases_mask_from_runners(runners, "originBase"),
                "event_code": event_code,
                "event_text": event_text,
                "mlb_event_type": event_type or None,
                "event_type_description": result.get("event"),
                "trajectory": trajectory,
                "is_at_bat": is_at_bat,
                "is_plate_appearance": is_plate_appearance,
                "hit_value": hit_value,
                "is_hit": hit_value > 0,
                "is_walk": event_code in (14, 15),
                "is_strikeout": event_code == 3,
                "is_home_run": event_code == 23,
                "runs_on_play": parse_runs_on_play(runners),
                "rbi": result.get("rbi", 0),
                "home_score_after": result.get("homeScore"),
                "away_score_after": result.get("awayScore"),
                "source_type": "mlb_live",
                "mlb_game_pk": snapshot.game_pk,
                "snapshot_id": snapshot.snapshot_id,
                "raw_play": play,
            }
        )
    return rows


def upsert_live_game(conn, game_row: dict[str, Any]) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO core.live_games (
                game_id, mlb_game_pk, season, game_date, home_team_id, away_team_id,
                home_team_name, away_team_name, park_id, venue_name, home_score, away_score,
                is_complete, status_code, detailed_state, source_type, snapshot_id,
                snapshot_fetched_at, raw_payload, updated_at
            ) VALUES (
                %(game_id)s, %(mlb_game_pk)s, %(season)s, %(game_date)s, %(home_team_id)s, %(away_team_id)s,
                %(home_team_name)s, %(away_team_name)s, %(park_id)s, %(venue_name)s, %(home_score)s, %(away_score)s,
                %(is_complete)s, %(status_code)s, %(detailed_state)s, %(source_type)s, %(snapshot_id)s,
                %(snapshot_fetched_at)s, %(raw_payload)s::jsonb, now()
            )
            ON CONFLICT (game_id) DO UPDATE
            SET mlb_game_pk = EXCLUDED.mlb_game_pk,
                season = EXCLUDED.season,
                game_date = EXCLUDED.game_date,
                home_team_id = EXCLUDED.home_team_id,
                away_team_id = EXCLUDED.away_team_id,
                home_team_name = EXCLUDED.home_team_name,
                away_team_name = EXCLUDED.away_team_name,
                park_id = EXCLUDED.park_id,
                venue_name = EXCLUDED.venue_name,
                home_score = EXCLUDED.home_score,
                away_score = EXCLUDED.away_score,
                is_complete = EXCLUDED.is_complete,
                status_code = EXCLUDED.status_code,
                detailed_state = EXCLUDED.detailed_state,
                source_type = EXCLUDED.source_type,
                snapshot_id = EXCLUDED.snapshot_id,
                snapshot_fetched_at = EXCLUDED.snapshot_fetched_at,
                raw_payload = EXCLUDED.raw_payload,
                updated_at = now()
            """,
            {
                **game_row,
                "raw_payload": Json(game_row["raw_payload"]),
            },
        )


def upsert_live_events(conn, event_rows: list[dict[str, Any]]) -> None:
    if not event_rows:
        return
    columns = [
        "game_id",
        "event_id",
        "season",
        "inning",
        "is_bottom_inning",
        "event_sequence",
        "batter_id",
        "pitcher_id",
        "batter_hand",
        "pitcher_hand",
        "outs_before",
        "balls",
        "strikes",
        "start_bases",
        "event_code",
        "event_text",
        "is_at_bat",
        "is_plate_appearance",
        "hit_value",
        "is_hit",
        "is_walk",
        "is_strikeout",
        "is_home_run",
        "runs_on_play",
        "rbi",
        "source_type",
        "raw_play",
        "mlb_game_pk",
        "snapshot_id",
        "plate_appearance_index",
        "mlb_event_type",
        "event_type_description",
        "trajectory",
        "home_score_after",
        "away_score_after",
    ]
    values = [
        tuple(Json(row[column]) if column == "raw_play" else row[column] for column in columns)
        for row in event_rows
    ]
    with conn.cursor() as cur:
        execute_values(
            cur,
            f"""
            INSERT INTO core.live_events (
                {", ".join(columns)}
            ) VALUES %s
            ON CONFLICT (game_id, event_id) DO UPDATE
            SET season = EXCLUDED.season,
                inning = EXCLUDED.inning,
                is_bottom_inning = EXCLUDED.is_bottom_inning,
                event_sequence = EXCLUDED.event_sequence,
                batter_id = EXCLUDED.batter_id,
                pitcher_id = EXCLUDED.pitcher_id,
                batter_hand = EXCLUDED.batter_hand,
                pitcher_hand = EXCLUDED.pitcher_hand,
                outs_before = EXCLUDED.outs_before,
                balls = EXCLUDED.balls,
                strikes = EXCLUDED.strikes,
                start_bases = EXCLUDED.start_bases,
                event_code = EXCLUDED.event_code,
                event_text = EXCLUDED.event_text,
                is_at_bat = EXCLUDED.is_at_bat,
                is_plate_appearance = EXCLUDED.is_plate_appearance,
                hit_value = EXCLUDED.hit_value,
                is_hit = EXCLUDED.is_hit,
                is_walk = EXCLUDED.is_walk,
                is_strikeout = EXCLUDED.is_strikeout,
                is_home_run = EXCLUDED.is_home_run,
                runs_on_play = EXCLUDED.runs_on_play,
                rbi = EXCLUDED.rbi,
                source_type = EXCLUDED.source_type,
                raw_play = EXCLUDED.raw_play,
                mlb_game_pk = EXCLUDED.mlb_game_pk,
                snapshot_id = EXCLUDED.snapshot_id,
                plate_appearance_index = EXCLUDED.plate_appearance_index,
                mlb_event_type = EXCLUDED.mlb_event_type,
                event_type_description = EXCLUDED.event_type_description,
                trajectory = EXCLUDED.trajectory,
                home_score_after = EXCLUDED.home_score_after,
                away_score_after = EXCLUDED.away_score_after,
                updated_at = now()
            """,
            values,
        )


def delete_stale_live_rows(conn, *, mlb_game_pk: int, canonical_game_id: str) -> None:
    legacy_game_id = f"MLB{mlb_game_pk}"
    with conn.cursor() as cur:
        cur.execute(
            """
            DELETE FROM core.live_events
            WHERE (
                    mlb_game_pk = %s
                    OR game_id = %s
                  )
              AND game_id <> %s
            """,
            (mlb_game_pk, legacy_game_id, canonical_game_id),
        )
        cur.execute(
            """
            DELETE FROM core.live_games
            WHERE (
                    mlb_game_pk = %s
                    OR game_id = %s
                  )
              AND game_id <> %s
            """,
            (mlb_game_pk, legacy_game_id, canonical_game_id),
        )


def transform_live_game(game_pk: int) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    conn = psycopg2.connect(**database_kwargs())
    try:
        snapshot = fetch_latest_snapshot(conn, game_pk)
        game_row = transform_game(conn, snapshot)
        event_rows = transform_events(conn, snapshot, game_row)
        delete_stale_live_rows(
            conn,
            mlb_game_pk=snapshot.game_pk,
            canonical_game_id=game_row["game_id"],
        )
        upsert_live_game(conn, game_row)
        upsert_live_events(conn, event_rows)
        conn.commit()
        return game_row, event_rows
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Transform a stored MLB live-feed snapshot into canonical live tables."
    )
    parser.add_argument("--game-pk", type=int, required=True)
    args = parser.parse_args()

    try:
        game_row, event_rows = transform_live_game(args.game_pk)
    except Exception as exc:
        print(f"Error: {exc}")
        raise SystemExit(1) from exc

    print(
        f"Transformed snapshot for game_pk {args.game_pk} into {game_row['game_id']} "
        f"with {len(event_rows)} live events."
    )


if __name__ == "__main__":
    main()
