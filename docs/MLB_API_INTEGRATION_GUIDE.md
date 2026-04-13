# MLB Stats API Integration Guide

## Overview

This document outlines the comprehensive integration with MLB Stats API (statsapi.mlb.com) for real-time baseball data ingestion. The MLB Stats API provides live game data, schedules, player information, and historical statistics through RESTful endpoints.

## API Architecture

### Base URL
```
https://statsapi.mlb.com/api/v1
```

### Authentication
- **No API Key Required**: Public API with rate limiting
- **Rate Limits**: ~60 requests/minute (enforced by IP)
- **CORS**: Enabled for web applications
- **Format**: JSON responses only

### Response Format
```json
{
  "copyright": "© 2026 MLB Advanced Media, L.P. All rights reserved.",
  "teams": [...],
  "dates": [...]
}
```

## Core Endpoints

### 1. Schedule Endpoint
**Purpose**: Get games for specific dates or date ranges

**URL Pattern**:
```
GET /api/v1/schedule?sportId=1&date=YYYY-MM-DD
GET /api/v1/schedule?sportId=1&startDate=YYYY-MM-DD&endDate=YYYY-MM-DD
```

**Parameters**:
- `sportId=1`: MLB games (required)
- `date`: Single date (YYYY-MM-DD)
- `startDate`/`endDate`: Date range
- `teamId`: Filter by team
- `season`: Filter by season year

**Response Structure**:
```json
{
  "dates": [{
    "date": "2026-04-09",
    "games": [{
      "gamePk": 823884,
      "gameDate": "2026-04-09T20:10:00Z",
      "status": {
        "abstractGameState": "Live|Final|Preview",
        "codedGameState": "I|F|P",
        "detailedState": "In Progress|Final|Scheduled"
      },
      "teams": {
        "home": {
          "team": {"id": 146, "name": "Miami Marlins"},
          "score": 1
        },
        "away": {
          "team": {"id": 113, "name": "Cincinnati Reds"},
          "score": 8
        }
      }
    }]
  }]
}
```

### 2. Live Feed Endpoint
**Purpose**: Get live game data including play-by-play, box score, and current game state

**URL Pattern**:
```
GET /api/v1.1/game/{gamePk}/feed/live
```

**Parameters**:
- `gamePk`: MLB game identifier (required)

**Response Structure**:
```json
{
  "gamePk": 823884,
  "gameData": {
    "game": {
      "pk": 823884,
      "season": "2026",
      "gameDate": "2026-04-09T20:10:00Z"
    },
    "teams": {
      "home": {
        "id": 146,
        "name": "Miami Marlins",
        "venue": {"id": 4169, "name": "loanDepot park"}
      },
      "away": {
        "id": 113,
        "name": "Cincinnati Reds"
      }
    },
    "players": {
      "ID": {
        "id": 123456,
        "fullName": "Player Name",
        "primaryNumber": "12",
        "currentTeam": {"id": 113},
        "position": {"abbreviation": "CF"},
        "batSide": {"code": "R"},
        "pitchHand": {"code": "R"}
      }
    },
    "weather": {
      "condition": "Clear",
      "temp": 72,
      "windSpeed": 8,
      "windDirection": 45
    }
  },
  "liveData": {
    "plays": {
      "allPlays": [{
        "result": {
          "type": "single|double|home_run|strikeout|walk",
          "event": "Single|Double|Home Run|Strikeout|Walk",
          "eventCode": 20,
          "description": "TJ Friedl singles on a line drive...",
          "rbi": 1
        },
        "about": {
          "atBatIndex": 0,
          "halfInning": "top|bottom",
          "inning": 1,
          "isTopInning": true,
          "halfInningOuts": 0
        },
        "count": {
          "balls": 0,
          "strikes": 0,
          "outs": 0,
          "awayScore": 0,
          "homeScore": 0
        },
        "matchup": {
          "batter": {"id": 123456, "fullName": "TJ Friedl"},
          "pitcher": {"id": 234567, "fullName": "Pitcher Name"},
          "batSide": {"code": "R"},
          "pitchHand": {"code": "R"}
        },
        "runners": [{
          "movement": {
            "originBase": null,
            "start": null,
            "end": "1B",
            "isOut": false,
            "outBase": null
          }
        }]
      }],
      "currentPlay": {...},
      "scoringPlays": [...]
    },
    "linescore": {
      "teams": {
        "home": {"runs": 1, "hits": 5, "errors": 0},
        "away": {"runs": 8, "hits": 12, "errors": 1}
      },
      "innings": [...]
    },
    "boxscore": {
      "teams": {
        "home": {
          "teamStats": {...},
          "players": {...}
        }
      }
    }
  }
}
```

### 3. Teams Endpoint
**Purpose**: Get team information and rosters

**URL Pattern**:
```
GET /api/v1/teams?sportId=1&season=2026
GET /api/v1/teams/{teamId}/roster?season=2026
```

### 4. Players Endpoint
**Purpose**: Get player information

**URL Pattern**:
```
GET /api/v1/people/{playerId}
GET /api/v1/people?personIds=123456,234567
```

## Ingestion Workflow

### Phase 1: Schedule Discovery
**Script**: `scripts/fetch_mlb_schedule.py`

```python
def fetch_mlb_schedule(date: str) -> Dict[str, Any]:
    """Fetch MLB schedule for a specific date."""
    url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={date}"

    with urllib.request.urlopen(url, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))

def get_active_games(schedule_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract games that are currently active."""
    active_games = []

    dates = schedule_data.get("dates", [])
    for date_info in dates:
        games = date_info.get("games", [])
        for game in games:
            status = game.get("status", {})
            abstract_state = status.get("abstractGameState", "")

            # Consider games that are live, in progress, or recently final
            if abstract_state in ["Live", "In Progress", "Final"]:
                active_games.append({
                    "game_pk": game["gamePk"],
                    "status": abstract_state,
                    "home_team": game["teams"]["home"]["team"]["name"],
                    "away_team": game["teams"]["away"]["team"]["name"],
                    "home_score": game.get("teams", {}).get("home", {}).get("score", 0),
                    "away_score": game.get("teams", {}).get("away", {}).get("score", 0),
                })

    return active_games
```

**Process**:
1. Query schedule endpoint for target dates
2. Parse JSON response for games
3. Filter for active/recent games
4. Return list of game PKs for ingestion

### Phase 2: Live Feed Ingestion
**Script**: `scripts/warehouse.py fetch-live-game`

```python
def fetch_live_game(game_pk: int) -> bool:
    """Fetch live game data for a single game."""
    url = f"https://statsapi.mlb.com/api/v1.1/game/{game_pk}/feed/live"

    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            feed_data = json.loads(response.read().decode("utf-8"))

        # Store raw JSON
        conn = psycopg2.connect(**database_kwargs())
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO raw_mlb.live_feed_snapshots
                (game_pk, fetched_at, endpoint, payload, request_params)
                VALUES (%s, now(), %s, %s, %s)
                ON CONFLICT (game_pk, fetched_at) DO NOTHING
            """, (game_pk, url, Json(feed_data), Json({})))

        conn.commit()
        return True

    except Exception as e:
        print(f"Error fetching game {game_pk}: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()
```

**Process**:
1. Construct live feed URL with game PK
2. Make HTTP request with timeout
3. Parse JSON response
4. Store raw JSON in database with metadata
5. Handle errors and duplicates

### Phase 3: Data Transformation
**Script**: `scripts/transform_live_game.py`

```python
def transform_live_game(feed: dict) -> Dict[str, Any]:
    """Transform MLB live feed into core.games format."""
    game_data = feed.get("gameData", {})
    live_data = feed.get("liveData", {})

    # Extract game metadata
    game_pk = game_data.get("game", {}).get("pk")
    season = game_data.get("game", {}).get("season")
    game_date = game_data.get("datetime", {}).get("dateTime")

    # Team information with ID mapping
    teams = game_data.get("teams", {})
    home_team = teams.get("home", {})
    away_team = teams.get("away", {})

    # Map MLB team IDs to Retrosheet IDs
    home_team_id = lookup_retrosheet_team_id(home_team.get("id"), conn) or f"MLB{home_team.get('id')}"
    away_team_id = lookup_retrosheet_team_id(away_team.get("id"), conn) or f"MLB{away_team.get('id')}"

    # Score information
    linescore = live_data.get("linescore", {})
    home_score = linescore.get("teams", {}).get("home", {}).get("runs", 0)
    away_score = linescore.get("teams", {}).get("away", {}).get("runs", 0)

    # Game status
    status = live_data.get("gameData", {}).get("status", {})
    is_complete = status.get("abstractGameState") == "Final"

    return {
        "game_id": f"MLB{game_pk}",
        "season": season,
        "game_date": game_date.split("T")[0] if game_date else None,
        "home_team_id": home_team_id,
        "away_team_id": away_team_id,
        "home_team_name": home_team.get("name"),
        "away_team_name": away_team.get("name"),
        "park_id": f"MLB{game_data.get('venue', {}).get('id')}" if game_data.get('venue', {}).get('id') else None,
        "home_score": home_score,
        "away_score": away_score,
        "is_complete": is_complete,
        "source_type": "mlb_live",
        "mlb_game_pk": game_pk,
        "raw_payload": feed
    }

def transform_live_events(feed: dict, game_id: str, snapshot_id: int) -> List[Dict[str, Any]]:
    """Transform MLB live feed plays into core.events format."""
    live_data = feed.get("liveData", {})
    plays = live_data.get("plays", {}).get("allPlays", [])

    events = []
    for play_idx, play in enumerate(plays):
        result = play.get("result", {})
        about = play.get("about", {})
        count = play.get("count", {})

        # Basic event info
        inning = about.get("inning")
        is_bottom = about.get("isTopInning", True)
        event_sequence = about.get("atBatIndex", play_idx)

        # Count info
        balls = count.get("balls", 0)
        strikes = count.get("strikes", 0)
        outs_before = about.get("halfInningOuts", 0)
        away_score_before = count.get("awayScore", 0)
        home_score_before = count.get("homeScore", 0)

        # Player info with ID mapping
        matchup = play.get("matchup", {})
        batter = matchup.get("batter", {})
        pitcher = matchup.get("pitcher", {})

        batter_id = lookup_retrosheet_player_id(batter.get("id"), conn) if batter.get("id") else None
        pitcher_id = lookup_retrosheet_player_id(pitcher.get("id"), conn) if pitcher.get("id") else None

        # Teams
        batting_team_id = f"MLB{matchup.get('battingTeam', {}).get('id')}" if matchup.get('battingTeam', {}).get('id') else None
        fielding_team_id = f"MLB{matchup.get('pitchingTeam', {}).get('id')}" if matchup.get('pitchingTeam', {}).get('id') else None

        # Event details
        event_type = result.get("type", "unknown")
        event_desc = result.get("description", "")
        event_code = result.get("eventCode", 0)
        rbi = result.get("rbi", 0)

        # Determine event outcomes
        is_hit = event_type in ["single", "double", "triple", "home_run"]
        is_walk = event_type == "walk"
        is_strikeout = event_type == "strikeout"
        is_home_run = event_type == "home_run"

        # Base runner logic
        runners = play.get("runners", [])
        start_bases = 0
        end_bases = 0
        runs_on_play = 0

        for runner in runners:
            if runner.get("movement", {}).get("start"):
                base = runner.get("movement", {}).get("start")
                if base == "1B": start_bases |= 1
                elif base == "2B": start_bases |= 2
                elif base == "3B": start_bases |= 4

            if runner.get("movement", {}).get("end"):
                end_base = runner.get("movement", {}).get("end")
                if end_base == "1B": end_bases |= 1
                elif end_base == "2B": end_bases |= 2
                elif end_base == "3B": end_bases |= 4

            if runner.get("movement", {}).get("run", {}).get("isScoringEvent"):
                runs_on_play += 1

        # Outs on play
        outs_on_play = 0
        if event_type in ["strikeout", "field_out", "force_out", "grounded_into_double_play"]:
            outs_on_play = 1
        elif "double_play" in event_desc.lower():
            outs_on_play = 2

        # Plate appearance logic
        is_at_bat = event_type in ["single", "double", "triple", "home_run", "strikeout", "field_out", "force_out", "grounded_into_double_play", "field_error", "fielders_choice"]
        is_plate_appearance = is_at_bat or is_walk or event_type == "hit_by_pitch" or event_type == "catcher_interference"

        event = {
            "game_id": game_id,
            "event_id": event_sequence + 1,
            "season": int(feed.get("gameData", {}).get("game", {}).get("season")),
            "event_sequence": event_sequence + 1,
            "inning": inning,
            "is_bottom_inning": not is_bottom,  # Convert MLB's isTopInning to is_bottom_inning
            "outs_before": outs_before,
            "balls": balls,
            "strikes": strikes,
            "away_score_before": away_score_before,
            "home_score_before": home_score_before,
            "batting_team_id": batting_team_id,
            "fielding_team_id": fielding_team_id,
            "batter_id": batter_id,
            "batter_hand": batter.get("batSide", {}).get("code", "U"),
            "pitcher_id": pitcher_id,
            "pitcher_hand": pitcher.get("pitchHand", {}).get("code", "U"),
            "event_code": event_code,
            "event_text": event_desc,
            "is_plate_appearance": is_plate_appearance,
            "is_at_bat": is_at_bat,
            "hit_value": 1 if event_type == "single" else 2 if event_type == "double" else 3 if event_type == "triple" else 4 if event_type == "home_run" else 0,
            "is_hit": is_hit,
            "is_walk": is_walk,
            "is_strikeout": is_strikeout,
            "is_home_run": is_home_run,
            "outs_on_play": outs_on_play,
            "runs_on_play": runs_on_play,
            "rbi": rbi,
            "start_bases": start_bases,
            "end_bases": end_bases,
            "source_type": "mlb_live",
            "mlb_game_pk": feed.get("gameData", {}).get("game", {}).get("pk"),
            "snapshot_id": snapshot_id,
            "raw_play": play
        }
        events.append(event)

    return events
```

**Process**:
1. Parse game metadata (teams, scores, venue, weather)
2. Map MLB IDs to Retrosheet IDs via bridge tables
3. Extract play-by-play events with detailed game state
4. Transform to match core.events schema
5. Store in database with upsert logic

### Phase 4: Batch Orchestration
**Script**: `scripts/ingest_live_games.py`

```python
def ingest_game(game_pk: int) -> bool:
    """Complete ingestion pipeline for a single game."""
    # Check if already ingested recently
    if skip_existing:
        recently_ingested = get_recently_ingested_games()
        if game_pk in recently_ingested:
            print(f"Game {game_pk} already ingested recently, skipping.")
            return True

    # Fetch live feed
    success = fetch_live_game(game_pk)
    if not success:
        print(f"Failed to fetch game {game_pk}")
        return False

    # Transform to core schema
    success = transform_live_game(game_pk)
    if not success:
        print(f"Failed to transform game {game_pk}")
        return False

    print(f"Successfully ingested game {game_pk}")
    return True
```

## Error Handling & Resilience

### Network Errors
```python
def fetch_with_retry(url: str, max_retries: int = 3) -> dict:
    """Fetch with exponential backoff retry."""
    for attempt in range(max_retries):
        try:
            with urllib.request.urlopen(url, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 429:  # Rate limited
                wait_time = 2 ** attempt  # Exponential backoff
                print(f"Rate limited, waiting {wait_time}s...")
                time.sleep(wait_time)
                continue
            elif e.code >= 500:  # Server error
                if attempt < max_retries - 1:
                    time.sleep(1)
                    continue
            raise
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(1)
                continue
            raise
```

### Data Validation
```python
def validate_game_data(feed: dict) -> bool:
    """Validate MLB API response structure."""
    required_keys = ["gamePk", "gameData", "liveData"]

    if not all(key in feed for key in required_keys):
        return False

    game_data = feed.get("gameData", {})
    if not game_data.get("game", {}).get("pk"):
        return False

    return True
```

### Rate Limiting
- **Detection**: Monitor HTTP 429 responses
- **Backoff**: Exponential backoff (1s, 2s, 4s, 8s...)
- **Distribution**: Spread requests over time windows
- **Caching**: Cache frequently accessed data

## Query Patterns & Analytics

### Live Game Monitoring
```sql
-- Get current live games
SELECT
    lg.game_id,
    lg.home_team_name,
    lg.away_team_name,
    lg.home_score,
    lg.away_score,
    lg.status_code,
    lg.detailed_state,
    COUNT(le.event_id) as total_events
FROM core.live_games lg
LEFT JOIN core.live_events le ON lg.game_id = le.game_id
WHERE lg.detailed_state NOT IN ('Final', 'Postponed')
GROUP BY lg.game_id, lg.home_team_name, lg.away_team_name,
         lg.home_score, lg.away_score, lg.status_code, lg.detailed_state;
```

### Player Performance in Live Games
```sql
-- Live game player stats
SELECT
    le.batter_id,
    p.name_first,
    p.name_last,
    COUNT(*) FILTER (WHERE le.is_plate_appearance) as pa,
    COUNT(*) FILTER (WHERE le.is_hit) as hits,
    COUNT(*) FILTER (WHERE le.is_home_run) as hr,
    SUM(le.rbi) as rbi
FROM core.live_events le
JOIN core.players p ON le.batter_id = p.retrosheet_player_id
WHERE le.is_plate_appearance = true
GROUP BY le.batter_id, p.name_first, p.name_last
ORDER BY pa DESC;
```

### Real-time Game State
```sql
-- Current game state for live scoring
SELECT
    lg.game_id,
    lg.inning,
    lg.is_bottom_inning,
    lg.home_score,
    lg.away_score,
    lg.outs_before,
    lg.batter_id,
    lg.pitcher_id,
    lg.balls,
    lg.strikes,
    lg.start_bases
FROM core.live_events le
JOIN core.live_games lg ON le.game_id = lg.game_id
WHERE le.game_id = $1
ORDER BY le.event_sequence DESC
LIMIT 1;
```

## Maintenance & Monitoring

### Data Freshness Checks
```sql
-- Check for stale live data
SELECT
    game_id,
    detailed_state,
    MAX(snapshot_fetched_at) as last_update,
    EXTRACT(EPOCH FROM (now() - MAX(snapshot_fetched_at)))/60 as minutes_old
FROM core.live_games lg
JOIN core.live_events le ON lg.game_id = le.game_id
WHERE detailed_state NOT IN ('Final', 'Completed')
GROUP BY game_id, detailed_state
HAVING EXTRACT(EPOCH FROM (now() - MAX(snapshot_fetched_at)))/60 > 30; -- Older than 30 minutes
```

### API Health Monitoring
```sql
-- Track API response times and success rates
SELECT
    DATE_TRUNC('hour', fetched_at) as hour,
    COUNT(*) as requests,
    AVG(EXTRACT(EPOCH FROM (received_at - fetched_at))) as avg_response_time,
    SUM(CASE WHEN http_status >= 200 AND http_status < 300 THEN 1 ELSE 0 END)::float / COUNT(*) as success_rate
FROM raw_mlb.live_feed_snapshots
WHERE fetched_at >= now() - INTERVAL '24 hours'
GROUP BY DATE_TRUNC('hour', fetched_at)
ORDER BY hour DESC;
```

## Configuration & Deployment

### Environment Variables
```bash
# Database connection
export PGHOST=localhost
export PGPORT=5432
export PGDATABASE=retrosheet
export PGUSER=postgres
export PGPASSWORD=your_password

# MLB API settings
export MLB_API_BASE_URL=https://statsapi.mlb.com/api/v1
export MLB_API_TIMEOUT=30
export MLB_API_MAX_RETRIES=3
export MLB_RATE_LIMIT_DELAY=1
```

### Cron Jobs for Automated Ingestion
```bash
# Schedule discovery (every 15 minutes during game hours)
*/15 12-23 * * * /path/to/scripts/fetch_mlb_schedule.py --yesterday

# Live game ingestion (every 5 minutes during games)
*/5 18-23 * * * /path/to/scripts/ingest_live_games.py --schedule --dry-run

# Data cleanup (daily)
0 2 * * * /path/to/scripts/cleanup_old_data.py --days 30
```

## Troubleshooting Guide

### Common Issues

1. **Rate Limiting (HTTP 429)**
   - **Symptom**: Connection errors, timeouts
   - **Solution**: Implement exponential backoff, reduce request frequency
   - **Prevention**: Cache responses, batch requests

2. **Missing Game Data**
   - **Symptom**: Empty or incomplete responses
   - **Solution**: Check game PK validity, retry with backoff
   - **Prevention**: Validate game existence before fetching

3. **ID Mapping Failures**
   - **Symptom**: Unknown player/team IDs
   - **Solution**: Fall back to MLB-prefixed IDs, log for bridge table updates
   - **Prevention**: Regularly update bridge tables from Chadwick Register

4. **Data Structure Changes**
   - **Symptom**: Parsing errors, missing fields
   - **Solution**: Update transformation logic, add field existence checks
   - **Prevention**: Monitor API responses, version transformation code

### Monitoring Queries

```sql
-- Check ingestion health
SELECT
    'last_24h_ingestion' as metric,
    COUNT(*) as games_ingested,
    AVG(EXTRACT(EPOCH FROM (processed_at - fetched_at))) as avg_processing_time
FROM raw_mlb.live_feed_snapshots
WHERE fetched_at >= now() - INTERVAL '24 hours';

-- Error rate monitoring
SELECT
    http_status,
    COUNT(*) as count,
    COUNT(*)::float / SUM(COUNT(*)) OVER () as percentage
FROM raw_mlb.live_feed_snapshots
WHERE fetched_at >= now() - INTERVAL '24 hours'
GROUP BY http_status
ORDER BY count DESC;
```

## API Limits & Best Practices

- **Requests per Minute**: ~60 (enforced by IP)
- **Requests per Hour**: ~3,600
- **Data Freshness**: Live feeds update every ~10-30 seconds during games
- **Caching Strategy**: Cache static data (teams, players) for hours, live data for minutes
- **Error Handling**: Always implement retry logic with exponential backoff
- **Data Validation**: Validate response structure before processing
- **Logging**: Log all API interactions for debugging and monitoring

This comprehensive guide provides everything needed to reliably ingest and process MLB Stats API data at production scale.