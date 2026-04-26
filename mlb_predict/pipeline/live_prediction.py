"""Real-time prediction pipeline for live MLB games.

This module implements Phase 3: MLB Live Vertical Slice
- Live game state tracking
- Real-time feature computation
- Prediction pipeline for in-progress games

Author: Agent cbwinslow/retrosheet
Date: 2026-04-26
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from mlb_predict.features.live_features import FeatureComputation, LiveFeatureStore
from mlb_predict.pipeline.model_manager import LiveModelManager


@dataclass
class PredictionResult:
    """Result of a real-time prediction."""

    game_pk: int
    prediction_type: str  # win_prob, pa_outcome, etc.
    home_win_probability: float
    away_win_probability: float
    confidence: float
    features_used: list[str] = field(default_factory=list)
    model_version: str = 'unknown'
    computed_at: datetime = field(default_factory=datetime.now)
    latency_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class LiveGameContext:
    """Context for live game feature computation."""

    game_pk: int
    inning: int
    is_top: bool
    outs: int
    balls: int
    strikes: int
    home_score: int
    away_score: int
    base_state: int  # 0-7
    home_team_id: int
    away_team_id: int
    current_batter_id: int | None = None
    current_pitcher_id: int | None = None
    on_deck_batter_id: int | None = None
    in_hole_batter_id: int | None = None
    home_bullpen: list[int] = field(default_factory=list)
    away_bullpen: list[int] = field(default_factory=list)
    weather: dict[str, Any] | None = None
    wind: dict[str, Any] | None = None


class LivePredictionPipeline:
    """Real-time prediction pipeline for live MLB games.

    Architecture:
        Live Game State → Feature Computation → Model Inference → Prediction Cache
                              ↓
                    WebSocket/Streaming (future)

    Key Design Decisions:
    - Incremental feature computation (only recompute what changed)
    - Prediction caching with TTL
    - Sub-100ms latency target
    - Fallback to historical averages when live data incomplete
    """

    def __init__(
        self,
        model_path: Path | None = None,
        cache_ttl_seconds: float = 5.0,
        enable_websocket: bool = False,
    ):
        self._model_path = model_path or Path('data/models/live')
        self._cache_ttl = cache_ttl_seconds
        self._enable_websocket = enable_websocket

        # Prediction cache: game_pk -> (timestamp, result)
        self._prediction_cache: dict[int, tuple[float, PredictionResult]] = {}

        # Feature store for incremental computation
        self._feature_store = LiveFeatureStore(max_cache_size=1000)

        # Model manager for loading and inference
        self._model_manager = LiveModelManager(model_dir=self._model_path)

        # State change callbacks
        self._prediction_callbacks: list[Callable[[PredictionResult], None]] = []

        # Metrics
        self._predictions_made = 0
        self._cache_hits = 0
        self._cache_misses = 0
        self._total_latency_ms = 0.0

    def load_model(self, target: str = 'win_probability', model_name: str | None = None) -> bool:
        """Load the prediction model.

        Args:
            target: Prediction target (e.g., "win_probability")
            model_name: Specific model name (optional)

        Returns:
            True if model loaded successfully
        """
        return self._model_manager.load_model(target=target, model_name=model_name)

    def compute_features(
        self,
        context: LiveGameContext,
        incremental: bool = True,
    ) -> FeatureComputation:
        """Compute features for a live game situation.

        Args:
            context: Current live game context
            incremental: Only recompute changed features

        Returns:
            FeatureComputation with features and metadata
        """
        return self._feature_store.compute_features(
            context,
            force_recompute=not incremental,
        )

    def predict(
        self,
        context: LiveGameContext,
        use_cache: bool = True,
    ) -> PredictionResult:
        """Generate real-time prediction for a live game.

        Args:
            context: Current live game context
            use_cache: Use cached prediction if available

        Returns:
            Prediction result with probabilities and metadata
        """
        start_time = time.time()

        # Check cache
        if use_cache and context.game_pk in self._prediction_cache:
            timestamp, cached_result = self._prediction_cache[context.game_pk]
            if time.time() - timestamp < self._cache_ttl:
                self._cache_hits += 1
                return cached_result

        self._cache_misses += 1

        # Load model if not loaded
        if not self._model_manager.list_loaded_models():
            self.load_model()

        # Compute features (incremental)
        feature_result = self.compute_features(context)
        features = feature_result.features

        # Run inference with model manager
        home_win_prob, confidence, model_meta = self._model_manager.predict(
            'win_probability',
            features,
        )

        # Create result
        result = PredictionResult(
            game_pk=context.game_pk,
            prediction_type='win_probability',
            home_win_probability=home_win_prob,
            away_win_probability=1.0 - home_win_prob,
            confidence=confidence,
            features_used=[
                'inning', 'is_top', 'outs', 'base_state',
                'score_differential', 'leverage_index',
            ],
            model_version=model_meta.model_version,
            latency_ms=(time.time() - start_time) * 1000,
            metadata={
                'model_id': model_meta.model_id,
                'model_name': model_meta.model_name,
                'heuristic_used': model_meta.model_id == 'fallback_heuristic',
                'feature_compute_time_ms': feature_result.compute_time_ms,
                'feature_cache_hit': feature_result.cache_hit,
                'features_changed': list(feature_result.features_changed),
                'inning': context.inning,
                'is_top': context.is_top,
                'outs': context.outs,
            },
        )

        # Update metrics
        self._predictions_made += 1
        self._total_latency_ms += result.latency_ms

        # Cache result
        self._prediction_cache[context.game_pk] = (time.time(), result)

        # Notify callbacks
        self._notify_callbacks(result)

        return result

    def _heuristic_predict(
        self,
        context: LiveGameContext,
        features: dict[str, Any],
    ) -> float:
        """Simple heuristic for win probability when model not available.

        Uses score differential and inning to estimate probability.
        """
        score_diff = context.home_score - context.away_score
        outs_remaining = features.get('outs_remaining', 27)

        # Base probability from score
        if score_diff > 0 or score_diff < 0:
            base_prob = 0.5 + 0.1 * score_diff
        else:
            base_prob = 0.5

        # Adjust for remaining outs (later innings = more certain)
        progress_factor = 1 - (outs_remaining / 54)  # 0 to 1 as game progresses
        certainty = 0.3 + 0.4 * progress_factor

        # Blend toward extremes based on game progress
        if base_prob > 0.5:
            return min(0.95, base_prob + certainty * (base_prob - 0.5))
        return max(0.05, base_prob - certainty * (0.5 - base_prob))

    def on_prediction(self, callback: Callable[[PredictionResult], None]) -> None:
        """Register a callback for prediction updates."""
        self._prediction_callbacks.append(callback)

    def _notify_callbacks(self, result: PredictionResult) -> None:
        """Notify all registered callbacks."""
        for callback in self._prediction_callbacks:
            try:
                callback(result)
            except Exception:
                pass  # Continue even if one callback fails

    def invalidate_cache(self, game_pk: int) -> None:
        """Invalidate cache for a specific game."""
        self._prediction_cache.pop(game_pk, None)
        self._feature_store.invalidate(game_pk)

    def get_metrics(self) -> dict[str, Any]:
        """Get pipeline performance metrics."""
        total = self._cache_hits + self._cache_misses
        avg_latency = (
            self._total_latency_ms / self._predictions_made
            if self._predictions_made > 0
            else 0.0
        )

        return {
            'predictions_made': self._predictions_made,
            'cache_hits': self._cache_hits,
            'cache_misses': self._cache_misses,
            'cache_hit_rate': self._cache_hits / total if total > 0 else 0.0,
            'avg_latency_ms': avg_latency,
            'model_loaded': bool(self._model_manager.list_loaded_models()),
            'models': self._model_manager.list_loaded_models(),
            'games_in_cache': len(self._prediction_cache),
            'feature_store': self._feature_store.get_stats(),
            'model_manager': self._model_manager.get_stats(),
        }

    def reset_metrics(self) -> None:
        """Reset performance metrics."""
        self._predictions_made = 0
        self._cache_hits = 0
        self._cache_misses = 0
        self._total_latency_ms = 0.0

    def stream_predictions(
        self,
        game_pk: int,
        poll_interval: float = 10.0,
    ):
        """Stream predictions for a game (generator).

        Yields prediction results as game state changes.
        For future WebSocket integration.

        Args:
            game_pk: Game to stream
            poll_interval: Seconds between polls

        Yields:
            PredictionResult objects
        """
        from mlb_predict.sources import LiveMlbSource

        source = LiveMlbSource()
        last_state_hash = None

        while True:
            # Poll game state
            state = source.poll_game(game_pk)
            if not state:
                break

            # Check if state changed
            state_hash = f'{state.inning}_{state.is_top}_{state.outs}_{state.home_score}_{state.away_score}'
            if state_hash != last_state_hash:
                # Build context from state
                context = LiveGameContext(
                    game_pk=state.game_pk,
                    inning=state.inning,
                    is_top=state.is_top,
                    outs=state.outs,
                    balls=state.balls,
                    strikes=state.strikes,
                    home_score=state.home_score,
                    away_score=state.away_score,
                    base_state=state.base_state,
                    home_team_id=state.home_team_id,
                    away_team_id=state.away_team_id,
                    current_batter_id=state.current_batter_id,
                    current_pitcher_id=state.current_pitcher_id,
                )

                # Generate prediction
                result = self.predict(context)
                yield result

                last_state_hash = state_hash

            if state.is_complete:
                break

            time.sleep(poll_interval)
