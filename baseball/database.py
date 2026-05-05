"""Database module for baseball platform.

Provides database connection utilities (both sync and async).

Author: Agent cbwinslow/retrosheet
Date: 2026-05-03
"""

import os

import asyncpg
import psycopg2
from psycopg2.extensions import connection

from baseball.core.db import get_database_url


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


async def get_db_pool():
    """Get an async database connection pool.

    Returns:
        asyncpg pool object or None if connection fails
    """
    try:
        db_url = get_database_url()
        # Convert postgresql:// to postgresql:// for asyncpg
        return await asyncpg.create_pool(db_url)
    except Exception as e:
        import logging

        logging.getLogger(__name__).warning(f'Failed to create database pool: {e}')
        return None


__all__ = [
    'get_db_connection',
    'get_db_pool',
    'get_database_url',
]
