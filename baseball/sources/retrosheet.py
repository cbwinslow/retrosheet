"""Retrosheet source adapter - wraps existing scripts with new CLI interface.

Author: Agent cbwinslow/retrosheet
Date: 2026-04-26

This adapter wraps the existing retrosheet/ package scripts,
preserving working logic while adding the new baseball CLI interface.
"""

import subprocess
import sys
from datetime import date
from pathlib import Path

from baseball.core.types import SourceRequest, SourceResult
from baseball.sources.base import BaseSource


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class RetrosheetSource(BaseSource):
    """Retrosheet historical data source adapter."""

    def download(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
        force: bool = False,
    ) -> SourceResult:
        """Download Retrosheet event files.

        Wraps: scripts/data_ingestion/record_retrosheet_downloads.py
        """
        # Use archive.py for Retrosheet downloads
        cmd = [
            sys.executable,
            '-m',
            'retrosheet.archive',
        ]

        if start_date and end_date:
            # Download specific date range
            cmd.extend([
                '--start-date', start_date.isoformat(),
                '--end-date', end_date.isoformat(),
            ])

        if force:
            cmd.append('--force')

        try:
            result = subprocess.run(
                cmd,
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=3600,  # 1 hour timeout
            )

            if result.returncode == 0:
                return SourceResult(
                    success=True,
                    rows_downloaded=0,
                    metadata={'stdout': result.stdout[-1000:] if len(result.stdout) > 1000 else result.stdout},
                )
            else:
                return SourceResult(
                    success=False,
                    error_message=f'Retrosheet download failed: {result.stderr[:500]}',
                )
        except Exception as e:
            return SourceResult(
                success=False,
                error_message=f'Retrosheet download error: {str(e)}',
            )

    def ingest(self, validate: bool = True) -> SourceResult:
        """Ingest Retrosheet data using Chadwick tools.

        Wraps: retrosheet/parser.py
        """
        cmd = [
            sys.executable,
            '-m',
            'retrosheet.parser',
        ]

        if validate:
            cmd.append('--validate')

        try:
            result = subprocess.run(
                cmd,
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=1800,  # 30 minute timeout
            )

            if result.returncode == 0:
                return SourceResult(
                    success=True,
                    rows_inserted=0,
                    metadata={'stdout': result.stdout[-1000:] if len(result.stdout) > 1000 else result.stdout},
                )
            else:
                return SourceResult(
                    success=False,
                    error_message=f'Retrosheet ingest failed: {result.stderr[:500]}',
                )
        except Exception as e:
            return SourceResult(
                success=False,
                error_message=f'Retrosheet ingest error: {str(e)}',
            )

    def validate(self) -> SourceResult:
        """Validate Retrosheet data quality."""
        import psycopg2
        import os

        try:
            conn = psycopg2.connect(
                host=os.environ.get('PGHOST', 'localhost'),
                port=os.environ.get('PGPORT', '5432'),
                database=os.environ.get('PGDATABASE', 'retrosheet'),
                user=os.environ.get('PGUSER', 'postgres'),
                password=os.environ.get('PGPASSWORD', ''),
            )

            issues = []
            with conn.cursor() as cur:
                # Check core tables
                cur.execute('SELECT COUNT(*) FROM core.games')
                games = cur.fetchone()[0]

                cur.execute('SELECT COUNT(*) FROM core.events')
                events = cur.fetchone()[0]

                if games == 0:
                    issues.append('No games in core.games')
                if events == 0:
                    issues.append('No events in core.events')

            conn.close()

            return SourceResult(
                success=len(issues) == 0,
                issues=issues,
                metadata={'games': games, 'events': events},
            )
        except Exception as e:
            return SourceResult(
                success=False,
                error_message=f'Retrosheet validation error: {str(e)}',
            )

    def get_seasons_available(self) -> list[int]:
        """List available seasons in Retrosheet."""
        return list(range(1916, 2026))
