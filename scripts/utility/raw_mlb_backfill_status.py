#!/usr/bin/env python3
from __future__ import annotations

import os
from collections.abc import Sequence

import psycopg2


def database_kwargs() -> dict[str, str]:
    return {
        "host": os.environ.get("PGHOST", "localhost"),
        "port": os.environ.get("PGPORT", "5432"),
        "dbname": os.environ.get("PGDATABASE", "retrosheet"),
        "user": os.environ.get("PGUSER", "postgres"),
        "password": os.environ.get("PGPASSWORD", ""),
    }


def print_table(headers: Sequence[str], rows: Sequence[Sequence[object]]) -> None:
    widths = [len(header) for header in headers]
    for row in rows:
        for index, value in enumerate(row):
            widths[index] = max(widths[index], len(str(value)))

    header_line = " | ".join(
        str(header).ljust(widths[index]) for index, header in enumerate(headers)
    )
    divider = "-+-".join("-" * width for width in widths)
    print(header_line)
    print(divider)
    for row in rows:
        print(" | ".join(str(value).ljust(widths[index]) for index, value in enumerate(row)))


def main() -> None:
    conn = psycopg2.connect(**database_kwargs())
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    (SELECT COUNT(*) FROM raw_mlb.schedule_snapshots),
                    (SELECT COUNT(*) FROM raw_mlb.schedule_snapshots WHERE http_status = 200),
                    (SELECT COUNT(*) FROM raw_mlb.live_feed_snapshots),
                    (SELECT COUNT(*) FROM raw_mlb.live_feed_snapshots WHERE http_status = 200),
                    (SELECT COUNT(*) FROM raw_mlb.reference_snapshots),
                    (SELECT COUNT(*) FROM core.live_games),
                    (SELECT COUNT(*) FROM core.live_events)
                """
            )
            totals = cur.fetchone()

            cur.execute(
                """
                SELECT
                    COALESCE(season, EXTRACT(YEAR FROM game_date)::integer) AS season,
                    COUNT(*) AS total_snapshots,
                    COUNT(*) FILTER (WHERE http_status = 200) AS successful_snapshots
                FROM raw_mlb.live_feed_snapshots
                WHERE COALESCE(season, EXTRACT(YEAR FROM game_date)::integer) BETWEEN 2000 AND 2025
                GROUP BY 1
                ORDER BY 1
                """
            )
            live_feed_by_season = cur.fetchall()

            cur.execute(
                """
                SELECT
                    endpoint_family,
                    COUNT(*) AS snapshot_count,
                    COUNT(DISTINCT season) FILTER (WHERE season BETWEEN 2000 AND 2025) AS season_count
                FROM raw_mlb.reference_snapshots
                GROUP BY 1
                ORDER BY 1
                """
            )
            reference_by_family = cur.fetchall()
    finally:
        conn.close()

    print("Raw MLB Backfill Status")
    print("")
    print_table(
        (
            "metric",
            "value",
        ),
        (
            ("schedule_snapshots", totals[0]),
            ("schedule_snapshots_http_200", totals[1]),
            ("live_feed_snapshots", totals[2]),
            ("live_feed_snapshots_http_200", totals[3]),
            ("reference_snapshots", totals[4]),
            ("core.live_games", totals[5]),
            ("core.live_events", totals[6]),
        ),
    )

    print("")
    print("Live Feed Coverage By Season")
    print_table(
        ("season", "total_snapshots", "successful_snapshots"),
        [(season, total, successful) for season, total, successful in live_feed_by_season],
    )

    print("")
    print("Reference Snapshot Coverage")
    print_table(
        ("endpoint_family", "snapshot_count", "distinct_seasons"),
        [(family, count, season_count) for family, count, season_count in reference_by_family],
    )


if __name__ == "__main__":
    main()
