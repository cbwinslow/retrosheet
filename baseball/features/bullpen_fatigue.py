"""Bullpen fatigue feature calculator.

Tracks reliever workload and fatigue to predict performance degradation.
Uses sabermetric research on pitch count effects and rest day recovery.

Author: Agent Cascade
Date: 2026-04-30
"""

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Optional

import pandas as pd
from baseball.core.db import get_db_connection
from baseball.features.base import BaseFeature


@dataclass
class RelieverWorkload:
    """Complete workload picture for a relief pitcher."""
    player_id: str
    team_id: str
    
    # Recent usage (last 7 days)
    appearances_last_7: int = 0
    pitches_last_7: int = 0
    pitches_last_3: int = 0
    pitches_last_1: int = 0
    
    # Rest status
    days_since_last_appearance: Optional[int] = None
    days_rest: int = 10  # Default to well-rested if no appearances
    
    # High-leverage outings (stress factor)
    high_leverage_appearances: int = 0  # Leverage Index > 1.5
    
    # Season totals for context
    season_appearances: int = 0
    season_pitches: int = 0
    season_high_leverage: int = 0
    
    @property
    def fatigue_score(self) -> float:
        """Calculate fatigue score 0-1 (0=fresh, 1=exhausted).
        
        Based on:
        - Days rest (primary factor)
        - Pitches last 3 days (accumulation)
        - High leverage outings (stress)
        """
        # Rest factor: 0 days = 0.6 fatigue, 1 day = 0.4, 2 days = 0.2, 3+ = 0
        if self.days_rest == 0:
            rest_factor = 0.6
        elif self.days_rest == 1:
            rest_factor = 0.4
        elif self.days_rest == 2:
            rest_factor = 0.2
        else:
            rest_factor = 0.0
        
        # Pitch accumulation: 60+ pitches in 3 days = significant fatigue
        pitch_factor = min(0.3, self.pitches_last_3 / 200)
        
        # Stress factor: high leverage outings add mental/physical fatigue
        stress_factor = min(0.2, self.high_leverage_appearances * 0.05)
        
        # Combined score
        total = rest_factor + pitch_factor + stress_factor
        return min(1.0, max(0.0, total))
    
    @property
    def velocity_projection(self) -> float:
        """Projected velocity modifier (1.0 = normal, <1 = slower)."""
        # Each 0.1 fatigue = 0.5 mph velocity drop
        return max(0.95, 1.0 - (self.fatigue_score * 0.5))
    
    @property
    def command_projection(self) -> float:
        """Projected command (1.0 = normal, <1 = worse control)."""
        # Fatigue affects command more than velocity
        return max(0.90, 1.0 - (self.fatigue_score * 0.3))
    
    @property
    def performance_multiplier(self) -> float:
        """Overall performance adjustment for simulation.
        
        Returns factor to apply to underlying ability.
        Example: 0.90 means pitcher performs at 90% of true talent.
        """
        # Velocity affects power, command affects walks
        return (self.velocity_projection * 0.4 + self.command_projection * 0.6)


class BullpenFatigueCalculator(BaseFeature):
    """Calculate bullpen fatigue metrics for live game predictions.
    
    Uses live feed data to track reliever usage patterns and project
    fatigue effects on performance.
    """
    
    def __init__(self):
        self.name = "bullpen_fatigue"
        self.description = "Reliever workload and fatigue tracking"
        self.category = "pitching"
        
    def get_workload(
        self,
        player_id: str,
        as_of_date: date,
        team_id: Optional[str] = None
    ) -> RelieverWorkload:
        """Get complete workload picture for a relief pitcher.
        
        Args:
            player_id: MLB player ID
            as_of_date: Calculate workload as of this date
            team_id: Optional team filter
            
        Returns:
            RelieverWorkload with all fatigue metrics
        """
        with get_db_connection() as conn:
            # Get appearances in last 7 days
            query_7d = """
                SELECT 
                    COUNT(*) as appearances,
                    SUM(pitches) as total_pitches,
                    SUM(CASE WHEN leverage_index > 1.5 THEN 1 ELSE 0 END) as high_lev_apps
                FROM live.game_events
                WHERE player_id = %s
                    AND event_date BETWEEN %s AND %s
                    AND is_reliever = TRUE
            """
            
            seven_days_ago = as_of_date - timedelta(days=7)
            
            with conn.cursor() as cur:
                cur.execute(query_7d, (player_id, seven_days_ago, as_of_date))
                row = cur.fetchone()
                
                appearances_7d = row[0] or 0
                pitches_7d = row[1] or 0
                high_lev_7d = row[2] or 0
            
            # Get pitches last 3 days and 1 day
            three_days_ago = as_of_date - timedelta(days=3)
            yesterday = as_of_date - timedelta(days=1)
            
            query_3d = """
                SELECT SUM(pitches) 
                FROM live.game_events
                WHERE player_id = %s
                    AND event_date BETWEEN %s AND %s
                    AND is_reliever = TRUE
            """
            
            with conn.cursor() as cur:
                cur.execute(query_3d, (player_id, three_days_ago, as_of_date))
                pitches_3d = cur.fetchone()[0] or 0
                
                cur.execute(query_3d, (player_id, yesterday, as_of_date))
                pitches_1d = cur.fetchone()[0] or 0
            
            # Get last appearance date for rest calculation
            query_last = """
                SELECT MAX(event_date)
                FROM live.game_events
                WHERE player_id = %s
                    AND is_reliever = TRUE
                    AND event_date < %s
            """
            
            with conn.cursor() as cur:
                cur.execute(query_last, (player_id, as_of_date))
                last_app = cur.fetchone()[0]
                
                if last_app:
                    days_rest = (as_of_date - last_app).days
                else:
                    days_rest = 10  # Well-rested if no recent appearances
            
            # Get season totals
            query_season = """
                SELECT 
                    COUNT(*) as apps,
                    SUM(pitches) as pitches,
                    SUM(CASE WHEN leverage_index > 1.5 THEN 1 ELSE 0 END) as high_lev
                FROM live.game_events
                WHERE player_id = %s
                    AND EXTRACT(YEAR FROM event_date) = %s
                    AND is_reliever = TRUE
            """
            
            with conn.cursor() as cur:
                cur.execute(query_season, (player_id, as_of_date.year))
                season_row = cur.fetchone()
                season_apps = season_row[0] or 0
                season_pitches = season_row[1] or 0
                season_high_lev = season_row[2] or 0
        
        return RelieverWorkload(
            player_id=player_id,
            team_id=team_id or "",
            appearances_last_7=appearances_7d,
            pitches_last_7=pitches_7d,
            pitches_last_3=pitches_3d,
            pitches_last_1=pitches_1d,
            days_rest=days_rest,
            high_leverage_appearances=high_lev_7d,
            season_appearances=season_apps,
            season_pitches=season_pitches,
            season_high_leverage=season_high_lev
        )
    
    def get_bullpen_status(
        self,
        team_id: str,
        as_of_date: date
    ) -> dict[str, RelieverWorkload]:
        """Get fatigue status for all available relievers on a team.
        
        Args:
            team_id: Team identifier
            as_of_date: Calculate as of this date
            
        Returns:
            Dict mapping player_id to RelieverWorkload
        """
        # Get active relievers from roster
        with get_db_connection() as conn:
            query = """
                SELECT DISTINCT player_id
                FROM live.rosters
                WHERE team_id = %s
                    AND position = 'P'
                    AND role = 'reliever'
                    AND is_active = TRUE
            """
            
            with conn.cursor() as cur:
                cur.execute(query, (team_id,))
                reliever_ids = [row[0] for row in cur.fetchall()]
        
        # Get workload for each reliever
        workloads = {}
        for player_id in reliever_ids:
            workloads[player_id] = self.get_workload(player_id, as_of_date, team_id)
        
        return workloads
    
    def get_fatigue_adjusted_probabilities(
        self,
        player_id: str,
        base_probabilities: dict[str, float],
        as_of_date: date
    ) -> dict[str, float]:
        """Adjust base outcome probabilities for fatigue.
        
        Args:
            player_id: Relief pitcher
            base_probabilities: Dict of event -> probability
                e.g., {'strikeout': 0.25, 'walk': 0.08, 'hit': 0.22}
            as_of_date: Date for fatigue calculation
            
        Returns:
            Adjusted probabilities accounting for fatigue
        """
        workload = self.get_workload(player_id, as_of_date)
        perf_mult = workload.performance_multiplier
        
        adjusted = base_probabilities.copy()
        
        # Fatigue reduces strikeouts (velocity matters)
        if 'strikeout' in adjusted:
            adjusted['strikeout'] *= perf_mult
        
        # Fatigue increases walks (command suffers)
        if 'walk' in adjusted:
            adjusted['walk'] = min(0.25, adjusted['walk'] * (1 + (1 - perf_mult) * 2))
        
        # Fatigue slightly increases hits (worse stuff = more hard contact)
        if 'hit' in adjusted:
            adjusted['hit'] = min(0.40, adjusted['hit'] * (1 + (1 - perf_mult) * 0.5))
        
        # Re-normalize to ensure probabilities sum to reasonable range
        total = sum(adjusted.values())
        if total > 0:
            factor = 1.0 / total
            adjusted = {k: min(0.99, v * factor) for k, v in adjusted.items()}
        
        return adjusted
    
    def compute(self, game_pk: int, season: int) -> dict:
        """Compute bullpen fatigue features for a game.
        
        Required by BaseFeature interface. Returns aggregate
        bullpen fatigue metrics for both teams.
        """
        with get_db_connection() as conn:
            # Get game info
            query = """
                SELECT home_team_id, away_team_id, game_date
                FROM live.schedule
                WHERE game_pk = %s AND season = %s
            """
            
            with conn.cursor() as cur:
                cur.execute(query, (game_pk, season))
                row = cur.fetchone()
                
                if not row:
                    return {
                        "home_bullpen_avg_fatigue": 0.5,
                        "away_bullpen_avg_fatigue": 0.5,
                        "home_bullpen_warm_bodies": 0,
                        "away_bullpen_warm_bodies": 0
                    }
                
                home_team, away_team, game_date = row
        
        # Get bullpen status for both teams
        home_bullpen = self.get_bullpen_status(home_team, game_date)
        away_bullpen = self.get_bullpen_status(away_team, game_date)
        
        # Calculate aggregate metrics
        home_fatigues = [w.fatigue_score for w in home_bullpen.values()]
        away_fatigues = [w.fatigue_score for w in away_bullpen.values()]
        
        # "Warm bodies" = relievers with fatigue < 0.5 (usable)
        home_warm = sum(1 for f in home_fatigues if f < 0.5)
        away_warm = sum(1 for f in away_fatigues if f < 0.5)
        
        return {
            "home_bullpen_avg_fatigue": sum(home_fatigues) / len(home_fatigues) if home_fatigues else 0.5,
            "away_bullpen_avg_fatigue": sum(away_fatigues) / len(away_fatigues) if away_fatigues else 0.5,
            "home_bullpen_warm_bodies": home_warm,
            "away_bullpen_warm_bodies": away_warm,
            "home_bullpen_total_relief": len(home_bullpen),
            "away_bullpen_total_relief": len(away_bullpen)
        }


def get_fatigue_calculator() -> BullpenFatigueCalculator:
    """Factory function to get calculator instance."""
    return BullpenFatigueCalculator()
