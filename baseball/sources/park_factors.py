"""Park factors source adapter - wraps existing scripts with new CLI interface.

Author: Agent cbwinslow/retrosheet
Date: 2026-04-29

This adapter wraps the existing load_park_factors.py script,
preserving working logic while adding the new baseball CLI interface.
"""

import subprocess
import sys
from pathlib import Path

from baseball.core.types import SourceRequest, SourceResult
from baseball.sources.base import BaseSource


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class ParkFactorsSource(BaseSource):
    """Park factors source adapter that wraps Statcast park factors loader."""

    def download(self, config: SourceRequest) -> SourceResult:
        """Download park factors from Baseball Savant.

        Note: Requires manual download from baseballsavant.mlb.com
        """
        return SourceResult(
            success=False,
            error_message='Park factors require manual download from baseballsavant.mlb.com/leaderboard/park-factors',
        )

    def ingest(self, config: SourceRequest) -> SourceResult:
        """Load park factors CSV into raw_park_factors schema.

        Wraps: scripts/external_data/load_park_factors.py
        """
        file_path = config.params.get('file')

        if not file_path:
            return SourceResult(
                success=False,
                error_message='file parameter required (path to park_factors.csv)',
            )

        cmd = [
            sys.executable,
            'scripts/external_data/load_park_factors.py',
            '--file',
            str(file_path),
        ]

        try:
            result = subprocess.run(
                cmd,
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=60,
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
                error_message=f'Park factors load failed: {result.stderr[:500]}',
            )
        except Exception as e:
            return SourceResult(
                success=False,
                error_message=f'Park factors load error: {str(e)[:500]}',
            )

    def validate(self, config: SourceRequest) -> SourceResult:
        """Validate park factors data in database."""
        try:
            import psycopg2
            from baseball.core.db import get_database_url

            conn = psycopg2.connect(get_database_url())
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT COUNT(*)
                    FROM information_schema.tables
                    WHERE table_schema = 'raw_park_factors'
                    OR (table_schema = 'raw_statcast'
                        AND table_name = 'park_factors')
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
                    error_message='park_factors table not found',
                )
        except Exception as e:
            return SourceResult(
                success=False,
                error_message=f'Validation error: {str(e)[:500]}',
            )
