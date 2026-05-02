"""Tests for pitch sequence feature extraction.

Tests cover:
- Pitch sequence parsing
- Training row generation
- Count transition validation
- Integration with database procedures

Author: Agent Cascade
Date: 2026-05-01
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from baseball.features.pitch_sequence import (
    ParsedPitch,
    PitchSequenceConfig,
    PitchSequenceFeatureStore,
    ValidationError,
    get_pitch_training_rows,
    parse_pitch_sequence,
    validate_pitch_sequences,
)


class TestParsedPitch:
    """Tests for ParsedPitch dataclass."""

    def test_pitch_initialization(self):
        """Test creating a parsed pitch object."""
        pitch = ParsedPitch(
            game_id="2024_01_01_NYAL_BOS",
            plate_appearance_id="pa_001",
            pitch_index=1,
            raw_symbol="B",
            symbol_meaning="ball",
            symbol_group="ball",
            is_pitch_symbol=True,
            pre_pitch_balls=0,
            pre_pitch_strikes=0,
            post_pitch_balls=1,
            post_pitch_strikes=0,
            is_terminal_pitch=False,
            is_valid_transition=True,
            count_label="0-0",
            pitch_category="ball",
        )

        assert pitch.game_id == "2024_01_01_NYAL_BOS"
        assert pitch.raw_symbol == "B"
        assert pitch.count_label == "0-0"
        assert pitch.pitch_category == "ball"


class TestPitchSequenceConfig:
    """Tests for PitchSequenceConfig."""

    def test_default_config(self):
        """Test default configuration."""
        config = PitchSequenceConfig()

        assert config.seasons is None
        assert config.min_pitches_per_pa == 1
        assert config.validate_transitions is True
        assert config.include_terminal_outcomes is True

    def test_custom_config(self):
        """Test custom configuration."""
        config = PitchSequenceConfig(
            seasons=[2023, 2024],
            min_pitches_per_pa=3,
            validate_transitions=False,
        )

        assert config.seasons == [2023, 2024]
        assert config.min_pitches_per_pa == 3
        assert config.validate_transitions is False


class TestPitchSequenceFeatureStore:
    """Tests for PitchSequenceFeatureStore."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database."""
        db = MagicMock()
        db.fetch = AsyncMock()
        db.execute = AsyncMock()
        return db

    @pytest.fixture
    def store(self, mock_db):
        """Create feature store with mock DB."""
        with patch(
            "baseball.features.pitch_sequence.PitchSequenceFeatureStore._get_default_db",
            return_value=mock_db,
        ):
            return PitchSequenceFeatureStore()

    @pytest.mark.asyncio
    async def test_parse_sequence(self, store, mock_db):
        """Test parsing a pitch sequence."""
        # Mock database response
        mock_db.fetch.return_value = [
            {
                "game_id": "game_001",
                "plate_appearance_id": "pa_001",
                "pitch_index": 1,
                "raw_symbol": "B",
                "symbol_meaning": "ball",
                "symbol_group": "ball",
                "is_pitch_symbol": True,
                "pre_pitch_balls": 0,
                "pre_pitch_strikes": 0,
                "post_pitch_balls": 1,
                "post_pitch_strikes": 0,
                "is_terminal_pitch": False,
                "is_valid_transition": True,
            },
            {
                "game_id": "game_001",
                "plate_appearance_id": "pa_001",
                "pitch_index": 2,
                "raw_symbol": "C",
                "symbol_meaning": "called strike",
                "symbol_group": "called_strike",
                "is_pitch_symbol": True,
                "pre_pitch_balls": 1,
                "pre_pitch_strikes": 0,
                "post_pitch_balls": 1,
                "post_pitch_strikes": 1,
                "is_terminal_pitch": False,
                "is_valid_transition": True,
            },
        ]

        pitches = await store.parse_sequence(
            game_id="game_001",
            plate_appearance_id="pa_001",
            pitch_seq_tx="BC",
        )

        assert len(pitches) == 2
        assert pitches[0].raw_symbol == "B"
        assert pitches[0].count_label == "0-0"
        assert pitches[1].raw_symbol == "C"
        assert pitches[1].count_label == "1-0"

    @pytest.mark.asyncio
    async def test_parse_sequence_full_count(self, store, mock_db):
        """Test parsing sequence that reaches full count."""
        # B B C F F S sequence (3-2 count, foul with 2 strikes doesn't increment)
        mock_db.fetch.return_value = [
            {
                "game_id": "game_001",
                "plate_appearance_id": "pa_001",
                "pitch_index": i + 1,
                "raw_symbol": symbol,
                "symbol_meaning": desc,
                "symbol_group": group,
                "is_pitch_symbol": True,
                "pre_pitch_balls": pre_b,
                "pre_pitch_strikes": pre_s,
                "post_pitch_balls": post_b,
                "post_pitch_strikes": post_s,
                "is_terminal_pitch": is_term,
                "is_valid_transition": True,
            }
            for i, (symbol, desc, group, pre_b, pre_s, post_b, post_s, is_term) in enumerate(
                [
                    ("B", "ball", "ball", 0, 0, 1, 0, False),
                    ("B", "ball", "ball", 1, 0, 2, 0, False),
                    ("C", "called strike", "called_strike", 2, 0, 2, 1, False),
                    ("F", "foul", "foul", 2, 1, 2, 2, False),
                    ("F", "foul", "foul", 2, 2, 2, 2, False),  # Foul with 2 strikes
                    ("S", "swinging strike", "swinging_strike", 2, 2, 2, 3, True),  # Strikeout
                ]
            )
        ]

        pitches = await store.parse_sequence(
            game_id="game_001",
            plate_appearance_id="pa_001",
            pitch_seq_tx="BBCFFS",
        )

        # Verify count progression
        assert pitches[3].count_label == "2-1"
        assert pitches[4].count_label == "2-2"  # Foul with 2 strikes
        assert pitches[4].post_pitch_strikes == 2  # Didn't increment
        assert pitches[5].count_label == "2-2"
        assert pitches[5].is_terminal_pitch is True

    @pytest.mark.asyncio
    async def test_validate_transitions(self, store, mock_db):
        """Test validation of pitch transitions."""
        mock_db.fetch.return_value = [
            {
                "game_id": "game_001",
                "plate_appearance_id": "pa_001",
                "pitch_index": 3,
                "raw_symbol": "B",
                "expected_balls": 3,
                "expected_strikes": 0,
                "post_pitch_balls": 2,  # Wrong - should be 3
                "post_pitch_strikes": 0,
                "validation_error": "Count mismatch",
            }
        ]

        errors = await store.validate_transitions(season=2024)

        assert len(errors) == 1
        assert errors[0].game_id == "game_001"
        assert errors[0].expected_balls == 3
        assert errors[0].actual_balls == 2

    @pytest.mark.asyncio
    async def test_validate_transitions_clean(self, store, mock_db):
        """Test validation with no errors."""
        mock_db.fetch.return_value = []

        errors = await store.validate_transitions(season=2024)

        assert len(errors) == 0

    @pytest.mark.asyncio
    async def test_get_training_rows(self, store, mock_db):
        """Test retrieving training rows."""
        mock_db.fetch.return_value = [
            {
                "game_id": "game_001",
                "plate_appearance_id": "pa_001",
                "pitch_index": 1,
                "raw_symbol": "B",
                "count_label": "0-0",
                "pitch_category": "ball",
                "next_pitch_symbol": "C",
                "is_terminal_pitch": False,
            },
            {
                "game_id": "game_001",
                "plate_appearance_id": "pa_001",
                "pitch_index": 2,
                "raw_symbol": "C",
                "count_label": "1-0",
                "pitch_category": "strike",
                "next_pitch_symbol": "X",
                "is_terminal_pitch": False,
            },
        ]

        config = PitchSequenceConfig(seasons=[2024])
        rows = await store.get_training_rows(config)

        assert len(rows) == 2
        assert rows[0]["count_label"] == "0-0"
        assert rows[1]["count_label"] == "1-0"

    @pytest.mark.asyncio
    async def test_refresh_materialized_views(self, store, mock_db):
        """Test refreshing materialized views."""
        await store.refresh_materialized_views()

        mock_db.execute.assert_called_once_with("CALL pitch_sequence.refresh_all()")

    @pytest.mark.asyncio
    async def test_build_features(self, store, mock_db):
        """Test building features."""
        # Mock the coverage summary
        with patch.object(
            store, "refresh_materialized_views", AsyncMock()
        ) as mock_refresh:
            with patch.object(
                store,
                "get_coverage_summary",
                AsyncMock(return_value={"total_pitches": 1000, "total_plate_appearances": 300}),
            ):
                with patch.object(
                    store, "validate_transitions", AsyncMock(return_value=[])
                ):
                    stats = await store.build_features(seasons=[2024])

        assert stats["total_pitches"] == 1000
        assert stats["total_plate_appearances"] == 300
        assert stats["validation_errors"] == 0


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    @pytest.mark.asyncio
    async def test_parse_pitch_sequence(self):
        """Test parse_pitch_sequence convenience function."""
        with patch(
            "baseball.features.pitch_sequence.PitchSequenceFeatureStore.parse_sequence"
        ) as mock_parse:
            mock_parse.return_value = [
                ParsedPitch(
                    game_id="game_001",
                    plate_appearance_id="pa_001",
                    pitch_index=1,
                    raw_symbol="B",
                    symbol_meaning="ball",
                    symbol_group="ball",
                    is_pitch_symbol=True,
                    pre_pitch_balls=0,
                    pre_pitch_strikes=0,
                    post_pitch_balls=1,
                    post_pitch_strikes=0,
                    is_terminal_pitch=False,
                    is_valid_transition=True,
                    count_label="0-0",
                    pitch_category="ball",
                )
            ]

            pitches = await parse_pitch_sequence("B", "game_001", "pa_001")

            assert len(pitches) == 1
            assert pitches[0].raw_symbol == "B"

    @pytest.mark.asyncio
    async def test_get_pitch_training_rows(self):
        """Test get_pitch_training_rows convenience function."""
        with patch(
            "baseball.features.pitch_sequence.PitchSequenceFeatureStore.get_training_rows"
        ) as mock_get:
            mock_get.return_value = [{"game_id": "game_001"}]

            rows = await get_pitch_training_rows(seasons=[2024])

            assert len(rows) == 1
            assert rows[0]["game_id"] == "game_001"

    @pytest.mark.asyncio
    async def test_validate_pitch_sequences(self):
        """Test validate_pitch_sequences convenience function."""
        with patch(
            "baseball.features.pitch_sequence.PitchSequenceFeatureStore.validate_transitions"
        ) as mock_validate:
            mock_validate.return_value = []

            errors = await validate_pitch_sequences(season=2024)

            assert len(errors) == 0


class TestIntegration:
    """Integration tests for pitch sequence workflow."""

    @pytest.mark.asyncio
    async def test_end_to_end_workflow(self):
        """Test complete pitch sequence workflow."""
        # This would require a real database connection
        # For now, we verify the structure and call patterns

        store = PitchSequenceFeatureStore()

        # Verify the store has all required methods
        assert hasattr(store, "parse_sequence")
        assert hasattr(store, "get_training_rows")
        assert hasattr(store, "validate_transitions")
        assert hasattr(store, "refresh_materialized_views")
        assert hasattr(store, "build_features")
