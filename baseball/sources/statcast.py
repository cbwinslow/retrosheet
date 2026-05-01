"""Statcast source adapter - wraps existing scripts with new CLI interface.

Author: Agent cbwinslow/retrosheet
Date: 2026-04-26

This adapter wraps the existing download_statcast.py script,
preserving working logic while adding the new baseball CLI interface.
"""

import subprocess
import sys
from pathlib import Path

from baseball.core.types import SourceRequest, SourceResult
from baseball.sources.base import BaseSource


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class StatcastSource(BaseSource):
    """Statcast source adapter that wraps existing download scripts."""

    def download(self, config: SourceRequest) -> SourceResult:
        """Download Statcast data for a season.

        Wraps: scripts/data_ingestion/download_statcast.py
        """
        season = config.params.get('season')
        force = config.params.get('force', False)

        cmd = [
            sys.executable,
            'scripts/data_ingestion/download_statcast.py',
            '--season',
            str(season),
        ]

        if force:
            cmd.append('--force')

        try:
            result = subprocess.run(
                cmd,
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=3600,  # 1 hour timeout (Statcast is large)
            )

            if result.returncode == 0:
                return SourceResult(
                    success=True,
                    rows_downloaded=0,  # Would need to parse from output
                    metadata={
                        'stdout': result.stdout[-1000:]
                        if len(result.stdout) > 1000
                        else result.stdout,
                    },
                )
            return SourceResult(
                success=False,
                error_message=f'Statcast download failed: {result.stderr[:500]}',
            )
        except Exception as e:
            return SourceResult(
                success=False,
                error_message=f'Statcast download error: {e!s}',
            )

    def ingest(self, source_path: Path) -> SourceResult:
        """Ingest Statcast data into database.

        Wraps: scripts/external_data/load_statcast.py
        """
        cmd = [
            sys.executable,
            'scripts/external_data/load_statcast.py',
        ]

        try:
            result = subprocess.run(
                cmd,
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=1800,
            )

            if result.returncode == 0:
                return SourceResult(
                    success=True,
                    rows_inserted=0,
                    metadata={
                        'stdout': result.stdout[-1000:]
                        if len(result.stdout) > 1000
                        else result.stdout,
                    },
                )
            return SourceResult(
                success=False,
                error_message=f'Statcast ingest failed: {result.stderr[:500]}',
            )
        except Exception as e:
            return SourceResult(
                success=False,
                error_message=f'Statcast ingest error: {e!s}',
            )

    def validate(self, ingest_result: SourceResult) -> SourceResult:
        """Validate Statcast data quality."""
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

            with conn.cursor() as cur:
                cur.execute('SELECT COUNT(*) FROM raw_statcast.events')
                count = cur.fetchone()[0]

            conn.close()

            return SourceResult(
                success=True,
                metadata={'statcast_events': count},
            )
        except Exception as e:
            return SourceResult(
                success=False,
                error_message=f'Statcast validation error: {e!s}',
            )

    def get_available_seasons(self) -> list[int]:
        """List seasons with Statcast data (2015+)."""
        return list(range(2015, 2026))
