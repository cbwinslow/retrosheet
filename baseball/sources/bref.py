"""Baseball-Reference source adapter - wraps existing scripts with new CLI interface.

Author: Agent cbwinslow/retrosheet
Date: 2026-04-29

This adapter wraps the existing load_baseball_reference.py script,
preserving working logic while adding the new baseball CLI interface.
"""

import subprocess
import sys
from pathlib import Path

from baseball.core.types import SourceRequest, SourceResult
from baseball.sources.base import BaseSource


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class BRefSource(BaseSource):
    """Baseball-Reference source adapter that wraps existing load scripts."""

    def download(self, config: SourceRequest) -> SourceResult:
        """Download Baseball-Reference data.

        Wraps: scripts/data_ingestion/download_bref_data.py (if exists)
        """
        # BRef typically requires manual CSV download
        return SourceResult(
            success=False,
            error_message='BRef download requires manual CSV download from baseball-reference.com',
        )

    def ingest(self, config: SourceRequest) -> SourceResult:
        """Load Baseball-Reference game logs into raw_baseball_reference schema.

        Wraps: scripts/external_data/load_baseball_reference.py
        """
        data_dir = config.params.get('data_dir')

        cmd = [
            sys.executable,
            'scripts/external_data/load_baseball_reference.py',
        ]

        if data_dir:
            cmd.extend(['--dir', str(data_dir)])

        try:
            result = subprocess.run(
                cmd,
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=300,
            )

            if result.returncode == 0:
                return SourceResult(
                    success=True,
                    rows_downloaded=0,
                    metadata={
                        'stdout': result.stdout[-1000:]
                        if len(result.stdout) > 1000
                        else result.stdout,
                    },
                )
            return SourceResult(
                success=False,
                error_message=f'BRef load failed: {result.stderr[:500]}',
            )
        except Exception as e:
            return SourceResult(
                success=False,
                error_message=f'BRef load error: {str(e)[:500]}',
            )

    def validate(self, config: SourceRequest) -> SourceResult:
        """Validate Baseball-Reference data in database."""
        try:
            import psycopg2

            from baseball.core.db import get_database_url

            conn = psycopg2.connect(get_database_url())
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT COUNT(*)
                    FROM information_schema.tables
                    WHERE table_schema = 'raw_baseball_reference'
                    AND table_name = 'game_logs'
                """)
                count = cur.fetchone()[0]
                conn.close()

                if count >= 1:
                    return SourceResult(
                        success=True,
                        rows_downloaded=0,
                        metadata={'tables_found': count},
                    )
                return SourceResult(
                    success=False,
                    error_message='game_logs table not found',
                )
        except Exception as e:
            return SourceResult(
                success=False,
                error_message=f'Validation error: {str(e)[:500]}',
            )
