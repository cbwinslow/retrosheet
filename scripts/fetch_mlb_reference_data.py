#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
import urllib.parse
import urllib.request
from collections.abc import Iterable

import psycopg2
from psycopg2.extras import Json


BASE_URL = "https://statsapi.mlb.com/api/v1"


def database_kwargs() -> dict[str, str]:
    return {
        "host": os.environ.get("PGHOST", "localhost"),
        "port": os.environ.get("PGPORT", "5432"),
        "dbname": os.environ.get("PGDATABASE", "retrosheet"),
        "user": os.environ.get("PGUSER", "postgres"),
        "password": os.environ.get("PGPASSWORD", ""),
    }


def fetch_json(endpoint: str, params: dict[str, object]) -> dict[str, object]:
    query = urllib.parse.urlencode(params)
    url = f"{BASE_URL}{endpoint}"
    if query:
        url = f"{url}?{query}"

    start = time.time()
    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            body = response.read().decode("utf-8")
            elapsed_ms = int((time.time() - start) * 1000)
            payload = json.loads(body)
            return {
                "success": response.status == 200,
                "endpoint": url,
                "payload": payload,
                "http_status": response.status,
                "response_time_ms": elapsed_ms,
                "error_text": None if response.status == 200 else f"HTTP {response.status}",
            }
    except Exception as exc:
        elapsed_ms = int((time.time() - start) * 1000)
        return {
            "success": False,
            "endpoint": url,
            "payload": {},
            "http_status": None,
            "response_time_ms": elapsed_ms,
            "error_text": str(exc),
        }


def store_reference_snapshot(
    *,
    endpoint_family: str,
    resource_key: str | None,
    season: int | None,
    request_params: dict[str, object],
    result: dict[str, object],
) -> None:
    payload = result["payload"]
    payload_json = json.dumps(payload, separators=(",", ":"))
    checksum = hashlib.sha256(payload_json.encode("utf-8")).hexdigest() if payload else None

    conn = psycopg2.connect(**database_kwargs())
    try:
        with conn.cursor() as cur:
            # Idempotent raw acquisition rule: once a successful snapshot exists for
            # an endpoint family/resource/season key, reruns should not append another.
            cur.execute(
                """
                INSERT INTO raw_mlb.reference_snapshots (
                    endpoint_family, resource_key, season, endpoint, payload,
                    request_params, http_status, response_time_ms, error_text, payload_checksum
                )
                SELECT %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM raw_mlb.reference_snapshots existing
                    WHERE existing.endpoint_family = %s
                      AND existing.resource_key IS NOT DISTINCT FROM %s
                      AND existing.season IS NOT DISTINCT FROM %s
                      AND existing.http_status = 200
                )
                """,
                (
                    endpoint_family,
                    resource_key,
                    season,
                    result["endpoint"],
                    Json(payload),
                    Json(request_params),
                    result["http_status"],
                    result["response_time_ms"],
                    result["error_text"],
                    checksum,
                    endpoint_family,
                    resource_key,
                    season,
                ),
            )
        conn.commit()
    finally:
        conn.close()


def chunks(values: list[int], chunk_size: int) -> Iterable[list[int]]:
    for index in range(0, len(values), chunk_size):
        yield values[index : index + chunk_size]


def fetch_teams_for_season(season: int, delay: float) -> list[int]:
    result = fetch_json("/teams", {"sportId": 1, "season": season})
    store_reference_snapshot(
        endpoint_family="teams",
        resource_key=f"season:{season}",
        season=season,
        request_params={"sportId": 1, "season": season},
        result=result,
    )
    time.sleep(delay)
    teams = result.get("payload", {}).get("teams", []) if result["success"] else []
    return [int(team["id"]) for team in teams if team.get("id") is not None]


def fetch_standings_for_season(season: int, delay: float) -> None:
    result = fetch_json("/standings", {"sportId": 1, "season": season})
    store_reference_snapshot(
        endpoint_family="standings",
        resource_key=f"season:{season}",
        season=season,
        request_params={"sportId": 1, "season": season},
        result=result,
    )
    time.sleep(delay)


def fetch_rosters_for_season(team_ids: list[int], season: int, delay: float) -> list[int]:
    player_ids: list[int] = []
    for team_id in team_ids:
        params = {"season": season}
        result = fetch_json(f"/teams/{team_id}/roster", params)
        store_reference_snapshot(
            endpoint_family="rosters",
            resource_key=f"season:{season}:team:{team_id}",
            season=season,
            request_params=params,
            result=result,
        )
        if result["success"]:
            for roster_entry in result.get("payload", {}).get("roster", []):
                person = roster_entry.get("person", {})
                if person.get("id") is not None:
                    player_ids.append(int(person["id"]))
        time.sleep(delay)
    return sorted(set(player_ids))


def fetch_people_for_season(player_ids: list[int], season: int, delay: float, batch_size: int) -> None:
    for batch in chunks(player_ids, batch_size):
        params = {"personIds": ",".join(str(player_id) for player_id in batch)}
        result = fetch_json("/people", params)
        batch_key = f"season:{season}:people:{batch[0]}-{batch[-1]}"
        store_reference_snapshot(
            endpoint_family="people",
            resource_key=batch_key,
            season=season,
            request_params=params,
            result=result,
        )
        time.sleep(delay)


def fetch_venues_for_season(team_ids: list[int], season: int, delay: float) -> None:
    venue_ids: set[int] = set()

    conn = psycopg2.connect(**database_kwargs())
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT payload
                FROM raw_mlb.reference_snapshots
                WHERE endpoint_family = 'teams'
                  AND season = %s
                ORDER BY fetched_at DESC
                LIMIT 1
                """,
                (season,),
            )
            row = cur.fetchone()
    finally:
        conn.close()

    if row:
        payload = row[0]
        for team in payload.get("teams", []):
            venue = team.get("venue", {})
            if venue.get("id") is not None:
                venue_ids.add(int(venue["id"]))

    if not venue_ids:
        for team_id in team_ids:
            result = fetch_json(f"/teams/{team_id}", {})
            if result["success"]:
                teams = result.get("payload", {}).get("teams", [])
                for team in teams:
                    venue = team.get("venue", {})
                    if venue.get("id") is not None:
                        venue_ids.add(int(venue["id"]))
            time.sleep(delay)

    for venue_id in sorted(venue_ids):
        result = fetch_json(f"/venues/{venue_id}", {})
        store_reference_snapshot(
            endpoint_family="venues",
            resource_key=f"venue:{venue_id}",
            season=season,
            request_params={},
            result=result,
        )
        time.sleep(delay)


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch MLB Stats API reference endpoint snapshots into raw_mlb.reference_snapshots")
    parser.add_argument("--start-season", type=int, required=True)
    parser.add_argument("--end-season", type=int, required=True)
    parser.add_argument(
        "--include",
        default="teams,standings,rosters,people,venues",
        help="Comma-separated endpoint families: teams,standings,rosters,people,venues",
    )
    parser.add_argument("--delay", type=float, default=0.5)
    parser.add_argument("--people-batch-size", type=int, default=50)
    args = parser.parse_args()

    include = {item.strip() for item in args.include.split(",") if item.strip()}

    for season in range(args.start_season, args.end_season + 1):
        print(f"fetching MLB reference data for season {season}")
        team_ids: list[int] = []
        if "teams" in include:
            team_ids = fetch_teams_for_season(season, args.delay)
            print(f"  teams fetched: {len(team_ids)}")
        if "standings" in include:
            fetch_standings_for_season(season, args.delay)
            print("  standings fetched")
        player_ids: list[int] = []
        if "rosters" in include:
            if not team_ids:
                team_ids = fetch_teams_for_season(season, args.delay)
            player_ids = fetch_rosters_for_season(team_ids, season, args.delay)
            print(f"  rosters fetched, distinct players: {len(player_ids)}")
        if "people" in include:
            if not player_ids:
                if not team_ids:
                    team_ids = fetch_teams_for_season(season, args.delay)
                player_ids = fetch_rosters_for_season(team_ids, season, args.delay)
            fetch_people_for_season(player_ids, season, args.delay, args.people_batch_size)
            print("  people fetched")
        if "venues" in include:
            if not team_ids:
                team_ids = fetch_teams_for_season(season, args.delay)
            fetch_venues_for_season(team_ids, season, args.delay)
            print("  venues fetched")


if __name__ == "__main__":
    main()
