"""Advanced testing utilities for baseball testing infrastructure.

This module provides sophisticated testing utilities including performance measurement,
mock management, chaos engineering, and data validation tools.
"""

import time
import logging
import psutil
import os
import threading
import random
import pandas as pd
from typing import Any, Dict, List, Optional, Callable, ContextManager, Union
from unittest.mock import Mock, patch, MagicMock
from contextlib import contextmanager
from functools import wraps
from dataclasses import dataclass
from decimal import Decimal

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Performance measurement results."""
    operation_name: str
    duration_ms: float
    memory_delta_mb: float
    start_memory_mb: float
    end_memory_mb: float
    cpu_percent: Optional[float] = None
    success: bool = True
    error_message: Optional[str] = None


class PerformanceTimer:
    """Context manager for timing operations with performance monitoring."""
    
    def __init__(self, operation_name: str = "operation", target_ms: Optional[float] = None):
        self.operation_name = operation_name
        self.target_ms = target_ms
        self.start_time = None
        self.start_memory = None
        self.process = psutil.Process(os.getpid())
    
    def __enter__(self) -> 'PerformanceTimer':
        self.start_time = time.time()
        self.start_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time is None:
            return
        
        duration_ms = (time.time() - self.start_time) * 1000
        end_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        memory_delta = end_memory - self.start_memory
        
        logger.info(f"Performance: {self.operation_name} took {duration_ms:.2f}ms, "
                   f"memory delta: {memory_delta:+.2f}MB")
        
        if self.target_ms and duration_ms > self.target_ms:
            raise AssertionError(
                f"Operation {self.operation_name} took {duration_ms:.2f}ms, "
                f"exceeding target of {self.target_ms}ms"
            )
    
    @property
    def elapsed(self) -> float:
        """Get elapsed time in milliseconds."""
        if self.start_time is None:
            return 0.0
        return (time.time() - self.start_time) * 1000
    
    @classmethod
    def timer_decorator(cls, func: Callable) -> Callable:
        """Decorator to time a function."""
        @wraps(func)
        def wrapper(*args, **kwargs):
            with cls(f"{func.__module__}.{func.__name__}") as timer:
                result = func(*args, **kwargs)
            return result
        return wrapper


class DataValidator:
    """Utilities for validating baseball data integrity."""
    
    @staticmethod
    def validate_pitch_sequence(sequence: str) -> Dict[str, Any]:
        """Validate a pitch sequence format."""
        if not sequence:
            return {"valid": False, "error": "Empty sequence"}
        
        valid_pitches = {'B', 'S', 'F', 'X', '*', '+', '.', '/', 'C', 'L', 'R'}
        pitches = sequence.split(',')
        
        for i, pitch in enumerate(pitches):
            pitch = pitch.strip()
            if not pitch:
                return {"valid": False, "error": f"Empty pitch at position {i+1}"}
            if pitch not in valid_pitches:
                return {"valid": False, "error": f"Invalid pitch '{pitch}' at position {i+1}"}
        
        return {"valid": True}
    
    @staticmethod
    @staticmethod
    @staticmethod
    def validate_game_data(game: Dict) -> Dict[str, Any]:
        """Validate game data structure."""
        required_fields = ['game_id', 'date']
        
        for field in required_fields:
            if field not in game:
                return {"valid": False, "error": f"Missing required field: {field}"}
        
        return {"valid": True}
    @staticmethod
    @staticmethod
    def validate_player_data(player: Dict) -> Dict[str, Any]:
        """Validate player data structure."""
        required_fields = ['player_id', 'name']
        
        for field in required_fields:
            if field not in player:
                return {"valid": False, "error": f"Missing required field: {field}"}
        
        # Validate player_id format
        if not player['player_id']:
            return {"valid": False, "error": "Player ID cannot be empty"}
        
        return {"valid": True}
    @staticmethod
    def validate_betting_odds(odds: Union[int, float, str]) -> Dict[str, Any]:
        """Validate betting odds format."""
        try:
            if isinstance(odds, str):
                odds = int(odds)
            elif isinstance(odds, float):
                odds = int(odds)
            
            if odds == 0:
                return {"valid": False, "error": "Odds cannot be zero"}
            
            # Check if it's a reasonable odds range
            if abs(odds) > 10000:
                return {"valid": False, "error": f"Odds {odds} seem unrealistic"}
            
            return {"valid": True}
        except (ValueError, TypeError):
            return {"valid": False, "error": f"Invalid odds format: {odds}"}


class MockManager:
    """Advanced mocking utilities for testing."""
    
    def __init__(self):
        self.active_patches = []
        self.mock_objects = {}
    
    @contextmanager
    def mock_external_api(self, url_pattern: str, response_data: Any, 
                         status_code: int = 200, delay_ms: float = 0):
        """Mock external API calls with realistic behavior."""
        import requests
        
        mock_response = Mock()
        mock_response.status_code = status_code
        mock_response.json.return_value = response_data
        mock_response.text = str(response_data)
        mock_response.raise_for_status.return_value = None if status_code < 400 else Exception()
        
        if delay_ms > 0:
            original_get = requests.get
            def delayed_get(*args, **kwargs):
                time.sleep(delay_ms / 1000)
                return mock_response
            patch_obj = patch('requests.get', side_effect=delayed_get)
        else:
            patch_obj = patch('requests.get', return_value=mock_response)
        
        patch_obj.start()
        self.active_patches.append(patch_obj)
        
        try:
            yield mock_response
        finally:
            patch_obj.stop()
            self.active_patches.remove(patch_obj)
    
    @contextmanager
    def mock_database_query(self, table: str, return_data: List[Dict], 
                          query_pattern: Optional[str] = None):
        """Mock database queries with specific table responses."""
        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = return_data
        mock_cursor.fetchone.return_value = return_data[0] if return_data else None
        mock_cursor.rowcount = len(return_data)
        
        mock_conn = Mock()
        mock_conn.cursor.return_value = mock_cursor
        
        with patch('baseball.core.db.get_connection', return_value=mock_conn):
            yield mock_conn, mock_cursor
    
    @contextmanager
    def mock_redis_cache(self, cache_data: Dict[str, Any]):
        """Mock Redis cache operations."""
        mock_redis = Mock()
        
        def get_side_effect(key):
            return cache_data.get(key)
        
        def set_side_effect(key, value, *args, **kwargs):
            cache_data[key] = value
            return True
        
        mock_redis.get.side_effect = get_side_effect
        mock_redis.set.side_effect = set_side_effect
        mock_redis.exists.return_value = lambda key: key in cache_data
        mock_redis.delete.return_value = lambda key: cache_data.pop(key, None) is not None
        
        with patch('baseball.core.cache.redis_client', mock_redis):
            yield mock_redis
    
    def cleanup_all_mocks(self):
        """Clean up all active mock patches."""
        for patch_obj in self.active_patches:
            try:
                patch_obj.stop()
            except Exception as e:
                logger.warning(f"Error stopping patch: {e}")
        
        self.active_patches.clear()
        self.mock_objects.clear()


class ChaosEngineering:
    """Chaos engineering utilities for testing system resilience."""
    
    @staticmethod
    @contextmanager
    def inject_latency(target_func: Callable, delay_ms: float, 
                     probability: float = 1.0):
        """Inject latency into a function call."""
        original_func = target_func
        
        def delayed_func(*args, **kwargs):
            if random.random() < probability:
                time.sleep(delay_ms / 1000)
            return original_func(*args, **kwargs)
        
        with patch.object(target_func.__module__, target_func.__name__, delayed_func):
            yield
    
    @staticmethod
    @contextmanager
    def inject_failure(target_func: Callable, exception: Exception, 
                     probability: float = 0.1):
        """Inject failures into a function call."""
        original_func = target_func
        
        def failing_func(*args, **kwargs):
            if random.random() < probability:
                raise exception
            return original_func(*args, **kwargs)
        
        with patch.object(target_func.__module__, target_func.__name__, failing_func):
            yield
    
    @staticmethod
    @contextmanager
    def inject_corruption(target_func: Callable, corruption_func: Callable, 
                        probability: float = 0.1):
        """Inject data corruption into function return values."""
        original_func = target_func
        
        def corrupting_func(*args, **kwargs):
            result = original_func(*args, **kwargs)
            if random.random() < probability:
                result = corruption_func(result)
            return result
        
        with patch.object(target_func.__module__, target_func.__name__, corrupting_func):
            yield


class ConcurrencyTester:
    """Utilities for testing concurrent operations."""
    
    @staticmethod
    def run_concurrent_operations(operations: List[Callable], 
                                 max_workers: int = 5) -> List[Any]:
        """Run operations concurrently and return results."""
        import concurrent.futures
        
        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_op = {executor.submit(op): i for i, op in enumerate(operations)}
            
            for future in concurrent.futures.as_completed(future_to_op):
                op_index = future_to_op[future]
                try:
                    result = future.result()
                    results.append({'index': op_index, 'result': result, 'success': True})
                except Exception as e:
                    results.append({'index': op_index, 'error': str(e), 'success': False})
        
        # Sort by index to maintain order
        results.sort(key=lambda x: x['index'])
        # Extract just the results
        return [r['result'] for r in results if r['success']]
    
    @staticmethod
    @contextmanager
    def simulate_concurrent_load(target_func: Callable, num_threads: int = 10, 
                                operations_per_thread: int = 5):
        """Simulate concurrent load on a function."""
        results = []
        errors = []
        
        def worker():
            for _ in range(operations_per_thread):
                try:
                    result = target_func()
                    results.append(result)
                except Exception as e:
                    errors.append(e)
        
        threads = []
        for _ in range(num_threads):
            thread = threading.Thread(target=worker)
            threads.append(thread)
            thread.start()
        
        try:
            yield
        finally:
            for thread in threads:
                thread.join()
        
        return {'results': results, 'errors': errors}


class TestDataComparator:
    """Utilities for comparing test data and detecting regressions."""
    
    @staticmethod
    def compare_numeric_arrays(actual: List[float], expected: List[float], 
                             tolerance: float = 0.001) -> Dict[str, Any]:
        """Compare two numeric arrays with tolerance."""
        if len(actual) != len(expected):
            return {'equal': False, 'max_diff': None, 'errors': [f"Length mismatch: {len(actual)} vs {len(expected)}"]}
        
        errors = []
        max_diff = 0.0
        for i, (a, e) in enumerate(zip(actual, expected)):
            diff = abs(a - e)
            max_diff = max(max_diff, diff)
            if diff > tolerance:
                errors.append(f"Index {i}: {a} != {e} (diff: {diff})")
        
        return {'equal': len(errors) == 0, 'max_diff': max_diff, 'errors': errors}
    
    @staticmethod
    def compare_dataframes(df1: pd.DataFrame, df2: pd.DataFrame) -> Dict[str, Any]:
        """Compare two dataframes."""
        try:
            if df1.equals(df2):
                return {'equal': True}
            else:
                return {'equal': False}
        except Exception as e:
            return {'equal': False, 'error': str(e)}
    
    @staticmethod
    def compare_data_structures(actual: Dict, expected: Dict, 
                               ignore_keys: Optional[List[str]] = None) -> Dict[str, Any]:
        """Compare two data structures with optional key ignoring."""
        if ignore_keys is None:
            ignore_keys = []
        
        errors = []
        
        # Check for missing keys
        for key in expected:
            if key not in actual and key not in ignore_keys:
                errors.append(f"Missing key: {key}")
        
        # Check for extra keys
        for key in actual:
            if key not in expected and key not in ignore_keys:
                errors.append(f"Extra key: {key}")
        
        # Check values
        for key in expected:
            if key in actual and key not in ignore_keys:
                if actual[key] != expected[key]:
                    errors.append(f"Value mismatch for {key}: {actual[key]} != {expected[key]}")
        
        return {'equal': len(errors) == 0, 'errors': errors}
    
    @staticmethod
    def detect_performance_regression(current_metrics: PerformanceMetrics, 
                                    baseline_metrics: PerformanceMetrics,
                                    tolerance_factor: float = 1.5) -> Dict[str, Any]:
        """Detect performance regression compared to baseline."""
        regressions = []
        
        # Check duration regression
        if current_metrics.duration_ms > baseline_metrics.duration_ms * tolerance_factor:
            regressions.append(
                f"Duration regression: {current_metrics.duration_ms:.2f}ms vs "
                f"{baseline_metrics.duration_ms:.2f}ms baseline"
            )
        
        # Check memory regression
        if current_metrics.memory_delta_mb > baseline_metrics.memory_delta_mb * tolerance_factor:
            regressions.append(
                f"Memory regression: {current_metrics.memory_delta_mb:.2f}MB vs "
                f"{baseline_metrics.memory_delta_mb:.2f}MB baseline"
            )
        
        return {'has_regression': len(regressions) > 0, 'regressions': regressions}


# Decorators for advanced testing patterns

def with_performance_monitoring(target_ms: Optional[float] = None):
    """Decorator to monitor function performance."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            with PerformanceTimer(f"{func.__module__}.{func.__name__}", target_ms) as timer:
                return func(*args, **kwargs)
        return wrapper
    return decorator


def with_retry_mechanism(max_attempts: int = 3, delay: float = 1.0):
    """Decorator to add retry mechanism to flaky operations."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        logger.warning(f"Attempt {attempt + 1} failed for {func.__name__}, retrying: {e}")
                        time.sleep(delay * (2 ** attempt))  # Exponential backoff
                    else:
                        logger.error(f"All {max_attempts} attempts failed for {func.__name__}")
            raise last_exception
        return wrapper
    return decorator


def with_data_validation(validator_func: Callable):
    """Decorator to validate function inputs/outputs."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Validate inputs
            if len(args) > 1:  # Skip 'self' parameter
                for i, arg in enumerate(args[1:]):  # Skip 'self'
                    is_valid, error = validator_func(arg)
                    if not is_valid:
                        raise ValueError(f"Invalid argument {i}: {error}")
            
            # Call function
            result = func(*args, **kwargs)
            
            # Validate output
            is_valid, error = validator_func(result)
            if not is_valid:
                raise ValueError(f"Invalid return value: {error}")
            
            return result
        return wrapper
    return decorator


def with_chaos_testing(latency_ms: float = 0, failure_rate: float = 0.0):
    """Decorator to add chaos testing to functions."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Inject latency
            if latency_ms > 0 and random.random() < 0.5:
                time.sleep(latency_ms / 1000)
            
            # Inject failure
            if failure_rate > 0 and random.random() < failure_rate:
                raise Exception(f"Chaos testing induced failure in {func.__name__}")
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


def with_isolated_environment():
    """Decorator to run tests in isolated environment."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create isolated environment
            original_env = os.environ.copy()
            
            try:
                # Set test environment variables
                os.environ.update({
                    'TESTING': 'true',
                    'DATABASE_URL': 'postgresql://test:test@localhost:5432/test',
                    'REDIS_URL': 'redis://localhost:6379/1',
                    'LOG_LEVEL': 'DEBUG',
                })
                
                return func(*args, **kwargs)
            finally:
                # Restore original environment
                os.environ.clear()
                os.environ.update(original_env)
        return wrapper
    return decorator


# Utility functions for test data generation and manipulation

class TestDataManipulator:
    """Utilities for manipulating test data."""
    
    @staticmethod
    def corrupt_pitch_sequence(sequence: str, corruption_rate: float = 0.1) -> str:
        """Corrupt a pitch sequence for testing."""
        pitches = sequence.split(',')
        valid_pitches = ['B', 'S', 'F', 'X', '*', '+', '.', '/', 'C', 'L', 'R']
        
        for i, pitch in enumerate(pitches):
            if random.random() < corruption_rate:
                # Replace with invalid pitch
                pitches[i] = random.choice(['Z', 'Y', 'Q', '1', '2', '3'])
        
        return ','.join(pitches)
    
    @staticmethod
    def generate_edge_case_data(data_type: str) -> Any:
        """Generate edge case data for testing."""
        if data_type == 'pitch_sequence':
            return "B" * 100  # Very long sequence
        elif data_type == 'game_score':
            return 999  # Unreasonably high score
        elif data_type == 'player_age':
            return 150  # Impossible age
        elif data_type == 'betting_odds':
            return -999999  # Extreme odds
        elif data_type == 'empty_string':
            return ""
        elif data_type == 'null_value':
            return "null"
        elif data_type == 'zero':
            return 0
        elif data_type == 'large_number':
            return 1000001
        else:
            return "edge_case_data"
    
    @staticmethod
    def create_boundary_test_cases(value_range: tuple) -> List[Any]:
        """Create boundary test cases for a value range."""
        min_val, max_val = value_range
        return [
            min_val - 1,  # Below minimum
            min_val,      # At minimum
            min_val + 1,  # Just above minimum
            (min_val + max_val) // 2,  # Middle value
            max_val - 1,  # Just below maximum
            max_val,      # At maximum
            max_val + 1,  # Above maximum
        ]


# Test configuration and environment management

class TestEnvironment:
    """Manage test environment configuration."""
    
    def __init__(self):
        self.config = self._load_default_config()
    
    def _load_default_config(self) -> Dict:
        """Load default test configuration."""
        return {
            'database': {
                'url': 'postgresql://test:test@localhost:5432/test_baseball',
                'echo': False,
                'pool_size': 5,
            },
            'redis': {
                'url': 'redis://localhost:6379/1',
                'decode_responses': True,
            },
            'api': {
                'base_url': 'http://localhost:8000',
                'timeout': 30,
                'retries': 3,
            },
            'performance': {
                'max_duration_ms': 5000,
                'max_memory_mb': 512,
                'max_cpu_percent': 90,
            },
            'logging': {
                'level': 'DEBUG',
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            }
        }
    
    def get_config(self, section: str, key: Optional[str] = None) -> Any:
        """Get configuration value."""
        if key:
            return self.config.get(section, {}).get(key)
        return self.config.get(section, {})
    
    def set_config(self, section: str, key: str, value: Any):
        """Set configuration value."""
        if section not in self.config:
            self.config[section] = {}
        self.config[section][key] = value
    
    def update_config(self, section: str, updates: Dict):
        """Update multiple configuration values."""
        if section not in self.config:
            self.config[section] = {}
        self.config[section].update(updates)


# Global test environment instance
test_env = TestEnvironment()