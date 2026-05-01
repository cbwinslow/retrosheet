"""Weather source adapter - wraps existing scripts with new CLI interface.

Author: Agent cbwinslow/retrosheet
Date: 2026-04-29

This adapter wraps the existing fetch_weather.py script,
preserving working logic while adding the new baseball CLI interface.
"""

import subprocess
import sys
from pathlib import Path

from baseball.core.types import SourceRequest, SourceResult
from baseball.sources.base import BaseSource


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class WeatherSource(BaseSource):
    """Weather source adapter that wraps NOAA weather fetch scripts."""

    def download(self, config: SourceRequest) -> SourceResult:
        """Fetch weather observations for a venue/date from NOAA.

        Wraps: scripts/data_ingestion/fetch_weather.py
        """
        date = config.params.get('date')
        venue_id = config.params.get('venue_id')

        cmd = [
            sys.executable,
            'scripts/data_ingestion/fetch_weather.py',
        ]

        if date:
            cmd.extend(['--date', str(date)])
        if venue_id:
            cmd.extend(['--venue-id', str(venue_id)])

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
                    rows_downloaded=1,
                    metadata={
                        'stdout': result.stdout[-1000:]
                        if len(result.stdout) > 1000
                        else result.stdout
                    },
                )
            return SourceResult(
                success=False,
                error_message=f'Weather fetch failed: {result.stderr[:500]}',
            )
        except Exception as e:
            return SourceResult(
                success=False,
                error_message=f'Weather fetch error: {str(e)[:500]}',
            )

    def ingest(self, config: SourceRequest) -> SourceResult:
        """Weather data is ingested during download."""
        return SourceResult(
            success=True,
            rows_downloaded=0,
            metadata={'note': 'Weather data ingested during download'},
        )

    def validate(self, config: SourceRequest) -> SourceResult:
        """Validate weather data in database."""
        try:
            import psycopg2
            from baseball.core.db import get_database_url

            conn = psycopg2.connect(get_database_url())
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT COUNT(*)
                    FROM information_schema.tables
                    WHERE table_schema = 'raw_weather'
                    AND table_name = 'daily'
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
                    error_message='daily table not found in raw_weather',
                )
        except Exception as e:
            return SourceResult(
                success=False,
                error_message=f'Validation error: {str(e)[:500]}',
            )
