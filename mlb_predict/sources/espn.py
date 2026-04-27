"""ESPN data source adapter.

Author: Agent cbwinslow/retrosheet
Date: 2026-04-26
"""

import subprocess
from datetime import date
from pathlib import Path
from typing import Any

from mlb_predict.sources.base import BaseSource, DownloadResult, IngestResult, ValidationResult


class EspnSource(BaseSource):
    """ESPN API data source adapter.

    Wraps existing scripts:
    - fetch_espn_complete.py (schedules, boxscores, player stats, team stats)
    """

    def __init__(self, config: Any | None = None):
        super().__init__(config)
        self._scripts_dir = Path('scripts/data_ingestion')
        self._data_dir = Path('data/espn')

    def download(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
        season: int | None = None,
        output_dir: Path | None = None,
        force: bool = False,
    ) -> DownloadResult:
        """Download ESPN data for schedules and stats."""
        if season:
            return self._download_season(season)

        if start_date and end_date:
            return self._download_date_range(start_date, end_date)

        # Default to current season
        return self._download_season(date.today().year)

    def _download_season(self, season: int, force: bool = False) -> DownloadResult:
        """Download ESPN data for a full season."""
        script = self._scripts_dir / 'fetch_espn_complete.py'

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
            '--season',
            str(season),
        ]
        if force:
            cmd.append('--force')

        result = subprocess.run(cmd, capture_output=True, text=True)

        # Parse output to get counts
        games_count = 0
        plays_count = 0
        player_stats_count = 0
        team_stats_count = 0

        for line in result.stdout.split('\n'):
            if 'games' in line.lower() and 'fetched' in line.lower():
                try:
                    games_count = int(line.split()[0])
                except (ValueError, IndexError):
                    pass
            elif 'plays' in line.lower():
                try:
                    plays_count = int(line.split()[0])
                except (ValueError, IndexError):
                    pass

        return DownloadResult(
            success=result.returncode == 0,
            rows_downloaded=games_count + plays_count + player_stats_count + team_stats_count,
            error_message=result.stderr if result.returncode != 0 else None,
            metadata={
                'season': season,
                'games': games_count,
                'plays': plays_count,
                'player_stats': player_stats_count,
                'team_stats': team_stats_count,
            },
        )

    def _download_date_range(self, start_date: date, end_date: date) -> DownloadResult:
        """Download ESPN data for a specific date range."""
        # ESPN API doesn't have great date range support in the existing script
        # This would need enhancement to the underlying script
        return DownloadResult(
            success=False,
            error_message='Date range download not yet implemented for ESPN source',
        )

    def download_boxscore(self, espn_game_id: str) -> DownloadResult:
        """Download boxscore for a specific ESPN game ID."""
        script = self._scripts_dir / 'fetch_espn_complete.py'

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
            '--game-id',
            espn_game_id,
            '--boxscore-only',
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        return DownloadResult(
            success=result.returncode == 0,
            rows_downloaded=1 if result.returncode == 0 else 0,
            error_message=result.stderr if result.returncode != 0 else None,
            metadata={'espn_game_id': espn_game_id},
        )

    def ingest(
        self,
        input_path: Path | None = None,
        validate: bool = True,
    ) -> IngestResult:
        """Ingest downloaded ESPN data.

        ESPN data from fetch_espn_complete.py is already ingested during download.
        This method validates the ingestion.
        """
        import psycopg2

        try:
            conn = psycopg2.connect(
                host='localhost',
                port=5432,
                database='retrosheet',
            )

            tables = [
                'external.espn_schedule',
                'external.espn_boxscores',
                'external.espn_player_stats',
                'external.espn_team_stats',
                'external.espn_plays',
            ]

            total_rows = 0
            table_counts = {}

            with conn.cursor() as cur:
                for table in tables:
                    try:
                        cur.execute(f'SELECT COUNT(*) FROM {table}')
                        count = cur.fetchone()[0]
                        total_rows += count
                        table_counts[table] = count
                    except Exception:
                        table_counts[table] = 0

            conn.close()

            return IngestResult(
                success=True,
                rows_inserted=total_rows,
                metadata={'table_counts': table_counts},
            )

        except Exception as e:
            return IngestResult(
                success=False,
                error_message=str(e),
            )

    def validate(self) -> ValidationResult:
        """Validate ESPN data quality."""
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
                # Check ESPN tables exist
                cur.execute(
                    'SELECT COUNT(*) FROM information_schema.tables '
                    "WHERE table_schema = 'external' AND table_name LIKE 'espn_%'",
                )
                table_count = cur.fetchone()[0]
                checks.append({'check': 'espn_tables_exist', 'count': table_count})

                if table_count == 0:
                    issues.append('No ESPN tables found in external schema')

                # Check for recent ESPN data
                try:
                    cur.execute(
                        'SELECT COUNT(*) FROM external.espn_schedule '
                        "WHERE game_date >= CURRENT_DATE - INTERVAL '30 days'",
                    )
                    recent_count = cur.fetchone()[0]
                    checks.append({'check': 'recent_espn_data', 'count': recent_count})
                except Exception:
                    recent_count = 0

            conn.close()

            success = table_count > 0

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
        """Get list of dates with ESPN data.

        ESPN has MLB data from ~2005 onward.
        """
        if start_date and end_date:
            from datetime import timedelta

            dates = []
            current = start_date
            while current <= end_date:
                dates.append(current)
                current += timedelta(days=1)
            return dates

        # Default: current season
        return self.get_available_dates(
            date(date.today().year, 3, 1),
            date.today(),
        )

    def get_available_seasons(self) -> list[int]:
        """Get list of seasons with ESPN data."""
        return list(range(2005, date.today().year + 1))
