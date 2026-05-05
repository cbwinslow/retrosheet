"""Base classes for feature computation.

Provides the foundation for all feature calculators in the system.

Author: Agent cbwinslow/retrosheet
Date: 2026-04-26
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Any


logger = logging.getLogger(__name__)


class FeatureScope(Enum):
    """Scope of feature computation."""

    HISTORICAL = 'historical'
    LIVE = 'live'
    BOTH = 'both'


class FeatureStatus(Enum):
    """Status of feature computation."""

    PENDING = 'pending'
    COMPUTING = 'computing'
    COMPLETE = 'complete'
    FAILED = 'failed'


@dataclass
class FeatureConfig:
    """Configuration for feature computation.

    Attributes:
        scope: HISTORICAL, LIVE, or BOTH
        start_date: Start date for historical computation
        end_date: End date for historical computation
        season: Specific season to compute
        batch_size: Number of rows to process in each batch
        use_cache: Whether to use cached results
        force_recompute: Whether to force recomputation
        parallel_workers: Number of parallel workers
    """

    scope: FeatureScope = FeatureScope.BOTH
    start_date: date | None = None
    end_date: date | None = None
    season: int | None = None
    batch_size: int = 1000
    use_cache: bool = True
    force_recompute: bool = False
    parallel_workers: int = 4

    def __post_init__(self):
        """Validate configuration."""
        if self.start_date and self.end_date and self.start_date > self.end_date:
            msg = 'start_date must be before end_date'
            raise ValueError(msg)


@dataclass
class FeatureResult:
    """Result of feature computation.

    Attributes:
        success: Whether computation succeeded
        rows_computed: Number of rows computed
        rows_inserted: Number of rows inserted
        errors: List of error messages
        duration_seconds: Computation duration
        status: Computation status
        metadata: Additional metadata
    """

    success: bool = False
    rows_computed: int = 0
    rows_inserted: int = 0
    errors: list[str] = field(default_factory=list)
    duration_seconds: float = 0.0
    status: FeatureStatus = FeatureStatus.PENDING
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_error(self, error: str) -> None:
        """Add an error message."""
        self.errors.append(error)
        self.success = False
        self.status = FeatureStatus.FAILED

    def mark_complete(self) -> None:
        """Mark computation as complete."""
        self.status = FeatureStatus.COMPLETE
        self.success = len(self.errors) == 0


@dataclass
class GameState:
    """Represents a game state for feature computation.

    Attributes:
        inning: Inning number (1-20+)
        is_top: Top or bottom of inning
        outs: Number of outs (0-2)
        runner_1b: Runner on first base
        runner_2b: Runner on second base
        runner_3b: Runner on third base
        score_home: Home team score
        score_away: Away team score
    """

    inning: int
    is_top: bool
    outs: int
    runner_1b: bool = False
    runner_2b: bool = False
    runner_3b: bool = False
    score_home: int = 0
    score_away: int = 0

    @property
    def score_diff(self) -> int:
        """Score differential from home team perspective."""
        return self.score_home - self.score_away

    @property
    def base_state(self) -> str:
        """3-character base state code."""
        return (
            ('1' if self.runner_1b else '0')
            + ('1' if self.runner_2b else '0')
            + ('1' if self.runner_3b else '0')
        )

    @property
    def runners_on(self) -> int:
        """Number of runners on base."""
        return sum([self.runner_1b, self.runner_2b, self.runner_3b])

    def __str__(self) -> str:
        half = 'Top' if self.is_top else 'Bot'
        return f'{half} {self.inning}, {self.outs} outs, bases {self.base_state}'


class FeatureStore(ABC):
    """Abstract base class for feature stores.

    All feature calculators must inherit from this class.
    """

    def __init__(self, db_connection=None, config: FeatureConfig | None = None) -> None:
        """Initialize feature store.

        Args:
            db_connection: Database connection for persistence
            config: Feature computation configuration
        """
        self.db = db_connection
        self.config = config or FeatureConfig()
        self._cache: dict[str, Any] = {}

    @property
    @abstractmethod
    def feature_name(self) -> str:
        """Name of the feature."""

    @property
    @abstractmethod
    def table_name(self) -> str:
        """Database table name for storing features."""

    @abstractmethod
    def compute(self, game_state: GameState) -> float | None:
        """Compute feature for a game state.

        Args:
            game_state: Current game state

        Returns:
            Computed feature value or None
        """

    def compute_batch(self, game_states: list[GameState]) -> list[float | None]:
        """Compute features for multiple game states.

        Args:
            game_states: List of game states

        Returns:
            List of computed feature values
        """
        return [self.compute(gs) for gs in game_states]

    def save(
        self, game_pk: int, at_bat_index: int, value: float, metadata: dict | None = None,
    ) -> bool:
        """Save computed feature to database.

        Args:
            game_pk: Game ID
            at_bat_index: At-bat index within game
            value: Computed feature value
            metadata: Optional additional metadata

        Returns:
            True if saved successfully
        """
        if self.db is None:
            logger.warning('No database connection, cannot save feature')
            return False

        try:
            with self.db.cursor() as cur:
                cur.execute(
                    f"""INSERT INTO {self.table_name}
                        (game_pk, at_bat_index, feature_value, metadata, computed_at)
                        VALUES (%s, %s, %s, %s, NOW())
                        ON CONFLICT (game_pk, at_bat_index) DO UPDATE SET
                            feature_value = EXCLUDED.feature_value,
                            metadata = EXCLUDED.metadata,
                            computed_at = NOW()""",
                    (game_pk, at_bat_index, value, metadata if metadata else {}),
                )
            self.db.commit()
            return True
        except Exception as e:
            logger.exception(f'Failed to save feature: {e}')
            return False

    def load_from_db(self, game_pk: int | None = None) -> int:
        """Load features from database into cache.

        Args:
            game_pk: Optional game ID to filter by

        Returns:
            Number of features loaded
        """
        if self.db is None:
            return 0

        count = 0
        try:
            with self.db.cursor() as cur:
                if game_pk:
                    cur.execute(
                        f"""SELECT game_pk, at_bat_index, feature_value, metadata
                            FROM {self.table_name} WHERE game_pk = %s""",
                        (game_pk,),
                    )
                else:
                    cur.execute(
                        f"""SELECT game_pk, at_bat_index, feature_value, metadata
                            FROM {self.table_name}""",
                    )

                for row in cur.fetchall():
                    key = f'{row[0]}_{row[1]}'
                    self._cache[key] = {
                        'value': row[2],
                        'metadata': row[3],
                    }
                    count += 1

            logger.info(f'Loaded {count} {self.feature_name} features from database')
        except Exception as e:
            logger.exception(f'Failed to load features from DB: {e}')

        return count

    def get_cached(self, game_pk: int, at_bat_index: int) -> float | None:
        """Get cached feature value.

        Args:
            game_pk: Game ID
            at_bat_index: At-bat index

        Returns:
            Cached value or None
        """
        key = f'{game_pk}_{at_bat_index}'
        cached = self._cache.get(key)
        return cached['value'] if cached else None

    def build(self, config: FeatureConfig | None = None) -> FeatureResult:
        """Build features for configured scope.

        Args:
            config: Optional override configuration

        Returns:
            FeatureResult with computation results
        """
        import time

        start_time = time.time()
        result = FeatureResult(status=FeatureStatus.COMPUTING)

        cfg = config or self.config

        try:
            if cfg.scope in (FeatureScope.HISTORICAL, FeatureScope.BOTH):
                self._build_historical(cfg, result)

            if cfg.scope in (FeatureScope.LIVE, FeatureScope.BOTH):
                self._build_live(cfg, result)

            result.duration_seconds = time.time() - start_time
            result.mark_complete()

        except Exception as e:
            result.add_error(str(e))
            logger.exception(f'Feature build failed: {e}')

        return result

    def _build_historical(self, config: FeatureConfig, result: FeatureResult) -> None:
        """Build historical features.

        Args:
            config: Feature configuration
            result: Result object to update
        """
        logger.info(f'Building historical {self.feature_name} features')
        # Override in subclasses

    def _build_live(self, config: FeatureConfig, result: FeatureResult) -> None:
        """Build live features.

        Args:
            config: Feature configuration
            result: Result object to update
        """
        logger.info(f'Building live {self.feature_name} features')
        # Override in subclasses

    def get_stats(self) -> dict[str, Any]:
        """Get statistics about computed features.

        Returns:
            Dictionary with feature statistics
        """
        return {
            'feature_name': self.feature_name,
            'table_name': self.table_name,
            'cached_count': len(self._cache),
            'config': {
                'scope': self.config.scope.value,
                'batch_size': self.config.batch_size,
            },
        }


class BaseFeature(ABC):
    """Base class for feature calculators.
    
    Provides a common interface for all feature calculators in the system.
    Feature calculators can compute features for games, players, or other entities.
    
    Example:
        class MyFeatureCalculator(BaseFeature):
            def compute(self, game_pk: int, season: int) -> dict:
                # Compute features
                return {'feature_name': value}
    """
    
    def compute(self, *args, **kwargs) -> dict:
        """Compute features.
        
        Args:
            *args: Positional arguments for feature computation
            **kwargs: Keyword arguments for feature computation
            
        Returns:
            Dictionary containing computed features
            
        Raises:
            NotImplementedError: If not overridden by subclass
        """
        raise NotImplementedError("Subclasses must implement compute method")
