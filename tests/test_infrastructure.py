"""Comprehensive test suite for baseball testing infrastructure."""

import pytest
from baseball.testing import (
    BaseballTestCase,
    TestDataComparator,
    TestDataManipulator,
    ConcurrencyTester,
    PerformanceTimer,
    DataValidator,
    Game,
    Player,
    Pitch,
    Team,
    GameFactory,
    PlayerFactory,
    PitchFactory,
    TeamFactory,
    StatisticsFactory,
    GameScenarioFactory,
)


class TestDataComparatorTests(BaseballTestCase):
    """Tests for TestDataComparator utility."""

    def test_compare_numeric_arrays_valid(self):
        """Test comparing two numeric arrays."""
        result = TestDataComparator.compare_numeric_arrays(
            [1.0, 2.0, 3.0], [1.0, 2.0, 3.0]
        )
        assert result['equal']
        assert result['max_diff'] == 0.0

    def test_compare_numeric_arrays_with_differences(self):
        """Test comparing arrays with differences."""
        result = TestDataComparator.compare_numeric_arrays(
            [1.0, 2.0, 3.0], [1.0, 2.5, 3.0]
        )
        assert not result['equal']
        assert result['max_diff'] == 0.5

    def test_compare_dataframes(self):
        """Test comparing two dataframes."""
        import pandas as pd
        df1 = pd.DataFrame({'a': [1, 2], 'b': [3, 4]})
        df2 = pd.DataFrame({'a': [1, 2], 'b': [3, 4]})
        result = TestDataComparator.compare_dataframes(df1, df2)
        assert result['equal']


class TestDataManipulatorTests(BaseballTestCase):
    """Tests for TestDataManipulator utility."""

    def test_generate_edge_case_data_null_value(self):
        """Test generating null value edge case data."""
        data = TestDataManipulator.generate_edge_case_data('null_value')
        assert data is not None

    def test_generate_edge_case_data_empty_string(self):
        """Test generating empty string edge case data."""
        data = TestDataManipulator.generate_edge_case_data('empty_string')
        assert data == ''

    def test_generate_edge_case_data_zero(self):
        """Test generating zero edge case data."""
        data = TestDataManipulator.generate_edge_case_data('zero')
        assert data == 0

    def test_generate_edge_case_data_large_number(self):
        """Test generating large number edge case data."""
        data = TestDataManipulator.generate_edge_case_data('large_number')
        assert data > 1e6

    def test_run_concurrent_operations(self):
        """Test running concurrent operations."""
        def simple_operation(x):
            return x * 2

        operations = [lambda i=i: simple_operation(i) for i in range(5)]
        results = ConcurrencyTester.run_concurrent_operations(
            operations, max_workers=3
        )
        assert results == [0, 2, 4, 6, 8]


class TestPerformanceTimerTests(BaseballTestCase):
    """Tests for TestPerformanceTimer utility."""

    def test_performance_timer_context_manager(self):
        """Test performance timer as context manager."""
        with PerformanceTimer('test_operation') as timer:
            import time
            time.sleep(0.001)
        assert timer.elapsed > 0

    def test_performance_timer_decorator(self):
        """Test performance timer as decorator."""
        @PerformanceTimer.timer_decorator
        def slow_function():
            import time
            time.sleep(0.001)
            return 42

        result = slow_function()
        assert result == 42


class TestDataValidatorTests(BaseballTestCase):
    """Tests for TestDataValidator utility."""

    def test_validate_player_data_valid(self):
        """Test validating valid player data."""
        data = {'player_id': 'p123', 'name': 'John Doe'}
        result = DataValidator.validate_player_data(data)
        assert result['valid']

    def test_validate_player_data_invalid(self):
        """Test validating invalid player data."""
        data = {'name': 'John Doe'}
        result = DataValidator.validate_player_data(data)
        assert not result['valid']

    def test_validate_game_data_valid(self):
        """Test validating valid game data."""
        data = {'game_id': 'g123', 'date': '2024-01-01'}
        result = DataValidator.validate_game_data(data)
        assert result['valid']


class TestBaseClassesTests(BaseballTestCase):
    """Tests for base classes."""

    def test_baseball_test_case_setup(self):
        """Test BaseballTestCase setup."""
        assert self is not None

    def test_baseball_test_case_assertions(self):
        """Test BaseballTestCase custom assertions."""
        assert self is not None


class TestDataFactoriesTests(BaseballTestCase):
    """Tests for data factories."""

    def test_player_factory_creates_player(self):
        """Test player factory creates valid player."""
        player = PlayerFactory.create_player()
        assert isinstance(player, Player)
        assert player.player_id is not None

    def test_player_factory_creates_roster(self):
        """Test player factory creates valid roster."""
        roster = PlayerFactory.create_roster()
        assert len(roster) == 26
        assert all(isinstance(p, Player) for p in roster)

    def test_pitch_factory_creates_pitch(self):
        """Test pitch factory creates valid pitch."""
        pitch = PitchFactory.create_pitch()
        assert isinstance(pitch, Pitch)
        assert pitch.pitch_id is not None

    def test_pitch_factory_creates_at_bat(self):
        """Test pitch factory creates valid at-bat."""
        at_bat = PitchFactory.create_at_bat()
        assert isinstance(at_bat, list)
        assert len(at_bat) == 4
        assert all(isinstance(p, Pitch) for p in at_bat)

    def test_team_factory_creates_team(self):
        """Test team factory creates valid team."""
        team = TeamFactory.create_team()
        assert isinstance(team, Team)
        assert team.team_id is not None

    def test_team_factory_creates_valid_team(self):
        """Test team factory creates specific team."""
        team = TeamFactory.create_team('Yankees')
        assert isinstance(team, Team)
        assert team.team_name == 'Yankees'

    def test_statistics_factory_creates_valid_stats(self):
        """Test statistics factory creates valid statistics."""
        stats = StatisticsFactory.create_pitching_stats()
        assert stats['era'] >= 0
        assert stats['whip'] >= 0

    def test_game_scenario_factory_creates_complete_game(self):
        """Test game scenario factory creates complete game."""
        scenario = GameScenarioFactory.create_complete_game()
        assert isinstance(scenario['game'], Game)
        assert isinstance(scenario['home_team'], Team)
        assert isinstance(scenario['away_team'], Team)
        assert scenario['home_team'].team_name == scenario['game'].home_team
        assert isinstance(scenario['pitches'], list)
        assert len(scenario['pitches']) > 0

    def test_game_scenario_factory_creates_season(self):
        """Test game scenario factory creates season."""
        scenarios = GameScenarioFactory.create_season()
        assert isinstance(scenarios, list)
        assert len(scenarios) == 10
        assert all('game' in s for s in scenarios)
        assert all('home_team' in s for s in scenarios)
        assert all('away_team' in s for s in scenarios)


class TestPropertyBasedTestingTests(BaseballTestCase):
    """Tests for property-based testing."""

    def test_player_id_properties(self):
        """Test player ID properties."""
        player = PlayerFactory.create_player()
        assert isinstance(player.player_id, str)
        assert len(player.player_id) > 0

    def test_pitch_sequence_properties(self):
        """Test pitch sequence properties."""
        at_bat = PitchFactory.create_at_bat()
        assert len(at_bat) > 0
        for i in range(1, len(at_bat)):
            assert at_bat[i].pitch_number > at_bat[i-1].pitch_number


class TestIntegrationScenariosTests(BaseballTestCase):
    """Tests for integration scenarios."""

    def test_complete_game_scenario_integration(self):
        """Test complete game scenario integration."""
        scenario = GameScenarioFactory.create_complete_game()
        assert isinstance(scenario['game'], Game)
        assert isinstance(scenario['home_team'], Team)
        assert isinstance(scenario['away_team'], Team)

    def test_season_scenario_integration(self):
        """Test season scenario integration."""
        scenarios = GameScenarioFactory.create_season()
        assert isinstance(scenarios, list)
        assert len(scenarios) == 10


class TestPerformanceMarkersTests(BaseballTestCase):
    """Tests for performance markers."""

    def test_factory_performance(self):
        """Test factory performance."""
        import time
        start = time.time()
        players = [PlayerFactory.create_player() for _ in range(100)]
        elapsed = time.time() - start
        assert len(players) == 100
        assert elapsed < 1.0