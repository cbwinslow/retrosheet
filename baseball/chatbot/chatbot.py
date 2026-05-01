"""Main chatbot orchestrator.

Combines intent parsing, entity extraction, response generation,
and conversation management into a unified chatbot interface.

Author: Agent cbwinslow/retrosheet
Date: 2026-04-26
"""

import logging
from collections.abc import Callable
from typing import Any

from .conversation_manager import ConversationManager
from .entity_extractor import Entity, EntityExtractor
from .intent_parser import Intent, IntentParser, IntentType
from .response_generator import ResponseGenerator


logger = logging.getLogger(__name__)


class Chatbot:
    """Baseball prediction chatbot.

    Provides natural language interface for:
    - Win probability predictions
    - Player statistics queries
    - Game information
    - Standings and schedules
    - Model explanations

    Example:
        >>> from baseball.chatbot import Chatbot
        >>> bot = Chatbot()
        >>> # Simple interaction
        >>> response = bot.chat("What's the Yankees win probability?")
        >>> print(response)

        >>> # With conversation history
        >>> response = bot.chat('How about the Red Sox?')
        >>> print(response)  # Contextual response
    """

    def __init__(
        self,
        model_server=None,
        db_connection=None,
        query_handlers: dict[str, Callable] | None = None,
    ) -> None:
        """Initialize chatbot.

        Args:
            model_server: Model server for predictions
            db_connection: Database connection for data queries
            query_handlers: Custom handlers for specific intents
        """
        self.intent_parser = IntentParser()
        self.entity_extractor = EntityExtractor(db_connection)
        self.response_generator = ResponseGenerator()
        self.conversation = ConversationManager()

        self.model_server = model_server
        self.db = db_connection
        self.query_handlers = query_handlers or {}

        # Register default handlers
        self._register_default_handlers()

    def _register_default_handlers(self) -> None:
        """Register default query handlers."""
        self.query_handlers.update(
            {
                IntentType.PREDICTION: self._handle_prediction,
                IntentType.GAME_INFO: self._handle_game_info,
                IntentType.PLAYER_STATS: self._handle_player_stats,
                IntentType.STANDINGS: self._handle_standings,
                IntentType.SCHEDULE: self._handle_schedule,
                IntentType.COMPARISON: self._handle_comparison,
                IntentType.EXPLANATION: self._handle_explanation,
                IntentType.GREETING: self._handle_greeting,
                IntentType.HELP: self._handle_help,
                IntentType.UNKNOWN: self._handle_unknown,
            },
        )

    def chat(self, user_input: str) -> str:
        """Process user input and generate response.

        Args:
            user_input: Natural language input from user

        Returns:
            Natural language response
        """
        try:
            # Parse intent
            intent = self.intent_parser.parse(user_input)

            # Extract entities
            entities = self.entity_extractor.extract(user_input)

            # Add to conversation history
            self.conversation.add_user_message(
                content=user_input,
                intent=intent.intent_type.value,
                entities=[
                    {
                        'type': e.type,
                        'value': e.value,
                        'raw_text': e.raw_text,
                    }
                    for e in entities
                ],
            )

            # Get handler for intent
            handler = self.query_handlers.get(intent.intent_type)

            if handler:
                # Execute handler
                result = handler(intent, entities)

                # Generate response
                context = self._build_context(intent, entities)
                response = self.response_generator.generate(
                    intent.intent_type.value,
                    result,
                    context,
                )
            else:
                response = self.response_generator.generate_unknown_response()

            # Add response to history
            self.conversation.add_assistant_message(
                content=response,
                metadata={'intent': intent.intent_type.value},
            )

            return response

        except Exception as e:
            logger.exception(f'Error processing chat: {e}')
            return 'Sorry, I ran into an issue. Could you try rephrasing your question?'

    def _build_context(self, intent: Intent, entities: list[Entity]) -> dict[str, Any]:
        """Build context for response generation."""
        context = {
            'active_team': self.conversation.get_referred_team(),
            'active_player': self.conversation.get_referred_player(),
            'active_game': self.conversation.get_referred_game(),
            'is_follow_up': self.conversation.is_follow_up_question(),
            'intent_confidence': intent.confidence,
        }

        # Add entity values
        for entity in entities:
            if entity.type == 'team':
                context['active_team'] = entity.value
            elif entity.type == 'player':
                context['active_player'] = entity.value

        return context

    def _handle_prediction(self, intent: Intent, entities: list[Entity]) -> dict | None:
        """Handle prediction intent."""
        team = self._resolve_team(entities)

        if not team and self.model_server:
            # Try to get prediction for active game
            game_pk = self.conversation.get_referred_game()
            if game_pk:
                return self._get_live_prediction(game_pk)

        if not team:
            return None

        # Get prediction type from intent parameters
        pred_type = intent.parameters.get('prediction_type', 'win_probability')

        return {
            'prediction_type': pred_type,
            'team': team,
            'probability': 0.65,  # Placeholder - would query model
        }

    def _handle_game_info(self, intent: Intent, entities: list[Entity]) -> dict | None:
        """Handle game info intent."""
        team = self._resolve_team(entities)
        info_type = intent.parameters.get('info_type', 'general')

        # Placeholder - would query live data
        return {
            'info_type': info_type,
            'team': team,
            'home_team': team or 'Home',
            'away_team': 'Opponent',
            'home_score': 3,
            'away_score': 2,
            'inning': 7,
        }

    def _handle_player_stats(self, intent: Intent, entities: list[Entity]) -> dict | None:
        """Handle player stats intent."""
        # Try to get player from entities
        player = None
        for entity in entities:
            if entity.type == 'player':
                player = entity.value
                break

        # If no player found, try context
        if not player:
            player = self.conversation.get_referred_player()

        if not player:
            return None

        stat_type = intent.parameters.get('stat_type', 'general')

        # Placeholder stats
        stat_values = {
            'batting_average': '.285',
            'era': '3.45',
            'ops': '.892',
            'war': '4.2',
            'home_runs': '28',
            'rbis': '72',
        }

        return {
            'player_name': player,
            'stat_type': stat_type,
            'value': stat_values.get(stat_type, 'N/A'),
        }

    def _handle_standings(self, intent: Intent, entities: list[Entity]) -> dict | None:
        """Handle standings intent."""
        team = self._resolve_team(entities)

        if not team:
            return None

        standing_type = intent.parameters.get('standing_type', 'division')

        # Placeholder standings
        return {
            'team': team,
            'position': 2,
            'games_back': 2.5,
            'wins': 45,
            'losses': 35,
            'standing_type': standing_type,
        }

    def _handle_schedule(self, intent: Intent, entities: list[Entity]) -> dict | None:
        """Handle schedule intent."""
        team = self._resolve_team(entities)

        if not team:
            return None

        # Placeholder schedule
        return {
            'team': team,
            'opponent': 'Opponent',
            'date': 'tomorrow',
            'time': '7:05 PM',
            'location': 'home',
        }

    def _handle_comparison(self, intent: Intent, entities: list[Entity]) -> dict | None:
        """Handle comparison intent."""
        players = [e.value for e in entities if e.type == 'player']

        if len(players) < 2:
            return None

        return {
            'player1': players[0],
            'player2': players[1],
            'stat': 'batting_average',
            'player1_value': '.285',
            'player2_value': '.310',
        }

    def _handle_explanation(self, intent: Intent, entities: list[Entity]) -> dict | None:
        """Handle explanation intent."""
        return {
            'explanation': """I predict baseball outcomes using machine learning models trained on thousands of historical games.

My predictions consider:
• Current game state (score, inning, outs, base runners)
• Win Expectancy - historical probabilities for similar situations
• Leverage Index - how much the current situation affects the outcome
• Player matchups and recent performance
• Bullpen strength and fatigue

The models learn patterns from past games and apply them to current situations.""",
        }

    def _handle_greeting(self, intent: Intent, entities: list[Entity]) -> dict | None:
        """Handle greeting intent."""
        return {}  # Response generator handles greetings

    def _handle_help(self, intent: Intent, entities: list[Entity]) -> dict | None:
        """Handle help intent."""
        return {}  # Response generator handles help

    def _handle_unknown(self, intent: Intent, entities: list[Entity]) -> dict | None:
        """Handle unknown intent."""
        return None

    def _resolve_team(self, entities: list[Entity]) -> str | None:
        """Resolve team from entities or context."""
        # First try entities
        for entity in entities:
            if entity.type == 'team':
                return entity.value

        # Fall back to context
        return self.conversation.get_referred_team()

    def _get_live_prediction(self, game_pk: int) -> dict | None:
        """Get live prediction for a game."""
        if not self.model_server:
            return None

        # Would fetch live features and call model server
        # Placeholder for now
        return {
            'prediction_type': 'win_probability',
            'game_pk': game_pk,
            'probability': 0.65,
        }

    def get_conversation_summary(self) -> dict[str, Any]:
        """Get summary of current conversation.

        Returns:
            Conversation metadata and recent messages
        """
        return {
            'session_info': self.conversation.get_session_info(),
            'recent_messages': [
                {
                    'role': msg.role,
                    'content': msg.content[:100] + '...' if len(msg.content) > 100 else msg.content,
                }
                for msg in self.conversation.get_history(limit=5)
            ],
            'context': {
                'team': self.conversation.get_referred_team(),
                'player': self.conversation.get_referred_player(),
                'game': self.conversation.get_referred_game(),
            },
        }

    def reset_conversation(self) -> None:
        """Reset the conversation state."""
        self.conversation.reset()

    def get_supported_commands(self) -> list[str]:
        """Get list of supported commands.

        Returns:
            List of example commands
        """
        return [
            "What's the win probability for [team]?",
            'Will the [team] win today?',
            "What's [player]'s batting average?",
            "Who's pitching for [team]?",
            'Where are [team] in the standings?',
            'When do [team] play next?',
            'Compare [player1] and [player2]',
            'How do you calculate predictions?',
        ]
