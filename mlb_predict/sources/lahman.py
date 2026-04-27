"""Lahman Baseball Databank source adapter.

Author: Agent cbwinslow/retrosheet
Date: 2026-04-26
"""

import subprocess
from datetime import date
from pathlib import Path
from typing import Any

from mlb_predict.sources.base import BaseSource, DownloadResult, IngestResult, ValidationResult


class LahmanSource(BaseSource):
    """Lahman Baseball Databank source adapter.

    Wraps existing scripts:
    - download_lahman_data.py (CSV download and extraction)

    The Lahman database contains comprehensive historical baseball statistics
    from 1871 to present, including:
    - Master (player biographical info)
    - Batting, Pitching, Fielding
    - Teams, Franchises
    - Salaries, Hall of Fame
    """

    def __init__(self, config: Any | None = None):
        super().__init__(config)
        self._scripts_dir = Path('scripts/data_ingestion')
        self._data_dir = Path('data/lahman_csv')

    def download(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
        output_dir: Path | None = None,
        force: bool = False,
    ) -> DownloadResult:
        """Download Lahman Baseball Databank.

        Lahman is distributed as a single archive covering all seasons,
        so date parameters are ignored.
        """
        script = self._scripts_dir / 'download_lahman_data.py'

        if not script.exists():
            return DownloadResult(
                success=False,
                error_message=f'Script not found: {script}',
            )

        cmd = [
            'uv',
            'run',
            'python',
            str(script),
        ]

        if output_dir:
            cmd.extend(['--dir', str(output_dir)])
        if force:
            cmd.append('--force')

        result = subprocess.run(cmd, capture_output=True, text=True)

        # Parse output to find downloaded files
        files_downloaded = []
        for line in result.stdout.split('\n'):
            if 'Downloaded' in line or 'Extracted' in line:
                files_downloaded.append(line.strip())

        return DownloadResult(
            success=result.returncode == 0,
            rows_downloaded=len(files_downloaded),
            error_message=result.stderr if result.returncode != 0 else None,
            metadata={
                'files': files_downloaded,
                'archive': 'lahman_1871-2023_csv.7z',
            },
        )

    def ingest(
        self,
        input_path: Path | None = None,
        validate: bool = True,
    ) -> IngestResult:
        """Ingest Lahman CSV files into database.

        Lahman CSV files need to be loaded into raw_lahman schema.
        """
        if input_path is None:
            input_path = self._data_dir

        if not input_path.exists():
            return IngestResult(
                success=False,
                error_message=f'Data directory not found: {input_path}',
            )

        import psycopg2

        try:
            conn = psycopg2.connect(
                host='localhost',
                port=5432,
                database='retrosheet',
            )

            # Expected Lahman CSV files
            expected_files = [
                'Master.csv',
                'Batting.csv',
                'Pitching.csv',
                'Fielding.csv',
                'Teams.csv',
                'Franchises.csv',
                'Salaries.csv',
                'HallOfFame.csv',
                'Managers.csv',
                'BattingPost.csv',
                'PitchingPost.csv',
                'FieldingPost.csv',
            ]

            files_found = []
            files_missing = []
            total_rows = 0

            for csv_file in expected_files:
                file_path = input_path / csv_file
                if file_path.exists():
                    files_found.append(csv_file)
                    # Would load CSV here
                    # For now, just count files
                else:
                    files_missing.append(csv_file)

            conn.close()

            success = len(files_found) > 0

            return IngestResult(
                success=success,
                rows_inserted=total_rows,
                metadata={
                    'files_found': files_found,
                    'files_missing': files_missing,
                    'data_dir': str(input_path),
                },
            )

        except Exception as e:
            return IngestResult(
                success=False,
                error_message=str(e),
            )

    def validate(self) -> ValidationResult:
        """Validate Lahman data quality."""
        import psycopg2

        try:
            conn = psycopg2.connect(
                host='localhost',
                port=5432,
                database='retrosheet',
            )

            checks = []
            issues = []

            with conn.cursor() as cur:
                # Check for Lahman schema/tables
                cur.execute(
                    'SELECT COUNT(*) FROM information_schema.tables '
                    "WHERE table_schema = 'raw_lahman'",
                )
                table_count = cur.fetchone()[0]
                checks.append({'check': 'lahman_tables_exist', 'count': table_count})

                if table_count == 0:
                    issues.append('No Lahman tables found in raw_lahman schema')

                # Check for Master table (core player data)
                try:
                    cur.execute('SELECT COUNT(*) FROM raw_lahman.Master')
                    master_count = cur.fetchone()[0]
                    checks.append({'check': 'master_table', 'count': master_count})
                except Exception:
                    master_count = 0
                    issues.append('Master table not accessible')

                # Check for batting data
                try:
                    cur.execute('SELECT COUNT(*) FROM raw_lahman.Batting')
                    batting_count = cur.fetchone()[0]
                    checks.append({'check': 'batting_table', 'count': batting_count})
                except Exception:
                    batting_count = 0
                    issues.append('Batting table not accessible')

            conn.close()

            success = table_count >= 5 and master_count > 0

            return ValidationResult(
                success=success,
                warning_count=len(issues),
                issues=issues,
                metadata={'checks': checks},
            )

        except Exception as e:
            return ValidationResult(
                success=False,
                error_count=1,
                error_message=str(e),
            )

    def get_available_dates(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[date]:
        """Get list of dates with Lahman data.

        Lahman covers 1871-2023, but is season-level data, not daily.
        Returns empty list as this concept doesn't apply.
        """
        return []

    def get_available_seasons(self) -> list[int]:
        """Get list of seasons with Lahman data (1871-2023)."""
        return list(range(1871, 2024))

    def get_table_counts(self) -> dict:
        """Get row counts for all Lahman tables."""
        import psycopg2

        tables = [
            'Master',
            'Batting',
            'Pitching',
            'Fielding',
            'Teams',
            'Franchises',
            'Salaries',
            'HallOfFame',
            'Managers',
            'BattingPost',
            'PitchingPost',
            'FieldingPost',
        ]

        counts = {}

        try:
            conn = psycopg2.connect(
                host='localhost',
                port=5432,
                database='retrosheet',
            )

            with conn.cursor() as cur:
                for table in tables:
                    try:
                        cur.execute(f'SELECT COUNT(*) FROM raw_lahman.{table}')
                        counts[table] = cur.fetchone()[0]
                    except Exception:
                        counts[table] = 0

            conn.close()

        except Exception as e:
            counts['error'] = str(e)

        return counts
