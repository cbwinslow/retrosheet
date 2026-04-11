# MLB Stats API Data Dictionary

## Overview

This document provides a comprehensive data dictionary for the MLB Stats API responses used in our historical data ingestion pipeline. It maps API fields to our normalized database schema and explains data transformations.

## API Response Structure

### Schedule Endpoint Response
```json
{
  "copyright": "© 2026 MLB Advanced Media, L.P. All rights reserved.",
  "dates": [{
    "date": "2024-04-01",
    "games": [{
      "gamePk": 745842,
      "gameDate": "2024-04-01T20:10:00Z",
      "status": {
        "abstractGameState": "Final",
        "codedGameState": "F",
        "detailedState": "Final",
        "statusCode": "F"
      },
      "teams": {
        "home": {
          "team": {"id": 146, "name": "Miami Marlins"},
          "score": 6
        },
        "away": {
          "team": {"id": 113, "name": "Cincinnati Reds"},
          "score": 3
        }
      },
      "venue": {"id": 4169, "name": "loanDepot park"},
      "gameNumber": 1,
      "dayNight": "night",
      "scheduledInnings": 9
    }]
  }]
}
```

### Live Feed Endpoint Response
```json
{
  "gamePk": 745842,
  "gameData": {
    "game": {
      "pk": 745842,
      "season": 2024,
      "gameDate": "2024-04-01T20:10:00Z"
    },
    "teams": {
      "home": {"id": 146, "name": "Miami Marlins"},
      "away": {"id": 113, "name": "Cincinnati Reds"}
    },
    "venue": {"id": 4169, "name": "loanDepot park"},
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
          "type": "single",
          "event": "Single",
          "eventCode": 20,
          "rbi": 1,
          "description": "Player singles..."
        },
        "about": {
          "atBatIndex": 0,
          "inning": 1,
          "isTopInning": true,
          "halfInningOuts": 0
        },
        "count": {
          "balls": 1,
          "strikes": 2,
          "outs": 0
        },
        "matchup": {
          "batter": {"id": 123456, "fullName": "Player Name"},
          "pitcher": {"id": 234567, "fullName": "Pitcher Name"},
          "batSide": {"code": "R"},
          "pitchHand": {"code": "R"}
        },
        "runners": [{
          "movement": {
            "start": null,
            "end": "1B",
            "isOut": false,
            "outBase": null
          }
        }],
        "playEvents": [{
          "type": "pitch",
          "isPitch": true,
          "pitchData": {
            "startSpeed": 92.5,
            "endSpeed": 83.2,
            "coordinates": {"x": 54.37, "y": 171.75, "z": 2.45},
            "breaks": {
              "spinRate": 2150,
              "breakAngle": 12.5,
              "breakLength": 3.8,
              "breakVertical": -18.5,
              "breakHorizontal": 3.2
            }
          },
          "details": {
            "call": {"code": "B", "description": "Ball"},
            "type": {"code": "FF", "description": "Four-Seam Fastball"}
          }
        }]
      }]
    },
    "linescore": {
      "teams": {
        "home": {"runs": 6, "hits": 12, "errors": 1},
        "away": {"runs": 3, "hits": 8, "errors": 0}
      }
    }
  }
}
```

## Field Mapping Dictionary

### Games Table Mapping

| MLB API Field | Database Field | Transformation | Notes |
|---------------|----------------|----------------|--------|
| `game.pk` | `game_pk` | Direct | Primary key |
| `game.season` | `season` | Direct | Season year |
| `game.gameDate` | `game_date` | `date.split('T')[0]` | Extract date part |
| `teams.home.team.id` | `home_team_id` | Bridge table lookup | MLB → Retrosheet ID |
| `teams.away.team.id` | `away_team_id` | Bridge table lookup | MLB → Retrosheet ID |
| `teams.home.score` | `home_score` | Direct | Final score |
| `teams.away.score` | `away_score` | Direct | Final score |
| `venue.id` | `venue_id` | Bridge table lookup | MLB → Retrosheet venue |
| `venue.name` | `venue_name` | Direct | Venue display name |
| `weather.temp` | `temperature_f` | Direct | Fahrenheit |
| `weather.windSpeed` | `wind_speed_mph` | Direct | Wind speed |
| `weather.windDirection` | `wind_direction` | Direct | Degrees |
| `weather.condition` | `sky_condition` | Direct | Weather condition |
| `status.abstractGameState` | `status_abstract` | Direct | Live/Final/etc |
| `status.detailedState` | `status_detailed` | Direct | Detailed status |
| `linescore.teams.home.runs` | `home_score` | Direct | Final runs |
| `linescore.teams.home.hits` | `home_hits` | Direct | Final hits |
| `linescore.teams.home.errors` | `home_errors` | Direct | Final errors |

### Events Table Mapping

| MLB API Field | Database Field | Transformation | Notes |
|---------------|----------------|----------------|--------|
| `gamePk` | `game_pk` | Direct | Foreign key |
| `about.atBatIndex` | `event_index` | `index + 1` | Sequential within game |
| `about.inning` | `inning` | Direct | Inning number |
| `about.isTopInning` | `is_bottom_inning` | `not value` | Convert MLB convention |
| `about.halfInningOuts` | `outs_before` | Direct | Outs before this event |
| `count.balls` | `balls` | Direct | Ball count |
| `count.strikes` | `strikes` | Direct | Strike count |
| `count.awayScore` | `away_score_before` | Direct | Score before event |
| `count.homeScore` | `home_score_before` | Direct | Score before event |
| `matchup.batter.id` | `batter_id` | Bridge lookup | MLB → Retrosheet player |
| `matchup.pitcher.id` | `pitcher_id` | Bridge lookup | MLB → Retrosheet player |
| `matchup.batSide.code` | `batter_hand` | Direct | L/R/S |
| `matchup.pitchHand.code` | `pitcher_hand` | Direct | L/R |
| `result.eventCode` | `event_code` | Direct | MLB event code |
| `result.type` | `event_result` | Direct | single/double/etc |
| `result.description` | `event_text` | Direct | Play description |
| `result.rbi` | `rbi` | Direct | RBIs on play |
| `runners[].movement.end` | `start_bases/end_bases` | Bitmask encoding | Runner positions |

### Pitches Table Mapping

| MLB API Field | Database Field | Transformation | Notes |
|---------------|----------------|----------------|--------|
| `gamePk` | `game_pk` | Direct | Foreign key |
| `about.atBatIndex` | `event_index` | Direct | Links to event |
| `index` | `pitch_index` | Direct | Pitch within at-bat |
| `playId` | `play_id` | Direct | Unique play identifier |
| `details.type.code` | `pitch_type_code` | Direct | FF, SL, CU, etc |
| `details.type.description` | `pitch_type_description` | Direct | Four-Seam Fastball |
| `details.call.code` | `pitch_call_code` | Direct | B, S, F, X |
| `details.call.description` | `pitch_call_description` | Direct | Ball, Strike, Foul |
| `pitchData.coordinates.x` | `plate_x` | Direct | Horizontal location |
| `pitchData.coordinates.y` | `plate_y` | Direct | Vertical location (unused) |
| `pitchData.coordinates.z` | `plate_z` | Direct | Vertical location |
| `pitchData.zone` | `plate_zone` | Direct | Strike zone zone |
| `pitchData.startSpeed` | `start_speed` | Direct | Initial velocity (mph) |
| `pitchData.endSpeed` | `end_speed` | Direct | Final velocity (mph) |
| `pitchData.extension` | `extension` | Direct | Release extension (ft) |
| `pitchData.breaks.spinRate` | `spin_rate` | Direct | RPM |
| `pitchData.breaks.breakAngle` | `break_angle` | Direct | Degrees |
| `pitchData.breaks.breakLength` | `break_length` | Direct | Feet |
| `pitchData.breaks.breakVertical` | `break_vertical` | Direct | Inches |
| `pitchData.breaks.breakHorizontal` | `break_horizontal` | Direct | Inches |
| `pitchData.coordinates.pfxX` | `pfx_x` | Direct | Horizontal movement |
| `pitchData.coordinates.pfxZ` | `pfx_z` | Direct | Vertical movement |
| `pitchData.plateTime` | `plate_time` | Direct | Time to plate (sec) |
| `count.balls` | `balls_before` | Direct | Count before pitch |
| `count.strikes` | `strikes_before` | Direct | Count before pitch |
| `count.outs` | `outs_before` | Direct | Outs before pitch |
| `about.inning` | `inning` | Direct | Inning number |
| `about.isTopInning` | `is_top_inning` | Direct | Top/bottom half |

## Data Quality & Completeness

### Coverage Statistics
- **Schedule Data**: 100% coverage for all requested dates
- **Live Feed Data**: Available for completed games (typically 1-2 weeks history)
- **Pitch Data**: Available since 2015 (Statcast implementation)
- **Weather Data**: Available for most games since 2017

### Data Quality Scoring
```python
def calculate_data_quality(feed: dict) -> float:
    """Calculate data quality score (0.0 to 1.0)"""
    score = 0.5  # Base score

    # Check for pitch data (major quality indicator)
    live_data = feed.get('liveData', {})
    plays = live_data.get('plays', {}).get('allPlays', [])
    has_pitch_data = any(
        play.get('playEvents', [])
        for play in plays
    )
    if has_pitch_data:
        score += 0.3

    # Check for weather data
    game_data = feed.get('gameData', {})
    has_weather = bool(game_data.get('weather', {}).get('temp'))
    if has_weather:
        score += 0.1

    # Check for complete game data
    linescore = live_data.get('linescore', {})
    has_linescore = bool(linescore.get('teams'))
    if has_linescore:
        score += 0.1

    return min(1.0, score)
```

### Known Data Gaps
- **Pre-2015**: No pitch-by-pitch data (Statcast not implemented)
- **Weather Data**: Sporadic before 2017
- **Historical API**: Limited to ~2 weeks of live feeds
- **Cancelled Games**: May have incomplete data

## Error Codes & Handling

### HTTP Status Codes
- **200**: Success
- **404**: Game not found (check gamePk validity)
- **429**: Rate limited (implement exponential backoff)
- **500**: Server error (retry with backoff)

### Data Validation Errors
- **Missing gamePk**: Invalid game identifier
- **Empty playEvents**: No pitch data available
- **Malformed JSON**: API response corruption
- **Missing timestamps**: Data freshness issues

## API Rate Limiting Strategy

### Request Patterns
- **Schedule calls**: 1 request/second (safe margin)
- **Live feed calls**: 2 requests/minute (30 requests/hour)
- **Error backoff**: 1s, 2s, 4s, 8s, 16s, 32s (exponential)
- **Daily limits**: ~3,600 schedule requests, ~720 live feed requests

### Optimization Techniques
- **Batch processing**: Download multiple dates in parallel
- **Skip existing**: Don't re-download known data
- **Cache static data**: Teams, players, venues change rarely
- **Resume capability**: Track progress and restart from interruptions

## Data Transformation Rules

### ID Mapping Priority
1. **Bridge table lookup**: MLB ID → Retrosheet ID
2. **Fallback creation**: `MLB{mlb_id}` format
3. **Validation**: Ensure referential integrity

### Date/Time Handling
- **Game dates**: Extract date portion, ignore time
- **Timestamps**: Store as UTC with timezone info
- **Season calculation**: Year from game date

### Count/State Tracking
- **Ball/strike counts**: Track per pitch within at-bat
- **Runner positions**: Bitmask encoding (1=1B, 2=2B, 4=3B)
- **Score tracking**: Before/after values for each event
- **Outs tracking**: Half-inning and full-inning counts

### Event Classification
- **Plate appearances**: At-bats + walks + hit-by-pitch + interference
- **At-bats**: Exclude walks, hit-by-pitch, sacrifices
- **Hits**: Single, double, triple, home run
- **Extra bases**: Double=1, triple=2, home run=3

This data dictionary serves as the authoritative reference for MLB API data ingestion and transformation in our historical baseball analytics pipeline.