"""Live game state feature extraction for real-time predictions."""

from datetime import datetime
from typing import Any

from .base import FeatureExtractor
from .run_expectancy import RunExpectancyCalculator


class LiveStateExtractor(FeatureExtractor):
    """Extract features from live MLB game state for ML models."""

    def __init__(self, run_expectancy: RunExpectancyCalculator | None = None) -> None:
        super().__init__()
        self._re_calc = run_expectancy or RunExpectancyCalculator()

    def extract(self, game_state: dict[str, Any]) -> dict[str, Any]:
        """Extract features from a live game state dictionary."""
        features = {}

        # Inning state
        features['inning'] = game_state.get('inning', 1)
        features['is_top'] = 1 if game_state.get('is_top', True) else 0
        features['outs'] = game_state.get('outs', 0)

        # Score differential
        home_score = game_state.get('home_score', 0)
        away_score = game_state.get('away_score', 0)
        features['score_diff'] = home_score - away_score
        features['total_score'] = home_score + away_score

        # Base state (encoded as runners on 1st, 2nd, 3rd)
        bases = game_state.get('bases', {})
        features['runner_1b'] = 1 if bases.get('first', False) else 0
        features['runner_2b'] = 1 if bases.get('second', False) else 0
        features['runner_3b'] = 1 if bases.get('third', False) else 0

        # Run expectancy from base-out state
        f"{features['runner_1b']}{features['runner_2b']}{features['runner_3b']}"
        re_state = self._re_calc.get_run_expectancy(
            outs=features['outs'],
            runner_1b=features['runner_1b'],
            runner_2b=features['runner_2b'],
            runner_3b=features['runner_3b'],
        )
        features['run_expectancy'] = re_state

        # Game progression
        features['inning_normal'] = features['inning'] / 9.0

        # Win probability features
        features['leverage_index'] = game_state.get('leverage_index', 1.0)
        features['is_extra_innings'] = 1 if features['inning'] > 9 else 0

        # Pitcher state (if available)
        pitcher = game_state.get('pitcher', {})
        features['pitcher_pitches'] = pitcher.get('pitches', 0)
        features['pitcher_strikes'] = pitcher.get('strikes', 0)
        features['pitcher_balls'] = pitcher.get('balls', 0)

        # Count state
        count = game_state.get('count', {})
        balls = count.get('balls', 0)
        strikes = count.get('strikes', 0)
        features['count_balls'] = balls
        features['count_strikes'] = strikes
        features['count_strikes_adj'] = min(strikes, 2)  # 3rd strike not in count

        return features

    def extract_batch(self, game_states: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Extract features from multiple game states."""
        return [self.extract(state) for state in game_states]

    def get_feature_names(self) -> list[str]:
        """Return list of feature names produced by this extractor."""
        return [
            'inning', 'is_top', 'outs', 'score_diff', 'total_score',
            'runner_1b', 'runner_2b', 'runner_3b', 'run_expectancy',
            'inning_normal', 'leverage_index', 'is_extra_innings',
            'pitcher_pitches', 'pitcher_strikes', 'pitcher_balls',
            'count_balls', 'count_strikes', 'count_strikes_adj',
        ]


class GameContextExtractor(FeatureExtractor):
    """Extract game context features not tied to specific plate appearances."""

    def extract(self, game_data: dict[str, Any]) -> dict[str, Any]:
        """Extract game-level context features."""
        features = {}

        # Game info
        game = game_data.get('game', {})
        features['game_pk'] = game.get('game_pk', 0)
        features['season'] = game.get('season', datetime.now().year)
        features['game_type'] = game.get('game_type', 'R')  # Regular season

        # Teams
        features['home_team_id'] = game.get('home_team_id', 0)
        features['away_team_id'] = game.get('away_team_id', 0)

        # Game status
        features['is_night_game'] = 1 if game.get('is_night_game', True) else 0
        features['is_doubleheader'] = 1 if game.get('doubleheader', 'N') != 'N' else 0

        return features

    def extract_batch(self, game_data_list: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Extract features from multiple games."""
        return [self.extract(data) for data in game_data_list]

    def get_feature_names(self) -> list[str]:
        """Return list of feature names produced by this extractor."""
        return [
            'game_pk', 'season', 'game_type', 'home_team_id', 'away_team_id',
            'is_night_game', 'is_doubleheader',
        ]
