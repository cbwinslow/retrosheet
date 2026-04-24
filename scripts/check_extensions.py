#!/usr/bin/env python3
"""Check currently installed PostgreSQL extensions"""

import psycopg2

from scripts.database import database_kwargs


def main():
    conn = psycopg2.connect(**database_kwargs())
    cur = conn.cursor()

    cur.execute("""
        SELECT 
            name,
            default_version,
            installed_version,
            CASE 
                WHEN installed_version IS NOT NULL THEN 'INSTALLED'
                ELSE 'AVAILABLE'
            END as status
        FROM pg_available_extensions
        ORDER BY name;
    """)

    print("PostgreSQL Extensions Status:")
    print("=" * 80)
    print(f"{'Name':<30} {'Default':<15} {'Installed':<15} {'Status':<15}")
    print("=" * 80)

    for row in cur.fetchall():
        name, default_version, installed_version, status = row
        print(
            f"{name:<30} {default_version or 'N/A':<15} {installed_version or 'N/A':<15} {status:<15}"
        )

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
