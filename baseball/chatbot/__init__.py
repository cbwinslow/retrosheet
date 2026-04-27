"""Chatbot/Natural Language Interface for baseball predictions.

Provides conversational interface for querying predictions,
game data, and model insights via natural language.

Author: Agent cbwinslow/retrosheet
Date: 2026-04-26
"""

from .chatbot import Chatbot
from .conversation_manager import ConversationManager
from .entity_extractor import Entity, EntityExtractor
from .intent_parser import Intent, IntentParser
from .response_generator import ResponseGenerator


__all__ = [
    'Chatbot',
    'ConversationManager',
    'Entity',
    'EntityExtractor',
    'Intent',
    'IntentParser',
    'ResponseGenerator',
]
