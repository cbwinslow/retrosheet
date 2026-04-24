"""FastAPI endpoint for real-time query progress monitoring.

The endpoint queries ``pg_stat_activity`` to return all non-idle queries
running against the warehouse database.  It is used by the UI dashboard
to display a progress bar for long-running ingestion or model-training
steps.

Environment variables ``PGHOST``, ``PGPORT``, ``PGDATABASE`` and ``PGUSER``
are respected (defaulting to the typical local development values).
"""

import os

import asyncpg
from fastapi import FastAPI


app = FastAPI()


@app.get('/progress')
async def progress():
    """Return a list of active PostgreSQL queries with their duration.

    The result is a list of dictionaries containing ``pid``, ``query``,
    ``state`` and ``duration`` fields.  Idle connections are filtered out
    because they do not represent work in progress.
    """
    conn = await asyncpg.connect(
        host=os.getenv('PGHOST', 'localhost'),
        port=int(os.getenv('PGPORT', '5432')),
        database=os.getenv('PGDATABASE', 'retrosheet'),
        user=os.getenv('PGUSER', 'postgres'),
    )
    rows = await conn.fetch(
        """
        SELECT pid,
               query,
               state,
               now() - query_start AS duration
        FROM pg_stat_activity
        WHERE state <> 'idle'
        ORDER BY query_start;
        """,
    )
    await conn.close()
    # Convert asyncpg Record objects to plain dicts for JSON serialization
    return [dict(row) for row in rows]
