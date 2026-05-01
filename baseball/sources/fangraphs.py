"""FanGraphs source adapter - wraps existing scripts with new CLI interface.

Author: Agent cbwinslow/retrosheet
Date: 2026-04-29

This adapter wraps the existing load_fangraphs.py script,
preserving working logic while adding the new baseball CLI interface.
"""

import subprocess
import sys
from pathlib import Path

from baseball.core.types import SourceRequest, SourceResult
from baseball.sources.base import BaseSource


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class FanGraphsSource(BaseSource):
    """FanGraphs source adapter that wraps existing load scripts."""

    def download(self, config: SourceRequest) -> SourceResult:
        """Download FanGraphs data.

        Wraps: scripts/data_ingestion/download_fangraphs.py
        """
        season = config.params.get('season')
        force = config.params.get('force', False)

        cmd = [
            sys.executable,
            'scripts/data_ingestion/download_fangraphs.py',
        ]

        if season:
            cmd.extend(['--season', str(season)])
        if force:
            cmd.append('--force')

        try:
            result = subprocess.run(
                cmd,
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=600,
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
                error_message=f'FanGraphs download failed: {result.stderr[:500]}',
            )
        except Exception as e:
            return SourceResult(
                success=False,
                error_message=f'FanGraphs download error: {str(e)[:500]}',
            )

    def ingest(self, config: SourceRequest) -> SourceResult:
        """Load FanGraphs CSVs into raw_fangraphs schema.

        Wraps: scripts/external_data/load_fangraphs.py
        """
        player_file = config.params.get('player_file')
        team_file = config.params.get('team_file')

        cmd = [
            sys.executable,
            'scripts/external_data/load_fangraphs.py',
        ]

        if player_file:
            cmd.extend(['--player', str(player_file)])
        if team_file:
            cmd.extend(['--team', str(team_file)])

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
                error_message=f'FanGraphs load failed: {result.stderr[:500]}',
            )
        except Exception as e:
            return SourceResult(
                success=False,
                error_message=f'FanGraphs load error: {str(e)[:500]}',
            )

    def validate(self, config: SourceRequest) -> SourceResult:
        """Validate FanGraphs data in database."""
        try:
            # Basic validation - check table existence
            import psycopg2

            from baseball.core.db import get_database_url

            conn = psycopg2.connect(get_database_url())
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT COUNT(*)
                    FROM information_schema.tables
                    WHERE table_schema = 'raw_fangraphs'
                    AND table_name IN ('player_stats', 'team_stats')
                """)
                count = cur.fetchone()[0]
                conn.close()

                if count >= 2:
                    return SourceResult(
                        success=True,
                        rows_downloaded=0,
                        metadata={'tables_found': count},
                    )
                return SourceResult(
                    success=False,
                    error_message=f'Only {count}/2 expected tables found',
                )
        except Exception as e:
            return SourceResult(
                success=False,
                error_message=f'Validation error: {str(e)[:500]}',
            )
