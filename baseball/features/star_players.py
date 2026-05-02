"""
Star Players Fast Lookup

Provides pre-computed star player profiles for fast prediction lookups.
Uses materialized views for sub-millisecond queries during live games.

Usage:
    from baseball.features.star_players import StarPlayerStore
    
    store = StarPlayerStore()
    
    # Get star batter profile
    batter = store.get_star_batter('123456')
    
    # Get star pitcher profile
    pitcher = store.get_star_pitcher('654321')
    
    # Get matchup history between stars
    matchup = store.get_star_matchup('654321', '123456')
    
    # List today's active star players
    active = store.get_active_stars(team_id='108')
"""

from typing import Optional, List
from dataclasses import dataclass
from datetime import datetime

from baseball.core.db import get_db_connection


@dataclass
class StarBatter:
    """Star batter profile from materialized view."""
    player_id: str
    star_rank: int
    war_estimate: float
    avg_30d: float
    k_rate_30d: float
    bb_rate_30d: float
    hr_rate_30d: float
    pa_30d: float


@dataclass
class StarPitcher:
    """Star pitcher profile from materialized view."""
    player_id: str
    star_rank: int
    war_estimate: float
    k_rate_30d: float
    bb_rate_30d: float
    hr_rate_30d: float
    avg_velo_30d: float
    arsenal_depth: float
    total_bf_30d: float


@dataclass
class StarMatchup:
    """Pre-computed matchup between star players."""
    pitcher_id: str
    batter_id: str
    pitcher_rank: int
    batter_rank: int
    total_pas: int
    matchup_avg: float
    matchup_k_rate: float
    last_matchup_date: Optional[datetime]
    matchup_advantage: Optional[float]  # -1 to +1, positive favors pitcher


@dataclass
class ActiveStarPlayer:
    """Active star player in today's games."""
    player_id: str
    player_name: str
    position: str
    team_id: str
    team_name: str
    team_abbreviation: str
    player_type: str  # 'batter' or 'pitcher'
    star_rank: Optional[int]


class StarPlayerStore:
    """
    Fast lookup store for star player data.
    
    Uses pre-computed materialized views for sub-millisecond queries.
    Optimized for live prediction scenarios.
    """
    
    def get_star_batter(self, player_id: str) -> Optional[StarBatter]:
        """Get star batter profile (fast MV lookup)."""
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT player_id, star_rank, war_estimate, avg_30d,
                   k_rate_30d, bb_rate_30d, hr_rate_30d, pa_30d
            FROM features.star_batters
            WHERE player_id = %s
        """, (player_id,))
        
        row = cur.fetchone()
        cur.close()
        conn.close()
        
        if not row:
            return None
        
        return StarBatter(
            player_id=row[0],
            star_rank=row[1],
            war_estimate=row[2] or 0.0,
            avg_30d=row[3] or 0.0,
            k_rate_30d=row[4] or 0.0,
            bb_rate_30d=row[5] or 0.0,
            hr_rate_30d=row[6] or 0.0,
            pa_30d=row[7] or 0.0
        )
    
    def get_star_pitcher(self, player_id: str) -> Optional[StarPitcher]:
        """Get star pitcher profile (fast MV lookup)."""
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT player_id, star_rank, war_estimate, k_rate_30d,
                   bb_rate_30d, hr_rate_30d, avg_velo_30d, arsenal_depth, total_bf_30d
            FROM features.star_pitchers
            WHERE player_id = %s
        """, (player_id,))
        
        row = cur.fetchone()
        cur.close()
        conn.close()
        
        if not row:
            return None
        
        return StarPitcher(
            player_id=row[0],
            star_rank=row[1],
            war_estimate=row[2] or 0.0,
            k_rate_30d=row[3] or 0.0,
            bb_rate_30d=row[4] or 0.0,
            hr_rate_30d=row[5] or 0.0,
            avg_velo_30d=row[6] or 90.0,
            arsenal_depth=row[7] or 3.0,
            total_bf_30d=row[8] or 0.0
        )
    
    def get_star_matchup(
        self,
        pitcher_id: str,
        batter_id: str
    ) -> Optional[StarMatchup]:
        """Get pre-computed matchup between star players."""
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT pitcher_id, batter_id, pitcher_rank, batter_rank,
                   total_pas, matchup_avg, matchup_k_rate, last_matchup_date,
                   matchup_advantage
            FROM features.star_matchups
            WHERE pitcher_id = %s AND batter_id = %s
        """, (pitcher_id, batter_id))
        
        row = cur.fetchone()
        cur.close()
        conn.close()
        
        if not row:
            return None
        
        return StarMatchup(
            pitcher_id=row[0],
            batter_id=row[1],
            pitcher_rank=row[2],
            batter_rank=row[3],
            total_pas=row[4],
            matchup_avg=row[5] or 0.0,
            matchup_k_rate=row[6] or 0.0,
            last_matchup_date=row[7],
            matchup_advantage=row[8]
        )
    
    def get_active_stars(
        self,
        team_id: Optional[str] = None,
        player_type: Optional[str] = None
    ) -> List[ActiveStarPlayer]:
        """Get today's active star players."""
        conn = get_db_connection()
        cur = conn.cursor()
        
        query = """
            SELECT player_id, player_name, position, team_id,
                   team_name, team_abbreviation, player_type, COALESCE(batter_rank, pitcher_rank)
            FROM features.active_roster
            WHERE 1=1
        """
        params = []
        
        if team_id:
            query += " AND team_id = %s"
            params.append(team_id)
        
        if player_type:
            query += " AND player_type = %s"
            params.append(player_type)
        
        query += " ORDER BY COALESCE(batter_rank, pitcher_rank)"
        
        cur.execute(query, params)
        
        players = [
            ActiveStarPlayer(
                player_id=row[0],
                player_name=row[1],
                position=row[2],
                team_id=row[3],
                team_name=row[4],
                team_abbreviation=row[5],
                player_type=row[6],
                star_rank=row[7]
            )
            for row in cur.fetchall()
        ]
        
        cur.close()
        conn.close()
        
        return players
    
    def list_top_batters(self, limit: int = 25) -> List[StarBatter]:
        """List top N star batters."""
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT player_id, star_rank, war_estimate, avg_30d,
                   k_rate_30d, bb_rate_30d, hr_rate_30d, pa_30d
            FROM features.star_batters
            ORDER BY star_rank
            LIMIT %s
        """, (limit,))
        
        batters = [
            StarBatter(
                player_id=row[0],
                star_rank=row[1],
                war_estimate=row[2] or 0.0,
                avg_30d=row[3] or 0.0,
                k_rate_30d=row[4] or 0.0,
                bb_rate_30d=row[5] or 0.0,
                hr_rate_30d=row[6] or 0.0,
                pa_30d=row[7] or 0.0
            )
            for row in cur.fetchall()
        ]
        
        cur.close()
        conn.close()
        
        return batters
    
    def list_top_pitchers(self, limit: int = 25) -> List[StarPitcher]:
        """List top N star pitchers."""
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT player_id, star_rank, war_estimate, k_rate_30d,
                   bb_rate_30d, hr_rate_30d, avg_velo_30d, arsenal_depth, total_bf_30d
            FROM features.star_pitchers
            ORDER BY star_rank
            LIMIT %s
        """, (limit,))
        
        pitchers = [
            StarPitcher(
                player_id=row[0],
                star_rank=row[1],
                war_estimate=row[2] or 0.0,
                k_rate_30d=row[3] or 0.0,
                bb_rate_30d=row[4] or 0.0,
                hr_rate_30d=row[5] or 0.0,
                avg_velo_30d=row[6] or 90.0,
                arsenal_depth=row[7] or 3.0,
                total_bf_30d=row[8] or 0.0
            )
            for row in cur.fetchall()
        ]
        
        cur.close()
        conn.close()
        
        return pitchers
    
    def refresh_star_views(self) -> dict:
        """Refresh all star player materialized views."""
        conn = get_db_connection()
        cur = conn.cursor()
        
        results = {}
        
        views = [
            'features.star_batters',
            'features.star_pitchers',
            'features.active_roster',
            'features.star_matchups'
        ]
        
        for view in views:
            cur.execute(f"REFRESH MATERIALIZED VIEW {view}")
            conn.commit()
            results[view.split('.')[1]] = 'refreshed'
        
        cur.close()
        conn.close()
        
        return results


# Convenience functions
def get_star_batter(player_id: str) -> Optional[StarBatter]:
    """Quick function to get star batter profile."""
    store = StarPlayerStore()
    return store.get_star_batter(player_id)


def get_star_pitcher(player_id: str) -> Optional[StarPitcher]:
    """Quick function to get star pitcher profile."""
    store = StarPlayerStore()
    return store.get_star_pitcher(player_id)


def get_active_stars(team_id: Optional[str] = None) -> List[ActiveStarPlayer]:
    """Quick function to get active star players."""
    store = StarPlayerStore()
    return store.get_active_stars(team_id)
