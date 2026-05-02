"""
Player Context Features

Provides 30-day rolling player statistics for model features.
Used for live prediction context to enrich pitch-level predictions.

Usage:
    from baseball.features.player_context import PlayerContextStore
    
    store = PlayerContextStore()
    
    # Get batter context
    batter_stats = store.get_batter_context(batter_id='123456')
    
    # Get pitcher context
    pitcher_stats = store.get_pitcher_context(pitcher_id='654321')
    
    # Get matchup history
    matchup = store.get_matchup_history(
        pitcher_id='654321',
        batter_id='123456'
    )
"""

from typing import Optional
from dataclasses import dataclass
from datetime import datetime

from baseball.core.db import get_db_connection


@dataclass
class BatterContext:
    """30-day batter performance context."""
    batter_id: str
    context_date: datetime
    pa_30d: int
    avg_30d: float
    k_rate_30d: float
    bb_rate_30d: float
    hr_rate_30d: float
    avg_ev_30d: Optional[float]
    pa_7d: int
    k_rate_7d: float
    bb_rate_7d: float


@dataclass
class PitcherContext:
    """30-day pitcher performance context."""
    pitcher_id: str
    context_date: datetime
    bf_30d: int
    k_rate_30d: float
    bb_rate_30d: float
    hr_rate_30d: float
    avg_velo_30d: float
    arsenal_depth: float


@dataclass
class MatchupHistory:
    """Head-to-head matchup history."""
    pitcher_id: str
    batter_id: str
    total_pas: int
    hits: int
    strikeouts: int
    walks: int
    matchup_avg: float
    matchup_k_rate: float
    last_matchup_date: Optional[datetime]


class PlayerContextStore:
    """
    Store for player context features.
    
    Provides 30-day rolling averages and matchup history
    for enriching pitch-level predictions.
    """
    
    def get_batter_context(
        self, 
        batter_id: str,
        context_date: Optional[str] = None
    ) -> Optional[BatterContext]:
        """
        Get 30-day batter context.
        
        Args:
            batter_id: Player ID
            context_date: Date for context (default: latest available)
            
        Returns:
            BatterContext or None if no data
        """
        conn = get_db_connection()
        cur = conn.cursor()
        
        if context_date:
            query = """
                SELECT batter_id, context_date, pa_30d, avg_30d, 
                       k_rate_30d, bb_rate_30d, hr_rate_30d, avg_ev_30d,
                       pa_7d, k_rate_7d, bb_rate_7d
                FROM features.player_batter_30day
                WHERE batter_id = %s AND context_date = %s
            """
            cur.execute(query, (batter_id, context_date))
        else:
            query = """
                SELECT batter_id, context_date, pa_30d, avg_30d, 
                       k_rate_30d, bb_rate_30d, hr_rate_30d, avg_ev_30d,
                       pa_7d, k_rate_7d, bb_rate_7d
                FROM features.player_batter_30day
                WHERE batter_id = %s
                ORDER BY context_date DESC
                LIMIT 1
            """
            cur.execute(query, (batter_id,))
        
        row = cur.fetchone()
        cur.close()
        conn.close()
        
        if not row:
            return None
        
        return BatterContext(
            batter_id=row[0],
            context_date=row[1],
            pa_30d=row[2],
            avg_30d=row[3] or 0.0,
            k_rate_30d=row[4] or 0.0,
            bb_rate_30d=row[5] or 0.0,
            hr_rate_30d=row[6] or 0.0,
            avg_ev_30d=row[7],
            pa_7d=row[8] or 0,
            k_rate_7d=row[9] or 0.0,
            bb_rate_7d=row[10] or 0.0
        )
    
    def get_pitcher_context(
        self,
        pitcher_id: str,
        context_date: Optional[str] = None
    ) -> Optional[PitcherContext]:
        """
        Get 30-day pitcher context.
        
        Args:
            pitcher_id: Player ID
            context_date: Date for context (default: latest available)
            
        Returns:
            PitcherContext or None if no data
        """
        conn = get_db_connection()
        cur = conn.cursor()
        
        if context_date:
            query = """
                SELECT pitcher_id, context_date, bf_30d, k_rate_30d,
                       bb_rate_30d, hr_rate_30d, avg_velo_30d, arsenal_depth
                FROM features.player_pitcher_30day
                WHERE pitcher_id = %s AND context_date = %s
            """
            cur.execute(query, (pitcher_id, context_date))
        else:
            query = """
                SELECT pitcher_id, context_date, bf_30d, k_rate_30d,
                       bb_rate_30d, hr_rate_30d, avg_velo_30d, arsenal_depth
                FROM features.player_pitcher_30day
                WHERE pitcher_id = %s
                ORDER BY context_date DESC
                LIMIT 1
            """
            cur.execute(query, (pitcher_id,))
        
        row = cur.fetchone()
        cur.close()
        conn.close()
        
        if not row:
            return None
        
        return PitcherContext(
            pitcher_id=row[0],
            context_date=row[1],
            bf_30d=row[2],
            k_rate_30d=row[3] or 0.0,
            bb_rate_30d=row[4] or 0.0,
            hr_rate_30d=row[5] or 0.0,
            avg_velo_30d=row[6] or 90.0,
            arsenal_depth=row[7] or 3.0
        )
    
    def get_matchup_history(
        self,
        pitcher_id: str,
        batter_id: str
    ) -> Optional[MatchupHistory]:
        """
        Get head-to-head matchup history.
        
        Args:
            pitcher_id: Pitcher player ID
            batter_id: Batter player ID
            
        Returns:
            MatchupHistory or None if no history
        """
        conn = get_db_connection()
        cur = conn.cursor()
        
        query = """
            SELECT pitcher_id, batter_id, total_pas, hits, strikeouts, walks,
                   matchup_avg, matchup_k_rate, last_matchup_date
            FROM features.player_matchup_history
            WHERE pitcher_id = %s AND batter_id = %s
        """
        
        cur.execute(query, (pitcher_id, batter_id))
        row = cur.fetchone()
        cur.close()
        conn.close()
        
        if not row:
            return None
        
        return MatchupHistory(
            pitcher_id=row[0],
            batter_id=row[1],
            total_pas=row[2],
            hits=row[3],
            strikeouts=row[4],
            walks=row[5],
            matchup_avg=row[6] or 0.0,
            matchup_k_rate=row[7] or 0.0,
            last_matchup_date=row[8]
        )
    
    def refresh_context_tables(self) -> dict:
        """
        Refresh all player context materialized views.
        
        Should be run daily (or after each data load).
        
        Returns:
            Dict with refresh stats for each table
        """
        conn = get_db_connection()
        cur = conn.cursor()
        
        results = {}
        
        # Refresh batter context
        cur.execute("""
            SELECT COUNT(*) FROM features.player_batter_30day
        """)
        before_batter = cur.fetchone()[0]
        
        cur.execute("REFRESH MATERIALIZED VIEW features.player_batter_30day")
        conn.commit()
        
        cur.execute("SELECT COUNT(*) FROM features.player_batter_30day")
        after_batter = cur.fetchone()[0]
        
        results['batter_30day'] = {
            'rows_before': before_batter,
            'rows_after': after_batter,
            'new_rows': after_batter - before_batter
        }
        
        # Refresh pitcher context
        cur.execute("SELECT COUNT(*) FROM features.player_pitcher_30day")
        before_pitcher = cur.fetchone()[0]
        
        cur.execute("REFRESH MATERIALIZED VIEW features.player_pitcher_30day")
        conn.commit()
        
        cur.execute("SELECT COUNT(*) FROM features.player_pitcher_30day")
        after_pitcher = cur.fetchone()[0]
        
        results['pitcher_30day'] = {
            'rows_before': before_pitcher,
            'rows_after': after_pitcher,
            'new_rows': after_pitcher - before_pitcher
        }
        
        # Refresh matchup history
        cur.execute("SELECT COUNT(*) FROM features.player_matchup_history")
        before_matchup = cur.fetchone()[0]
        
        cur.execute("REFRESH MATERIALIZED VIEW features.player_matchup_history")
        conn.commit()
        
        cur.execute("SELECT COUNT(*) FROM features.player_matchup_history")
        after_matchup = cur.fetchone()[0]
        
        results['matchup_history'] = {
            'rows_before': before_matchup,
            'rows_after': after_matchup,
            'new_rows': after_matchup - before_matchup
        }
        
        cur.close()
        conn.close()
        
        return results


# Convenience functions
def get_batter_context(batter_id: str) -> Optional[BatterContext]:
    """Quick function to get batter context."""
    store = PlayerContextStore()
    return store.get_batter_context(batter_id)


def get_pitcher_context(pitcher_id: str) -> Optional[PitcherContext]:
    """Quick function to get pitcher context."""
    store = PlayerContextStore()
    return store.get_pitcher_context(pitcher_id)


def get_matchup_history(pitcher_id: str, batter_id: str) -> Optional[MatchupHistory]:
    """Quick function to get matchup history."""
    store = PlayerContextStore()
    return store.get_matchup_history(pitcher_id, batter_id)
