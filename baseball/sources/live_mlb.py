"""
MLB Live Data Source Adapter

Real-time game state ingestion from MLB Stats API for live predictions.
"""
from typing import Optional, Dict, Any, List
from datetime import datetime
import requests
import time
from .base import BaseSource, SourceResult


class LiveMlbSource(BaseSource):
    """Source adapter for live MLB game data."""

    def __init__(self, game_pk: Optional[int] = None, poll_interval: int = 10):
        self.name = 'live_mlb'
        self.game_pk = game_pk
        self.poll_interval = poll_interval
        self.base_url = 'https://statsapi.mlb.com/api/v1'
        self._last_hash: Optional[str] = None
        self._session = requests.Session()

    def download(self, game_pk: Optional[int] = None, **kwargs) -> SourceResult:
        """Fetch current live game state."""
        target_game = game_pk or self.game_pk

        try:
            if target_game:
                # Fetch specific game
                url = f'{self.base_url}/game/{target_game}/feed/live'
                resp = self._session.get(url, timeout=15)
                resp.raise_for_status()
                data = resp.json()

                # Check if game is actually live
                status = data.get('gameData', {}).get('status', {}).get('abstractGameCode', '')
                if status not in ('L', 'P'):
                    return SourceResult(
                        success=True,
                        records=0,
                        message=f'Game {target_game} not live (status: {status})'
                    )

                return SourceResult(
                    success=True,
                    records=1,
                    data=data,
                    raw_bytes=len(resp.content)
                )
            else:
                # Fetch all live games for today
                url = f'{self.base_url}/schedule?sportId=1&gameTypes=R,F,D,L,W&hydrate=linescore(runners)'
                resp = self._session.get(url, timeout=15)
                resp.raise_for_status()
                data = resp.json()

                # Count live/preview games
                live_count = 0
                for date_info in data.get('dates', []):
                    for game in date_info.get('games', []):
                        status = game.get('status', {}).get('abstractGameCode', '')
                        if status in ('L', 'P'):
                            live_count += 1

                return SourceResult(
                    success=True,
                    records=live_count,
                    data=data,
                    raw_bytes=len(resp.content)
                )

        except requests.RequestException as e:
            return SourceResult(success=False, error=str(e))
        except Exception as e:
            return SourceResult(success=False, error=f'Unexpected: {e}')

    def ingest(self, data: Dict[str, Any], **kwargs) -> SourceResult:
        """Transform live game data to canonical format."""
        try:
            if not data:
                return SourceResult(success=False, error='No data to ingest')

            game_pk = data.get('gamePk')
            if not game_pk and 'gameData' in data:
                game_pk = data['gameData'].get('game', {}).get('pk')

            if not game_pk:
                return SourceResult(success=False, error='No game_pk found')

            # Extract game state
            game_state = self._extract_game_state(data)
            if not game_state:
                return SourceResult(success=False, error='Failed to extract game state')

            return SourceResult(
                success=True,
                records=1,
                data={
                    'game_pk': game_pk,
                    'state': game_state,
                    'timestamp': datetime.utcnow().isoformat()
                }
            )

        except Exception as e:
            return SourceResult(success=False, error=str(e))

    def validate(self, data: Dict[str, Any], **kwargs) -> SourceResult:
        """Validate live game data completeness."""
        errors = []

        if not data:
            errors.append('Empty data')
            return SourceResult(success=False, error='; '.join(errors))

        # Check required fields
        game_pk = data.get('game_pk')
        if not game_pk:
            errors.append('Missing game_pk')

        state = data.get('state', {})
        required = ['inning', 'is_top', 'outs', 'score_home', 'score_away']
        for field in required:
            if field not in state:
                errors.append(f'Missing state.{field}')

        if errors:
            return SourceResult(success=False, error='; '.join(errors))

        return SourceResult(success=True, records=1, message='Valid live game state')

    def _extract_game_state(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract normalized game state from API response."""
        try:
            if 'liveData' in data and 'linescore' in data['liveData']:
                # Detailed feed format
                linescore = data['liveData']['linescore']
                game_data = data.get('gameData', {}).get('game', {})

                inning = linescore.get('currentInning', 1)
                is_top = linescore.get('isTopInning', True)
                outs = linescore.get('outs', 0)

                home_team = linescore.get('teams', {}).get('home', {})
                away_team = linescore.get('teams', {}).get('away', {})
                score_home = home_team.get('runs', 0)
                score_away = away_team.get('runs', 0)

                # Base state
                offense = linescore.get('offense', {})
                runner_1b = 'first' in offense
                runner_2b = 'second' in offense
                runner_3b = 'third' in offense
                base_state = (
                    (1 if runner_1b else 0) +
                    (2 if runner_2b else 0) +
                    (4 if runner_3b else 0)
                )

                return {
                    'inning': inning,
                    'is_top': is_top,
                    'outs': outs,
                    'score_home': score_home,
                    'score_away': score_away,
                    'base_state': base_state,
                    'score_diff': score_home - score_away,
                    'game_pk': game_data.get('pk') or data.get('gamePk'),
                    'status': data.get('gameData', {}).get('status', {}).get('abstractGameCode', 'U')
                }

            elif 'teams' in data:
                # Schedule format (less detailed)
                status = data.get('status', {}).get('abstractGameCode', 'U')
                return {
                    'game_pk': data.get('gamePk'),
                    'status': status,
                    'score_home': data.get('teams', {}).get('home', {}).get('score', 0),
                    'score_away': data.get('teams', {}).get('away', {}).get('score', 0),
                    'inning': data.get('linescore', {}).get('currentInning', 1),
                    'is_top': data.get('linescore', {}).get('isTopInning', True),
                    'outs': data.get('linescore', {}).get('outs', 0),
                    'base_state': 0  # Not available in schedule format
                }

        except Exception as e:
            return None

    def poll(self, game_pk: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """Poll for game updates. Returns data only if changed."""
        result = self.download(game_pk=game_pk)
        if not result.success or not result.data:
            return None

        # Simple change detection using content hash
        import hashlib
        content = str(result.data).encode()
        current_hash = hashlib.md5(content).hexdigest()

        if current_hash == self._last_hash:
            return None  # No change

        self._last_hash = current_hash
        return result.data

    def stream(self, game_pk: Optional[int] = None, duration: Optional[int] = None):
        """Generator that yields game state updates."""
        start_time = time.time()
        poll_count = 0

        while True:
            poll_count += 1
            current_time = time.time()
            elapsed = current_time - start_time

            if duration and elapsed > duration:
                break

            data = self.poll(game_pk=game_pk)
            if data:
                ingest_result = self.ingest(data)
                if ingest_result.success:
                    yield {
                        'poll': poll_count,
                        'elapsed': elapsed,
                        'data': ingest_result.data
                    }

            time.sleep(self.poll_interval)
