#!/usr/bin/env python3
"""
File: scripts/check_extensions.py
Purpose: Check currently installed PostgreSQL extensions
Author: Agent KiloSwift
Date: 2026-04-27
Usage: uv run python scripts/check_extensions.py
Dependencies: psycopg, sqlalchemy
Notes: Verifies all required and optional extensions for the retrosheet warehouse
"""

import sys

from baseball.core.db import get_db_connection


# Required extensions for core functionality
REQUIRED_EXTENSIONS = [
    'plpgsql',      # Default PostgreSQL procedural language
    'uuid-ossp',    # UUID generation
    'pg_trgm',      # Trigram matching for fuzzy searches
    'btree_gin',    # GIN indexes on B-tree
    'btree_gist',   # GiST indexes on B-tree
]

# Recommended optional extensions
OPTIONAL_EXTENSIONS = [
    'pg_cron',           # Job scheduling (HIGH priority)
    'pg_stat_statements', # Query performance monitoring (HIGH priority)
    'plpython3u',        # Python integration (MEDIUM priority)
    'vector',            # pgvector for vector similarity (HIGH priority)
    'postgis',           # Geospatial (LOW priority)
    'timescaledb',       # Time-series (LOW priority)
]

def check_extension(conn, ext_name):
    """Check if an extension is installed and return its version."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT name, default_version, installed_version
            FROM pg_available_extensions
            WHERE name = %s AND installed_version IS NOT NULL
        """, (ext_name,))
        return cur.fetchone()

def main():
    print('=' * 60)
    print('PostgreSQL Extension Status Check')
    print('=' * 60)

    try:
        conn = get_db_connection()
    except Exception as e:
        print(f'❌ ERROR: Could not connect to database: {e}')
        sys.exit(1)

    print(f"\n{'Extension':<25} {'Status':<12} {'Installed Version':<20} {'Default Version':<18}")
    print('-' * 75)

    missing_required = []
    missing_optional = []

    # Check required extensions
    print('\n📋 REQUIRED EXTENSIONS:')
    for ext in REQUIRED_EXTENSIONS:
        result = check_extension(conn, ext)
        if result:
            name, default, installed = result
            print(f"  {name:<22} {'✓ INSTALLED':<12} {installed:<20} {default:<18}")
        else:
            print(f"  {ext:<22} {'❌ MISSING':<12} {'N/A':<20} {'N/A':<18}")
            missing_required.append(ext)

    # Check optional extensions
    print('\n📋 OPTIONAL EXTENSIONS (Recommended):')
    for ext in OPTIONAL_EXTENSIONS:
        result = check_extension(conn, ext)
        if result:
            name, default, installed = result
            print(f"  {name:<22} {'✓ INSTALLED':<12} {installed:<20} {default:<18}")
        else:
            print(f"  {ext:<22} {'⚠ NOT INSTALLED':<12} {'N/A':<20} {'N/A':<18}")
            missing_optional.append(ext)

    conn.close()

    # Summary
    print('\n' + '=' * 60)
    print('SUMMARY:')
    print(f'  Total extensions checked: {len(REQUIRED_EXTENSIONS) + len(OPTIONAL_EXTENSIONS)}')
    print(f'  Missing required: {len(missing_required)}')
    print(f'  Missing optional: {len(missing_optional)}')

    if missing_required:
        print('\n⚠️  MISSING REQUIRED EXTENSIONS:')
        for ext in missing_required:
            print(f'   - {ext}')
        print('\nInstall all required extensions before proceeding:')
        print('  psql -f sql/maintenance/002_install_pg_cron.sql')
        print('  psql -f sql/maintenance/003_install_pg_stat_statements.sql')
        print('  psql -f sql/maintenance/004_install_pl_python3u.sql')
        print('  psql -f sql/maintenance/005_install_pgvector.sql')
        return 1

    if missing_optional:
        print('\n📌 RECOMMENDED OPTIONAL EXTENSIONS TO INSTALL:')
        for ext in missing_optional:
            print(f'   - {ext}')
        print('\nInstallation: see docs/POSTGRESQL_EXTENSIONS_RESEARCH.md')

    print('\n✅ All required extensions present.')
    return 0

if __name__ == '__main__':
    sys.exit(main())
