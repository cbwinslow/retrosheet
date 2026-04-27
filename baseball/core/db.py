"""Database connection manager for the baseball platform.

Author: Agent cbwinslow/retrosheet
Date: 2026-04-26
"""

import os


def get_database_url() -> str:
    """Get the database connection URL from environment."""
    return os.getenv(
        'DATABASE_URL',
        f"postgresql://{os.getenv('PGUSER', 'retrosheet')}:{os.getenv('PGPASSWORD', '')}@{os.getenv('PGHOST', 'localhost')}:{os.getenv('PGPORT', '5432')}/{os.getenv('PGDATABASE', 'retrosheet')}"
    )
