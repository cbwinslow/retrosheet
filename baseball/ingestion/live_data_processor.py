"""Enhanced live data processor for detailed play-by-play ingestion.

Handles real-time game data processing, play-by-play extraction,
and integration with prediction systems.

Author: Agent Cascade
Date: 2026-05-04
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from baseball.core.db import get_db_connection
from baseball.features import WinExpectancyCalculator
from baseball.models.registry import ModelRegistry
from baseball.ingestion.live_service import LiveDataIngestionService


logger = logging.getLogger(__name__)


class LiveGameDataProcessor:
    """Enhanced processor for live baseball game data.
    
    Integrates with:
    - Live data ingestion service
    - Feature calculation (win expectancy, leverage index)
    - Real-time predictions
    - Database storage
    """
    
    def __init__(
        self,
        buffer_size: int = 1000,
        prediction_interval: int = 30,
        feature_calc_interval: int = 15,
    ) -> None:
        """Initialize live data processor.
        
        Args:
            buffer_size: Number of game states to buffer
            prediction_interval: Seconds between prediction updates
            feature_calc_interval: Seconds between feature calculations
        """
        self.buffer_size = buffer_size
        self.prediction_interval = prediction_interval
        self.feature_calc_interval = feature_calc_interval
        
        # Game state buffers
        self.game_states: Dict[int, List[Dict]] = {}
        
        # Feature calculators
        self.we_calculator: Optional[WinExpectancyCalculator] = None
        self.model_registry: Optional[ModelRegistry] = None
        
        # Task tracking
        self._prediction_tasks: Dict[int, asyncio.Task] = {}
        self._feature_tasks: Dict[int, asyncio.Task] = {}
        
        # Statistics
        self.stats = {
            'games_processed': 0,
            'predictions_generated': 0,
            'features_calculated': 0,
            'errors': 0,
            'started_at': datetime.now(),
        }
        
        logger.info('LiveGameDataProcessor initialized')
    
    async def start_processing(self, live_service: LiveDataIngestionService) -> None:
        """Start processing live data from the live service.
        
        Args:
            live_service: Configured live data ingestion service
        """
        logger.info('Starting live data processing')
        
        # Initialize components
        await self._initialize_components()
        
        # Register event handlers
        live_service.on_message('mlb', self._handle_live_game_data)
        live_service.on_message('mlb', self._update_predictions)
        live_service.on_message('mlb', self._calculate_features)
        
        logger.info('Live data processing started')
    
    async def _initialize_components(self) -> None:
        """Initialize feature calculators and model registry."""
        try:
            # Initialize Win Expectancy Calculator
            conn = get_db_connection()
            self.we_calculator = WinExpectancyCalculator(db_connection=conn)
            result = self.we_calculator.load_from_db()
            logger.info(f'Win Expectancy Calculator loaded: {result}')
            
            # Initialize Model Registry
            self.model_registry = ModelRegistry()
            logger.info('Model Registry initialized')
            
        except Exception as e:
            logger.error(f'Failed to initialize components: {e}')
            raise
    
    async def _handle_live_game_data(self, message: Dict, context: Dict) -> None:
        """Process incoming live game data.
        
        Args:
            message: Live game data from MLB API
            context: Message context (feed, timestamp, etc.)
        """
        try:
            # Extract game information
            game_data = self._extract_game_info(message, context)
            if not game_data:
                logger.warning('Failed to extract game info from message')
                return
            
            game_pk = game_data['game_pk']
            
            # Update game state buffer
            self._update_game_buffer(game_pk, game_data)
            
            # Store in database
            await self._store_game_state(game_data)
            
            # Update statistics
            self.stats['games_processed'] += 1
            
            logger.debug(f'Processed live data for game {game_pk}')
            
        except Exception as e:
            logger.exception(f'Error processing live game data: {e}')
            self.stats['errors'] += 1
    
    def _extract_game_info(self, message: Dict, context: Dict) -> Optional[Dict]:
        """Extract normalized game information from live data message."""
        try:
            # Handle different message formats
            if 'gameData' in message and 'liveData' in message:
                # Full live feed format
                return self._extract_from_full_feed(message, context)
            elif 'gamePk' in message:
                # Schedule or simple format
                return self._extract_from_simple_format(message, context)
            else:
                logger.warning('Unknown message format')
                return None
                
        except Exception as e:
            logger.error(f'Error extracting game info: {e}')
            return None
    
    def _extract_from_full_feed(self, message: Dict, context: Dict) -> Dict:
        """Extract game info from full live feed format."""
        game_data = message.get('gameData', {}).get('game', {})
        live_data = message.get('liveData', {})
        linescore = live_data.get('linescore', {})
        
        # Basic game info
        game_pk = game_data.get('pk')
        status = game_data.get('status', {}).get('abstractGameCode', 'U')
        
        # Score and inning info
        home_team = linescore.get('teams', {}).get('home', {})
        away_team = linescore.get('teams', {}).get('away', {})
        
        score_home = home_team.get('runs', 0)
        score_away = away_team.get('runs', 0)
        inning = linescore.get('currentInning', 1)
        is_top = linescore.get('isTopInning', True)
        outs = linescore.get('outs', 0)
        
        # Base runners
        offense = linescore.get('offense', {})
        runner_1b = 'first' in offense
        runner_2b = 'second' in offense
        runner_3b = 'third' in offense
        base_state = (
            (1 if runner_1b else 0) +
            (2 if runner_2b else 0) +
            (4 if runner_3b else 0)
        )
        
        # Play-by-play data if available
        plays = live_data.get('plays', {}).get('allPlays', [])
        current_play = None
        if plays:
            current_play = plays[-1]  # Most recent play
        
        return {
            'game_pk': game_pk,
            'status': status,
            'inning': inning,
            'is_top': is_top,
            'outs': outs,
            'score_home': score_home,
            'score_away': score_away,
            'base_state': base_state,
            'score_diff': score_home - score_away,
            'timestamp': context.get('received_at', datetime.now()),
            'current_play': current_play,
            'pitch_count': self._extract_pitch_count(current_play),
            'at_bat_number': self._extract_at_bat_number(current_play),
        }
    
    def _extract_from_simple_format(self, message: Dict, context: Dict) -> Dict:
        """Extract game info from simple schedule format."""
        game_pk = message.get('gamePk')
        status = message.get('status', {}).get('abstractGameCode', 'U')
        
        teams = message.get('teams', {})
        home_team = teams.get('home', {})
        away_team = teams.get('away', {})
        
        return {
            'game_pk': game_pk,
            'status': status,
            'score_home': home_team.get('score', 0),
            'score_away': away_team.get('score', 0),
            'timestamp': context.get('received_at', datetime.now()),
            # Limited info in simple format
            'inning': 1,
            'is_top': True,
            'outs': 0,
            'base_state': 0,
            'score_diff': home_team.get('score', 0) - away_team.get('score', 0),
            'current_play': None,
            'pitch_count': 0,
            'at_bat_number': 0,
        }
    
    def _extract_pitch_count(self, play: Optional[Dict]) -> int:
        """Extract pitch count from play data."""
        if not play:
            return 0
        
        play_events = play.get('playEvents', [])
        pitch_events = [e for e in play_events if e.get('type') == 'pitch']
        return len(pitch_events)
    
    def _extract_at_bat_number(self, play: Optional[Dict]) -> int:
        """Extract at-bat number from play data."""
        if not play:
            return 0
        
        about = play.get('about', {})
        return about.get('atBatIndex', 0)
    
    def _update_game_buffer(self, game_pk: int, game_data: Dict) -> None:
        """Update the circular buffer for a game."""
        if game_pk not in self.game_states:
            self.game_states[game_pk] = []
        
        buffer = self.game_states[game_pk]
        buffer.append(game_data)
        
        # Trim buffer to maintain size
        if len(buffer) > self.buffer_size:
            buffer.pop(0)
    
    async def _store_game_state(self, game_data: Dict) -> None:
        """Store game state in database."""
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                # Store in core.live_games table
                cur.execute("""
                    INSERT INTO core.live_games
                    (game_pk, status, inning, is_top, outs, score_home, score_away,
                     base_state, score_diff, timestamp, current_play_data)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (game_pk) DO UPDATE SET
                        status = EXCLUDED.status,
                        inning = EXCLUDED.inning,
                        is_top = EXCLUDED.is_top,
                        outs = EXCLUDED.outs,
                        score_home = EXCLUDED.score_home,
                        score_away = EXCLUDED.score_away,
                        base_state = EXCLUDED.base_state,
                        score_diff = EXCLUDED.score_diff,
                        timestamp = EXCLUDED.timestamp,
                        current_play_data = EXCLUDED.current_play_data
                """, (
                    game_data['game_pk'],
                    game_data['status'],
                    game_data['inning'],
                    game_data['is_top'],
                    game_data['outs'],
                    game_data['score_home'],
                    game_data['score_away'],
                    game_data['base_state'],
                    game_data['score_diff'],
                    game_data['timestamp'],
                    json.dumps(game_data.get('current_play', {})),
                ))
                
                # Store detailed play-by-play if available
                if game_data.get('current_play'):
                    await self._store_play_by_play(game_data)
                
                conn.commit()
                
        except Exception as e:
            logger.error(f'Error storing game state: {e}')
            raise
    
    async def _store_play_by_play(self, game_data: Dict) -> None:
        """Store detailed play-by-play data."""
        try:
            play = game_data['current_play']
            if not play:
                return
            
            conn = get_db_connection()
            with conn.cursor() as cur:
                # Store in core.live_events table
                cur.execute("""
                    INSERT INTO core.live_events
                    (game_pk, at_bat_number, pitch_count, play_data, created_at)
                    VALUES (%s, %s, %s, %s, NOW())
                """, (
                    game_data['game_pk'],
                    game_data['at_bat_number'],
                    game_data['pitch_count'],
                    json.dumps(play),
                ))
                
                conn.commit()
                
        except Exception as e:
            logger.error(f'Error storing play-by-play data: {e}')
    
    async def _update_predictions(self, message: Dict, context: Dict) -> None:
        """Update real-time predictions for live games."""
        try:
            game_data = self._extract_game_info(message, context)
            if not game_data or game_data['status'] not in ('L', 'P'):
                return  # Only update for live/preview games
            
            game_pk = game_data['game_pk']
            
            # Check if prediction task is already running
            if game_pk in self._prediction_tasks and not self._prediction_tasks[game_pk].done():
                return
            
            # Start prediction task
            task = asyncio.create_task(self._generate_predictions(game_data))
            self._prediction_tasks[game_pk] = task
            
            # Clean up completed tasks
            self._cleanup_completed_tasks(self._prediction_tasks)
            
        except Exception as e:
            logger.error(f'Error updating predictions: {e}')
    
    async def _generate_predictions(self, game_data: Dict) -> None:
        """Generate predictions for a live game."""
        try:
            game_pk = game_data['game_pk']
            
            # Calculate win expectancy using current state
            if self.we_calculator:
                we = self.we_calculator.get_win_expectancy(
                    inning=game_data['inning'],
                    is_top=game_data['is_top'],
                    outs=game_data['outs'],
                    base_state=game_data['base_state'],
                    score_diff=game_data['score_diff'],
                )
                
                # Store prediction
                await self._store_prediction(game_pk, 'win_expectancy', we, game_data)
                self.stats['predictions_generated'] += 1
                
                logger.debug(f'Generated win expectancy prediction for game {game_pk}: {we:.3f}')
            
        except Exception as e:
            logger.error(f'Error generating predictions for game {game_data["game_pk"]}: {e}')
    
    async def _store_prediction(self, game_pk: int, prediction_type: str, value: float, game_data: Dict) -> None:
        """Store prediction in database."""
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO predictions.live_predictions
                    (game_pk, prediction_type, value, game_state, created_at)
                    VALUES (%s, %s, %s, %s, NOW())
                    ON CONFLICT (game_pk, prediction_type) DO UPDATE SET
                        value = EXCLUDED.value,
                        game_state = EXCLUDED.game_state,
                        created_at = EXCLUDED.created_at
                """, (
                    game_pk,
                    prediction_type,
                    value,
                    json.dumps(game_data),
                ))
                
                conn.commit()
                
        except Exception as e:
            logger.error(f'Error storing prediction: {e}')
    
    async def _calculate_features(self, message: Dict, context: Dict) -> None:
        """Calculate real-time features for live games."""
        try:
            game_data = self._extract_game_info(message, context)
            if not game_data or game_data['status'] not in ('L', 'P'):
                return
            
            game_pk = game_data['game_pk']
            
            # Check if feature task is already running
            if game_pk in self._feature_tasks and not self._feature_tasks[game_pk].done():
                return
            
            # Start feature calculation task
            task = asyncio.create_task(self._calculate_game_features(game_data))
            self._feature_tasks[game_pk] = task
            
            # Clean up completed tasks
            self._cleanup_completed_tasks(self._feature_tasks)
            
        except Exception as e:
            logger.error(f'Error calculating features: {e}')
    
    async def _calculate_game_features(self, game_data: Dict) -> None:
        """Calculate features for a live game."""
        try:
            game_pk = game_data['game_pk']
            
            # Calculate leverage index
            if self.we_calculator and hasattr(self.we_calculator, 'get_leverage_index'):
                leverage = self.we_calculator.get_leverage_index(
                    inning=game_data['inning'],
                    is_top=game_data['is_top'],
                    outs=game_data['outs'],
                    base_state=game_data['base_state'],
                    score_diff=game_data['score_diff'],
                )
                
                # Store feature
                await self._store_feature(game_pk, 'leverage_index', leverage, game_data)
                self.stats['features_calculated'] += 1
                
                logger.debug(f'Calculated leverage index for game {game_pk}: {leverage:.2f}')
            
        except Exception as e:
            logger.error(f'Error calculating features for game {game_data["game_pk"]}: {e}')
    
    async def _store_feature(self, game_pk: int, feature_name: str, value: float, game_data: Dict) -> None:
        """Store feature in database."""
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO features.live_features
                    (game_pk, feature_name, value, game_state, created_at)
                    VALUES (%s, %s, %s, %s, NOW())
                    ON CONFLICT (game_pk, feature_name) DO UPDATE SET
                        value = EXCLUDED.value,
                        game_state = EXCLUDED.game_state,
                        created_at = EXCLUDED.created_at
                """, (
                    game_pk,
                    feature_name,
                    value,
                    json.dumps(game_data),
                ))
                
                conn.commit()
                
        except Exception as e:
            logger.error(f'Error storing feature: {e}')
    
    def _cleanup_completed_tasks(self, task_dict: Dict[int, asyncio.Task]) -> None:
        """Clean up completed tasks from the dictionary."""
        completed = [pk for pk, task in task_dict.items() if task.done()]
        for pk in completed:
            del task_dict[pk]
    
    def get_statistics(self) -> Dict:
        """Get processing statistics."""
        stats = self.stats.copy()
        stats['uptime'] = datetime.now() - stats['started_at']
        stats['active_games'] = len(self.game_states)
        stats['active_prediction_tasks'] = len(self._prediction_tasks)
        stats['active_feature_tasks'] = len(self._feature_tasks)
        return stats
    
    async def shutdown(self) -> None:
        """Shutdown the processor and clean up resources."""
        logger.info('Shutting down live data processor')
        
        # Cancel all tasks
        for task in self._prediction_tasks.values():
            task.cancel()
        for task in self._feature_tasks.values():
            task.cancel()
        
        # Wait for tasks to complete
        await asyncio.gather(
            *self._prediction_tasks.values(),
            *self._feature_tasks.values(),
            return_exceptions=True
        )
        
        logger.info('Live data processor shutdown complete')
