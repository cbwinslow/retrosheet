"""Smoke tests for chatbot namespace components."""

from baseball.chatbot.entity_extractor import EntityExtractor
from baseball.chatbot.response_generator import ResponseGenerator


def test_entity_extractor_maps_as_team_alias() -> None:
    extractor = EntityExtractor()
    entities = extractor.extract("How are the A's doing today?")
    teams = [entity.value for entity in entities if entity.type == 'team']
    assert 'OAK' in teams


def test_response_generator_help_contains_examples() -> None:
    generator = ResponseGenerator()
    response = generator.generate('help', result=None)
    assert 'ask' in response.lower() or 'what would you like' in response.lower()
