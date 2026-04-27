"""MLB Stats API source adapter.

Author: Agent cbwinslow/retrosheet
Date: 2026-04-26
"""

import subprocess
from datetime import date
from pathlib import Path
from typing import Any

from mlb_predict.sources.base import BaseSource, DownloadResult, IngestResult, ValidationResult


class MlbSource(BaseSource):
    """MLB Stats API data source adapter.

    Wraps existing scripts:
    - fetch_mlb_stats_api_complete.py (main fetcher)
    - download_mlb_games.py (bulk download)
    - ingest_mlb_pbp.py (play-by-play ingest)
    """

    def __init__(self, config: Any | None = None):
        super().__init__(config)
        self._scripts_dir = Path('scripts/data_ingestion')

    def download(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
        game_pks: list[int] | None = None,
        output_dir: Path | None = None,
        force: bool = False,
    ) -> DownloadResult:
        """Download MLB data using existing scripts."""
        if game_pks:
            # Download specific games
            return self._download_games(game_pks, force)
        if start_date and end_date:
            # Download date range
            return self._download_date_range(start_date, end_date, force)
        return DownloadResult(
            success=False,
            error_message='Must specify game_pks or date range (start_date + end_date)',
        )

    def _download_games(self, game_pks: list[int], force: bool) -> DownloadResult:
        """Download specific games by ID."""
        script = self._scripts_dir / 'download_mlb_games.py'

        success_count = 0
        failed_count = 0

        for game_pk in game_pks:
            cmd = [
                'uv',
                'run',
                'python',
                str(script),
                '--game-pk',
                str(game_pk),
            ]
            if force:
                cmd.append('--force')

            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                success_count += 1
            else:
                failed_count += 1

        return DownloadResult(
            success=failed_count == 0,
            rows_downloaded=success_count,
            rows_failed=failed_count,
            metadata={'game_pks': game_pks},
        )

    def _download_date_range(
        self,
        start_date: date,
        end_date: date,
        force: bool,
    ) -> DownloadResult:
        """Download games for a date range."""
        script = self._scripts_dir / 'fetch_mlb_stats_api_complete.py'

        # Get season from start_date
        season = start_date.year

        cmd = [
            'uv',
            'run',
            'python',
            str(script),
            '--season',
            str(season),
            '--start-date',
            start_date.isoformat(),
            '--end-date',
            end_date.isoformat(),
        ]
        if force:
            cmd.append('--force')

        result = subprocess.run(cmd, capture_output=True, text=True)

        # Parse output to get counts (simplified)
        success = result.returncode == 0

        return DownloadResult(
            success=success,
            rows_downloaded=0,  # TODO: Parse from script output
            rows_failed=0 if success else 1,
            error_message=result.stderr if not success else None,
            metadata={
                'season': season,
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
            },
        )

    def ingest(
        self,
        input_path: Path | None = None,
        validate: bool = True,
    ) -> IngestResult:
        """Ingest downloaded MLB data into database."""
        # MLB data is already ingested by the download scripts
        # This is a no-op or validation pass
        if validate:
            validation = self.validate()
            return IngestResult(
                success=validation.success,
                rows_inserted=0,
                rows_updated=0,
                rows_failed=validation.error_count,
                metadata={'validated': True},
            )

        return IngestResult(
            success=True,
            rows_inserted=0,
            metadata={'note': 'MLB data ingested during download'},
        )

    def validate(self) -> ValidationResult:
        """Validate MLB data quality."""
        script = self._scripts_dir / 'validate_mlb_ingestion.py'

        if not script.exists():
            # Basic validation via SQL
            return self._validate_via_sql()

        result = subprocess.run(
            ['uv', 'run', 'python', str(script)],
            capture_output=True,
            text=True,
        )

        success = result.returncode == 0

        return ValidationResult(
            success=success,
            error_count=0 if success else 1,
            metadata={'output': result.stdout},
        )

    def _validate_via_sql(self) -> ValidationResult:
        """Basic SQL-based validation."""
        import psycopg2

        try:
            conn = psycopg2.connect(
                host='localhost',
                port=5432,
                database='retrosheet',
            )

            with conn.cursor() as cur:
                # Check for recent data
                cur.execute(
                    'SELECT COUNT(*) FROM raw_mlb.live_feed_snapshots '
                    "WHERE snapshot_date > CURRENT_DATE - INTERVAL '7 days'",
                )
                recent_count = cur.fetchone()[0]

                conn.close()

                return ValidationResult(
                    success=recent_count > 0,
                    metadata={'recent_snapshots': recent_count},
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
        """Get list of dates with MLB schedule data."""
        # MLB season typically runs March-October
        # Return placeholder - actual implementation would query schedule API
        if start_date and end_date:
            # Generate dates (simplified)
            from datetime import timedelta

            dates = []
            current = start_date
            while current <= end_date:
                dates.append(current)
                current += timedelta(days=1)
            return dates

        return []

    def fetch_today(self) -> DownloadResult:
        """Quick method to fetch today's games."""
        today = date.today()
        return self.download(start_date=today, end_date=today)

    def fetch_season(self, season: int) -> DownloadResult:
        """Fetch entire season."""
        start = date(season, 3, 1)  # March 1st
        end = date(season, 11, 1)  # November 1st
        return self.download(start_date=start, end_date=end)
