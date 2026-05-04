"""Data factories for baseball testing infrastructure.

This module provides factory classes for generating test data including players, teams, games, and scenarios.
"""

import random
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from .utils import PerformanceTimer, DataValidator


@dataclass
class Game:
    """Represents a baseball game."""
    game_pk: int
    date: str
    home_team: str
    away_team: str
    home_score: int
    away_score: int
    venue: str = ""
    attendance: int = 0


@dataclass
class Player:
    """Represents a baseball player."""
    player_id: str
    first_name: str
    last_name: str
    position: str
    bats: str = "R"
    throws: str = "R"
    height: str = ""
    weight: int = 0
    birth_date: str = ""


@dataclass
class Pitch:
    """Represents a single pitch in a baseball game."""
    pitch_id: str
    game_pk: int
    at_bat_num: int
    pitch_number: int
    batter_id: str
    pitcher_id: str
    pitch_type: str
    result: str
    velocity: float = 0.0
    spin_rate: float = 0.0
    release_point: float = 0.0


@dataclass
class Team:
    """Represents a baseball team."""
    team_id: str
    team_name: str
    city: str
    league: str
    division: str
    stadium: str = ""
    manager: str = ""


class GameFactory:
    """Factory for creating game-related test data."""
    
    @staticmethod
    def create_game(**kwargs) -> Game:
        """Create a game instance with default or provided values."""
        defaults = {
            'game_pk': random.randint(100000, 999999),
            'date': '2024-01-01',
            'home_team': 'Yankees',
            'away_team': 'Red Sox',
            'home_score': random.randint(0, 10),
            'away_score': random.randint(0, 10),
            'venue': 'Yankee Stadium',
            'attendance': random.randint(10000, 50000)
        }
        defaults.update(kwargs)
        return Game(**defaults)
    
    @staticmethod
    def create_complete_game() -> Dict[str, Any]:
        """Create a complete game scenario with all components."""
        game = GameFactory.create_game()
        home_team = TeamFactory.create_team(game.home_team)
        away_team = TeamFactory.create_team(game.away_team)
        
        # Create 50-100 pitches for the game
        num_pitches = random.randint(50, 100)
        pitches = []
        for i in range(num_pitches):
            pitch = PitchFactory.create_pitch(game_pk=game.game_pk, at_bat_num=i // 4)
            pitches.append(pitch)
        
        return {
            'game': game,
            'home_team': home_team,
            'away_team': away_team,
            'pitches': pitches
        }
    
    @staticmethod
    def create_season(num_games: int = 10) -> List[Dict[str, Any]]:
        """Create a season of games."""
        season = []
        for _ in range(num_games):
            game_scenario = GameFactory.create_complete_game()
            season.append(game_scenario)
        return season


class PlayerFactory:
    """Factory for creating player test data."""
    
    _first_names = ['Chris', 'Mike', 'John', 'David', 'James', 'Robert', 'Michael', 'William']
    _last_names = ['Brown', 'Smith', 'Johnson', 'Williams', 'Jones', 'Garcia', 'Miller', 'Davis']
    _positions = ['P', 'C', '1B', '2B', '3B', 'SS', 'LF', 'CF', 'RF', 'DH']
    
    @classmethod
    def create_player(cls, **kwargs) -> Player:
        """Create a player instance with default or provided values."""
        defaults = {
            'player_id': str(random.randint(100000, 999999)),
            'first_name': random.choice(cls._first_names),
            'last_name': random.choice(cls._last_names),
            'position': random.choice(cls._positions),
            'bats': random.choice(['L', 'R', 'S']),
            'throws': random.choice(['L', 'R', 'S']),
            'height': f"{random.randint(68, 80)}\"{random.choice(['', '  ', '  '])}",
            'weight': random.randint(160, 250),
            'birth_date': f"{random.randint(1980, 2000)}-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}"
        }
        defaults.update(kwargs)
        return Player(**defaults)
    
    @classmethod
    def create_roster(cls, team_name: str = 'Yankees', num_players: int = 26) -> List[Player]:
        """Create a full team roster."""
        roster = []
        for _ in range(num_players):
            player = cls.create_player()
            roster.append(player)
        return roster


class PitchFactory:
    """Factory for creating pitch test data."""
    
    _pitch_types = ['FF', 'SI', 'SL', 'CU', 'CH', 'KC', 'EP']
    _pitch_results = ['S', 'B', 'F', 'X', 'H', 'O']
    
    @classmethod
    def create_pitch(cls, game_pk: int = 100000, at_bat_num: int = 0, **kwargs) -> Pitch:
        """Create a pitch instance with default or provided values."""
        pitch_num = random.randint(1, 10)
        defaults = {
            'pitch_id': f"{game_pk}_{at_bat_num}_{pitch_num}",
            'game_pk': game_pk,
            'at_bat_num': at_bat_num,
            'pitch_number': pitch_num,
            'batter_id': str(random.randint(100000, 999999)),
            'pitcher_id': str(random.randint(100000, 999999)),
            'pitch_type': random.choice(cls._pitch_types),
            'result': random.choice(cls._pitch_results),
            'velocity': round(random.uniform(80.0, 105.0), 1),
            'spin_rate': round(random.uniform(2000.0, 3000.0), 1),
            'release_point': round(random.uniform(5.0, 6.5), 2)
        }
        defaults.update(kwargs)
        return Pitch(**defaults)
    
    @classmethod
    def create_at_bat(cls, game_pk: int = 100000, at_bat_num: int = 0, num_pitches: int = 4) -> List[Pitch]:
        """Create a complete at-bat sequence."""
        at_bat = []
        for i in range(num_pitches):
            pitch = cls.create_pitch(game_pk, at_bat_num, pitch_number=i+1)
            at_bat.append(pitch)
        return at_bat


class TeamFactory:
    """Factory for creating team test data."""
    
    _teams_data = {
        'Yankees': {'city': 'New York', 'league': 'AL', 'division': 'East', 'stadium': 'Yankee Stadium'},
        'Red Sox': {'city': 'Boston', 'league': 'AL', 'division': 'East', 'stadium': 'Fenway Park'},
        'Dodgers': {'city': 'Los Angeles', 'league': 'NL', 'division': 'West', 'stadium': 'Dodger Stadium'},
        'Cubs': {'city': 'Chicago', 'league': 'NL', 'division': 'Central', 'stadium': 'Wrigley Field'},
        'Astros': {'city': 'Houston', 'league': 'AL', 'division': 'West', 'stadium': 'Minute Maid Park'},
        'Giants': {'city': 'San Francisco', 'league': 'NL', 'division': 'West', 'stadium': 'Oracle Park'},
        'Braves': {'city': 'Atlanta', 'league': 'NL', 'division': 'East', 'stadium': 'Truist Park'},
        'Cardinals': {'city': 'St. Louis', 'league': 'NL', 'division': 'Central', 'stadium': 'Busch Stadium'},
    }
    
    @classmethod
    def create_team(cls, team_name: Optional[str] = None) -> Team:
        """Create a team instance with default or provided values."""
        if team_name and team_name in cls._teams_data:
            data = cls._teams_data[team_name]
            team_id = f"{team_name[:3].upper()}{random.randint(100, 999)}"
            return Team(
                team_id=team_id,
                team_name=team_name,
                city=data['city'],
                league=data['league'],
                division=data['division'],
                stadium=data['stadium'],
                manager=random.choice(['Aaron Boone', 'Alex Cora', 'Dave Roberts', 'David Ross'])
            )
        else:
            # Create a random team
            team_name = team_name or f"Team_{random.randint(1, 999)}"
            return Team(
                team_id=f"T{random.randint(1000, 9999)}",
                team_name=team_name,
                city=f"City_{random.randint(1, 100)}",
                league=random.choice(['AL', 'NL']),
                division=random.choice(['East', 'West', 'Central']),
                stadium=f"Stadium_{random.randint(1, 50)}",
                manager=f"Manager_{random.randint(1, 20)}"
            )


class StatisticsFactory:
    """Factory for creating statistics test data."""
    
    @classmethod
    def create_batting_stats(cls, **kwargs) -> Dict[str, float]:
        """Create batting statistics."""
        defaults = {
            'avg': round(random.uniform(0.200, 0.350), 3),
            'obp': round(random.uniform(0.300, 0.450), 3),
            'slg': round(random.uniform(0.350, 0.600), 3),
            'ops': round(random.uniform(0.650, 1.050), 3),
            'hr': random.randint(0, 50),
            'rbi': random.randint(0, 150),
            'sb': random.randint(0, 50),
            'ops_plus': random.randint(80, 150)
        }
        defaults.update(kwargs)
        return defaults
    
    @classmethod
    def create_pitching_stats(cls, **kwargs) -> Dict[str, float]:
        """Create pitching statistics."""
        defaults = {
            'era': round(random.uniform(2.00, 6.00), 2),
            'whip': round(random.uniform(0.90, 1.80), 2),
            'k_per_9': round(random.uniform(5.0, 12.0), 1),
            'bb_per_9': round(random.uniform(1.0, 5.0), 1),
            'hr_per_9': round(random.uniform(0.5, 3.0), 1),
            'wins': random.randint(0, 25),
            'losses': random.randint(0, 20),
            'saves': random.randint(0, 40)
        }
        defaults.update(kwargs)
        return defaults


class GameScenarioFactory:
    """Factory for creating game scenario test data."""
    
    @classmethod
    def create_complete_game(cls) -> Dict[str, Any]:
        """Create a complete game scenario."""
        return GameFactory.create_complete_game()
    
    @classmethod
    def create_season(cls, num_games: int = 10) -> List[Dict[str, Any]]:
        """Create a season of games."""
        return GameFactory.create_season(num_games)
    
    @classmethod
    def create_playoff_series(cls, num_games: int = 7) -> List[Dict[str, Any]]:
        """Create a playoff series."""
        series = []
        for _ in range(num_games):
            game_scenario = GameFactory.create_complete_game()
            series.append(game_scenario)
        return series