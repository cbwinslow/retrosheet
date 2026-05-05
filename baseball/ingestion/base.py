"""Base ingestion source with event hooks.

Provides super class for all data ingestion sources with:
- Event-driven hook system (pre_fetch, post_fetch, pre_load, on_error)
- Delegate functions for transformation
- Lambda-friendly data processing

Author: Agent Cascade
Date: 2026-04-30
"""

import logging
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol, Optional


logger = logging.getLogger(__name__)


# ============================================================================
# Result Types
# ============================================================================

@dataclass
class IngestionResult:
    """Standard result type for ingestion operations."""
    
    status: str  # 'success', 'error', 'no_data'
    records_processed: int = 0
    records_loaded: int = 0
    error_message: Optional[str] = None
    duration_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


# ============================================================================
# Hook Protocol (for type safety)
# ============================================================================

class IngestionHook(Protocol):
    """Protocol for ingestion hook functions."""
    def __call__(self, data: Any, context: dict[str, Any]) -> Any: ...


# ============================================================================
# Base Ingestion Source
# ============================================================================

class BaseIngestionSource(ABC):
    """Abstract base class for data ingestion sources.

    All ingestion sources (live feeds, REST APIs, WebSockets) inherit from this.
    Provides event hooks for extensible data pipelines.

    Hooks (Event Programming Pattern):
    - pre_fetch: Before API/WebSocket call (rate limiting, auth)
    - post_fetch: After data received (validation, caching)
    - pre_transform: Before normalization (custom parsing)
    - post_transform: After schema conversion (enrichment)
    - pre_load: Before database insert (deduplication)
    - on_error: Error handling (retries, alerts)

    Example:
        >>> class MlbLiveSource(BaseIngestionSource):
        ...     def fetch(self, params):
        ...         return requests.get(self.url).json()
        ...
        >>> source = MlbLiveSource()
        >>> source.on('post_fetch', lambda d, ctx: validate_schema(d))
        >>> data = source.ingest(game_id='716190')
    """

    def __init__(
        self,
        name: str,
        source_type: str,
        rate_limit_per_minute: int = 60,
        timeout_seconds: int = 30,
        retry_count: int = 3,
        transform_fn: Callable[[Any], Any] | None = None,
        filter_fn: Callable[[Any], bool] | None = None,
    ) -> None:
        """Initialize ingestion source.

        Args:
            name: Source identifier
            source_type: Type of source ('rest', 'websocket', 'file')
            rate_limit_per_minute: API rate limit
            timeout_seconds: Request timeout
            retry_count: Number of retries on failure
            transform_fn: Delegate for data transformation (lambda-friendly)
            filter_fn: Delegate for data filtering (lambda-friendly)
        """
        self.name = name
        self.source_type = source_type
        self.rate_limit_per_minute = rate_limit_per_minute
        self.timeout_seconds = timeout_seconds
        self.retry_count = retry_count

        # Delegate functions for flexibility
        self.transform_fn = transform_fn or (lambda x: x)
        self.filter_fn = filter_fn or (lambda x: True)

        # Event hooks storage (Event Pattern)
        self._hooks: dict[str, list[Callable]] = {
            'pre_fetch': [],
            'post_fetch': [],
            'pre_transform': [],
            'post_transform': [],
            'pre_load': [],
            'on_error': [],
        }

        # Statistics
        self._stats = {
            'fetch_count': 0,
            'records_processed': 0,
            'errors': 0,
            'last_fetch': None,
        }

        logger.info(f'Initialized {self.__class__.__name__}: {name}')

    # ========================================================================
    # Event Hook System
    # ========================================================================

    def on(self, event: str, handler: Callable[[Any, dict], Any]) -> 'BaseIngestionSource':
        """Register an event handler (Fluent interface).

        Args:
            event: Hook name (pre_fetch, post_fetch, etc.)
            handler: Callable to execute

        Returns:
            Self for method chaining

        Example:
            >>> source.on('post_fetch', lambda d, ctx: print(f"Fetched {len(d)} records"))
        """
        if event not in self._hooks:
            msg = f'Unknown event: {event}. Valid: {list(self._hooks.keys())}'
            raise ValueError(msg)

        self._hooks[event].append(handler)
        logger.debug(f'Registered handler for {event}')
        return self

    def off(self, event: str, handler: Callable | None = None) -> 'BaseIngestionSource':
        """Remove an event handler.

        Args:
            event: Hook name
            handler: Specific handler to remove, or None to remove all

        Returns:
            Self for method chaining
        """
        if handler is None:
            self._hooks[event] = []
        else:
            self._hooks[event] = [h for h in self._hooks[event] if h != handler]
        return self

    def emit(self, event: str, data: Any, context: dict[str, Any]) -> Any:
        """Trigger all handlers for an event.

        Args:
            event: Hook name
            data: Data to pass to handlers
            context: Additional context (metadata, params)

        Returns:
            Potentially modified data (handlers can transform)
        """
        result = data
        for handler in self._hooks.get(event, []):
            try:
                result = handler(result, context)
            except Exception as e:
                logger.warning(f'Hook {event} failed: {e}')
                # Continue with other handlers
        return result

    # ========================================================================
    # Abstract Methods (Must Implement)
    # ========================================================================

    @abstractmethod
    def fetch(self, params: dict[str, Any]) -> Any:
        """Fetch data from source.

        Args:
            params: Fetch parameters (game_id, date range, etc.)

        Returns:
            Raw data from source
        """

    @abstractmethod
    def transform(self, raw_data: Any) -> list[dict[str, Any]]:
        """Transform raw data to standardized format.

        Args:
            raw_data: Data from fetch()

        Returns:
            List of standardized record dictionaries
        """

    @abstractmethod
    def load(self, records: list[dict[str, Any]]) -> int:
        """Load records into database.

        Args:
            records: Transformed records

        Returns:
            Number of records loaded
        """

    # ========================================================================
    # Main Ingestion Pipeline
    # ========================================================================

    def ingest(self, **params) -> dict[str, Any]:
        """Execute full ingestion pipeline with hooks.

        Pipeline:
        1. pre_fetch hooks
        2. fetch() with retries
        3. post_fetch hooks
        4. transform() + pre_transform/post_transform hooks
        5. filter with filter_fn delegate
        6. pre_load hooks
        7. load()

        Args:
            **params: Parameters for fetch()

        Returns:
            Statistics about the ingestion run

        Example:
            >>> result = source.ingest(game_id='716190', date='2024-04-30')
            >>> print(f"Loaded {result['loaded']} records")
        """
        context = {
            'source_name': self.name,
            'params': params,
            'started_at': datetime.now(),
        }

        try:
            # Step 1: Pre-fetch hooks
            params = self.emit('pre_fetch', params, context)

            # Step 2: Fetch with retries
            raw_data = self._fetch_with_retry(params, context)

            if raw_data is None:
                return {'status': 'no_data', 'loaded': 0}

            # Step 3: Post-fetch hooks
            raw_data = self.emit('post_fetch', raw_data, context)

            # Step 4: Transform
            raw_data = self.emit('pre_transform', raw_data, context)
            records = self.transform(raw_data)
            records = self.emit('post_transform', records, context)

            # Step 5: Filter using delegate
            records = list(filter(self.filter_fn, records))

            # Step 6: Pre-load hooks
            records = self.emit('pre_load', records, context)

            # Step 7: Load
            loaded_count = self.load(records)

            # Update stats
            self._stats['fetch_count'] += 1
            self._stats['records_processed'] += len(records)
            self._stats['last_fetch'] = datetime.now()

            return {
                'status': 'success',
                'fetched': len(records),
                'loaded': loaded_count,
                'duration_ms': (datetime.now() - context['started_at']).total_seconds() * 1000,
            }

        except Exception as e:
            self._stats['errors'] += 1

            # Error hook
            error_context = {**context, 'error': str(e)}
            self.emit('on_error', e, error_context)

            logger.exception(f'Ingestion failed: {e}')
            raise

    def _fetch_with_retry(self, params: dict, context: dict) -> Any:
        """Fetch with automatic retry logic."""
        for attempt in range(self.retry_count):
            try:
                return self.fetch(params)
            except Exception as e:
                if attempt == self.retry_count - 1:
                    raise
                logger.warning(f'Fetch attempt {attempt + 1} failed: {e}, retrying...')
        return None

    def get_stats(self) -> dict[str, Any]:
        """Get ingestion statistics."""
        return self._stats.copy()

    def health_check(self) -> bool:
        """Verify source is operational."""
        try:
            self.fetch({})  # Minimal fetch
            return True
        except Exception as e:
            logger.exception(f'Health check failed for {self.name}: {e}')
            return False


# ============================================================================
# WebSocket Extension
# ============================================================================

class WebSocketIngestionSource(BaseIngestionSource):
    """Extension of BaseIngestionSource for WebSocket connections.

    Adds WebSocket-specific hooks:
    - on_connect: When connection established
    - on_message: When message received
    - on_disconnect: When connection closed
    - on_reconnect: Automatic reconnection
    """

    def __init__(self, *args, websocket_url: str, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.websocket_url = websocket_url
        self._ws_hooks = {
            'on_connect': [],
            'on_message': [],
            'on_disconnect': [],
            'on_reconnect': [],
        }
        self._connected = False
        self._messages_received = 0

    def fetch(self, params: dict[str, Any]) -> Any:
        """WebSocket sources fetch from connection buffer."""
        # WebSocket data arrives asynchronously
        # This method would return buffered messages
        msg = 'WebSocket sources use async message handling'
        raise NotImplementedError(msg)

    def on_ws(self, event: str, handler: Callable) -> 'WebSocketIngestionSource':
        """Register WebSocket-specific event handler."""
        if event not in self._ws_hooks:
            msg = f'Unknown WebSocket event: {event}'
            raise ValueError(msg)
        self._ws_hooks[event].append(handler)
        return self

    def emit_ws(self, event: str, data: Any) -> None:
        """Emit WebSocket event to all handlers."""
        for handler in self._ws_hooks.get(event, []):
            try:
                handler(data, {'source': self.name, 'event': event})
            except Exception as e:
                logger.warning(f'WebSocket hook {event} failed: {e}')


# ============================================================================
# Utility Functions (Lambda-friendly)
# ============================================================================

def create_filter(predicate: Callable[[Any], bool]) -> Callable[[Any], bool]:
    """Create filter function from predicate (for reuse).

    Example:
        >>> is_mlb = create_filter(lambda r: r.get('sport') == 'MLB')
        >>> source = SomeSource(filter_fn=is_mlb)
    """
    return predicate


def create_transform(*functions: Callable[[Any], Any]) -> Callable[[Any], Any]:
    """Chain multiple transform functions into one delegate.

    Example:
        >>> normalize = create_transform(
        ...     lambda r: {**r, 'date': parse_date(r['date'])},
        ...     lambda r: {**r, 'odds': decimalize(r['odds'])}
        ... )
    """
    def chained(data):
        for fn in functions:
            data = fn(data)
        return data
    return chained
