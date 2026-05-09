"""Entity extraction from natural language.

Extracts structured entities like teams, players, dates
from natural language input.

Author: Agent cbwinslow/retrosheet
Date: 2026-04-26
"""

import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any


@dataclass
class Entity:
    """Extracted entity from text.
    
    Attributes:
        type: Entity type (team, player, date, etc.)
        value: Normalized value
        raw_text: Original text that matched
        start: Start position in text
        end: End position in text
        confidence: Extraction confidence (0-1)
    """
    type: str
    value: str
    raw_text: str
    start: int
    end: int
    confidence: float


class EntityExtractor:
    """Extract entities from natural language text.
    
    Identifies and extracts:
    - Team names and abbreviations
    - Player names
    - Dates and times
    - Numbers and statistics
    
    Example:
        >>> extractor = EntityExtractor()
        >>> entities = extractor.extract("How are the Yankees doing?")
        >>> print([e.value for e in entities if e.type == 'team'])
        ['NYY']
    """
    
    # Team name mappings
    TEAM_NAMES = {
        'angels': 'LAA', 'los angeles angels': 'LAA', 'laa': 'LAA',
        'astros': 'HOU', 'houston': 'HOU',
        'athletics': 'OAK', "a's": 'OAK', 'oakland': 'OAK',
        'blue jays': 'TOR', 'jays': 'TOR', 'toronto': 'TOR',
        'braves': 'ATL', 'atlanta': 'ATL',
        'brewers': 'MIL', 'milwaukee': 'MIL',
        'cardinals': 'STL', 'st louis': 'STL', 'st. louis': 'STL',
        'cubs': 'CHC', 'chicago cubs': 'CHC',
        'diamondbacks': 'ARI', 'd-backs': 'ARI', 'arizona': 'ARI',
        'dodgers': 'LAD', 'los angeles dodgers': 'LAD', 'la dodgers': 'LAD',
        'giants': 'SF', 'san francisco': 'SF',
        'guardians': 'CLE', 'cleveland': 'CLE',
        'mariners': 'SEA', 'seattle': 'SEA',
        'marlins': 'MIA', 'miami': 'MIA',
        'mets': 'NYM', 'new york mets': 'NYM',
        'nationals': 'WSH', 'washington': 'WSH',
        'orioles': 'BAL', 'baltimore': 'BAL',
        'padres': 'SD', 'san diego': 'SD',
        'phillies': 'PHI', 'philadelphia': 'PHI',
        'pirates': 'PIT', 'pittsburgh': 'PIT',
        'rangers': 'TEX', 'texas': 'TEX',
        'rays': 'TB', 'tampa bay': 'TB',
        'red sox': 'BOS', 'boston': 'BOS',
        'reds': 'CIN', 'cincinnati': 'CIN',
        'rockies': 'COL', 'colorado': 'COL',
        'royals': 'KC', 'kansas city': 'KC',
        'tigers': 'DET', 'detroit': 'DET',
        'twins': 'MIN', 'minnesota': 'MIN',
        'white sox': 'CHW', 'chicago white sox': 'CHW',
        'yankees': 'NYY', 'new york yankees': 'NYY', 'ny yankees': 'NYY', 'yanks': 'NYY',
    }
    
    # Common player names (would be loaded from database)
    COMMON_PLAYERS = {
        'aaron judge': '592450',
        'shohei ohtani': '660271',
        'mike trout': '545361',
        'mookie betts': '605141',
        'juan soto': '665742',
        'ronald acuna': '660670',
        'fernando tatis': '665487',
        'vladimir guerrero': '665489',
        'julio rodriguez': '677594',
        'corbin carroll': '682998',
    }
    
    def __init__(self, db_connection=None):
        """Initialize entity extractor.
        
        Args:
            db_connection: Optional database connection for loading entities
        """
        self.db = db_connection
        self._compile_patterns()
        
        if db_connection:
            self._load_entities_from_db()
    
    def _compile_patterns(self) -> None:
        """Compile regex patterns for entity extraction."""
        # Team pattern
        team_alternatives = '|'.join(re.escape(name) for name in self.TEAM_NAMES.keys())
        self._team_pattern = re.compile(
            rf'\b({team_alternatives})\b',
            re.IGNORECASE
        )
        
        # Player name pattern (simplified - would use NER in production)
        self._player_pattern = re.compile(
            r'\b([A-Z][a-z]+\s[A-Z][a-z]+)\b',
            re.IGNORECASE
        )
        
        # Date patterns
        self._date_patterns = [
            # "today", "tomorrow", "yesterday"
            (re.compile(r'\b(today|tomorrow|yesterday)\b', re.IGNORECASE), 'relative'),
            # "April 26" or "Apr 26"
            (re.compile(r'\b(jan|january|feb|february|mar|march|apr|april|may|jun|june|jul|july|aug|august|sep|september|oct|october|nov|november|dec|december)\s+(\d{1,2})\b', re.IGNORECASE), 'month_day'),
            # "4/26" or "04/26"
            (re.compile(r'\b(\d{1,2})/(\d{1,2})\b'), 'numeric'),
            # "next Monday", "this weekend"
            (re.compile(r'\b(next|this)\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday|weekend|week)\b', re.IGNORECASE), 'relative_day'),
        ]
        
        # Number patterns
        self._number_pattern = re.compile(
            r'\b(\d+\.?\d*)\s*(percent|%|pct)?\b',
            re.IGNORECASE
        )
        
        # Stat patterns
        self._stat_patterns = {
            'batting_average': re.compile(r'(\d{3})\s*(?:ba|avg|batting average)', re.IGNORECASE),
            'era': re.compile(r'(\d+\.?\d*)\s*era', re.IGNORECASE),
            'ops': re.compile(r'(\d{3})\s*ops', re.IGNORECASE),
            'home_runs': re.compile(r'(\d+)\s*(?:hr|home run)', re.IGNORECASE),
        }
    
    def _load_entities_from_db(self) -> None:
        """Load additional entities from database."""
        try:
            with self.db.cursor() as cur:
                # Load active players
                cur.execute('''
                    SELECT player_name, mlbam_id 
                    FROM core.players 
                    WHERE active = true
                    LIMIT 1000
                ''')
                for row in cur.fetchall():
                    name = row[0].lower()
                    self.COMMON_PLAYERS[name] = str(row[1])
        except Exception as e:
            # Silently fail if database unavailable
            pass
    
    def extract(self, text: str) -> List[Entity]:
        """Extract all entities from text.
        
        Args:
            text: Natural language input
            
        Returns:
            List of extracted entities
        """
        if not text:
            return []
        
        entities = []
        entities.extend(self._extract_teams(text))
        entities.extend(self._extract_players(text))
        entities.extend(self._extract_dates(text))
        entities.extend(self._extract_numbers(text))
        entities.extend(self._extract_stats(text))
        
        return entities
    
    def _extract_teams(self, text: str) -> List[Entity]:
        """Extract team entities."""
        entities = []
        for match in self._team_pattern.finditer(text):
            team_name = match.group(1).lower()
            team_code = self.TEAM_NAMES.get(team_name)
            if team_code:
                entities.append(Entity(
                    type='team',
                    value=team_code,
                    raw_text=match.group(1),
                    start=match.start(),
                    end=match.end(),
                    confidence=0.95
                ))
        return entities
    
    def _extract_players(self, text: str) -> List[Entity]:
        """Extract player entities."""
        entities = []
        text_lower = text.lower()
        
        for player_name, player_id in self.COMMON_PLAYERS.items():
            if player_name in text_lower:
                start = text_lower.index(player_name)
                end = start + len(player_name)
                entities.append(Entity(
                    type='player',
                    value=player_id,
                    raw_text=text[start:end],
                    start=start,
                    end=end,
                    confidence=0.90
                ))
        
        return entities
    
    def _extract_dates(self, text: str) -> List[Entity]:
        """Extract date entities."""
        entities = []
        
        for pattern, date_type in self._date_patterns:
            for match in pattern.finditer(text):
                value = self._normalize_date(match.group(0), date_type)
                entities.append(Entity(
                    type='date',
                    value=value,
                    raw_text=match.group(0),
                    start=match.start(),
                    end=match.end(),
                    confidence=0.85
                ))
        
        return entities
    
    def _normalize_date(self, raw_date: str, date_type: str) -> str:
        """Normalize extracted date to standard format."""
        today = datetime.now()
        
        if date_type == 'relative':
            if 'today' in raw_date.lower():
                return today.strftime('%Y-%m-%d')
            elif 'tomorrow' in raw_date.lower():
                return (today + timedelta(days=1)).strftime('%Y-%m-%d')
            elif 'yesterday' in raw_date.lower():
                return (today - timedelta(days=1)).strftime('%Y-%m-%d')
        
        # For other types, return ISO format or original
        return raw_date
    
    def _extract_numbers(self, text: str) -> List[Entity]:
        """Extract numeric entities."""
        entities = []
        
        for match in self._number_pattern.finditer(text):
            value = match.group(1)
            suffix = match.group(2) or ''
            
            if 'percent' in suffix.lower() or '%' in suffix or 'pct' in suffix.lower():
                entity_type = 'percentage'
                # Convert to decimal
                try:
                    value = str(float(value) / 100)
                except ValueError:
                    continue
            else:
                entity_type = 'number'
            
            entities.append(Entity(
                type=entity_type,
                value=value,
                raw_text=match.group(0),
                start=match.start(),
                end=match.end(),
                confidence=0.90
            ))
        
        return entities
    
    def _extract_stats(self, text: str) -> List[Entity]:
        """Extract statistical entities."""
        entities = []
        
        for stat_type, pattern in self._stat_patterns.items():
            for match in pattern.finditer(text):
                entities.append(Entity(
                    type=f'stat_{stat_type}',
                    value=match.group(1),
                    raw_text=match.group(0),
                    start=match.start(),
                    end=match.end(),
                    confidence=0.85
                ))
        
        return entities
    
    def get_teams(self, text: str) -> List[str]:
        """Convenience method to get just team codes.
        
        Args:
            text: Input text
            
        Returns:
            List of team codes
        """
        return [e.value for e in self.extract(text) if e.type == 'team']
    
    def get_players(self, text: str) -> List[str]:
        """Convenience method to get just player IDs.
        
        Args:
            text: Input text
            
        Returns:
            List of player IDs
        """
        return [e.value for e in self.extract(text) if e.type == 'player']
    
    def get_dates(self, text: str) -> List[str]:
        """Convenience method to get just dates.
        
        Args:
            text: Input text
            
        Returns:
            List of normalized dates
        """
        return [e.value for e in self.extract(text) if e.type == 'date']
