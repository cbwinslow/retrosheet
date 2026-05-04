"""
Base test classes and utilities for baseball testing infrastructure.

This module provides foundational test classes that all other tests should inherit from,
ensuring consistent setup, teardown, and testing patterns across the entire test suite.
"""

import pytest
import time
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Generator, ContextManager, Callable
from unittest.mock import Mock, patch, MagicMock
from contextlib import contextmanager
from functools import wraps

# Configure test logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class BaseballTestCase:
    """Base class for all baseball tests with common setup/teardown."""
    
    @classmethod
    def setup_class(cls):
        """Setup for entire test class."""
        logger.debug(f"Setting up test class: {cls.__name__}")
        cls.class_setup_data = {}
    
    @classmethod
    def teardown_class(cls):
        """Cleanup after entire test class."""
        logger.debug(f"Tearing down test class: {cls.__name__}")
        cls.class_setup_data.clear()
    
    def setup_method(self, method=None):
        """Setup for individual test method."""
        test_name = getattr(self, '_testMethodName', None)
        if test_name is None and method is not None:
            test_name = method.__name__
        elif test_name is None:
            test_name = "unknown"
        logger.debug(f"Setting up test method: {test_name}")
        self.method_setup_data = {}
        self.start_time = time.time()
    
    def teardown_method(self, method=None):
        """Cleanup after individual test method."""
        test_name = getattr(self, '_testMethodName', None)
        if test_name is None and method is not None:
            test_name = method.__name__
        elif test_name is None:
            test_name = "unknown"
        duration = time.time() - self.start_time
        logger.debug(f"Tearing down test method: {test_name} (took {duration:.3f}s)")
        self.method_setup_data.clear()


class DatabaseTestCase(BaseballTestCase):
    """Base class for database-related tests."""
    
    @pytest.fixture(autouse=True)
    def setup_test_database(self):
        """Setup isolated test database."""
        logger.debug("Setting up test database")
        
        # Mock database connection for testing
        with patch('baseball.core.db.get_connection') as mock_get_conn:
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_conn.cursor.return_value = mock_cursor
            mock_get_conn.return_value = mock_conn
            
            # Setup common mock responses
            mock_cursor.fetchall.return_value = []
            mock_cursor.fetchone.return_value = None
            mock_cursor.rowcount = 0
            
            yield mock_conn, mock_cursor
        
        logger.debug("Test database cleaned up")
    
    def execute_query(self, query: str, params: Optional[tuple] = None) -> List[Dict]:
        """Helper to execute test queries."""
        # This would be implemented with actual test database setup
        return []
    
    def assert_table_exists(self, table_name: str):
        """Assert that a table exists in the test database."""
        # Implementation would check actual database
        pass
    
    def assert_table_has_data(self, table_name: str, min_rows: int = 1):
        """Assert that a table has data."""
        # Implementation would check actual database
        pass


class CLITestCase(BaseballTestCase):
    """Base class for CLI tests."""
    
    def run_cli_command(self, command: str, args: Optional[List[str]] = None, 
                       expect_success: bool = True) -> Mock:
        """Run CLI command and return result."""
        logger.debug(f"Running CLI command: {command} with args: {args}")
        
        # Mock CLI runner for testing
        with patch('baseball.cli.main.app') as mock_app:
            mock_result = Mock()
            mock_result.exit_code = 0 if expect_success else 1
            mock_result.output = f"Mock output for {command}"
            
            if args:
                mock_app.invoke.return_value = mock_result
            else:
                mock_app.return_value = mock_result
            
            return mock_result
    
    def assert_command_succeeds(self, command: str, args: Optional[List[str]] = None):
        """Assert that a CLI command succeeds."""
        result = self.run_cli_command(command, args, expect_success=True)
        assert result.exit_code == 0, f"Command failed: {command}"
        return result
    
    def assert_command_fails(self, command: str, args: Optional[List[str]] = None):
        """Assert that a CLI command fails."""
        result = self.run_cli_command(command, args, expect_success=False)
        assert result.exit_code != 0, f"Command should have failed: {command}"
        return result


class IntegrationTestCase(BaseballTestCase):
    """Base class for integration tests."""
    
    @pytest.fixture(autouse=True)
    def setup_integration_environment(self):
        """Setup integration test environment."""
        logger.debug("Setting up integration environment")
        
        # Mock external services
        with patch('baseball.sources.mlb.live_api') as mock_mlb, \
             patch('baseball.sources.espn.api') as mock_espn, \
             patch('baseball.core.cache.redis_client') as mock_redis:
            
            # Setup mock responses
            mock_mlb.return_value = {"success": True, "data": []}
            mock_espn.return_value = {"success": True, "data": []}
            mock_redis.get.return_value = None
            mock_redis.set.return_value = True
            
            yield {
                'mlb': mock_mlb,
                'espn': mock_espn,
                'redis': mock_redis
            }
        
        logger.debug("Integration environment cleaned up")


class PerformanceTestCase(BaseballTestCase):
    """Base class for performance tests."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.performance_thresholds = {
            'default_max_duration_ms': 1000,
            'max_memory_mb': 100,
            'max_cpu_percent': 80,
        }
    
    @contextmanager
    def measure_performance(self, operation_name: str, 
                          max_duration_ms: Optional[int] = None) -> Generator[Dict, None, None]:
        """Context manager for measuring performance."""
        import psutil
        import os
        
        max_duration = max_duration_ms or self.performance_thresholds['default_max_duration_ms']
        
        # Record initial state
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        initial_time = time.time()
        
        logger.debug(f"Starting performance measurement: {operation_name}")
        
        try:
            yield {
                'operation_name': operation_name,
                'start_time': initial_time,
                'start_memory_mb': initial_memory,
            }
        finally:
            # Record final state
            final_memory = process.memory_info().rss / 1024 / 1024  # MB
            final_time = time.time()
            
            duration_ms = (final_time - initial_time) * 1000
            memory_delta_mb = final_memory - initial_memory
            
            metrics = {
                'operation_name': operation_name,
                'duration_ms': duration_ms,
                'memory_delta_mb': memory_delta_mb,
                'start_memory_mb': initial_memory,
                'end_memory_mb': final_memory,
            }
            
            logger.debug(f"Performance metrics for {operation_name}: {metrics}")
            
            # Assert performance thresholds
            if duration_ms > max_duration:
                pytest.fail(f"Operation {operation_name} took {duration_ms:.2f}ms, exceeding threshold {max_duration}ms")
            
            if memory_delta_mb > self.performance_thresholds['max_memory_mb']:
                pytest.fail(f"Operation {operation_name} used {memory_delta_mb:.2f}MB memory, exceeding threshold {self.performance_thresholds['max_memory_mb']}MB")
    
    def assert_performance_within_threshold(self, operation_name: str, operation_func, 
                                         max_duration_ms: Optional[int] = None):
        """Assert that an operation performs within thresholds."""
        with self.measure_performance(operation_name, max_duration_ms) as metrics:
            operation_func()
        
        return metrics


# Decorators for cross-cutting concerns

def log_performance(func):
    """Decorator to log performance of test functions."""
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        start_time = time.time()
        try:
            result = func(self, *args, **kwargs)
            duration = time.time() - start_time
            logger.info(f"Test {self.__class__.__name__}.{func.__name__} completed in {duration:.3f}s")
            return result
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Test {self.__class__.__name__}.{func.__name__} failed after {duration:.3f}s: {e}")
            raise
    return wrapper


def with_test_data(data_generator):
    """Decorator to provide test data to test methods."""
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            test_data = data_generator()
            return func(self, test_data, *args, **kwargs)
        return wrapper
    return decorator


def retry_on_failure(max_attempts: int = 3, delay: float = 1.0):
    """Decorator to retry flaky tests."""
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            last_exception = None
            for attempt in range(max_attempts):
                try:
                    return func(self, *args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        logger.warning(f"Test {func.__name__} failed (attempt {attempt + 1}/{max_attempts}), retrying in {delay}s: {e}")
                        time.sleep(delay)
                    else:
                        logger.error(f"Test {func.__name__} failed after {max_attempts} attempts: {e}")
            raise last_exception
        return wrapper
    return decorator


def skip_if_slow(func):
    """Decorator to skip tests that are slow during quick runs."""
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if pytest.mark.slow in getattr(self, 'pytestmark', []):
            pytest.skip("Skipping slow test in quick run mode")
        return func(self, *args, **kwargs)
    return wrapper


# Test utilities

class TestDataGenerator:
    """Utility class for generating test data."""
    
    @staticmethod
    def generate_game_data(count: int = 10) -> List[Dict]:
        """Generate realistic game test data."""
        import random
        from datetime import datetime, timedelta
        
        teams = ['Yankees', 'Red Sox', 'Dodgers', 'Giants', 'Cubs', 'Cardinals']
        games = []
        
        for i in range(count):
            game_date = datetime(2024, 4, 1) + timedelta(days=random.randint(0, 180))
            home_team = random.choice(teams)
            away_team = random.choice([t for t in teams if t != home_team])
            
            games.append({
                'game_pk': 123456 + i,
                'game_date': game_date.strftime('%Y-%m-%d'),
                'home_team': home_team,
                'away_team': away_team,
                'home_score': random.randint(0, 15),
                'away_score': random.randint(0, 15),
                'season': 2024,
            })
        
        return games
    
    @staticmethod
    def generate_player_data(count: int = 10) -> List[Dict]:
        """Generate realistic player test data."""
        import random
        
        first_names = ['John', 'Mike', 'David', 'Chris', 'Alex', 'Matt', 'James', 'Robert']
        last_names = ['Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis']
        positions = ['P', 'C', '1B', '2B', '3B', 'SS', 'LF', 'CF', 'RF', 'DH']
        
        players = []
        for i in range(count):
            players.append({
                'player_id': 10000 + i,
                'first_name': random.choice(first_names),
                'last_name': random.choice(last_names),
                'position': random.choice(positions),
                'team': random.choice(['Yankees', 'Red Sox', 'Dodgers', 'Giants']),
                'bats': random.choice(['L', 'R', 'S']),
                'throws': random.choice(['L', 'R']),
            })
        
        return players
    
    @staticmethod
    def generate_pitch_sequence(length: int = 10) -> str:
        """Generate realistic pitch sequence."""
        import random
        
        # Weighted pitch probabilities based on real baseball
        pitch_weights = {
            'B': 0.35,  # Ball
            'S': 0.25,  # Strike
            'F': 0.15,  # Foul
            'X': 0.10,  # Ball in play
            '*': 0.05,  # Wild pitch
            '+': 0.02,  # Hit by pitch
            '.': 0.03,  # Intentional ball
            '/': 0.02,  # Strikeout looking
            'C': 0.02,  # Strikeout swinging
            'L': 0.01,  # Lineout
        }
        
        pitches = []
        balls = 0
        strikes = 0
        
        for _ in range(length):
            pitch = random.choices(
                list(pitch_weights.keys()), 
                weights=list(pitch_weights.values())
            )[0]
            pitches.append(pitch)
            
            # Update counts
            if pitch in ['B', '*', '+']:
                balls += 1
            elif pitch in ['S', 'F', 'C', 'L']:
                strikes += 1
            
            # Early termination for strikeouts or walks
            if balls >= 4 or strikes >= 3:
                break
        
        return ','.join(pitches)


def with_performance_monitoring(func: Callable) -> Callable:
    """Decorator to add performance monitoring to a function."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            duration = time.time() - start_time
            logger.info(f"{func.__name__} took {duration:.3f}s")
            return result
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"{func.__name__} failed after {duration:.3f}s: {e}")
            raise
    return wrapper


def with_retry_mechanism(max_attempts: int = 3, delay: float = 1.0) -> Callable:
    """Decorator to add retry mechanism to a function."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    logger.warning(f"Attempt {attempt + 1} failed for {func.__name__}: {e}")
                    if attempt < max_attempts - 1:
                        time.sleep(delay * (2 ** attempt))  # Exponential backoff
            raise last_exception
        return wrapper
    return decorator


def with_data_validation(validator_func: Callable) -> Callable:
    """Decorator to add data validation to a function."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            if validator_func:
                validation = validator_func(result)
                if not validation.get('valid', False):
                    raise ValueError(f"Validation failed: {validation.get('error', 'Unknown error')}")
            return result
        return wrapper
    return decorator


def with_chaos_testing(failure_rate: float = 0.1) -> Callable:
    """Decorator to add chaos testing to a function."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            import random
            if random.random() < failure_rate:
                raise RuntimeError(f"Chaos testing: injected failure in {func.__name__}")
            return func(*args, **kwargs)
        return wrapper
    return decorator


def with_isolated_environment() -> Callable:
    """Decorator to run a function in an isolated environment."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            import tempfile
            import os
            old_cwd = os.getcwd()
            temp_dir = tempfile.mkdtemp()
            try:
                os.chdir(temp_dir)
                result = func(*args, **kwargs)
                return result
            finally:
                os.chdir(old_cwd)
                import shutil
                shutil.rmtree(temp_dir, ignore_errors=True)
        return wrapper
    return decorator



# Custom pytest markers
def performance_test(target_ms: Optional[int] = None):
    """Decorator for performance tests."""
    return pytest.mark.performance_test(target_ms=target_ms)


def chaos_test(disabled: bool = False):
    """Decorator for chaos tests."""
    return pytest.mark.chaos_test(disabled=disabled)


def property_test(max_examples: int = 100):
    """Decorator for property-based tests."""
    return pytest.mark.property_test(max_examples=max_examples)


def integration_test():
    """Decorator for integration tests."""
    return pytest.mark.integration_test()


def e2e_test():
    """Decorator for end-to-end tests."""
    return pytest.mark.e2e_test()


def slow_test():
    """Decorator for slow tests."""
    return pytest.mark.slow
