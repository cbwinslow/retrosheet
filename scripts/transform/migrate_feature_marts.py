#!/usr/bin/env python3
"""Run SQL migration files that create/refresh feature marts.

This script executes all ``*.sql`` files in the ``sql`` directory that are
related to feature marts (files starting with ``05`` or ``06`` or ``08``).
It can be run in a dry‑run mode to preview the commands without applying
them.

Usage:
    python scripts/migrate_feature_marts.py [--dry-run]

The script expects a PostgreSQL database reachable via the ``DATABASE_URL``
environment variable (or the default ``postgresql://localhost/retrosheet``).
"""

import os
import subprocess
import sys
from pathlib import Path


DRY_RUN = '--dry-run' in sys.argv

# Resolve the database URL – fallback to a local default
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://localhost/retrosheet')


def run_sql_file(sql_path: Path) -> None:
    """Execute a single SQL file using ``psql``.

    Args:
        sql_path: Path to the ``.sql`` file.
    """
    cmd = [
        'psql',
        DATABASE_URL,
        '-f',
        str(sql_path),
    ]
    if DRY_RUN:
        print(f"[dry‑run] Would execute: {' '.join(cmd)}")
        return
    print(f'Executing {sql_path.name} …')
    subprocess.check_call(cmd)


def main() -> None:
    sql_dir = Path(__file__).resolve().parent.parent / 'sql'
    if not sql_dir.is_dir():
        print(f'SQL directory not found: {sql_dir}')
        sys.exit(1)

    # Select files that are part of the feature‑mart pipeline
    pattern = '[05][0-9]*_*.sql'
    sql_files = sorted(sql_dir.glob(pattern))
    if not sql_files:
        print('No feature‑mart SQL files found.')
        return

    for sql_file in sql_files:
        run_sql_file(sql_file)

    # Refresh materialized views if any were created
    refresh_cmd = [
        'psql',
        DATABASE_URL,
        '-c',
        'SELECT pg_catalog.pg_reload_conf();',
    ]
    if not DRY_RUN:
        # Refresh all materialized views concurrently
        refresh_sql = (
            "DO $$ DECLARE r RECORD; BEGIN "
            "FOR r IN SELECT schemaname, matviewname FROM pg_matviews LOOP "
            "EXECUTE format('REFRESH MATERIALIZED VIEW CONCURRENTLY %I.%I', r.schemaname, r.matviewname); "
            "END LOOP; END $$;"
        )
        subprocess.check_call(['psql', DATABASE_URL, '-c', refresh_sql])


if __name__ == '__main__':
    main()
