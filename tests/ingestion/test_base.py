"""Tests for BaseIngestionSource super class.

Covers:
- Abstract method enforcement
- Event hooks (pre_fetch, post_fetch, etc.)
- Delegate functions (transform_fn, filter_fn)
- Pipeline execution flow
- Error handling
- Multiple event consumers
"""


import contextlib

import pytest

from baseball.ingestion.base import BaseIngestionSource, WebSocketIngestionSource


# =============================================================================
# Concrete Implementation for Testing
# =============================================================================

class ConcreteIngestionSource(BaseIngestionSource):
    """Concrete implementation for testing."""

    def __init__(self, name='test', source_type='rest', **kwargs):
        super().__init__(name, source_type, **kwargs)
        self.fetch_called = False
        self.transform_called = False
        self.load_called = False
        self.last_fetch_params = None
        self.last_transform_data = None
        self.last_load_records = None

    def fetch(self, params=None):
        self.fetch_called = True
        self.last_fetch_params = params
        return {'data': 'test', 'params': params}

    def transform(self, raw_data):
        self.transform_called = True
        self.last_transform_data = raw_data
        return [{'transformed': True, 'raw': raw_data}]

    def load(self, records):
        self.load_called = True
        self.last_load_records = records
        return len(records)


class ConcreteWebSocketSource(WebSocketIngestionSource):
    """Concrete WebSocket implementation for testing."""

    def __init__(self, name='ws_test', **kwargs):
        super().__init__(name, **kwargs)
        self.connected = False
        self.received_messages = []

    async def connect(self):
        self.connected = True
        return True

    async def disconnect(self):
        self.connected = False
        return True

    async def receive_message(self):
        return {'type': 'test', 'data': 'message'}

    async def send_message(self, message):
        return True


# =============================================================================
# Abstract Class Tests
# =============================================================================

class TestBaseIngestionSourceAbstract:
    """Test abstract class behavior."""

    def test_abstract_methods_must_be_implemented(self):
        """Abstract methods must be implemented by subclass."""

        class IncompleteSource(BaseIngestionSource):
            def fetch(self, params): pass
            # Missing transform and load

        with pytest.raises(TypeError):
            IncompleteSource('test', 'rest')

    def test_concrete_class_can_instantiate(self):
        """Concrete implementation can be instantiated."""
        source = ConcreteIngestionSource()

        assert source.name == 'test'
        assert source.source_type == 'rest'
        assert source.state == 'idle'


# =============================================================================
# Event Hook Tests
# =============================================================================

class TestEventHooks:
    """Test event hook system."""

    def test_pre_fetch_hook_fires(self):
        """pre_fetch hook fires before fetch."""
        events = []
        source = ConcreteIngestionSource()
        source.on('pre_fetch', lambda ctx: events.append('pre_fetch'))

        source.ingest()

        assert 'pre_fetch' in events

    def test_post_fetch_hook_fires(self):
        """post_fetch hook fires after fetch."""
        events = []
        source = ConcreteIngestionSource()
        source.on('post_fetch', lambda data, ctx: events.append('post_fetch'))

        source.ingest()

        assert 'post_fetch' in events

    def test_pre_transform_hook_fires(self):
        """pre_transform hook fires before transform."""
        events = []
        source = ConcreteIngestionSource()
        source.on('pre_transform', lambda data, ctx: events.append('pre_transform'))

        source.ingest()

        assert 'pre_transform' in events

    def test_post_transform_hook_fires(self):
        """post_transform hook fires after transform."""
        events = []
        source = ConcreteIngestionSource()
        source.on('post_transform', lambda records, ctx: events.append('post_transform'))

        source.ingest()

        assert 'post_transform' in events

    def test_pre_load_hook_fires(self):
        """pre_load hook fires before load."""
        events = []
        source = ConcreteIngestionSource()
        source.on('pre_load', lambda records, ctx: events.append('pre_load'))

        source.ingest()

        assert 'pre_load' in events

    def test_post_complete_hook_fires(self):
        """post_complete hook fires at end."""
        events = []
        source = ConcreteIngestionSource()
        source.on('post_complete', lambda result, ctx: events.append('post_complete'))

        source.ingest()

        assert 'post_complete' in events

    def test_multiple_consumers_same_event(self):
        """Multiple consumers can listen to same event."""
        events = []
        source = ConcreteIngestionSource()

        source.on('pre_fetch', lambda ctx: events.append('consumer1'))
        source.on('pre_fetch', lambda ctx: events.append('consumer2'))
        source.on('pre_fetch', lambda ctx: events.append('consumer3'))

        source.ingest()

        assert events.count('consumer1') == 1
        assert events.count('consumer2') == 1
        assert events.count('consumer3') == 1

    def test_off_removes_listener(self):
        """off() removes event listener."""
        events = []
        source = ConcreteIngestionSource()

        def handler(ctx):
            return events.append('handler')
        source.on('pre_fetch', handler)
        source.off('pre_fetch', handler)

        source.ingest()

        assert 'handler' not in events

    def test_once_listener_only_fires_once(self):
        """once() listener only fires once."""
        events = []
        source = ConcreteIngestionSource()

        source.once('pre_fetch', lambda ctx: events.append('once'))

        source.ingest()
        source.ingest()  # Second call

        assert events.count('once') == 1


# =============================================================================
# Pipeline Execution Tests
# =============================================================================

class TestPipelineExecution:
    """Test ingest pipeline execution."""

    def test_ingest_executes_full_pipeline(self):
        """ingest() runs fetch → transform → load."""
        source = ConcreteIngestionSource()

        result = source.ingest()

        assert source.fetch_called is True
        assert source.transform_called is True
        assert source.load_called is True
        assert result == 1  # One record loaded

    def test_ingest_with_params_passed_to_fetch(self):
        """Params passed to ingest reach fetch."""
        source = ConcreteIngestionSource()
        test_params = {'sport': 'mlb', 'date': '2024-04-30'}

        source.ingest(params=test_params)

        assert source.last_fetch_params == test_params

    def test_fetch_data_reaches_transform(self):
        """Fetch output becomes transform input."""
        source = ConcreteIngestionSource()

        source.ingest()

        assert source.last_transform_data == {'data': 'test', 'params': None}

    def test_transform_output_reaches_load(self):
        """Transform output becomes load input."""
        source = ConcreteIngestionSource()

        source.ingest()

        assert len(source.last_load_records) == 1
        assert source.last_load_records[0]['transformed'] is True


# =============================================================================
# Delegate Function Tests
# =============================================================================

class TestDelegateFunctions:
    """Test transform and filter delegates."""

    def test_transform_fn_applied_in_pipeline(self):
        """Custom transform_fn modifies data."""
        transform_log = []

        def custom_transform(data):
            transform_log.append(data)
            return {**data, 'custom': True}

        source = ConcreteIngestionSource(transform_fn=custom_transform)
        source.ingest()

        assert len(transform_log) == 1
        # Data should have custom field after transform
        assert source.last_transform_data.get('custom') is True

    def test_filter_fn_filters_records(self):
        """Filter_fn filters transformed records."""
        class FilteringSource(BaseIngestionSource):
            def fetch(self, params):
                return [{'id': 1, 'valid': True}, {'id': 2, 'valid': False}]

            def transform(self, raw_data):
                return raw_data  # Pass through

            def load(self, records):
                self.loaded_records = records
                return len(records)

        source = FilteringSource(
            'filter_test', 'rest',
            filter_fn=lambda r: r.get('valid', False),
        )

        source.ingest()

        assert len(source.loaded_records) == 1
        assert source.loaded_records[0]['id'] == 1

    def test_default_transform_is_identity(self):
        """Default transform_fn is identity."""
        source = ConcreteIngestionSource()

        data = {'key': 'value'}
        result = source.transform_fn(data)

        assert result == data

    def test_default_filter_passes_all(self):
        """Default filter_fn passes all."""
        source = ConcreteIngestionSource()

        assert source.filter_fn({'any': 'data'}) is True
        assert source.filter_fn(None) is True

    def test_transform_fn_at_runtime(self):
        """transform_fn can be changed at runtime."""
        source = ConcreteIngestionSource()

        source.transform_fn = lambda d: {**d, 'runtime': True}
        source.ingest()

        assert source.last_transform_data.get('runtime') is True


# =============================================================================
# State Management Tests
# =============================================================================

class TestStateManagement:
    """Test state tracking."""

    def test_state_idle_initially(self):
        """Initial state is idle."""
        source = ConcreteIngestionSource()

        assert source.state == 'idle'

    def test_state_changes_during_ingest(self):
        """State changes through ingest lifecycle."""
        source = ConcreteIngestionSource()
        states = []

        source.on('pre_fetch', lambda ctx: states.append(source.state))
        source.on('post_fetch', lambda d, ctx: states.append(source.state))
        source.on('post_complete', lambda r, ctx: states.append(source.state))

        source.ingest()

        # States should show progression
        assert len(states) >= 3

    def test_state_error_on_failure(self):
        """State becomes error on failure."""

        class FailingSource(BaseIngestionSource):
            def fetch(self, params):
                msg = 'Fetch failed'
                raise Exception(msg)
            def transform(self, data):
                return data
            def load(self, records):
                return len(records)

        source = FailingSource('fail', 'rest')

        with contextlib.suppress(BaseException):
            source.ingest()

        assert source.state == 'error'


# =============================================================================
# Error Handling Tests
# =============================================================================

class TestErrorHandling:
    """Test error handling."""

    def test_fetch_error_fires_on_error_hook(self):
        """on_error hook fires on fetch failure."""

        class FailingSource(BaseIngestionSource):
            def fetch(self, params):
                msg = 'Fetch error'
                raise ValueError(msg)
            def transform(self, data):
                return data
            def load(self, records):
                return len(records)

        errors = []
        source = FailingSource('fail', 'rest', on_error=lambda e, ctx: errors.append(e))

        with contextlib.suppress(BaseException):
            source.ingest()

        assert len(errors) == 1
        assert 'Fetch error' in str(errors[0])

    def test_transform_error_fires_on_error_hook(self):
        """on_error hook fires on transform failure."""

        class BadTransformSource(BaseIngestionSource):
            def fetch(self, params):
                return {'data': 'test'}
            def transform(self, data):
                msg = 'Transform error'
                raise ValueError(msg)
            def load(self, records):
                return len(records)

        errors = []
        source = BadTransformSource('bad', 'rest', on_error=lambda e, ctx: errors.append(e))

        with contextlib.suppress(BaseException):
            source.ingest()

        assert len(errors) == 1
        assert 'Transform error' in str(errors[0])

    def test_load_error_fires_on_error_hook(self):
        """on_error hook fires on load failure."""

        class BadLoadSource(BaseIngestionSource):
            def fetch(self, params):
                return [{'test': 'data'}]
            def transform(self, data):
                return data
            def load(self, records):
                msg = 'Load error'
                raise ValueError(msg)

        errors = []
        source = BadLoadSource('bad', 'rest', on_error=lambda e, ctx: errors.append(e))

        with contextlib.suppress(BaseException):
            source.ingest()

        assert len(errors) == 1
        assert 'Load error' in str(errors[0])

    def test_error_does_not_call_post_complete(self):
        """post_complete not called on error."""

        class FailingSource(BaseIngestionSource):
            def fetch(self, params):
                msg = 'Fail'
                raise Exception(msg)
            def transform(self, data):
                return data
            def load(self, records):
                return len(records)

        completed = []
        source = FailingSource('fail', 'rest')
        source.on('post_complete', lambda r, ctx: completed.append(True))

        with contextlib.suppress(BaseException):
            source.ingest()

        assert len(completed) == 0


# =============================================================================
# WebSocket Source Tests
# =============================================================================

class TestWebSocketSource:
    """Test WebSocketIngestionSource."""

    @pytest.mark.asyncio
    async def test_websocket_connection(self):
        """WebSocket connects successfully."""
        source = ConcreteWebSocketSource()

        result = await source.connect()

        assert result is True
        assert source.connected is True

    @pytest.mark.asyncio
    async def test_websocket_disconnection(self):
        """WebSocket disconnects successfully."""
        source = ConcreteWebSocketSource()

        await source.connect()
        result = await source.disconnect()

        assert result is True
        assert source.connected is False

    def test_event_handlers_empty_initially(self):
        """Event handlers dict empty initially."""
        source = ConcreteWebSocketSource()

        assert source._event_handlers == {}

    def test_on_message_registers_handler(self):
        """on_message registers message handler."""
        source = ConcreteWebSocketSource()

        source.on_message('mlb', lambda msg, ctx: None)

        assert 'mlb' in source._event_handlers

    def test_on_connect_registers_handler(self):
        """on_connect registers connect handler."""
        source = ConcreteWebSocketSource()

        source.on_connect(lambda: None)

        assert 'connect' in source._event_handlers

    def test_on_disconnect_registers_handler(self):
        """on_disconnect registers disconnect handler."""
        source = ConcreteWebSocketSource()

        source.on_disconnect(lambda: None)

        assert 'disconnect' in source._event_handlers

    def test_on_error_registers_handler(self):
        """on_error registers error handler."""
        source = ConcreteWebSocketSource()

        source.on_error(lambda e: None)

        assert 'error' in source._event_handlers


# =============================================================================
# Integration Pattern Tests
# =============================================================================

class TestIntegrationPatterns:
    """Test source works in integration patterns."""

    def test_source_in_mapping_pattern(self):
        """Source can be used in source mapping."""
        source_map = {
            'test': ConcreteIngestionSource,
        }

        source_class = source_map['test']
        instance = source_class('instance', 'rest')

        assert isinstance(instance, BaseIngestionSource)

    def test_multiple_sources_polymorphism(self):
        """Multiple sources work polymorphically."""

        class SourceA(BaseIngestionSource):
            def fetch(self, params): return {'source': 'A'}
            def transform(self, data): return [data]
            def load(self, records): return len(records)

        class SourceB(BaseIngestionSource):
            def fetch(self, params): return {'source': 'B'}
            def transform(self, data): return [data]
            def load(self, records): return len(records)

        sources = [SourceA('a', 'rest'), SourceB('b', 'rest')]
        results = [s.ingest() for s in sources]

        assert results == [1, 1]

    def test_context_passed_through_pipeline(self):
        """Context passed through all stages."""
        source = ConcreteIngestionSource()
        contexts = []

        source.on('pre_fetch', lambda ctx: contexts.append(ctx.copy()))
        source.on('post_fetch', lambda d, ctx: contexts.append(ctx.copy()))
        source.on('post_complete', lambda r, ctx: contexts.append(ctx.copy()))

        source.ingest(params={'test': 'param'})

        # All contexts should have params
        for ctx in contexts:
            assert 'params' in ctx
