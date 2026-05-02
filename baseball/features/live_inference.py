"""
Live Inference Feature Mapper

Maps live pitch data from core.live_pitch_events to model input format.
Ensures feature parity between historical training data and live inference data.

Usage:
    from baseball.features.live_inference import LiveFeatureMapper
    
    mapper = LiveFeatureMapper()
    features = mapper.get_features_for_prediction(game_pk=12345)
    predictions = model.predict(features)
"""

from typing import Optional
import numpy as np

from baseball.core.db import get_db_connection


# Feature columns expected by the XGBoost model
MODEL_FEATURE_COLUMNS = [
    'release_speed', 'release_pos_x', 'release_pos_y', 'release_pos_z',
    'pfx_x', 'pfx_z', 'plate_x', 'plate_z',
    'effective_speed', 'release_spin_rate', 'spin_axis',
    'balls', 'strikes',
    'break_magnitude', 'approach_angle',
    'leverage_index', 'score_diff',
    'plate_distance_from_center',
    'inning', 'outs_when_up'
]


class LiveFeatureMapper:
    """
    Maps live pitch events to model input format.
    
    Ensures feature parity between:
    - Historical: features_pitch.base_features
    - Live: core.live_pitch_events → features.live_pitch_inference
    
    Key mappings:
    - pitch_speed → release_speed
    - pitch_spin_rate → release_spin_rate
    - pitch_spin_axis → spin_axis
    """
    
    def __init__(self):
        self._feature_cache = {}
    
    def get_latest_pitch_context(
        self, 
        game_pk: int,
        pitcher_id: Optional[str] = None
    ) -> Optional[dict]:
        """
        Get the latest pitch context for a game.
        
        Returns the most recent pitch data to use as context for
        predicting the NEXT pitch.
        
        Args:
            game_pk: MLB game ID
            pitcher_id: Optional filter for specific pitcher
            
        Returns:
            Dict with feature values or None if no live data
        """
        conn = get_db_connection()
        cur = conn.cursor()
        
        query = """
            SELECT 
                game_year,
                game_date,
                pitcher_id,
                batter_id,
                pitch_type,
                release_speed,
                release_spin_rate,
                spin_axis,
                count_label,
                balls_pre as balls,
                strikes_pre as strikes,
                inning,
                outs_when_up,
                score_diff,
                leverage_index
            FROM features.live_pitch_inference_mv
            WHERE game_pk = %s
            ORDER BY live_timestamp DESC
            LIMIT 1
        """
        
        cur.execute(query, (game_pk,))
        row = cur.fetchone()
        
        cur.close()
        conn.close()
        
        if not row:
            return None
        
        columns = [
            'game_year', 'game_date', 'pitcher_id', 'batter_id',
            'pitch_type', 'release_speed', 'release_spin_rate', 'spin_axis',
            'count_label', 'balls', 'strikes', 'inning', 'outs_when_up',
            'score_diff', 'leverage_index'
        ]
        
        return dict(zip(columns, row))
    
    def build_prediction_features(
        self,
        game_pk: int,
        current_count: str = "0-0",
        last_pitch_type: Optional[str] = None
    ) -> np.ndarray:
        """
        Build feature vector for predicting next pitch.
        
        Args:
            game_pk: MLB game ID
            current_count: Current count (e.g., "1-2", "2-0")
            last_pitch_type: Previous pitch type (e.g., "FF", "SL")
            
        Returns:
            numpy array of features for model.predict()
        """
        # Get context from live data
        context = self.get_latest_pitch_context(game_pk)
        
        if not context:
            # No live data available - return zeros or defaults
            return np.zeros(len(MODEL_FEATURE_COLUMNS))
        
        # Parse current count
        balls, strikes = map(int, current_count.split('-'))
        
        # Build feature dict with defaults for unavailable physics data
        features = {
            'release_speed': context.get('release_speed', 90.0) or 90.0,
            'release_pos_x': 0.0,  # Not available in live
            'release_pos_y': 0.0,
            'release_pos_z': context.get('release_speed', 90.0) or 90.0,  # Approximate
            'pfx_x': 0.0,  # Not available in live
            'pfx_z': 0.0,
            'plate_x': 0.0,
            'plate_z': 0.0,
            'effective_speed': context.get('release_speed', 90.0) or 90.0,
            'release_spin_rate': context.get('release_spin_rate', 2000.0) or 2000.0,
            'spin_axis': context.get('spin_axis', 150.0) or 150.0,
            'balls': balls,
            'strikes': strikes,
            'break_magnitude': 0.0,  # Not available in live
            'approach_angle': 0.0,
            'leverage_index': context.get('leverage_index', 1.0) or 1.0,
            'score_diff': context.get('score_diff', 0) or 0,
            'plate_distance_from_center': 0.0,
            'inning': context.get('inning', 1) or 1,
            'outs_when_up': context.get('outs_when_up', 0) or 0,
        }
        
        # Convert to ordered array
        return np.array([features.get(col, 0.0) for col in MODEL_FEATURE_COLUMNS])
    
    def refresh_live_cache(self) -> dict:
        """
        Refresh the materialized view of live pitch features.
        
        Should be called every 30-60 seconds during active games.
        
        Returns:
            Dict with refresh stats
        """
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Get count before refresh
        cur.execute("SELECT COUNT(*) FROM features.live_pitch_inference_mv")
        count_before = cur.fetchone()[0]
        
        # Refresh materialized view
        cur.execute("REFRESH MATERIALIZED VIEW features.live_pitch_inference_mv")
        conn.commit()
        
        # Get count after refresh
        cur.execute("SELECT COUNT(*) FROM features.live_pitch_inference_mv")
        count_after = cur.fetchone()[0]
        
        # Get latest timestamp
        cur.execute("""
            SELECT MAX(live_timestamp) 
            FROM features.live_pitch_inference_mv
        """)
        latest = cur.fetchone()[0]
        
        cur.close()
        conn.close()
        
        return {
            'rows_before': count_before,
            'rows_after': count_after,
            'new_rows': count_after - count_before,
            'latest_timestamp': latest
        }
    
    def get_active_games(self) -> list:
        """Get list of currently active games with live pitch data."""
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT DISTINCT 
                game_pk,
                COUNT(*) as pitch_count,
                MAX(live_timestamp) as last_update
            FROM features.live_pitch_inference_mv
            WHERE live_timestamp >= NOW() - INTERVAL '4 hours'
            GROUP BY game_pk
            ORDER BY last_update DESC
        """)
        
        games = [
            {
                'game_pk': row[0],
                'pitch_count': row[1],
                'last_update': row[2]
            }
            for row in cur.fetchall()
        ]
        
        cur.close()
        conn.close()
        
        return games


# Convenience function for quick access
def get_live_features(game_pk: int, count: str = "0-0") -> np.ndarray:
    """Quick function to get live features for prediction."""
    mapper = LiveFeatureMapper()
    return mapper.build_prediction_features(game_pk, count)
