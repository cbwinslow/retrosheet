"""Pitch sequence feature extraction and training row generation.

This module provides:
- Pitch sequence parsing from Chadwick/Retrosheet data
- Training row generation for next-pitch and at-bat models
- Validation of count transitions
- Integration with the feature store workflow

Uses PostgreSQL stored procedures for efficient sequence parsing.

Author: Agent Cascade
Date: 2026-05-01
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from baseball.core.db import DatabasePool


logger = logging.getLogger(__name__)


@dataclass
class PitchSequenceConfig:
    """Configuration for pitch sequence feature extraction."""

    seasons: list[int] | None = None
    min_pitches_per_pa: int = 1
    validate_transitions: bool = True
    include_terminal_outcomes: bool = True


@dataclass
class ParsedPitch:
    """Single pitch with count context."""

    game_id: str
    plate_appearance_id: str
    pitch_index: int
    raw_symbol: str
    symbol_meaning: str
    symbol_group: str
    is_pitch_symbol: bool
    pre_pitch_balls: int
    pre_pitch_strikes: int
    post_pitch_balls: int
    post_pitch_strikes: int
    is_terminal_pitch: bool
    is_valid_transition: bool
    count_label: str
    pitch_category: str


@dataclass
class ValidationError:
    """Count transition validation error."""

    game_id: str
    plate_appearance_id: str
    pitch_index: int
    raw_symbol: str
    expected_balls: int
    expected_strikes: int
    actual_balls: int
    actual_strikes: int
    error_message: str


class PitchSequenceFeatureStore:
    """Feature store for pitch sequence data.

    Integrates with the existing baseball.features workflow and provides
    training rows for next-pitch and within-at-bat transition models.

    Uses PostgreSQL stored procedures for efficient parsing.
    """

    def __init__(self, db: DatabasePool | None = None) -> None:
        """Initialize pitch sequence feature store.

        Args:
            db: Database connection pool (uses default if not provided)
        """
        self.db = db or self._get_default_db()

    def _get_default_db(self) -> DatabasePool:
        """Get default database connection."""
        from baseball.core.db import get_db_connection

        return get_db_connection()

    async def parse_sequence(
        self,
        game_id: str,
        plate_appearance_id: str,
        pitch_seq_tx: str,
    ) -> list[ParsedPitch]:
        """Parse a pitch sequence string into individual pitches.

        Uses the pitch_sequence.parse_sequence PostgreSQL function
        for efficient server-side parsing with count tracking.

        Args:
            game_id: Game identifier
            plate_appearance_id: Plate appearance identifier
            pitch_seq_tx: Retrosheet pitch sequence string (e.g., "BBSX")

        Returns:
            List of parsed pitches with running count context
        """
        query = """
            SELECT * FROM pitch_sequence.parse_sequence($1, $2, $3)
        """

        rows = await self.db.fetch(query, game_id, plate_appearance_id, pitch_seq_tx)

        pitches = []
        for row in rows:
            pitch = ParsedPitch(
                game_id=row["game_id"],
                plate_appearance_id=row["plate_appearance_id"],
                pitch_index=row["pitch_index"],
                raw_symbol=row["raw_symbol"],
                symbol_meaning=row["symbol_meaning"],
                symbol_group=row["symbol_group"],
                is_pitch_symbol=row["is_pitch_symbol"],
                pre_pitch_balls=row["pre_pitch_balls"],
                pre_pitch_strikes=row["pre_pitch_strikes"],
                post_pitch_balls=row["post_pitch_balls"],
                post_pitch_strikes=row["post_pitch_strikes"],
                is_terminal_pitch=row["is_terminal_pitch"],
                is_valid_transition=row["is_valid_transition"],
                count_label=self._format_count_label(
                    row["pre_pitch_balls"], row["pre_pitch_strikes"]
                ),
                pitch_category=self._categorize_pitch(row["symbol_group"]),
            )
            pitches.append(pitch)

        logger.debug(
            "Parsed %d pitches from sequence '%s' for PA %s",
            len(pitches),
            pitch_seq_tx,
            plate_appearance_id,
        )

        return pitches

    def _format_count_label(self, balls: int, strikes: int) -> str:
        """Format count as 'B-S' label."""
        return f"{balls}-{strikes}"

    def _categorize_pitch(self, symbol_group: str) -> str:
        """Categorize pitch into modeling groups."""
        ball_groups = {"ball", "intentional_ball", "pitchout", "awarded_ball"}
        strike_groups = {
            "called_strike",
            "swinging_strike",
            "foul",
            "foul_tip",
            "foul_bunt",
            "automatic_strike",
        }
        in_play_groups = {"in_play", "in_play_pitchout"}

        if symbol_group in ball_groups:
            return "ball"
        elif symbol_group in strike_groups:
            return "strike"
        elif symbol_group in in_play_groups:
            return "in_play"
        elif symbol_group == "hit_by_pitch":
            return "hbp"
        else:
            return "other"

    async def get_training_rows(
        self,
        config: PitchSequenceConfig | None = None,
    ) -> list[dict[str, Any]]:
        """Get pitch-level training rows for modeling.

        Retrieves from pitch_sequence.training_rows materialized view
        with optional filtering.

        Args:
            config: Filter configuration

        Returns:
            List of training rows with features and targets
        """
        config = config or PitchSequenceConfig()

        query = """
            SELECT 
                game_id,
                plate_appearance_id,
                season,
                game_date,
                inning,
                is_bottom_inning,
                outs_before,
                start_bases,
                batting_team_id,
                fielding_team_id,
                batter_id,
                batter_hand,
                pitcher_id,
                pitcher_hand,
                event_code,
                outcome_class,
                outcome_group,
                pitch_index,
                raw_symbol,
                symbol_meaning,
                count_label,
                pitch_category,
                pre_pitch_balls,
                pre_pitch_strikes,
                is_two_strike,
                is_three_ball,
                is_terminal_pitch,
                next_pitch_symbol,
                terminal_outcome
            FROM pitch_sequence.training_rows
            WHERE ($1::int[] IS NULL OR season = ANY($1))
              AND ($2::int IS NULL OR pitch_index >= $2)
              AND ($3::bool IS FALSE OR is_valid_transition)
            ORDER BY season, game_date, game_id, plate_appearance_id, pitch_index
        """

        rows = await self.db.fetch(
            query,
            config.seasons,
            config.min_pitches_per_pa,
            config.validate_transitions,
        )

        result = [dict(row) for row in rows]

        logger.info("Retrieved %d pitch sequence training rows", len(result))

        return result

    async def validate_transitions(
        self,
        game_id: str | None = None,
        plate_appearance_id: str | None = None,
        season: int | None = None,
    ) -> list[ValidationError]:
        """Validate pitch sequence count transitions.

        Uses pitch_sequence.validate_transitions PostgreSQL function
        to detect any invalid count transitions.

        Args:
            game_id: Optional game filter
            plate_appearance_id: Optional PA filter
            season: Optional season filter

        Returns:
            List of validation errors found
        """
        query = """
            SELECT * FROM pitch_sequence.validate_transitions($1, $2, $3)
        """

        rows = await self.db.fetch(query, game_id, plate_appearance_id, season)

        errors = []
        for row in rows:
            error = ValidationError(
                game_id=row["game_id"],
                plate_appearance_id=row["plate_appearance_id"],
                pitch_index=row["pitch_index"],
                raw_symbol=row["raw_symbol"],
                expected_balls=row["expected_balls"],
                expected_strikes=row["expected_strikes"],
                actual_balls=row["post_pitch_balls"],
                actual_strikes=row["post_pitch_strikes"],
                error_message=row["validation_error"],
            )
            errors.append(error)

        if errors:
            logger.warning(
                "Found %d invalid pitch sequence transitions",
                len(errors),
            )
        else:
            logger.info("All pitch sequence transitions validated successfully")

        return errors

    async def get_coverage_summary(self, season: int | None = None) -> dict[str, Any]:
        """Get pitch sequence coverage summary statistics.

        Args:
            season: Optional season filter

        Returns:
            Summary statistics dict
        """
        query = """
            SELECT *
            FROM pitch_sequence.coverage_summary
            WHERE ($1::int IS NULL OR season = $1)
        """

        rows = await self.db.fetch(query, season)

        if not rows:
            return {}

        return dict(rows[0])

    async def get_symbol_distribution(
        self,
        season: int | None = None,
    ) -> list[dict[str, Any]]:
        """Get pitch symbol frequency distribution.

        Args:
            season: Optional season filter

        Returns:
            List of symbol frequencies
        """
        query = """
            SELECT *
            FROM pitch_sequence.symbol_distribution
            WHERE ($1::int IS NULL OR season = $1)
            ORDER BY frequency DESC
        """

        rows = await self.db.fetch(query, season)

        return [dict(row) for row in rows]

    async def refresh_materialized_views(self) -> None:
        """Refresh pitch sequence materialized views.

        Calls pitch_sequence.refresh_all() PostgreSQL procedure.
        Should be run after new data ingestion.
        """
        await self.db.execute("CALL pitch_sequence.refresh_all()")

        logger.info("Pitch sequence materialized views refreshed")

    async def build_features(
        self,
        seasons: list[int] | None = None,
    ) -> dict[str, int]:
        """Build pitch sequence features for specified seasons.

        Integrates with the feature store workflow. Refreshes materialized
        views and returns statistics.

        Args:
            seasons: Seasons to process (None = all)

        Returns:
            Statistics dict with row counts
        """
        logger.info("Building pitch sequence features for seasons: %s", seasons)

        # Refresh views
        await self.refresh_materialized_views()

        # Get stats
        summary = await self.get_coverage_summary(
            seasons[0] if seasons and len(seasons) == 1 else None
        )

        # Validate
        errors = await self.validate_transitions(season=seasons[0] if seasons else None)

        return {
            "total_pitches": summary.get("total_pitches", 0),
            "total_plate_appearances": summary.get("total_plate_appearances", 0),
            "total_games": summary.get("total_games", 0),
            "validation_errors": len(errors),
        }


# Convenience functions for CLI integration

async def parse_pitch_sequence(
    pitch_seq_tx: str,
    game_id: str = "",
    plate_appearance_id: str = "",
) -> list[ParsedPitch]:
    """Parse a pitch sequence string (convenience function).

    Args:
        pitch_seq_tx: Retrosheet pitch sequence (e.g., "BBSX")
        game_id: Optional game identifier
        plate_appearance_id: Optional PA identifier

    Returns:
        List of parsed pitches
    """
    store = PitchSequenceFeatureStore()
    return await store.parse_sequence(game_id, plate_appearance_id, pitch_seq_tx)


async def get_pitch_training_rows(
    seasons: list[int] | None = None,
) -> list[dict[str, Any]]:
    """Get training rows for pitch sequence models (convenience function).

    Args:
        seasons: Seasons to include

    Returns:
        List of training rows
    """
    store = PitchSequenceFeatureStore()
    config = PitchSequenceConfig(seasons=seasons)
    return await store.get_training_rows(config)


async def validate_pitch_sequences(season: int | None = None) -> list[ValidationError]:
    """Validate all pitch sequences (convenience function).

    Args:
        season: Optional season to validate

    Returns:
        List of validation errors
    """
    store = PitchSequenceFeatureStore()
    return await store.validate_transitions(season=season)
