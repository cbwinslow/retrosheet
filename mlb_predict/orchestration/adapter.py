"""SQL Procedure Adapter.

Adapts SQL files for execution with parameter binding and error handling.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import psycopg2


class SQLProcedureAdapter:
    """Adapter for executing SQL procedures with parameter binding."""

    def __init__(self, sql_dir: Path | str):
        self.sql_dir = Path(sql_dir)

    def load_sql(self, filename: str) -> str:
        """Load SQL from file."""
        file_path = self.sql_dir / filename
        with open(file_path) as f:
            return f.read()

    def execute(
        self,
        conn: psycopg2.extensions.connection,
        filename: str,
        params: dict[str, Any] | None = None,
    ) -> list[tuple]:
        """Execute SQL file with optional parameter binding."""
        sql = self.load_sql(filename)

        # Simple parameter substitution for named params
        if params:
            for key, value in params.items():
                placeholder = f':{key}'
                if isinstance(value, str):
                    sql = sql.replace(placeholder, f"'{value}'")
                elif isinstance(value, (int, float)):
                    sql = sql.replace(placeholder, str(value))
                elif value is None:
                    sql = sql.replace(placeholder, 'NULL')

        with conn.cursor() as cur:
            cur.execute(sql)
            try:
                return cur.fetchall()
            except psycopg2.ProgrammingError:
                # No results to fetch
                return []

    def execute_procedure(
        self,
        conn: psycopg2.extensions.connection,
        procedure_name: str,
        args: tuple[Any, ...] = (),
    ) -> None:
        """Execute a stored procedure."""
        with conn.cursor() as cur:
            cur.execute(f'CALL {procedure_name}(%s)', (args,))
        conn.commit()
