"""Simulation service for querying Monte Carlo results.

Provides probability extraction from simulation runs for betting analysis.
Queries simulation.results and simulation.runs tables.

Author: Agent Cascade
Date: 2026-04-30
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, List, Tuple
import logging

from baseball.database import get_db_pool

logger = logging.getLogger(__name__)


class SimulationService:
    """Service for querying simulation results from database.
    
    Extracts win probabilities, score distributions, and other
    aggregated metrics from completed Monte Carlo simulations.
    
    Example:
        >>> service = SimulationService()
        >>> probs = await service.get_game_probabilities("716190")
        >>> print(f"Home win: {probs['home_win']:.1%}")
    """
    
    def __init__(self, db_pool=None):
        """Initialize with optional db pool.
        
        Args:
            db_pool: AsyncPG pool (uses default if None)
        """
        self.db_pool = db_pool
    
    async def _get_pool(self):
        """Get database pool."""
        if self.db_pool is None:
            self.db_pool = await get_db_pool()
        return self.db_pool
    
    async def get_game_probabilities(
        self,
        game_id: str,
        model_id: Optional[str] = None
    ) -> Dict[str, Decimal]:
        """Get win probabilities for a game from latest simulation.
        
        Args:
            game_id: Game identifier (e.g., "716190")
            model_id: Optional model filter (uses latest if None)
            
        Returns:
            Dict with keys: home_win, away_win, push (if applicable)
            
        Example:
            >>> probs = await service.get_game_probabilities("716190")
            >>> # Returns: {'home_win': Decimal('0.582'), 'away_win': Decimal('0.418')}
        """
        pool = await self._get_pool()
        
        # Build query
        model_filter = "AND r.model_id = $2" if model_id else ""
        params = [game_id, model_id] if model_id else [game_id]
        
        query = f"""
        SELECT 
            r.run_id,
            r.model_id,
            r.num_iterations,
            AVG(res.home_score) as avg_home_score,
            AVG(res.away_score) as avg_away_score,
            SUM(CASE WHEN res.home_score > res.away_score THEN 1 ELSE 0 END)::DECIMAL / NULLIF(r.num_iterations, 0) as home_win_prob,
            SUM(CASE WHEN res.away_score > res.home_score THEN 1 ELSE 0 END)::DECIMAL / NULLIF(r.num_iterations, 0) as away_win_prob,
            SUM(CASE WHEN res.home_score = res.away_score THEN 1 ELSE 0 END)::DECIMAL / NULLIF(r.num_iterations, 0) as push_prob
        FROM simulation.runs r
        JOIN simulation.results res ON r.run_id = res.run_id
        WHERE r.game_id = $1
          AND r.status = 'completed'
          {model_filter}
        GROUP BY r.run_id, r.model_id, r.num_iterations
        ORDER BY r.created_at DESC
        LIMIT 1
        """
        
        async with pool.acquire() as conn:
            row = await conn.fetchrow(query, *params)
            
            if row is None:
                logger.warning(f"No simulation found for game {game_id}")
                return {}
            
            result = {
                'home_win': Decimal(str(row['home_win_prob'] or 0)),
                'away_win': Decimal(str(row['away_win_prob'] or 0)),
            }
            
            if row['push_prob']:
                result['push'] = Decimal(str(row['push_prob']))
            
            logger.info(
                f"Simulation {row['run_id'][:8]}: "
                f"Home {result['home_win']:.1%}, "
                f"Away {result['away_win']:.1%}"
            )
            
            return result
    
    async def get_score_distribution(
        self,
        game_id: str,
        model_id: Optional[str] = None
    ) -> Dict[str, List[Tuple[int, Decimal]]]:
        """Get score probability distributions.
        
        Args:
            game_id: Game identifier
            model_id: Optional model filter
            
        Returns:
            Dict with home_runs and away_runs distributions.
            Each is a list of (score, probability) tuples.
        """
        pool = await self._get_pool()
        
        model_filter = "AND r.model_id = $2" if model_id else ""
        params = [game_id, model_id] if model_id else [game_id]
        
        query = f"""
        WITH latest_run AS (
            SELECT r.run_id, r.num_iterations
            FROM simulation.runs r
            WHERE r.game_id = $1
              AND r.status = 'completed'
              {model_filter}
            ORDER BY r.created_at DESC
            LIMIT 1
        )
        SELECT 
            res.home_score,
            res.away_score,
            COUNT(*) as frequency,
            COUNT(*)::DECIMAL / lr.num_iterations as probability
        FROM simulation.results res
        JOIN latest_run lr ON res.run_id = lr.run_id
        GROUP BY res.home_score, res.away_score, lr.num_iterations
        ORDER BY probability DESC
        LIMIT 20
        """
        
        async with pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            
            home_dist: Dict[int, Decimal] = {}
            away_dist: Dict[int, Decimal] = {}
            
            for row in rows:
                home_score = row['home_score']
                away_score = row['away_score']
                prob = Decimal(str(row['probability']))
                
                home_dist[home_score] = home_dist.get(home_score, Decimal('0')) + prob
                away_dist[away_score] = away_dist.get(away_score, Decimal('0')) + prob
            
            return {
                'home_runs': sorted(home_dist.items(), key=lambda x: x[1], reverse=True),
                'away_runs': sorted(away_dist.items(), key=lambda x: x[1], reverse=True)
            }
    
    async def get_total_probabilities(
        self,
        game_id: str,
        total_line: Decimal,
        model_id: Optional[str] = None
    ) -> Dict[str, Decimal]:
        """Get over/under probabilities for a total line.
        
        Args:
            game_id: Game identifier
            total_line: The total runs line (e.g., 8.5)
            model_id: Optional model filter
            
        Returns:
            Dict with 'over' and 'under' probabilities
        """
        pool = await self._get_pool()
        
        model_filter = "AND r.model_id = $3" if model_id else ""
        params = [game_id, float(total_line)]
        if model_id:
            params.append(model_id)
        
        query = f"""
        WITH latest_run AS (
            SELECT r.run_id, r.num_iterations
            FROM simulation.runs r
            WHERE r.game_id = $1
              AND r.status = 'completed'
              {model_filter}
            ORDER BY r.created_at DESC
            LIMIT 1
        )
        SELECT 
            SUM(CASE WHEN (res.home_score + res.away_score) > $2 THEN 1 ELSE 0 END)::DECIMAL / lr.num_iterations as over_prob,
            SUM(CASE WHEN (res.home_score + res.away_score) < $2 THEN 1 ELSE 0 END)::DECIMAL / lr.num_iterations as under_prob,
            SUM(CASE WHEN (res.home_score + res.away_score) = $2 THEN 1 ELSE 0 END)::DECIMAL / lr.num_iterations as push_prob
        FROM simulation.results res
        JOIN latest_run lr ON res.run_id = lr.run_id
        """
        
        async with pool.acquire() as conn:
            row = await conn.fetchrow(query, *params)
            
            if row is None:
                return {'over': Decimal('0'), 'under': Decimal('0'), 'push': Decimal('0')}
            
            return {
                'over': Decimal(str(row['over_prob'] or 0)),
                'under': Decimal(str(row['under_prob'] or 0)),
                'push': Decimal(str(row['push_prob'] or 0))
            }
    
    async def get_spread_probabilities(
        self,
        game_id: str,
        spread_line: Decimal,
        model_id: Optional[str] = None
    ) -> Dict[str, Decimal]:
        """Get spread cover probabilities.
        
        Args:
            game_id: Game identifier
            spread_line: The spread line (e.g., -1.5 for home favorite)
            model_id: Optional model filter
            
        Returns:
            Dict with 'home_cover' and 'away_cover' probabilities
        """
        pool = await self._get_pool()
        
        model_filter = "AND r.model_id = $3" if model_id else ""
        params = [game_id, float(spread_line)]
        if model_id:
            params.append(model_id)
        
        query = f"""
        WITH latest_run AS (
            SELECT r.run_id, r.num_iterations
            FROM simulation.runs r
            WHERE r.game_id = $1
              AND r.status = 'completed'
              {model_filter}
            ORDER BY r.created_at DESC
            LIMIT 1
        )
        SELECT 
            -- Home covers if (home_score + spread) > away_score
            -- For spread -1.5, home must win by 2+
            SUM(CASE WHEN (res.home_score + $2) > res.away_score THEN 1 ELSE 0 END)::DECIMAL / lr.num_iterations as home_cover_prob,
            SUM(CASE WHEN (res.away_score - $2) > res.home_score THEN 1 ELSE 0 END)::DECIMAL / lr.num_iterations as away_cover_prob
        FROM simulation.results res
        JOIN latest_run lr ON res.run_id = lr.run_id
        """
        
        async with pool.acquire() as conn:
            row = await conn.fetchrow(query, *params)
            
            if row is None:
                return {'home_cover': Decimal('0'), 'away_cover': Decimal('0')}
            
            return {
                'home_cover': Decimal(str(row['home_cover_prob'] or 0)),
                'away_cover': Decimal(str(row['away_cover_prob'] or 0))
            }
    
    async def list_available_simulations(
        self,
        game_id: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict]:
        """List available completed simulations.
        
        Args:
            game_id: Optional game filter
            limit: Max results to return
            
        Returns:
            List of simulation metadata dicts
        """
        pool = await self._get_pool()
        
        game_filter = "AND game_id = $1" if game_id else ""
        params = [game_id] if game_id else []
        
        query = f"""
        SELECT 
            run_id,
            game_id,
            model_id,
            simulation_type,
            num_iterations,
            status,
            created_at,
            completed_at,
            duration_seconds
        FROM simulation.runs
        WHERE status = 'completed'
          {game_filter}
        ORDER BY created_at DESC
        LIMIT ${len(params) + 1}
        """
        
        async with pool.acquire() as conn:
            rows = await conn.fetch(query, *params, limit)
            
            return [{
                'run_id': str(r['run_id']),
                'game_id': r['game_id'],
                'model_id': r['model_id'],
                'simulation_type': r['simulation_type'],
                'num_iterations': r['num_iterations'],
                'created_at': r['created_at'],
                'completed_at': r['completed_at'],
                'duration_seconds': r['duration_seconds']
            } for r in rows]
