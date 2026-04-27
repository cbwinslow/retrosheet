"""Lahman source adapter - wraps existing scripts with new CLI interface.

Author: Agent cbwinslow/retrosheet
Date: 2026-04-26

This adapter wraps the existing download_lahman_data.py script,
preserving working logic while adding the new baseball CLI interface.
"""

import subprocess
import sys
from pathlib import Path

from baseball.core.types import SourceRequest, SourceResult
from baseball.sources.base import BaseSource


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class LahmanSource(BaseSource):
    """Lahman Baseball Databank source adapter."""

    def download(self, config: SourceRequest) -> SourceResult:
        """Download Lahman Baseball Databank (1871-2023).

        Wraps: scripts/data_ingestion/download_lahman_data.py
        """
        force = config.params.get('force', False)

        cmd = [
            sys.executable,
            'scripts/data_ingestion/download_lahman_data.py',
        ]

        if force:
            cmd.append('--force')

        try:
            result = subprocess.run(
                cmd,
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
            )

            if result.returncode == 0:
                return SourceResult(
                    success=True,
                    rows_downloaded=0,
                    metadata={
                        'stdout': result.stdout[-1000:]
                        if len(result.stdout) > 1000
                        else result.stdout
                    },
                )
            return SourceResult(
                success=False,
                error_message=f'Lahman download failed: {result.stderr[:500]}',
            )
        except Exception as e:
            return SourceResult(
                success=False,
                error_message=f'Lahman download error: {e!s}',
            )

    def ingest(self, source_path: Path) -> SourceResult:
        """Ingest Lahman CSV files into database.

        Wraps: scripts/external_data/load_lahman.py
        """
        cmd = [
            sys.executable,
            'scripts/external_data/load_lahman.py',
        ]

        try:
            result = subprocess.run(
                cmd,
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=600,  # 10 minute timeout
            )

            if result.returncode == 0:
                return SourceResult(
                    success=True,
                    rows_inserted=0,
                    metadata={
                        'stdout': result.stdout[-1000:]
                        if len(result.stdout) > 1000
                        else result.stdout
                    },
                )
            return SourceResult(
                success=False,
                error_message=f'Lahman ingest failed: {result.stderr[:500]}',
            )
        except Exception as e:
            return SourceResult(
                success=False,
                error_message=f'Lahman ingest error: {e!s}',
            )

    def validate(self, ingest_result: SourceResult) -> SourceResult:
        """Validate Lahman data quality."""
        import os

        import psycopg2

        try:
            conn = psycopg2.connect(
                host=os.environ.get('PGHOST', 'localhost'),
                port=os.environ.get('PGPORT', '5432'),
                database=os.environ.get('PGDATABASE', 'retrosheet'),
                user=os.environ.get('PGUSER', 'postgres'),
                password=os.environ.get('PGPASSWORD', ''),
            )

            counts = {}
            with conn.cursor() as cur:
                tables = ['players', 'teams', 'batting', 'pitching', 'salaries']
                for table in tables:
                    try:
                        cur.execute(f'SELECT COUNT(*) FROM raw_lahman.{table}')
                        counts[table] = cur.fetchone()[0]
                    except Exception:
                        counts[table] = 0

            conn.close()

            return SourceResult(
                success=True,
                metadata={'table_counts': counts},
            )
        except Exception as e:
            return SourceResult(
                success=False,
                error_message=f'Lahman validation error: {e!s}',
            )

    def get_table_counts(self) -> dict[str, int]:
        """Get row counts for all Lahman tables."""
        result = self.validate(SourceResult(success=True))
        if result.success and result.metadata:
            return result.metadata.get('table_counts', {})
        return {}
