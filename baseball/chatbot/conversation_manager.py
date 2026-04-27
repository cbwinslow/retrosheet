"""Conversation state management.

Tracks conversation history, context, and user preferences
for the chatbot system.

Author: Agent cbwinslow/retrosheet
Date: 2026-04-26
"""

import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class Message:
    """A single message in the conversation.

    Attributes:
        role: 'user' or 'assistant'
        content: Message text
        timestamp: When message was sent
        intent: Detected intent (for user messages)
        entities: Extracted entities (for user messages)
    """

    role: str
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    intent: str | None = None
    entities: list[dict] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ConversationContext:
    """Context for the current conversation.

    Attributes:
        active_game: Currently discussed game PK
        active_team: Currently discussed team code
        active_player: Currently discussed player ID
        topic_stack: Stack of conversation topics
        user_preferences: User-specific preferences
    """

    active_game: int | None = None
    active_team: str | None = None
    active_player: str | None = None
    topic_stack: list[str] = field(default_factory=list)
    user_preferences: dict[str, Any] = field(default_factory=dict)


class ConversationManager:
    """Manage conversation state and history.

    Tracks:
    - Message history
    - Conversation context (active game/team/player)
    - User preferences
    - Session state

    Example:
        >>> manager = ConversationManager()
        >>> manager.add_user_message('How are the Yankees doing?')
        >>> manager.add_assistant_message('The Yankees are currently...')
        >>> context = manager.get_context()
        >>> print(context.active_team)  # 'NYY'
    """

    def __init__(self, max_history: int = 20, session_id: str | None = None):
        """Initialize conversation manager.

        Args:
            max_history: Maximum number of messages to retain
            session_id: Optional session identifier
        """
        self.session_id = session_id or str(uuid.uuid4())
        self.max_history = max_history
        self._messages: deque = deque(maxlen=max_history)
        self._context = ConversationContext()
        self._created_at = datetime.now()
        self._last_activity = datetime.now()

    def add_user_message(
        self, content: str, intent: str | None = None, entities: list[dict] | None = None
    ) -> None:
        """Add a user message to history.

        Args:
            content: Message text
            intent: Detected intent type
            entities: Extracted entities
        """
        message = Message(
            role='user',
            content=content,
            intent=intent,
            entities=entities or [],
            timestamp=datetime.now(),
        )
        self._messages.append(message)
        self._last_activity = datetime.now()

        # Update context based on entities
        if entities:
            self._update_context_from_entities(entities)

    def add_assistant_message(self, content: str, metadata: dict | None = None) -> None:
        """Add an assistant message to history.

        Args:
            content: Message text
            metadata: Optional response metadata
        """
        message = Message(
            role='assistant',
            content=content,
            metadata=metadata or {},
            timestamp=datetime.now(),
        )
        self._messages.append(message)
        self._last_activity = datetime.now()

    def _update_context_from_entities(self, entities: list[dict]) -> None:
        """Update conversation context based on extracted entities."""
        for entity in entities:
            entity_type = entity.get('type')
            value = entity.get('value')

            if entity_type == 'team':
                self._context.active_team = value
                self._context.topic_stack.append(f'team:{value}')
            elif entity_type == 'player':
                self._context.active_player = value
                self._context.topic_stack.append(f'player:{value}')
            elif entity_type == 'game':
                self._context.active_game = int(value)
                self._context.topic_stack.append(f'game:{value}')

    def get_history(self, limit: int | None = None) -> list[Message]:
        """Get conversation history.

        Args:
            limit: Maximum number of messages (None = all)

        Returns:
            List of messages
        """
        messages = list(self._messages)
        if limit:
            messages = messages[-limit:]
        return messages

    def get_context(self) -> ConversationContext:
        """Get current conversation context."""
        return self._context

    def set_context(self, **kwargs) -> None:
        """Set conversation context values.

        Args:
            **kwargs: Context attributes to set
        """
        for key, value in kwargs.items():
            if hasattr(self._context, key):
                setattr(self._context, key, value)

    def get_last_user_message(self) -> Message | None:
        """Get the most recent user message."""
        for msg in reversed(self._messages):
            if msg.role == 'user':
                return msg
        return None

    def get_last_assistant_message(self) -> Message | None:
        """Get the most recent assistant message."""
        for msg in reversed(self._messages):
            if msg.role == 'assistant':
                return msg
        return None

    def is_follow_up_question(self) -> bool:
        """Check if the last message appears to be a follow-up.

        Returns:
            True if context suggests this is a follow-up
        """
        last_user = self.get_last_user_message()
        if not last_user:
            return False

        # Short messages often indicate follow-up
        if len(last_user.content.split()) <= 3:
            return True

        # Check for pronouns/references
        follow_up_indicators = [
            'they',
            'them',
            'their',
            'he',
            'she',
            'him',
            'his',
            'her',
            'that',
            'it',
            'this',
            'those',
            'these',
            'the',
            'a',
            'an',
        ]
        words = last_user.content.lower().split()
        if any(word in follow_up_indicators for word in words[:3]):
            return True

        return False

    def get_referred_team(self) -> str | None:
        """Get the team being referred to in context."""
        return self._context.active_team

    def get_referred_player(self) -> str | None:
        """Get the player being referred to in context."""
        return self._context.active_player

    def get_referred_game(self) -> int | None:
        """Get the game being referred to in context."""
        return self._context.active_game

    def set_preference(self, key: str, value: Any) -> None:
        """Set a user preference.

        Args:
            key: Preference name
            value: Preference value
        """
        self._context.user_preferences[key] = value

    def get_preference(self, key: str, default: Any = None) -> Any:
        """Get a user preference.

        Args:
            key: Preference name
            default: Default value if not set

        Returns:
            Preference value or default
        """
        return self._context.user_preferences.get(key, default)

    def clear_context(self) -> None:
        """Clear conversation context (keep history)."""
        self._context = ConversationContext()

    def reset(self) -> None:
        """Reset the entire conversation."""
        self._messages.clear()
        self._context = ConversationContext()
        self._last_activity = datetime.now()

    def get_session_info(self) -> dict[str, Any]:
        """Get session information.

        Returns:
            Dictionary with session metadata
        """
        return {
            'session_id': self.session_id,
            'created_at': self._created_at.isoformat(),
            'last_activity': self._last_activity.isoformat(),
            'message_count': len(self._messages),
            'user_message_count': sum(1 for m in self._messages if m.role == 'user'),
            'assistant_message_count': sum(1 for m in self._messages if m.role == 'assistant'),
            'active_team': self._context.active_team,
            'active_player': self._context.active_player,
            'active_game': self._context.active_game,
        }

    def to_dict(self) -> dict[str, Any]:
        """Serialize conversation to dictionary."""
        return {
            'session_id': self.session_id,
            'created_at': self._created_at.isoformat(),
            'last_activity': self._last_activity.isoformat(),
            'messages': [
                {
                    'role': m.role,
                    'content': m.content,
                    'timestamp': m.timestamp.isoformat(),
                    'intent': m.intent,
                    'entities': m.entities,
                    'metadata': m.metadata,
                }
                for m in self._messages
            ],
            'context': {
                'active_team': self._context.active_team,
                'active_player': self._context.active_player,
                'active_game': self._context.active_game,
                'topic_stack': self._context.topic_stack,
                'user_preferences': self._context.user_preferences,
            },
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'ConversationManager':
        """Create conversation manager from dictionary."""
        manager = cls(
            session_id=data.get('session_id'),
            max_history=20,
        )

        # Restore messages
        for msg_data in data.get('messages', []):
            msg = Message(
                role=msg_data['role'],
                content=msg_data['content'],
                timestamp=datetime.fromisoformat(msg_data['timestamp']),
                intent=msg_data.get('intent'),
                entities=msg_data.get('entities', []),
                metadata=msg_data.get('metadata', {}),
            )
            manager._messages.append(msg)

        # Restore context
        ctx_data = data.get('context', {})
        manager._context.active_team = ctx_data.get('active_team')
        manager._context.active_player = ctx_data.get('active_player')
        manager._context.active_game = ctx_data.get('active_game')
        manager._context.topic_stack = ctx_data.get('topic_stack', [])
        manager._context.user_preferences = ctx_data.get('user_preferences', {})

        # Restore timestamps
        manager._created_at = datetime.fromisoformat(data['created_at'])
        manager._last_activity = datetime.fromisoformat(data['last_activity'])

        return manager
