#!/usr/bin/env python3
"""
Validation script for MLB ingestion.

Runs the stored procedure ``analysis.validate_mlb_data()`` and prints a concise
summary.  The script exits with status 0 when no warnings are emitted and with
status 1 otherwise, making it suitable for CI pipelines.

Optional arguments:
  --recent          Limit validation to games fetched in the last 24 hours.
  --hours N         Limit validation to the last N hours (default 24).
"""

import argparse
import sys
import psycopg2

from scripts.utility.setup_mlb_analytics import database_kwargs


def run_validation(limit_hours: int = None) -> int:
    """Execute the validation procedure and return the number of warnings.

    If ``limit_hours`` is provided, the procedure is called with a temporary
    view that filters ``core.live_games`` to recent rows.  The stored procedure
    itself does not accept parameters, so we create a session‑local view that
    the procedure will read.
    """
    conn = psycopg2.connect(**database_kwargs())
    try:
        with conn.cursor() as cur:
            if limit_hours is not None:
                cur.execute(
                    """
                    CREATE OR REPLACE TEMP VIEW recent_live_games AS
                    SELECT * FROM core.live_games
                    WHERE fetched_at >= now() - interval '%s hour';
                    """,
                    (limit_hours,)
                )
                # The validation procedure references core.live_games, so we
                # temporarily rename the table within the session.
                cur.execute(
                    """
                    ALTER TABLE core.live_games RENAME TO live_games_original;
                    ALTER TABLE recent_live_games RENAME TO live_games;
                    """
                )

            cur.execute("CALL analysis.validate_mlb_data();")
            # Capture NOTICE and WARNING messages from the procedure.
            notices = conn.notices
            warning_count = sum(1 for n in notices if "WARNING" in n)
            if warning_count:
                print("⚠️ Validation completed with warnings:")
                for n in notices:
                    if "WARNING" in n:
                        print(n.strip())
            else:
                print("✅ Validation completed with no warnings.")
            return warning_count
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="Validate MLB ingestion data")
    parser.add_argument(
        "--hours",
        type=int,
        default=None,
        help="Limit validation to the last N hours (default: all data)",
    )
    args = parser.parse_args()

    warnings = run_validation(limit_hours=args.hours)
    sys.exit(1 if warnings else 0)


if __name__ == "__main__":
    main()
