#!/usr/bin/env python3
"""
Shared database configuration.
"""

import os


def database_kwargs() -> dict[str, str]:
    """Get database connection kwargs from environment."""
    return {
        "host": os.getenv("PGHOST", "localhost"),
        "port": int(os.getenv("PGPORT", 5432)),
        "database": os.getenv("PGDATABASE", "retrosheet"),
        "user": os.getenv("PGUSER", os.getenv("USER")),
        "password": os.getenv("PGPASSWORD", ""),
    }


def database_url() -> str:
    """Get database URL."""
    kwargs = database_kwargs()
    return (
        f"postgresql://{kwargs['user']}:{kwargs['password']}@"
        f"{kwargs['host']}:{kwargs['port']}/{kwargs['database']}"
    )


__all__ = ["database_kwargs", "database_url"]
