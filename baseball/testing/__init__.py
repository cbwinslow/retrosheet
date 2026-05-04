"""
Baseball Testing Infrastructure

This module provides comprehensive testing infrastructure for the baseball prediction platform,
including base test classes, data factories, utilities, and advanced testing tools.

Following AGENTS.md namespace rules, all testing infrastructure exists under the baseball namespace.
"""

# Import base test classes
from .base import (
    BaseballTestCase,
    DatabaseTestCase, 
    CLITestCase,
    IntegrationTestCase,
    PerformanceTestCase,
    TestDataGenerator
)

# Import data factories
from .factories import (
    Game,
    Player,
    Pitch,
    Team,
    GameFactory,
    PlayerFactory,
    PitchFactory,
    TeamFactory,
    StatisticsFactory,
    GameScenarioFactory
)

# Import testing utilities
from .utils import (
    PerformanceTimer,
    DataValidator,
    MockManager,
    ChaosEngineering,
    ConcurrencyTester,
    TestDataComparator,
    TestDataManipulator,
    TestEnvironment,
    with_performance_monitoring,
    with_retry_mechanism,
    with_data_validation,
    with_chaos_testing,
    with_isolated_environment
)

# Import property-based testing utilities
from .properties import (
    WinExpectancyProperties,
    PitchSequenceProperties,
    FeatureCalculationProperties,
    ModelPredictionProperties,
    BettingAnalysisProperties,
    RetrosheetDataProperties,
    StatcastDataProperties,
    CrossSourceProperties,
    ScalabilityProperties,
    MemoryProperties,
    ConcurrencyProperties,
    player_ids_strategy,
    pitch_counts_strategy,
    game_score_strategy,
    inning_strategy,
    probability_strategy,
    run_expectancy_strategy,
    run_property_tests
)

__all__ = [
    # Base test classes
    'BaseballTestCase',
    'DatabaseTestCase',
    'CLITestCase', 
    'IntegrationTestCase',
    'PerformanceTestCase',
    'TestDataGenerator',
    
    # Data models
    'Game',
    'Player', 
    'Pitch',
    'Team',
    
    # Data factories
    'GameFactory',
    'PlayerFactory',
    'PitchFactory',
    'TeamFactory',
    'StatisticsFactory',
    'GameScenarioFactory',
    
    # Testing utilities
    'PerformanceTimer',
    'DataValidator',
    'MockManager',
    'ChaosEngineering',
    'ConcurrencyTester',
    'TestDataComparator',
    'TestDataManipulator',
    'TestEnvironment',
    'test_env',
    
    # Decorators
    'with_performance_monitoring',
    'with_retry_mechanism',
    'with_data_validation',
    'with_chaos_testing',
    'with_isolated_environment',
    
    # Property-based testing
    'WinExpectancyProperties',
    'PitchSequenceProperties',
    'FeatureCalculationProperties',
    'ModelPredictionProperties',
    'BettingAnalysisProperties',
    'RetrosheetDataProperties',
    'StatcastDataProperties',
    'CrossSourceProperties',
    'ScalabilityProperties',
    'MemoryProperties',
    'ConcurrencyProperties',
    'player_ids_strategy',
    'pitch_counts_strategy',
    'game_score_strategy',
    'inning_strategy',
    'probability_strategy',
    'run_expectancy_strategy',
    'run_property_tests'
]

# Global test environment instance
test_env = TestEnvironment()
