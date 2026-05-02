"""Smart scheduler for MLB data ingestion with adaptive polling rates.

Dynamically adjusts polling frequency based on game schedule:
- During games: Poll every 10-30 seconds
- Between games: Poll every 5 minutes  
- Off-season: Poll once per hour

Uses timezone-agnostic datetime handling for consistency.

Author: Agent Cascade
Date: 2026-05-01
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Callable, Optional

from baseball.core.db import get_db_connection
from baseball.core.time_util import BaseballDateTime, is_during_season

logger = logging.getLogger(__name__)


@dataclass
class PollingSchedule:
    """Polling schedule configuration."""
    
    # Polling intervals in seconds
    during_game: int = 10  # Active game polling
    pre_game: int = 60     # Within 1 hour of game start
    game_day: int = 300    # During game day but no active games (5 min)
    off_hours: int = 3600  # Overnight/off-season (1 hour)
    
    # Window definitions
    pre_game_minutes: int = 60  # Consider "pre-game" within this many minutes


@dataclass
class GameWindow:
    """Represents a time window when games are occurring."""
    
    game_pk: int
    start_time: BaseballDateTime
    end_time: BaseballDateTime  # Estimated (start + 4 hours)
    home_team: str
    away_team: str
    status: str = 'scheduled'
    
    def is_active(self, now: Optional[BaseballDateTime] = None) -> bool:
        """Check if game is currently active."""
        if now is None:
            now = BaseballDateTime.now()
        return now.is_between(self.start_time, self.end_time)
    
    def is_pre_game(self, minutes_before: int = 60, now: Optional[BaseballDateTime] = None) -> bool:
        """Check if we're in pre-game window."""
        if now is None:
            now = BaseballDateTime.now()
        pre_start = self.start_time.add_minutes(-minutes_before)
        return now.is_between(pre_start, self.start_time)
    
    def minutes_until_start(self, now: Optional[BaseballDateTime] = None) -> float:
        """Minutes until game starts."""
        if now is None:
            now = BaseballDateTime.now()
        return self.start_time.minutes_until(now)


class SmartScheduler:
    """Smart scheduler that adapts polling rate to game schedule.
    
    Example:
        >>> scheduler = SmartScheduler()
        >>> await scheduler.start()
        >>> 
        >>> # Polling rate automatically adjusts:
        >>> # - During games: every 10 seconds
        >>> # - Off-hours: every 1 hour
    """
    
    def __init__(
        self,
        schedule: Optional[PollingSchedule] = None,
        db_connection=None,
    ) -> None:
        """Initialize smart scheduler.
        
        Args:
            schedule: Polling schedule configuration
            db_connection: Database connection (uses default if None)
        """
        self.schedule = schedule or PollingSchedule()
        self.db = db_connection or get_db_connection()
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._current_interval = self.schedule.off_hours
        self._game_windows: list[GameWindow] = []
        self._last_schedule_check: Optional[BaseballDateTime] = None
        
    async def start(self) -> None:
        """Start the smart scheduler loop."""
        if self._running:
            return
            
        self._running = True
        self._task = asyncio.create_task(self._scheduler_loop())
        logger.info('SmartScheduler started')
        
    async def stop(self) -> None:
        """Stop the scheduler."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info('SmartScheduler stopped')
        
    def get_current_interval(self) -> int:
        """Get current polling interval in seconds."""
        return self._current_interval
    
    async def _scheduler_loop(self) -> None:
        """Main scheduler loop with adaptive polling."""
        while self._running:
            try:
                # Update game schedule (refresh every 15 minutes)
                now = BaseballDateTime.now()
                if (self._last_schedule_check is None or 
                    self._last_schedule_check.minutes_since(now) > 15):
                    await self._refresh_game_schedule()
                    self._last_schedule_check = now
                
                # Calculate optimal polling interval
                new_interval = self._calculate_polling_interval(now)
                
                if new_interval != self._current_interval:
                    logger.info(
                        f'Polling interval changed: {self._current_interval}s -> {new_interval}s'
                    )
                    self._current_interval = new_interval
                
                # Execute ingestion task
                await self._execute_ingestion()
                
                # Wait for next poll
                await asyncio.sleep(self._current_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception(f'Scheduler error: {e}')
                # Back off on error
                await asyncio.sleep(min(self._current_interval * 2, 300))
    
    async def _refresh_game_schedule(self) -> None:
        """Refresh today's game schedule from database."""
        try:
            today = BaseballDateTime.today()
            tomorrow = today.add_days(1)
            
            with self.db.cursor() as cur:
                cur.execute("""
                    SELECT 
                        game_pk,
                        game_date,
                        game_time,
                        home_team_id,
                        away_team_id,
                        status_code
                    FROM core.games
                    WHERE game_date >= %s 
                      AND game_date < %s
                      AND status_code IN ('S', 'P', 'L', 'F')
                    ORDER BY game_time
                """, (today.datetime.date(), tomorrow.datetime.date()))
                
                rows = cur.fetchall()
                self._game_windows = []
                
                for row in rows:
                    game_pk = row[0]
                    game_date = row[1]
                    game_time = row[2]
                    home_team = row[3]
                    away_team = row[4]
                    status = row[5]
                    
                    # Combine date and time
                    if game_time:
                        start_dt = datetime.combine(game_date, game_time)
                    else:
                        # Default to 7:05 PM ET if no time specified
                        start_dt = datetime.combine(game_date, datetime.strptime('19:05', '%H:%M').time())
                    
                    start = BaseballDateTime.from_mlb_api(start_dt.isoformat())
                    # Estimate 4 hour game duration
                    end = start.add_hours(4)
                    
                    self._game_windows.append(GameWindow(
                        game_pk=game_pk,
                        start_time=start,
                        end_time=end,
                        home_team=home_team,
                        away_team=away_team,
                        status=status,
                    ))
                
                logger.info(f'Refreshed schedule: {len(self._game_windows)} games today')
                
        except Exception as e:
            logger.error(f'Failed to refresh game schedule: {e}')
    
    def _calculate_polling_interval(self, now: BaseballDateTime) -> int:
        """Calculate optimal polling interval based on game status."""
        # Check season
        if not is_during_season(now):
            return self.schedule.off_hours
        
        # Check if any games are active
        active_games = [g for g in self._game_windows if g.is_active(now)]
        if active_games:
            return self.schedule.during_game
        
        # Check pre-game windows
        pre_game_games = [
            g for g in self._game_windows 
            if g.is_pre_game(self.schedule.pre_game_minutes, now)
        ]
        if pre_game_games:
            return self.schedule.pre_game
        
        # Check if any games today
        if self._game_windows:
            # Games today but not started/finished
            return self.schedule.game_day
        
        # No games today
        return self.schedule.off_hours
    
    async def _execute_ingestion(self) -> None:
        """Execute the ingestion task. Override or subclass to customize."""
        # Default: call the live game ingestion script
        try:
            import subprocess
            import sys
            from pathlib import Path
            
            root = Path(__file__).resolve().parents[2]
            script = root / 'scripts' / 'data_ingestion' / 'ingest_live_games.py'
            
            result = subprocess.run(
                [sys.executable, str(script), '--active'],
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
            )
            
            if result.returncode != 0:
                logger.error(f'Ingestion failed: {result.stderr}')
            else:
                logger.debug(f'Ingestion completed: {result.stdout[:200]}')
                
        except subprocess.TimeoutExpired:
            logger.warning('Ingestion timeout')
        except Exception as e:
            logger.exception(f'Ingestion error: {e}')


class IdempotentIngestionMixin:
    """Mixin to make ingestion operations idempotent.
    
    Prevents duplicate ingestion by checking checksums/IDs before insert.
    """
    
    def __init__(self, db_connection=None) -> None:
        self.db = db_connection or get_db_connection()
        self._recent_ingestions: set[str] = set()
        
    def is_already_ingested(self, checksum: str, table: str = 'raw_mlb.live_feed_snapshots') -> bool:
        """Check if data has already been ingested.
        
        Args:
            checksum: Data checksum or unique ID
            table: Table to check
            
        Returns:
            True if already ingested
        """
        # Check in-memory cache first
        if checksum in self._recent_ingestions:
            return True
        
        try:
            with self.db.cursor() as cur:
                cur.execute(f"""
                    SELECT 1 FROM {table}
                    WHERE checksum = %s
                    AND fetched_at > NOW() - INTERVAL '24 hours'
                    LIMIT 1
                """, (checksum,))
                
                if cur.fetchone():
                    self._recent_ingestions.add(checksum)
                    return True
                    
        except Exception as e:
            logger.error(f'Error checking ingestion status: {e}')
            # Fail open - assume not ingested to be safe
            return False
        
        return False
    
    def mark_ingested(self, checksum: str) -> None:
        """Mark data as ingested in memory cache."""
        self._recent_ingestions.add(checksum)
        
        # Keep cache size manageable
        if len(self._recent_ingestions) > 10000:
            # Remove oldest (first 1000)
            self._recent_ingestions = set(list(self._recent_ingestions)[1000:])
    
    def get_ingestion_checksum(self, data: dict) -> str:
        """Generate checksum for data to check for duplicates.
        
        Uses game_pk + timestamp for MLB data.
        """
        import hashlib
        import json
        
        # Extract identifying fields
        game_pk = data.get('game_pk', '')
        timestamp = data.get('timestamp', '')
        
        content = f"{game_pk}:{timestamp}"
        return hashlib.sha256(content.encode()).hexdigest()[:32]
