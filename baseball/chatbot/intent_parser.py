"""Intent parsing for natural language queries.

Converts natural language input into structured intents
for handling by the chatbot system.

Author: Agent cbwinslow/retrosheet
Date: 2026-04-26
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any


class IntentType(Enum):
    """Types of supported intents."""

    PREDICTION = 'prediction'  # "What's the win probability?"
    GAME_INFO = 'game_info'  # "Who's pitching?"
    PLAYER_STATS = 'player_stats'  # "What's Judge's batting average?"
    STANDINGS = 'standings'  # "Where are the Yankees in the standings?"
    SCHEDULE = 'schedule'  # "When do the Red Sox play next?"
    COMPARISON = 'comparison'  # "Compare Ohtani and Trout"
    EXPLANATION = 'explanation'  # "Why is the win probability 65%?"
    GREETING = 'greeting'  # "Hello"
    HELP = 'help'  # "What can you do?"
    UNKNOWN = 'unknown'


@dataclass
class Intent:
    """Parsed intent from user input.

    Attributes:
        intent_type: Type of intent
        confidence: Confidence score (0-1)
        raw_input: Original user input
        parameters: Extracted parameters for the intent
    """

    intent_type: IntentType
    confidence: float
    raw_input: str
    parameters: dict[str, Any]


class IntentParser:
    """Parse natural language into structured intents.

    Uses pattern matching and keyword detection to identify
    user intent from text input.

    Example:
        >>> parser = IntentParser()
        >>> intent = parser.parse("What's the win probability for the Yankees?")
        >>> print(intent.intent_type)  # IntentType.PREDICTION
    """

    # Intent patterns
    PATTERNS = {
        IntentType.PREDICTION: [
            r'win probability',
            r'chance of winning',
            r'odds of winning',
            r'will.*win',
            r'who.*win',
            r'prediction',
            r'forecast',
            r'run probability',
            r'will.*score',
            r'next run',
        ],
        IntentType.GAME_INFO: [
            r'who.*pitching',
            r'who.*batting',
            r'starting pitcher',
            r'lineup',
            r'score',
            r'inning',
            r'who.*playing',
            r'game.*status',
        ],
        IntentType.PLAYER_STATS: [
            r'batting average',
            r'era\b',
            r'ops\b',
            r'war\b',
            r'stats? for',
            r'how.*doing',
            r'what.*average',
            r'what.*stats',
            r'home runs',
            r'rbis?',
        ],
        IntentType.STANDINGS: [
            r'standings',
            r'division',
            r'wildcard',
            r'where.*rank',
            r'what.*place',
            r'games (behind|back)',
            r'gb\b',
        ],
        IntentType.SCHEDULE: [
            r'when.*play',
            r'schedule',
            r'next game',
            r'who.*playing',
            r'upcoming',
            r'tomorrow',
        ],
        IntentType.COMPARISON: [
            r'compare',
            r'vs\b',
            r'versus',
            r'better than',
            r'who.*better',
        ],
        IntentType.EXPLANATION: [
            r'why',
            r'how.*calculate',
            r'explain',
            r'what.*mean',
            r'how.*work',
        ],
        IntentType.GREETING: [
            r'^hello',
            r'^hi\b',
            r'^hey',
            r'^good morning',
            r'^good afternoon',
            r'^good evening',
        ],
        IntentType.HELP: [
            r'help',
            r'what.*do',
            r'what.*can',
            r'capabilities',
            r'commands',
            r'how.*use',
        ],
    }

    def __init__(self):
        """Initialize intent parser."""
        self._compile_patterns()

    def _compile_patterns(self) -> None:
        """Compile regex patterns for efficiency."""
        self._compiled = {}
        for intent_type, patterns in self.PATTERNS.items():
            self._compiled[intent_type] = [re.compile(p, re.IGNORECASE) for p in patterns]

    def parse(self, user_input: str) -> Intent:
        """Parse user input into intent.

        Args:
            user_input: Natural language input from user

        Returns:
            Parsed intent with confidence score
        """
        if not user_input or not user_input.strip():
            return Intent(
                intent_type=IntentType.UNKNOWN,
                confidence=0.0,
                raw_input=user_input,
                parameters={},
            )

        text = user_input.strip().lower()
        scores = self._score_intents(text)

        # Find best match
        best_intent = max(scores, key=scores.get)
        best_score = scores[best_intent]

        # Extract parameters
        parameters = self._extract_parameters(text, best_intent)

        return Intent(
            intent_type=best_intent,
            confidence=best_score,
            raw_input=user_input,
            parameters=parameters,
        )

    def _score_intents(self, text: str) -> dict[IntentType, float]:
        """Score all intents against input text.

        Args:
            text: Lowercase user input

        Returns:
            Dictionary mapping intent types to confidence scores
        """
        scores = dict.fromkeys(IntentType, 0.0)

        for intent_type, patterns in self._compiled.items():
            for pattern in patterns:
                if pattern.search(text):
                    scores[intent_type] += 1.0

            # Normalize by number of patterns
            if patterns:
                scores[intent_type] /= len(patterns)

        return scores

    def _extract_parameters(self, text: str, intent_type: IntentType) -> dict[str, Any]:
        """Extract relevant parameters based on intent.

        Args:
            text: Lowercase user input
            intent_type: Detected intent type

        Returns:
            Dictionary of extracted parameters
        """
        params = {}

        if intent_type == IntentType.PREDICTION:
            params.update(self._extract_prediction_params(text))
        elif intent_type == IntentType.PLAYER_STATS:
            params.update(self._extract_player_params(text))
        elif intent_type == IntentType.GAME_INFO:
            params.update(self._extract_game_params(text))
        elif intent_type == IntentType.STANDINGS:
            params.update(self._extract_standings_params(text))

        return params

    def _extract_prediction_params(self, text: str) -> dict[str, Any]:
        """Extract prediction-related parameters."""
        params = {}

        # Prediction type
        if 'win' in text or 'game' in text:
            params['prediction_type'] = 'win_probability'
        elif 'run' in text or 'score' in text:
            params['prediction_type'] = 'run_probability'
        elif 'outcome' in text or 'result' in text:
            params['prediction_type'] = 'pa_outcome'

        return params

    def _extract_player_params(self, text: str) -> dict[str, Any]:
        """Extract player-related parameters."""
        params = {}

        # Stat type
        stat_patterns = {
            'batting_average': r'batting average|ba\b|avg\b',
            'era': r'era\b',
            'ops': r'ops\b',
            'war': r'war\b',
            'home_runs': r'home runs?|hrs?\b',
            'rbis': r'rbis?|runs batted in',
        }

        for stat_type, pattern in stat_patterns.items():
            if re.search(pattern, text, re.IGNORECASE):
                params['stat_type'] = stat_type
                break

        return params

    def _extract_game_params(self, text: str) -> dict[str, Any]:
        """Extract game-related parameters."""
        params = {}

        # Game info type
        if 'pitch' in text:
            params['info_type'] = 'pitching'
        elif 'lineup' in text or 'batting' in text:
            params['info_type'] = 'lineup'
        elif 'score' in text:
            params['info_type'] = 'score'

        return params

    def _extract_standings_params(self, text: str) -> dict[str, Any]:
        """Extract standings-related parameters."""
        params = {}

        # Standing type
        if 'division' in text:
            params['standing_type'] = 'division'
        elif 'wildcard' in text or 'wild card' in text:
            params['standing_type'] = 'wildcard'
        elif 'league' in text:
            params['standing_type'] = 'league'

        return params

    def get_supported_intents(self) -> list[str]:
        """Get list of supported intent descriptions.

        Returns:
            List of human-readable intent descriptions
        """
        return [
            'Prediction queries (win probability, run probability)',
            'Game information (pitching matchups, lineups, scores)',
            'Player statistics (batting average, ERA, OPS, WAR)',
            'Standings (division, wildcard, league)',
            'Schedule (upcoming games, next game)',
            'Comparisons (player vs player)',
            'Explanations (how predictions work)',
        ]
