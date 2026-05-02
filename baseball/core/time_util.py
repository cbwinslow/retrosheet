"""Timezone-agnostic datetime utilities for baseball data.

All times are stored and processed in UTC to ensure consistency
regardless of where the code runs (West Coast, East Coast, etc.)

Author: Agent Cascade
Date: 2026-05-01
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

import pytz

# MLB operates primarily in Eastern Time for scheduling
MLB_TZ = pytz.timezone('America/New_York')
UTC = timezone.utc


class BaseballDateTime:
    """Timezone-agnostic datetime handler for baseball operations.
    
    All internal storage is UTC. Conversion to local time only
    happens at display boundaries.
    
    Example:
        >>> # Game time from MLB API (usually ET)
        >>> game_time = BaseballDateTime.from_mlb_api("2024-07-15T19:05:00")
        >>> 
        >>> # Current time in UTC
        >>> now = BaseballDateTime.now()
        >>> 
        >>> # Time until game
        >>> minutes_until = game_time.minutes_until()
        >>> 
        >>> # Convert to user's local time for display only
        >>> local_str = game_time.to_local_display()
    """
    
    def __init__(self, dt: Optional[datetime] = None) -> None:
        """Initialize with datetime. If naive, assumes UTC.
        
        Args:
            dt: datetime object (naive or timezone-aware)
        """
        if dt is None:
            self._dt = datetime.now(UTC)
        elif dt.tzinfo is None:
            # Naive datetime - treat as UTC
            self._dt = dt.replace(tzinfo=UTC)
        else:
            # Convert to UTC
            self._dt = dt.astimezone(UTC)
    
    @classmethod
    def now(cls) -> BaseballDateTime:
        """Get current time in UTC."""
        return cls(datetime.now(UTC))
    
    @classmethod
    def from_timestamp(cls, timestamp: float) -> BaseballDateTime:
        """Create from Unix timestamp (seconds since epoch)."""
        return cls(datetime.fromtimestamp(timestamp, tz=UTC))
    
    @classmethod
    def from_iso(cls, iso_string: str) -> BaseballDateTime:
        """Create from ISO 8601 string. Handles various formats."""
        # Try parsing with timezone
        try:
            dt = datetime.fromisoformat(iso_string.replace('Z', '+00:00'))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=UTC)
            return cls(dt)
        except ValueError:
            # Try without timezone - assume UTC
            dt = datetime.fromisoformat(iso_string)
            return cls(dt)
    
    @classmethod
    def from_mlb_api(cls, api_string: str) -> BaseballDateTime:
        """Create from MLB API datetime string (usually ET).
        
        MLB API returns times like '2024-07-15T19:05:00' in Eastern Time.
        """
        # Parse as Eastern, convert to UTC
        dt = datetime.fromisoformat(api_string)
        if dt.tzinfo is None:
            dt = MLB_TZ.localize(dt)
        return cls(dt)
    
    @classmethod
    def from_date(cls, year: int, month: int, day: int) -> BaseballDateTime:
        """Create from date components (midnight UTC)."""
        return cls(datetime(year, month, day, 0, 0, 0, tzinfo=UTC))
    
    @classmethod
    def today(cls) -> BaseballDateTime:
        """Get today's date at midnight UTC."""
        now = datetime.now(UTC)
        return cls(datetime(now.year, now.month, now.day, 0, 0, 0, tzinfo=UTC))
    
    # =========================================================================
    # Properties
    # =========================================================================
    
    @property
    def datetime(self) -> datetime:
        """Get underlying UTC datetime."""
        return self._dt
    
    @property
    def timestamp(self) -> float:
        """Get Unix timestamp."""
        return self._dt.timestamp()
    
    @property
    def iso_format(self) -> str:
        """Get ISO 8601 string with UTC timezone."""
        return self._dt.isoformat()
    
    @property
    def date(self) -> datetime:
        """Get date component (midnight UTC)."""
        return datetime(self._dt.year, self._dt.month, self._dt.day, 0, 0, 0, tzinfo=UTC)
    
    @property
    def year(self) -> int:
        return self._dt.year
    
    @property
    def month(self) -> int:
        return self._dt.month
    
    @property
    def day(self) -> int:
        return self._dt.day
    
    @property
    def hour(self) -> int:
        return self._dt.hour
    
    @property
    def minute(self) -> int:
        return self._dt.minute
    
    # =========================================================================
    # Comparison Methods
    # =========================================================================
    
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, BaseballDateTime):
            return False
        return self._dt == other._dt
    
    def __lt__(self, other: BaseballDateTime) -> bool:
        return self._dt < other._dt
    
    def __le__(self, other: BaseballDateTime) -> bool:
        return self._dt <= other._dt
    
    def __gt__(self, other: BaseballDateTime) -> bool:
        return self._dt > other._dt
    
    def __ge__(self, other: BaseballDateTime) -> bool:
        return self._dt >= other._dt
    
    # =========================================================================
    # Time Calculations
    # =========================================================================
    
    def minutes_until(self, other: Optional[BaseballDateTime] = None) -> float:
        """Minutes until another time (or from now if None)."""
        if other is None:
            other = BaseballDateTime.now()
        diff = self._dt - other._dt
        return diff.total_seconds() / 60.0
    
    def minutes_since(self, other: Optional[BaseballDateTime] = None) -> float:
        """Minutes since another time (or from now if None)."""
        if other is None:
            other = BaseballDateTime.now()
        return other.minutes_until(self)
    
    def add_minutes(self, minutes: float) -> BaseballDateTime:
        """Add minutes to this time."""
        return BaseballDateTime(self._dt + timedelta(minutes=minutes))
    
    def add_hours(self, hours: float) -> BaseballDateTime:
        """Add hours to this time."""
        return BaseballDateTime(self._dt + timedelta(hours=hours))
    
    def add_days(self, days: float) -> BaseballDateTime:
        """Add days to this time."""
        return BaseballDateTime(self._dt + timedelta(days=days))
    
    def is_before(self, other: BaseballDateTime) -> bool:
        """Check if this time is before another."""
        return self._dt < other._dt
    
    def is_after(self, other: BaseballDateTime) -> bool:
        """Check if this time is after another."""
        return self._dt > other._dt
    
    def is_between(self, start: BaseballDateTime, end: BaseballDateTime) -> bool:
        """Check if this time is between start and end (inclusive)."""
        return start._dt <= self._dt <= end._dt
    
    # =========================================================================
    # Display Methods (Conversion for UI only)
    # =========================================================================
    
    def to_local_display(self, tz: Optional[str] = None) -> str:
        """Convert to local timezone for display.
        
        Args:
            tz: Timezone name (e.g., 'America/Los_Angeles'). 
                If None, uses system local timezone.
        """
        if tz:
            local_tz = pytz.timezone(tz)
            local_dt = self._dt.astimezone(local_tz)
        else:
            # Convert to system local time
            local_dt = self._dt.astimezone()
        return local_dt.strftime('%Y-%m-%d %H:%M %Z')
    
    def to_mlb_display(self) -> str:
        """Convert to MLB timezone (Eastern) for display."""
        et_dt = self._dt.astimezone(MLB_TZ)
        return et_dt.strftime('%Y-%m-%d %H:%M %Z')
    
    def to_short_display(self) -> str:
        """Short display format (MM-DD HH:MM UTC)."""
        return self._dt.strftime('%m-%d %H:%M UTC')
    
    # =========================================================================
    # Game Status Helpers
    # =========================================================================
    
    def is_game_day(self, game_time: BaseballDateTime) -> bool:
        """Check if this time is on the same calendar day as game time.
        
        Uses MLB's definition: games typically start 1pm-10pm ET.
        """
        # Convert both to Eastern for day comparison
        self_et = self._dt.astimezone(MLB_TZ)
        game_et = game_time._dt.astimezone(MLB_TZ)
        return (self_et.year, self_et.month, self_et.day) == (game_et.year, game_et.month, game_et.day)
    
    def get_game_window(self) -> tuple[BaseballDateTime, BaseballDateTime]:
        """Get typical MLB game window for this date.
        
        Returns:
            (window_start, window_end) in UTC
            Window is typically 11:00 ET to 01:00+1 ET
        """
        # Get midnight ET for this date
        et_date = self._dt.astimezone(MLB_TZ).replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Game window: 11:00 AM ET to 1:00 AM+1 ET
        window_start = MLB_TZ.localize(et_date.replace(hour=11))
        window_end = MLB_TZ.localize((et_date + timedelta(days=1)).replace(hour=1))
        
        return BaseballDateTime(window_start), BaseballDateTime(window_end)
    
    def is_within_game_window(self) -> bool:
        """Check if current time is within typical game hours."""
        window_start, window_end = self.get_game_window()
        return self.is_between(window_start, window_end)
    
    # =========================================================================
    # String Representation
    # =========================================================================
    
    def __repr__(self) -> str:
        return f"BaseballDateTime({self._dt.isoformat()})"
    
    def __str__(self) -> str:
        return self._dt.strftime('%Y-%m-%d %H:%M:%S UTC')


# =========================================================================
# Utility Functions
# =========================================================================

def utc_now() -> datetime:
    """Get current UTC datetime."""
    return datetime.now(UTC)


def format_for_db(dt: datetime) -> str:
    """Format datetime for PostgreSQL (always UTC)."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC).isoformat()


def parse_from_db(db_string: str) -> datetime:
    """Parse datetime from PostgreSQL (assumes UTC if no tz)."""
    if db_string.endswith('+00'):
        db_string = db_string.replace('+00', '+00:00')
    dt = datetime.fromisoformat(db_string)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def get_season_dates(season: int) -> tuple[BaseballDateTime, BaseballDateTime]:
    """Get typical MLB season start and end dates.
    
    Args:
        season: Year (e.g., 2024)
        
    Returns:
        (season_start, season_end) in UTC
    """
    # MLB season typically starts late March/early April
    # and ends late September/early October
    start = BaseballDateTime.from_date(season, 3, 15)  # March 15
    end = BaseballDateTime.from_date(season, 10, 15)  # October 15
    return start, end


def is_during_season(dt: Optional[BaseballDateTime] = None) -> bool:
    """Check if current time is during MLB regular season."""
    if dt is None:
        dt = BaseballDateTime.now()
    
    season_start, season_end = get_season_dates(dt.year)
    return dt.is_between(season_start, season_end)
