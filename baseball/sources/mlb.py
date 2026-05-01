"""MLB source adapter - wraps existing scripts with new CLI interface.

Author: Agent cbwinslow/retrosheet
Date: 2026-04-26

This adapter wraps the existing download_mlb_bulk.py script,
preserving working logic while adding the new baseball CLI interface.
"""

import subprocess
import sys
from pathlib import Path

from baseball.core.types import SourceRequest, SourceResult
from baseball.sources.base import BaseSource


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class MlbSource(BaseSource):
    """MLB source adapter that wraps existing download scripts."""

    def download(self, config: SourceRequest) -> SourceResult:
        """Download MLB data from Stats API.

        Wraps: scripts/data_ingestion/download_mlb_bulk.py
        """
        season = config.params.get('season')
        start_season = config.params.get('start_season', season)
        end_season = config.params.get('end_season', season)
        mode = config.params.get('mode', 'both')  # schedules, games, or both
        workers = config.params.get('workers', 8)
        delay = config.params.get('delay', 0.5)

        cmd = [
            sys.executable,
            'scripts/data_ingestion/download_mlb_bulk.py',
            '--start-season',
            str(start_season),
            '--end-season',
            str(end_season),
            '--mode',
            mode,
            '--workers',
            str(workers),
            '--delay',
            str(delay),
        ]

        try:
            result = subprocess.run(
                cmd,
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=3600,  # 1 hour timeout
            )

            if result.returncode == 0:
                # Parse output for row counts
                rows = self._parse_download_output(result.stdout)
                return SourceResult(
                    success=True,
                    rows_downloaded=rows,
                    rows_inserted=0,
                    metadata={
                        'stdout': result.stdout[-1000:]
                        if len(result.stdout) > 1000
                        else result.stdout,
                    },
                )
            return SourceResult(
                success=False,
                error_message=f'Download failed: {result.stderr[:500]}',
            )
        except subprocess.TimeoutExpired:
            return SourceResult(
                success=False,
                error_message='Download timed out after 1 hour',
            )
        except Exception as e:
            return SourceResult(
                success=False,
                error_message=f'Download error: {e!s}',
            )

    def ingest(self, source_path: Path) -> SourceResult:
        """Ingest downloaded MLB data into database.

        Wraps: scripts/data_ingestion/ingest_all_mlb_data.py
        """
        cmd = [
            sys.executable,
            'scripts/data_ingestion/ingest_all_mlb_data.py',
            '--transform-only',  # Assumes download already happened
        ]

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
                    rows_inserted=0,  # Would need to parse from output
                    metadata={
                        'stdout': result.stdout[-1000:]
                        if len(result.stdout) > 1000
                        else result.stdout,
                    },
                )
            return SourceResult(
                success=False,
                error_message=f'Ingest failed: {result.stderr[:500]}',
            )
        except Exception as e:
            return SourceResult(
                success=False,
                error_message=f'Ingest error: {e!s}',
            )

    def validate(self, ingest_result: SourceResult) -> SourceResult:
        """Validate ingested MLB data quality."""
        # Run validation query
        cmd = [
            sys.executable,
            'scripts/data_ingestion/validate_mlb_ingestion.py',
        ]

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
                    metadata={'validation_output': result.stdout},
                )
            return SourceResult(
                success=False,
                error_message=f'Validation failed: {result.stderr[:500]}',
            )
        except Exception as e:
            return SourceResult(
                success=False,
                error_message=f'Validation error: {e!s}',
            )

    def _parse_download_output(self, output: str) -> int:
        """Parse download script output to extract row count."""
        # Look for patterns like "Downloaded X items" or "X schedules downloaded"
        import re

        matches = re.findall(
            r'(\d+)\s+(?:items|schedules|games|feeds)\s+(?:downloaded|processed)',
            output,
            re.IGNORECASE,
        )
        if matches:
            return sum(int(m) for m in matches)
        return 0

    def fetch_today(self) -> SourceResult:
        """Fetch today's MLB schedule and games."""
        from datetime import date

        today = date.today()
        config = SourceRequest(
            source='mlb',
            params={
                'season': today.year,
                'start_season': today.year,
                'end_season': today.year,
                'mode': 'both',
            },
        )
        return self.download(config)

    def fetch_season(self, season: int) -> SourceResult:
        """Fetch full season of MLB data."""
        config = SourceRequest(
            source='mlb',
            params={
                'season': season,
                'start_season': season,
                'end_season': season,
                'mode': 'both',
            },
        )
        return self.download(config)

    def transform_live(self, game_pk: int) -> SourceResult:
        """Transform live MLB feed snapshot into canonical live tables.

        Wraps: scripts/transform/transform_live_game.py
        Transforms raw_mlb.live_feed_snapshots into:
        - core.live_games
        - core.live_events
        - staging.stg_mlb_live_events
        """
        cmd = [
            sys.executable,
            'scripts/transform/transform_live_game.py',
            '--game-pk',
            str(game_pk),
        ]

        try:
            result = subprocess.run(
                cmd,
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
            )

            if result.returncode == 0:
                # Parse output for event count
                events = self._parse_transform_output(result.stdout)
                return SourceResult(
                    success=True,
                    rows_inserted=events,
                    metadata={
                        'stdout': result.stdout[-1000:]
                        if len(result.stdout) > 1000
                        else result.stdout,
                    },
                )
            return SourceResult(
                success=False,
                error_message=f'Transform failed: {result.stderr[:500]}',
            )
        except subprocess.TimeoutExpired:
            return SourceResult(
                success=False,
                error_message='Transform timed out after 5 minutes',
            )
        except Exception as e:
            return SourceResult(
                success=False,
                error_message=f'Transform error: {e!s}',
            )

    def _parse_transform_output(self, output: str) -> int:
        """Parse transform script output to extract event count."""
        import re

        matches = re.findall(r'with (\d+) live events', output)
        if matches:
            return int(matches[0])
        return 0
