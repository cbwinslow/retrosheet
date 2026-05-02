"""Real-time prediction engine for live MLB games.

Uses live feed data to make next-pitch and at-bat outcome predictions
during active games. Leverages Markov models trained on historical data
and updates predictions as game state changes.

Author: Agent Cascade
Date: 2026-05-02
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4

import numpy as np
from rich.console import Console
from rich.table import Table

from baseball.core.db import get_db_connection
from baseball.models.schemas import GameState, EventType
from baseball.features.pitch_sequence import get_pitch_training_rows

logger = logging.getLogger(__name__)
console = Console()


class PredictionType(Enum):
    """Types of predictions the system can make."""
    NEXT_PITCH_TYPE = 'next_pitch_type'
    NEXT_PITCH_LOCATION = 'next_pitch_location'
    SWING_DECISION = 'swing_decision'
    CONTACT_OUTCOME = 'contact_outcome'
    PA_RESULT = 'pa_result'
    GAME_STATE_TRANSITION = 'game_state_transition'


@dataclass
class Prediction:
    """A single prediction with confidence."""
    prediction_type: PredictionType
    prediction: str
    confidence: float
    probabilities: dict[str, float] = field(default_factory=dict)
    features_used: dict[str, Any] = field(default_factory=dict)
    prediction_id: UUID = field(default_factory=uuid4)


@dataclass
class LiveGameContext:
    """Current state of a live game for prediction."""
    game_pk: int
    inning: int
    is_top_inning: bool
    outs: int
    balls: int
    strikes: int
    batter_id: int
    pitcher_id: int
    on_first: bool
    on_second: bool
    on_third: bool
    score_diff: int  # Positive = batting team ahead
    pitch_count_pa: int  # Pitches in current PA
    last_pitch_type: Optional[str] = None
    last_pitch_result: Optional[str] = None
    
    @property
    def base_state(self) -> str:
        """Encode base state as string (e.g., '101' for runners on 1st and 3rd)."""
        return f"{int(self.on_first)}{int(self.on_second)}{int(self.on_third)}"
    
    @property
    def count_label(self) -> str:
        """Format count as 'B-S' (e.g., '1-2')."""
        return f"{self.balls}-{self.strikes}"


class MarkovPitchPredictor:
    """Markov chain predictor for next pitch type based on count and previous pitch."""
    
    def __init__(self):
        self._transition_matrix: dict = {}
        self._is_trained = False
    
    def train(self, seasons: list[int] = None) -> None:
        """Train the Markov model on historical pitch sequence data."""
        logger.info("Training Markov pitch predictor...")
        
        # Query training data from pitch_sequence.training_rows
        query = """
        SELECT 
            count_label,
            raw_symbol as prev_pitch,
            next_pitch_symbol,
            COUNT(*) as freq
        FROM pitch_sequence.training_rows
        WHERE next_pitch_symbol IS NOT NULL
        GROUP BY count_label, raw_symbol, next_pitch_symbol
        ORDER BY count_label, raw_symbol, freq DESC
        """
        
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(query)
        
        # Build transition matrix: P(next | count, prev)
        transitions = {}
        for row in cur.fetchall():
            count_label, prev_pitch, next_pitch, freq = row
            key = (count_label, prev_pitch)
            
            if key not in transitions:
                transitions[key] = {}
            transitions[key][next_pitch] = freq
        
        # Normalize to probabilities
        for key, pitch_counts in transitions.items():
            total = sum(pitch_counts.values())
            self._transition_matrix[key] = {
                pitch: count / total for pitch, count in pitch_counts.items()
            }
        
        self._is_trained = True
        logger.info(f"Trained on {len(self._transition_matrix)} count+prev_pitch combinations")
    
    def predict(self, context: LiveGameContext) -> Optional[Prediction]:
        """Predict next pitch type given current game context."""
        if not self._is_trained:
            return None
        
        key = (context.count_label, context.last_pitch_type or 'X')
        
        if key not in self._transition_matrix:
            # Fall back to count-only lookup
            key = (context.count_label, None)
            if key not in self._transition_matrix:
                return None
        
        probs = self._transition_matrix[key]
        
        # Get most likely pitch
        best_pitch = max(probs, key=probs.get)
        confidence = probs[best_pitch]
        
        return Prediction(
            prediction_type=PredictionType.NEXT_PITCH_TYPE,
            prediction=best_pitch,
            confidence=confidence,
            probabilities=probs,
            features_used={
                'count': context.count_label,
                'prev_pitch': context.last_pitch_type,
                'pitcher_id': context.pitcher_id
            }
        )


class LivePredictionEngine:
    """Main engine for real-time predictions during live games."""
    
    def __init__(self):
        self.pitch_predictor = MarkovPitchPredictor()
        self._trained = False
    
    def initialize(self) -> None:
        """Load/training all prediction models."""
        logger.info("Initializing live prediction engine...")
        self.pitch_predictor.train()
        self._trained = True
        logger.info("Prediction engine ready")
    
    def get_live_context(self, game_pk: int) -> Optional[LiveGameContext]:
        """Fetch current game state from live tables."""
        query = """
        SELECT 
            g.game_pk,
            g.inning,
            g.is_top_inning,
            g.outs,
            e.balls,
            e.strikes,
            e.batter_id,
            e.pitcher_id,
            g.on_first,
            g.on_second,
            g.on_third,
            g.away_score - g.home_score as score_diff,
            e.event_index as pitch_count_pa
        FROM core.live_games g
        LEFT JOIN core.live_events e ON g.game_pk = e.game_pk
        WHERE g.game_pk = %s
        AND g.status_code = 'Live'
        ORDER BY e.event_index DESC
        LIMIT 1
        """
        
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(query, (game_pk,))
        row = cur.fetchone()
        
        if not row:
            return None
        
        return LiveGameContext(
            game_pk=row[0],
            inning=row[1],
            is_top_inning=row[2],
            outs=row[3],
            balls=row[4] or 0,
            strikes=row[5] or 0,
            batter_id=row[6],
            pitcher_id=row[7],
            on_first=row[8] or False,
            on_second=row[9] or False,
            on_third=row[10] or False,
            score_diff=row[11] or 0,
            pitch_count_pa=row[12] or 0
        )
    
    def predict_next_pitch(self, game_pk: int) -> Optional[Prediction]:
        """Get next pitch prediction for a live game."""
        if not self._trained:
            self.initialize()
        
        context = self.get_live_context(game_pk)
        if not context:
            logger.warning(f"No live context found for game {game_pk}")
            return None
        
        return self.pitch_predictor.predict(context)
    
    def predict_all(self, game_pk: int) -> dict[PredictionType, Prediction]:
        """Generate all available predictions for a game state."""
        predictions = {}
        
        # Next pitch prediction
        pitch_pred = self.predict_next_pitch(game_pk)
        if pitch_pred:
            predictions[PredictionType.NEXT_PITCH_TYPE] = pitch_pred
        
        return predictions


def display_prediction(prediction: Prediction, context: LiveGameContext = None) -> None:
    """Display a prediction in a formatted table."""
    table = Table(title="Live Game Prediction", show_header=True)
    table.add_column("Type", style="cyan")
    table.add_column("Prediction", style="green")
    table.add_column("Confidence", style="yellow")
    table.add_column("Context", style="dim")
    
    if context:
        ctx_str = f"{context.count_label}, Bases: {context.base_state}"
    else:
        ctx_str = "N/A"
    
    table.add_row(
        prediction.prediction_type.value,
        prediction.prediction,
        f"{prediction.confidence:.1%}",
        ctx_str
    )
    
    # Add probability breakdown
    if prediction.probabilities:
        table.add_section()
        for pitch, prob in sorted(prediction.probabilities.items(), key=lambda x: -x[1])[:5]:
            table.add_row(
                "",
                f"  {pitch}",
                f"{prob:.1%}",
                ""
            )
    
    console.print(table)


# Singleton instance
_prediction_engine: Optional[LivePredictionEngine] = None


def get_prediction_engine() -> LivePredictionEngine:
    """Get or create the singleton prediction engine."""
    global _prediction_engine
    if _prediction_engine is None:
        _prediction_engine = LivePredictionEngine()
    return _prediction_engine
