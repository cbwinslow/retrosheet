"""Database connection manager for the baseball platform.

Author: Agent cbwinslow/retrosheet
Date: 2026-04-27
"""

import os

import psycopg2
from psycopg2.extensions import connection


def get_database_url() -> str:
    """Get the database connection URL from environment."""
    return os.getenv(
        'DATABASE_URL',
        f'postgresql://{os.getenv("PGUSER", "retrosheet")}:{os.getenv("PGPASSWORD", "")}@{os.getenv("PGHOST", "localhost")}:{os.getenv("PGPORT", "5432")}/{os.getenv("PGDATABASE", "retrosheet")}',
    )


def get_db_connection() -> connection | None:
    """Get a database connection.

    Returns:
        psycopg2 connection object or None if connection fails
    """
    try:
        db_url = get_database_url()
        return psycopg2.connect(db_url)
    except Exception as e:
        import logging

        logging.getLogger(__name__).warning(f'Failed to connect to database: {e}')
        return None
