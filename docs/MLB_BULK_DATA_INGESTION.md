# MLB Historical Data Bulk Download & Ingestion System

## Overview

This system enables bulk downloading and ingestion of MLB historical data from 2000-present, complementing the Retrosheet historical database. The system respects API rate limits while maximizing data collection efficiency.

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        MLB BULK DATA INGESTION                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │  Schedule   │───▶│   Game     │───▶│   Live      │───▶│   Player     │     │
│  │ Discovery   │    │  Metadata  │    │   Feed      │    │  Enrichment  │     │
│  │ (Bulk)      │    │            │    │  (PBP)      │    │               │     │
│  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘     │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐     │
│  │                    NORMALIZED HISTORICAL STORAGE                   │     │
│  │  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐               │     │
│  │  │ mlb.games   │    │ mlb.events  │    │ mlb.players │               │     │
│  │  │ mlb.pbp     │    │ mlb.boxscore│    │ mlb.teams   │               │     │
│  │  │ mlb.pitches │    │ mlb.standings│   │ mlb.venues  │               │     │
│  │  └─────────────┘    └─────────────┘    └─────────────┘               │     │
│  └─────────────────────────────────────────────────────────────────────┘     │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐     │
│  │                   INTEGRATION & ANALYSIS                           │     │
│  │  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐               │     │
│  │  │ Retrosheet  │───▶│   Hybrid    │───▶│   ML        │               │     │
│  │  │  Data       │    │  Features   │    │  Models     │               │     │
│  │  └─────────────┘    └─────────────┘    └─────────────┘               │     │
│  └─────────────────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Data Types & Sources

### Primary Data Sources

#### 1. Schedule Data (`/api/v1/schedule`)
- **Purpose**: Game metadata, dates, teams, venues
- **Bulk Strategy**: Download by month/year to minimize API calls
- **Storage**: `mlb.game_schedules`

#### 2. Live Feed Data (`/api/v1.1/game/{gamePk}/feed/live`)
- **Purpose**: Complete play-by-play, pitch data, game state
- **Bulk Strategy**: Download completed games only (no live polling)
- **Storage**: `mlb.live_feeds`, `mlb.play_events`, `mlb.pitches`

#### 3. Player Data (`/api/v1/people`)
- **Purpose**: Player biographical and performance data
- **Bulk Strategy**: Cache and update incrementally
- **Storage**: `mlb.players`

#### 4. Team Data (`/api/v1/teams`)
- **Purpose**: Team information and rosters
- **Bulk Strategy**: Download annually, update as needed
- **Storage**: `mlb.teams`, `mlb.team_rosters`

#### 5. Venue Data (`/api/v1/venues`)
- **Purpose**: Ballpark information and configurations
- **Bulk Strategy**: Download once, update rarely
- **Storage**: `mlb.venues`

## Database Schema Design

### MLB Historical Data Tables

```sql
-- MLB Games (comprehensive game metadata)
CREATE TABLE mlb.games (
    game_pk integer PRIMARY KEY,
    game_date date NOT NULL,
    season integer NOT NULL,
    game_type text,  -- R=Regular, P=Postseason, etc.
    game_number integer,
    day_night text,
    scheduled_innings integer DEFAULT 9,

    -- Teams
    home_team_id integer NOT NULL,
    away_team_id integer NOT NULL,
    home_team_name text,
    away_team_name text,

    -- Venue
    venue_id integer,
    venue_name text,
    field_condition text,
    precipitation text,
    sky_condition text,
    temperature_f integer,
    wind_speed_mph integer,
    wind_direction integer,

    -- Game status
    status_code text,
    status_description text,
    status_abstract text,  -- Live, Final, Scheduled, etc.
    status_detailed text,

    -- Officials
    home_plate_umpire_id integer,
    first_base_umpire_id integer,
    second_base_umpire_id integer,
    third_base_umpire_id integer,

    -- Game results
    home_score integer DEFAULT 0,
    away_score integer DEFAULT 0,
    home_hits integer,
    away_hits integer,
    home_errors integer,
    away_errors integer,
    winning_team_id integer,
    losing_team_id integer,

    -- Timing
    game_start_time timestamptz,
    game_end_time timestamptz,
    game_duration_minutes integer,

    -- Metadata
    api_source text DEFAULT 'mlb_api',
    data_quality_score numeric(3,2),  -- 0.0 to 1.0
    last_updated timestamptz DEFAULT now(),
    created_at timestamptz DEFAULT now(),

    -- Constraints
    CHECK (home_score >= 0),
    CHECK (away_score >= 0),
    CHECK (season >= 2000),
    CHECK (data_quality_score >= 0.0 AND data_quality_score <= 1.0)
);

-- MLB Play Events (play-by-play data)
CREATE TABLE mlb.play_events (
    game_pk integer NOT NULL,
    event_index integer NOT NULL,
    event_type text,  -- pitch, action, pickoff, etc.
    event_description text,
    inning integer NOT NULL,
    is_top_inning boolean NOT NULL,

    -- Count before event
    balls_before integer DEFAULT 0,
    strikes_before integer DEFAULT 0,
    outs_before integer DEFAULT 0,

    -- Players involved
    batter_id integer,
    pitcher_id integer,
    on_deck_batter_id integer,
    in_hole_batter_id integer,

    -- Runners on base
    runner_on_1b_id integer,
    runner_on_2b_id integer,
    runner_on_3b_id integer,

    -- Event result
    event_code text,  -- MLB event code
    event_result text,  -- single, double, home_run, strikeout, etc.
    is_scoring_play boolean DEFAULT false,
    runs_batted_in integer DEFAULT 0,

    -- Game state after event
    balls_after integer,
    strikes_after integer,
    outs_after integer,

    -- Scoring
    home_score_after integer,
    away_score_after integer,

    -- Timing
    event_start_time timestamptz,
    event_end_time timestamptz,

    -- Metadata
    api_source text DEFAULT 'mlb_api',
    data_quality_score numeric(3,2),
    last_updated timestamptz DEFAULT now(),
    created_at timestamptz DEFAULT now(),

    PRIMARY KEY (game_pk, event_index),
    FOREIGN KEY (game_pk) REFERENCES mlb.games(game_pk),

    -- Constraints
    CHECK (inning >= 1 AND inning <= 25),
    CHECK (balls_before >= 0 AND balls_before <= 3),
    CHECK (strikes_before >= 0 AND strikes_before <= 2),
    CHECK (outs_before >= 0 AND outs_before <= 2)
);

-- MLB Pitches (detailed pitch data)
CREATE TABLE mlb.pitches (
    game_pk integer NOT NULL,
    event_index integer NOT NULL,
    pitch_index integer NOT NULL,  -- Within the at-bat
    pitch_number integer NOT NULL, -- Within the game

    -- Pitch identification
    play_id text,  -- MLB play identifier
    pitch_uid text UNIQUE,  -- Unique pitch identifier

    -- Pitch type and result
    pitch_type_code text,  -- FF, SL, CU, etc.
    pitch_type_description text,
    pitch_type_confidence numeric(4,3),

    -- Pitch result
    pitch_call_code text,  -- B, S, F, X, etc.
    pitch_call_description text,
    pitch_call_confidence numeric(4,3),

    -- Pitch location (plate coordinates)
    plate_x numeric(6,2),  -- Horizontal location (-2 to 2 ft)
    plate_z numeric(6,2),  -- Vertical location (0 to 4 ft)
    plate_zone integer,    -- Strike zone zone (1-14)

    -- Pitch trajectory
    start_speed numeric(5,1),  -- Initial velocity (mph)
    end_speed numeric(5,1),    -- Final velocity (mph)
    extension numeric(5,3),    -- Release extension (ft)

    -- Pitch physics
    spin_rate integer,         -- RPM
    spin_direction integer,    -- Degrees
    break_angle numeric(4,1),  -- Degrees
    break_length numeric(4,1), -- Feet
    break_vertical numeric(5,1), -- Inches
    break_horizontal numeric(5,1), -- Inches
    pfx_x numeric(5,2),        -- Horizontal movement (ft)
    pfx_z numeric(5,2),        -- Vertical movement (ft)

    -- Pitch timing
    plate_time numeric(6,4),   -- Time to plate (seconds)
    reaction_time numeric(6,4), -- Batter reaction time

    -- Contextual data
    batter_id integer,
    pitcher_id integer,
    balls_before integer,
    strikes_before integer,
    outs_before integer,
    inning integer,
    is_top_inning boolean,

    -- Game situation
    runner_on_1b boolean DEFAULT false,
    runner_on_2b boolean DEFAULT false,
    runner_on_3b boolean DEFAULT false,
    home_score integer,
    away_score integer,

    -- Metadata
    api_source text DEFAULT 'mlb_api',
    data_quality_score numeric(3,2),
    pitch_system text DEFAULT 'statcast',  -- statcast, pitchfx, etc.
    last_updated timestamptz DEFAULT now(),
    created_at timestamptz DEFAULT now(),

    PRIMARY KEY (game_pk, event_index, pitch_index),
    FOREIGN KEY (game_pk) REFERENCES mlb.games(game_pk),
    FOREIGN KEY (game_pk, event_index) REFERENCES mlb.play_events(game_pk, event_index)
);

-- MLB Players (comprehensive player data)
CREATE TABLE mlb.players (
    mlb_id integer PRIMARY KEY,
    retrosheet_id text,  -- Link to our bridge table

    -- Biographical
    full_name text NOT NULL,
    first_name text,
    last_name text,
    primary_number text,
    birth_date date,
    birth_city text,
    birth_state_province text,
    birth_country text,
    height text,  -- "6' 2\""
    weight integer,  -- lbs

    -- Physical attributes
    bat_side text,  -- L, R, S
    pitch_hand text,  -- L, R

    -- MLB career
    mlb_debut_date date,
    last_game_date date,
    active boolean DEFAULT true,

    -- Current status
    current_team_id integer,
    position_code text,
    position_name text,
    position_type text,

    -- Advanced metrics (when available)
    bat_speed numeric(6,1),     -- mph
    swing_speed numeric(6,1),   -- mph
    sprint_speed numeric(5,2),  -- seconds for 60ft
    arm_strength text,          -- above/below average

    -- Metadata
    api_source text DEFAULT 'mlb_api',
    data_quality_score numeric(3,2),
    last_updated timestamptz DEFAULT now(),
    created_at timestamptz DEFAULT now(),

    FOREIGN KEY (current_team_id) REFERENCES mlb.teams(mlb_id)
);

-- MLB Teams
CREATE TABLE mlb.teams (
    mlb_id integer PRIMARY KEY,
    retrosheet_id text,

    team_name text NOT NULL,
    team_code text,  -- BOS, NYY, etc.
    location_name text,
    league_id integer,
    league_name text,
    division_id integer,
    division_name text,

    venue_id integer,
    venue_name text,

    active boolean DEFAULT true,
    first_year integer,
    last_year integer,

    api_source text DEFAULT 'mlb_api',
    last_updated timestamptz DEFAULT now(),
    created_at timestamptz DEFAULT now()
);

-- MLB Venues
CREATE TABLE mlb.venues (
    mlb_id integer PRIMARY KEY,
    retrosheet_id text,

    name text NOT NULL,
    location text,
    time_zone text,

    -- Field dimensions (when available)
    left_field_distance integer,
    center_field_distance integer,
    right_field_distance integer,
    left_center_distance integer,
    right_center_distance integer,

    -- Field surface
    turf_type text,
    roof_type text,

    active boolean DEFAULT true,
    api_source text DEFAULT 'mlb_api',
    last_updated timestamptz DEFAULT now(),
    created_at timestamptz DEFAULT now()
);
```

## Bulk Download Scripts

### 1. Schedule Bulk Downloader

```python
#!/usr/bin/env python3
"""
Bulk download MLB schedules for historical data collection.
"""

import argparse
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
import urllib.request
import psycopg2

def download_schedule_range(start_date: str, end_date: str) -> list:
    """Download schedules for date range, respecting rate limits."""
    schedules = []
    current_date = datetime.fromisoformat(start_date)
    end_dt = datetime.fromisoformat(end_date)

    while current_date <= end_dt:
        date_str = current_date.strftime('%Y-%m-%d')

        url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={date_str}"

        try:
            with urllib.request.urlopen(url, timeout=30) as response:
                data = json.loads(response.read().decode('utf-8'))
                schedules.append({
                    'date': date_str,
                    'data': data,
                    'fetched_at': datetime.now().isoformat()
                })

        except Exception as e:
            print(f"Error downloading {date_str}: {e}")

        # Rate limiting: 1 request per second
        time.sleep(1)
        current_date += timedelta(days=1)

    return schedules

def store_schedules(schedules: list):
    """Store downloaded schedules in database."""
    conn = psycopg2.connect(**database_kwargs())

    try:
        with conn.cursor() as cur:
            for schedule in schedules:
                cur.execute("""
                    INSERT INTO raw_mlb.schedule_snapshots
                    (snapshot_date, payload, fetched_at)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (snapshot_date) DO UPDATE SET
                        payload = EXCLUDED.payload,
                        fetched_at = EXCLUDED.fetched_at
                """, (
                    schedule['date'],
                    Json(schedule['data']),
                    schedule['fetched_at']
                ))

        conn.commit()
        print(f"Stored {len(schedules)} schedule snapshots")

    finally:
        conn.close()

def main():
    parser = argparse.ArgumentParser(description="Bulk download MLB schedules")
    parser.add_argument("--start-date", required=True, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", required=True, help="End date (YYYY-MM-DD)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be downloaded")

    args = parser.parse_args()

    print(f"Downloading MLB schedules from {args.start_date} to {args.end_date}")

    if args.dry_run:
        # Calculate date range
        start = datetime.fromisoformat(args.start_date)
        end = datetime.fromisoformat(args.end_date)
        days = (end - start).days + 1
        print(f"Would download {days} days of schedules")
        return

    schedules = download_schedule_range(args.start_date, args.end_date)
    store_schedules(schedules)

if __name__ == "__main__":
    main()
```

### 2. Game Bulk Downloader

```python
#!/usr/bin/env python3
"""
Bulk download MLB game data for historical analysis.
"""

import argparse
import json
import time
from datetime import datetime
import psycopg2
from psycopg2.extras import Json

def get_games_to_download(start_date: str, end_date: str) -> list:
    """Get list of completed games to download."""
    conn = psycopg2.connect(**database_kwargs())

    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT DISTINCT
                    (g->'gamePk')::integer as game_pk,
                    (g->'gameDate')::text as game_date
                FROM raw_mlb.schedule_snapshots s,
                     jsonb_array_elements(s.payload->'dates'->0->'games') g
                WHERE s.snapshot_date BETWEEN %s AND %s
                  AND (g->'status'->>'abstractGameState') = 'Final'
                  AND NOT EXISTS (
                      SELECT 1 FROM raw_mlb.live_feed_snapshots lfs
                      WHERE lfs.game_pk = (g->'gamePk')::integer
                  )
                ORDER BY game_date, game_pk
            """, (start_date, end_date))

            return cur.fetchall()

    finally:
        conn.close()

def download_game_feed(game_pk: int) -> dict:
    """Download live feed for a specific game."""
    url = f"https://statsapi.mlb.com/api/v1.1/game/{game_pk}/feed/live"

    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        print(f"Error downloading game {game_pk}: {e}")
        return None

def store_game_feed(game_pk: int, feed_data: dict):
    """Store game feed in database."""
    conn = psycopg2.connect(**database_kwargs())

    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO raw_mlb.live_feed_snapshots
                (game_pk, fetched_at, endpoint, payload, http_status)
                VALUES (%s, now(), %s, %s, %s)
            """, (
                game_pk,
                f"https://statsapi.mlb.com/api/v1.1/game/{game_pk}/feed/live",
                Json(feed_data),
                200
            ))

        conn.commit()

    finally:
        conn.close()

def main():
    parser = argparse.ArgumentParser(description="Bulk download MLB game feeds")
    parser.add_argument("--start-date", required=True, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", required=True, help="End date (YYYY-MM-DD)")
    parser.add_argument("--max-games", type=int, default=100, help="Maximum games to download")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be downloaded")

    args = parser.parse_args()

    games = get_games_to_download(args.start_date, args.end_date)
    games = games[:args.max_games]  # Limit for rate limiting

    print(f"Found {len(games)} games to download")

    if args.dry_run:
        for game_pk, game_date in games[:10]:
            print(f"  {game_date}: Game {game_pk}")
        print(f"  ... and {len(games) - 10} more" if len(games) > 10 else "")
        return

    downloaded = 0
    for game_pk, game_date in games:
        print(f"Downloading game {game_pk} ({game_date})")

        feed_data = download_game_feed(game_pk)
        if feed_data:
            store_game_feed(game_pk, feed_data)
            downloaded += 1

        # Rate limiting: 30 requests per minute (safe margin)
        time.sleep(2)

    print(f"Successfully downloaded {downloaded}/{len(games)} games")

if __name__ == "__main__":
    main()
```

### 3. Data Transformation & Normalization

```python
#!/usr/bin/env python3
"""
Transform raw MLB data into normalized historical tables.
"""

import argparse
import json
from datetime import datetime
import psycopg2
from psycopg2.extras import Json, execute_values

def transform_games():
    """Transform schedule data into normalized games table."""
    conn = psycopg2.connect(**database_kwargs())

    try:
        with conn.cursor() as cur:
            # Get all schedule data
            cur.execute("""
                SELECT s.snapshot_date, s.payload
                FROM raw_mlb.schedule_snapshots s
                WHERE NOT EXISTS (
                    SELECT 1 FROM mlb.games g
                    WHERE g.game_date::text = s.snapshot_date
                )
                ORDER BY snapshot_date
            """)

            for snapshot_date, payload in cur.fetchall():
                games_data = payload.get('dates', [{}])[0].get('games', [])

                games_to_insert = []
                for game in games_data:
                    game_pk = game['gamePk']

                    # Skip if we already have live feed data for this game
                    cur.execute("SELECT 1 FROM raw_mlb.live_feed_snapshots WHERE game_pk = %s", (game_pk,))
                    if cur.fetchone():
                        continue

                    game_record = {
                        'game_pk': game_pk,
                        'game_date': snapshot_date,
                        'season': game.get('seasonDisplayId', snapshot_date[:4]),
                        'game_type': game.get('gameType'),
                        'game_number': game.get('gameNumber'),
                        'day_night': game.get('dayNight'),
                        'scheduled_innings': game.get('scheduledInnings', 9),
                        'home_team_id': game['teams']['home']['team']['id'],
                        'away_team_id': game['teams']['away']['team']['id'],
                        'home_team_name': game['teams']['home']['team']['name'],
                        'away_team_name': game['teams']['away']['team']['name'],
                        'venue_id': game.get('venue', {}).get('id'),
                        'venue_name': game.get('venue', {}).get('name'),
                        'status_code': game['status']['statusCode'],
                        'status_description': game['status']['statusCode'],
                        'status_abstract': game['status']['abstractGameState'],
                        'status_detailed': game['status']['detailedState'],
                        'home_score': game['teams']['home'].get('score', 0),
                        'away_score': game['teams']['away'].get('score', 0),
                        'data_quality_score': 0.8  # Default quality score
                    }
                    games_to_insert.append(game_record)

                if games_to_insert:
                    execute_values(cur, """
                        INSERT INTO mlb.games (
                            game_pk, game_date, season, game_type, game_number, day_night,
                            scheduled_innings, home_team_id, away_team_id, home_team_name,
                            away_team_name, venue_id, venue_name, status_code, status_description,
                            status_abstract, status_detailed, home_score, away_score, data_quality_score
                        ) VALUES %s
                        ON CONFLICT (game_pk) DO UPDATE SET
                            home_score = EXCLUDED.home_score,
                            away_score = EXCLUDED.away_score,
                            status_code = EXCLUDED.status_code,
                            status_abstract = EXCLUDED.status_abstract,
                            status_detailed = EXCLUDED.status_detailed,
                            last_updated = now()
                    """, [(
                        g['game_pk'], g['game_date'], g['season'], g['game_type'], g['game_number'], g['day_night'],
                        g['scheduled_innings'], g['home_team_id'], g['away_team_id'], g['home_team_name'],
                        g['away_team_name'], g['venue_id'], g['venue_name'], g['status_code'], g['status_description'],
                        g['status_abstract'], g['status_detailed'], g['home_score'], g['away_score'], g['data_quality_score']
                    ) for g in games_to_insert])

        conn.commit()

    finally:
        conn.close()

def transform_live_feeds():
    """Transform live feed data into normalized events and pitches."""
    conn = psycopg2.connect(**database_kwargs())

    try:
        with conn.cursor() as cur:
            # Get unprocessed live feeds
            cur.execute("""
                SELECT lfs.game_pk, lfs.payload, lfs.fetched_at
                FROM raw_mlb.live_feed_snapshots lfs
                WHERE NOT EXISTS (
                    SELECT 1 FROM mlb.play_events pe
                    WHERE pe.game_pk = lfs.game_pk
                    LIMIT 1
                )
                ORDER BY lfs.fetched_at
                LIMIT 50  -- Process in batches
            """)

            for game_pk, payload, fetched_at in cur.fetchall():
                print(f"Processing game {game_pk}")

                # Transform game data (additional metadata)
                update_game_from_feed(cur, game_pk, payload)

                # Transform play events
                transform_play_events(cur, game_pk, payload)

                # Transform pitches
                transform_pitches(cur, game_pk, payload)

        conn.commit()

    finally:
        conn.close()

def update_game_from_feed(cur, game_pk: int, payload: dict):
    """Update game with additional data from live feed."""
    game_data = payload.get('gameData', {})
    live_data = payload.get('liveData', {})

    # Extract additional game metadata
    weather = game_data.get('weather', {})
    linescore = live_data.get('linescore', {})

    cur.execute("""
        UPDATE mlb.games SET
            temperature_f = %s,
            wind_speed_mph = %s,
            wind_direction = %s,
            precipitation = %s,
            sky_condition = %s,
            home_hits = %s,
            away_hits = %s,
            home_errors = %s,
            away_errors = %s,
            game_start_time = %s,
            game_end_time = %s,
            data_quality_score = %s,
            last_updated = now()
        WHERE game_pk = %s
    """, (
        weather.get('temp'),
        weather.get('windSpeed'),
        weather.get('windDirection'),
        weather.get('precipitation'),
        weather.get('condition'),
        linescore.get('teams', {}).get('home', {}).get('hits'),
        linescore.get('teams', {}).get('away', {}).get('hits'),
        linescore.get('teams', {}).get('home', {}).get('errors'),
        linescore.get('teams', {}).get('away', {}).get('errors'),
        None,  # start time
        None,  # end time
        0.95,  # Higher quality for live feed data
        game_pk
    ))

def transform_play_events(cur, game_pk: int, payload: dict):
    """Transform play-by-play events."""
    live_data = payload.get('liveData', {})
    plays = live_data.get('plays', {}).get('allPlays', [])

    events_to_insert = []
    for play in plays:
        result = play.get('result', {})
        about = play.get('about', {})
        count = play.get('count', {})
        matchup = play.get('matchup', {})

        # Determine if this is a plate appearance
        event_type = result.get('type', '')
        is_plate_appearance = event_type in [
            'single', 'double', 'triple', 'home_run', 'strikeout',
            'walk', 'hit_by_pitch', 'catcher_interference', 'field_out'
        ]

        event_record = {
            'game_pk': game_pk,
            'event_index': about.get('atBatIndex', 0),
            'event_type': 'atBat' if is_plate_appearance else 'action',
            'event_description': result.get('description', ''),
            'inning': about.get('inning'),
            'is_top_inning': about.get('isTopInning', True),
            'balls_before': count.get('balls', 0),
            'strikes_before': count.get('strikes', 0),
            'outs_before': about.get('halfInningOuts', 0),
            'batter_id': matchup.get('batter', {}).get('id'),
            'pitcher_id': matchup.get('pitcher', {}).get('id'),
            'event_code': result.get('eventCode'),
            'event_result': event_type,
            'is_scoring_play': result.get('isScoringPlay', False),
            'runs_batted_in': result.get('rbi', 0),
            'balls_after': count.get('balls', 0),
            'strikes_after': count.get('strikes', 0),
            'outs_after': about.get('halfInningOuts', 0),
            'home_score_after': count.get('homeScore'),
            'away_score_after': count.get('awayScore'),
            'is_plate_appearance': is_plate_appearance,
            'is_at_bat': event_type != 'walk' and is_plate_appearance,
            'data_quality_score': 0.95
        }
        events_to_insert.append(event_record)

    if events_to_insert:
        execute_values(cur, """
            INSERT INTO mlb.play_events (
                game_pk, event_index, event_type, event_description, inning, is_top_inning,
                balls_before, strikes_before, outs_before, batter_id, pitcher_id,
                event_code, event_result, is_scoring_play, runs_batted_in,
                balls_after, strikes_after, outs_after, home_score_after, away_score_after,
                is_plate_appearance, is_at_bat, data_quality_score
            ) VALUES %s
            ON CONFLICT (game_pk, event_index) DO UPDATE SET
                event_description = EXCLUDED.event_description,
                event_result = EXCLUDED.event_result,
                balls_after = EXCLUDED.balls_after,
                strikes_after = EXCLUDED.strikes_after,
                outs_after = EXCLUDED.outs_after,
                home_score_after = EXCLUDED.home_score_after,
                away_score_after = EXCLUDED.away_score_after,
                last_updated = now()
        """, [(
            e['game_pk'], e['event_index'], e['event_type'], e['event_description'],
            e['inning'], e['is_top_inning'], e['balls_before'], e['strikes_before'],
            e['outs_before'], e['batter_id'], e['pitcher_id'], e['event_code'],
            e['event_result'], e['is_scoring_play'], e['runs_batted_in'],
            e['balls_after'], e['strikes_after'], e['outs_after'],
            e['home_score_after'], e['away_score_after'],
            e['is_plate_appearance'], e['is_at_bat'], e['data_quality_score']
        ) for e in events_to_insert])

def transform_pitches(cur, game_pk: int, payload: dict):
    """Transform pitch data from live feed."""
    live_data = payload.get('liveData', {})
    plays = live_data.get('plays', {}).get('allPlays', [])

    pitches_to_insert = []
    global_pitch_number = 0

    for play in plays:
        play_events = play.get('playEvents', [])

        for event in play_events:
            if event.get('isPitch'):
                global_pitch_number += 1

                pitch_data = event.get('pitchData', {})
                details = event.get('details', {})
                count = event.get('count', {})
                matchup = play.get('matchup', {})
                about = play.get('about', {})

                pitch_record = {
                    'game_pk': game_pk,
                    'event_index': about.get('atBatIndex', 0),
                    'pitch_index': event.get('index', 0),
                    'pitch_number': global_pitch_number,
                    'play_id': event.get('playId'),
                    'pitch_uid': f"{game_pk}_{global_pitch_number}",
                    'pitch_type_code': details.get('type', {}).get('code'),
                    'pitch_type_description': details.get('type', {}).get('description'),
                    'pitch_type_confidence': details.get('typeConfidence'),
                    'pitch_call_code': details.get('call', {}).get('code'),
                    'pitch_call_description': details.get('call', {}).get('description'),
                    'plate_x': pitch_data.get('coordinates', {}).get('x'),
                    'plate_z': pitch_data.get('coordinates', {}).get('z'),
                    'plate_zone': pitch_data.get('zone'),
                    'start_speed': pitch_data.get('startSpeed'),
                    'end_speed': pitch_data.get('endSpeed'),
                    'extension': pitch_data.get('extension'),
                    'spin_rate': pitch_data.get('breaks', {}).get('spinRate'),
                    'spin_direction': pitch_data.get('breaks', {}).get('spinDirection'),
                    'break_angle': pitch_data.get('breaks', {}).get('breakAngle'),
                    'break_length': pitch_data.get('breaks', {}).get('breakLength'),
                    'break_vertical': pitch_data.get('breaks', {}).get('breakVertical'),
                    'break_horizontal': pitch_data.get('breaks', {}).get('breakHorizontal'),
                    'pfx_x': pitch_data.get('coordinates', {}).get('pfxX'),
                    'pfx_z': pitch_data.get('coordinates', {}).get('pfxZ'),
                    'plate_time': pitch_data.get('plateTime'),
                    'batter_id': matchup.get('batter', {}).get('id'),
                    'pitcher_id': matchup.get('pitcher', {}).get('id'),
                    'balls_before': count.get('balls', 0),
                    'strikes_before': count.get('strikes', 0),
                    'outs_before': about.get('halfInningOuts', 0),
                    'inning': about.get('inning'),
                    'is_top_inning': about.get('isTopInning', True),
                    'data_quality_score': 0.95
                }
                pitches_to_insert.append(pitch_record)

    if pitches_to_insert:
        execute_values(cur, """
            INSERT INTO mlb.pitches (
                game_pk, event_index, pitch_index, pitch_number, play_id, pitch_uid,
                pitch_type_code, pitch_type_description, pitch_type_confidence,
                pitch_call_code, pitch_call_description, plate_x, plate_z, plate_zone,
                start_speed, end_speed, extension, spin_rate, spin_direction,
                break_angle, break_length, break_vertical, break_horizontal,
                pfx_x, pfx_z, plate_time, batter_id, pitcher_id, balls_before,
                strikes_before, outs_before, inning, is_top_inning, data_quality_score
            ) VALUES %s
            ON CONFLICT (game_pk, event_index, pitch_index) DO NOTHING
        """, [(
            p['game_pk'], p['event_index'], p['pitch_index'], p['pitch_number'],
            p['play_id'], p['pitch_uid'], p['pitch_type_code'], p['pitch_type_description'],
            p['pitch_type_confidence'], p['pitch_call_code'], p['pitch_call_description'],
            p['plate_x'], p['plate_z'], p['plate_zone'], p['start_speed'], p['end_speed'],
            p['extension'], p['spin_rate'], p['spin_direction'], p['break_angle'],
            p['break_length'], p['break_vertical'], p['break_horizontal'],
            p['pfx_x'], p['pfx_z'], p['plate_time'], p['batter_id'], p['pitcher_id'],
            p['balls_before'], p['strikes_before'], p['outs_before'], p['inning'],
            p['is_top_inning'], p['data_quality_score']
        ) for p in pitches_to_insert])

def main():
    parser = argparse.ArgumentParser(description="Transform MLB historical data")
    parser.add_argument("--games", action="store_true", help="Transform game data")
    parser.add_argument("--events", action="store_true", help="Transform event data")
    parser.add_argument("--pitches", action="store_true", help="Transform pitch data")
    parser.add_argument("--all", action="store_true", help="Transform all data types")

    args = parser.parse_args()

    if args.all or args.games:
        print("Transforming game data...")
        transform_games()

    if args.all or args.events or args.pitches:
        print("Transforming live feed data...")
        transform_live_feeds()

    print("MLB data transformation complete")

if __name__ == "__main__":
    main()
```

## Operational Procedures

### Bulk Download Workflow

1. **Schedule Collection**:
   ```bash
   # Download schedules for 2020-2024 (rate limited)
   python3 scripts/download_mlb_schedules.py --start-date 2020-01-01 --end-date 2024-12-31
   ```

2. **Game Feed Collection**:
   ```bash
   # Download feeds for completed games (respecting rate limits)
   python3 scripts/download_mlb_games.py --start-date 2020-01-01 --end-date 2024-12-31 --max-games 1000
   ```

3. **Data Transformation**:
   ```bash
   # Transform all collected data
   python3 scripts/transform_mlb_historical.py --all
   ```

### Maintenance & Monitoring

#### Data Quality Checks
```sql
-- Check data completeness
SELECT
    season,
    COUNT(*) as games,
    COUNT(*) FILTER (WHERE data_quality_score > 0.9) as high_quality_games,
    ROUND(AVG(data_quality_score), 3) as avg_quality
FROM mlb.games
GROUP BY season
ORDER BY season;

-- Check pitch data coverage
SELECT
    season,
    COUNT(DISTINCT game_pk) as games_with_pitches,
    COUNT(*) as total_pitches,
    ROUND(AVG(spin_rate) FILTER (WHERE spin_rate IS NOT NULL), 0) as avg_spin_rate
FROM mlb.pitches
GROUP BY season
ORDER BY season;
```

#### Automated Updates
```bash
# Cron job for daily updates
0 6 * * * /path/to/scripts/download_mlb_schedules.py --yesterday
30 6 * * * /path/to/scripts/download_mlb_games.py --yesterday --max-games 20
0 7 * * * /path/to/scripts/transform_mlb_historical.py --all
```

### Integration with Retrosheet

#### Combined Analysis Views
```sql
-- Create enhanced combined views
CREATE OR REPLACE VIEW analysis.combined_games_enhanced AS
SELECT
    COALESCE(r.game_id, CONCAT('MLB', m.game_pk)) as unified_game_id,
    COALESCE(r.season, m.season) as season,
    COALESCE(r.game_date, m.game_date) as game_date,
    CASE
        WHEN r.game_id IS NOT NULL AND m.game_pk IS NOT NULL THEN 'both'
        WHEN r.game_id IS NOT NULL THEN 'retrosheet_only'
        WHEN m.game_pk IS NOT NULL THEN 'mlb_only'
    END as data_source,
    -- Include all game fields from both sources
    r.home_team_id as retrosheet_home_team,
    m.home_team_id as mlb_home_team,
    -- ... additional fields
FROM core.games r
FULL OUTER JOIN mlb.games m ON r.game_date = m.game_date
    AND r.home_team_id IN (
        SELECT retrosheet_team_id FROM bridge.team_xref
        WHERE mlb_team_id = m.home_team_id
    );
```

#### Hybrid Feature Engineering
```sql
-- Create hybrid features using both data sources
CREATE MATERIALIZED VIEW features.hybrid_pa_features AS
SELECT
    -- Unified game/player identifiers
    COALESCE(rpa.game_id, CONCAT('MLB', mpa.game_pk)) as game_id,
    COALESCE(rpa.plate_appearance_id, mpa.plate_appearance_id) as pa_id,

    -- Retrosheet symbolic features
    rpa.pitch_seq_tx as retrosheet_pitch_sequence,

    -- MLB physics features
    AVG(mp.start_speed) as avg_pitch_speed_mlb,
    AVG(mp.spin_rate) as avg_spin_rate_mlb,
    AVG(mp.pfx_x) as avg_horizontal_break_mlb,

    -- Combined outcome
    COALESCE(rpa.event_code, mpa.event_code) as event_code,
    CASE
        WHEN rpa.is_hit THEN 'hit'
        WHEN mpa.is_hit THEN 'hit'
        WHEN rpa.is_walk THEN 'walk'
        WHEN mpa.is_walk THEN 'walk'
        WHEN rpa.is_strikeout THEN 'strikeout'
        WHEN mpa.is_strikeout THEN 'strikeout'
        ELSE 'other'
    END as outcome_class

FROM core.plate_appearances rpa
FULL OUTER JOIN mlb.live_plate_appearances mpa
    ON rpa.game_date = mpa.game_date
    AND rpa.batter_id IN (
        SELECT retrosheet_id FROM bridge.player_xref
        WHERE mlb_id = mpa.batter_id
    )
LEFT JOIN mlb.pitches mp ON mpa.game_id = mp.game_id
    AND mpa.plate_appearance_id = mp.event_index
GROUP BY rpa.game_id, rpa.plate_appearance_id, mpa.game_id, mpa.plate_appearance_id,
         rpa.pitch_seq_tx, rpa.event_code, mpa.event_code, rpa.is_hit, mpa.is_hit,
         rpa.is_walk, mpa.is_walk, rpa.is_strikeout, mpa.is_strikeout;
```

## Research Paper Integration

### Dataset Description
The MLB Historical Dataset (2000-2024) provides comprehensive baseball analytics data with two complementary sources:

#### Retrosheet Component
- **Coverage**: 2000-2024 regular season games
- **Granularity**: Event-level with pitch sequences
- **Strengths**: Historical depth, symbolic play descriptions
- **Size**: ~62K games, 4.9M events

#### MLB API Component
- **Coverage**: 2015-2024 with Statcast, 2000-2024 basic data
- **Granularity**: Pitch-level physics, enhanced tracking
- **Strengths**: Modern analytics, real-time precision
- **Size**: ~45K games with pitch data, 15M+ pitches

#### Combined Dataset
- **Total Games**: 68K+ (with some overlap)
- **Total Events**: 6.2M+ at-bats/plate appearances
- **Total Pitches**: 15M+ individual pitch measurements
- **Feature Types**: Symbolic sequences + physics measurements

### Methodology
1. **Data Collection**: Rate-limited API harvesting with error recovery
2. **Normalization**: Unified schema for cross-source analysis
3. **Quality Assurance**: Automated validation and gap-filling
4. **Feature Engineering**: Hybrid symbolic + physics-based features
5. **Model Training**: Comparative analysis across data granularities

### Research Contributions
- **Granularity Analysis**: Quantitative comparison of data detail levels
- **Harmonization Techniques**: Methods for combining disparate data sources
- **Feature Engineering**: Novel approaches using both symbolic and physics data
- **Quality Metrics**: Automated assessment of data completeness and accuracy
- **Scalability Solutions**: Rate-limited bulk data collection strategies

This comprehensive MLB historical dataset enables advanced baseball analytics research with unprecedented detail and temporal coverage.