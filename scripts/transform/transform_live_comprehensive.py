#!/usr/bin/env python3
"""
Enhanced MLB Live Data Transformation - Create Retrosheet-Compatible Tables

This script transforms MLB live feed snapshots into tables that mirror the
complete Retrosheet core schema, enabling seamless analysis and modeling.

Creates:
- core.live_games (extended with all Retrosheet fields)
- core.live_events (extended with all Retrosheet fields)
- core.live_plate_appearances (complete PA records)
"""

from __future__ import annotations

import argparse
import os
from collections import defaultdict
from dataclasses import dataclass

import psycopg2
from psycopg2.extras import Json, execute_values


def database_kwargs() -> dict[str, str]:
    return {
        'host': os.environ.get('PGHOST', 'localhost'),
        'port': os.environ.get('PGPORT', '5432'),
        'dbname': os.environ.get('PGDATABASE', 'retrosheet'),
        'user': os.environ.get('PGUSER', 'postgres'),
        'password': os.environ.get('PGPASSWORD', ''),
    }


@dataclass
class LiveGame:
    """Complete game data matching core.games schema."""

    game_id: str
    season: int
    game_date: str
    away_team_id: str
    home_team_id: str
    away_score: int = 0
    home_score: int = 0
    home_team_name: str = None
    away_team_name: str = None
    game_number: int = None
    day_of_week: str = None
    start_time: str = None
    doubleheader_flag: str = None
    day_night: str = None
    park_id: str = None
    away_starting_pitcher_id: str = None
    home_starting_pitcher_id: str = None
    attendance: int = None
    temperature_f: int = None
    wind_direction: str = None
    wind_speed_mph: int = None
    field_condition: str = None
    precipitation: str = None
    sky_condition: str = None
    duration_minutes: int = None
    innings: int = None
    away_hits: int = None
    home_hits: int = None
    away_errors: int = None
    home_errors: int = None
    away_lob: int = None
    home_lob: int = None
    winning_team_id: str = None
    home_win: bool = None
    win_pitcher_id: str = None
    loss_pitcher_id: str = None
    save_pitcher_id: str = None
    source_type: str = 'mlb_live'
    mlb_game_pk: int = None
    snapshot_id: int = None
    snapshot_fetched_at: str = None
    status_code: str = None
    detailed_state: str = None
    venue_name: str = None
    raw_payload: dict = None


@dataclass
class LiveEvent:
    """Complete event data matching core.events schema."""

    game_id: str
    event_id: int
    season: int
    event_sequence: int
    inning: int
    is_bottom_inning: bool
    outs_before: int
    away_score_before: int
    home_score_before: int
    batter_id: str
    batter_hand: str
    pitcher_id: str
    pitcher_hand: str
    event_code: int
    event_text: str
    is_plate_appearance: bool
    is_at_bat: bool
    source_type: str = 'mlb_live'
    balls: int = None
    strikes: int = None
    batting_team_id: str = None
    fielding_team_id: str = None
    hit_value: int = 0
    is_hit: bool = False
    is_walk: bool = False
    is_strikeout: bool = False
    is_home_run: bool = False
    outs_on_play: int = 0
    runs_on_play: int = 0
    rbi: int = 0
    start_bases: int = 0
    end_bases: int = 0
    away_score_after: int = None
    home_score_after: int = None
    game_pa_count: int = None
    half_inning_pa_count: int = None
    is_new_plate_appearance: bool = True
    is_inning_start: bool = False
    is_inning_end: bool = False
    is_game_end: bool = False
    raw_loaded_at: str = None
    mlb_game_pk: int = None
    snapshot_id: int = None
    plate_appearance_index: int = None
    mlb_event_type: str = None
    event_type_description: str = None
    trajectory: str = None
    raw_play: dict = None


@dataclass
class LivePlateAppearance:
    """Complete plate appearance data matching core.plate_appearances schema."""

    game_id: str
    plate_appearance_id: int
    game_pa_number: int
    half_inning_pa_number: int
    season: int
    game_date: str
    event_sequence: int
    inning: int
    is_bottom_inning: bool
    outs_before: int
    away_score_before: int
    home_score_before: int
    home_team_id: str
    away_team_id: str
    batting_team_id: str
    fielding_team_id: str
    batter_id: str
    batter_hand: str
    pitcher_id: str
    pitcher_hand: str
    event_code: int
    event_text: str
    is_at_bat: bool
    source_type: str = 'mlb_live'
    balls: int = None
    strikes: int = None
    start_bases: int = 0
    end_bases: int = 0
    away_score_after: int = None
    home_score_after: int = None
    hit_value: int = 0
    is_hit: bool = False
    is_walk: bool = False
    is_strikeout: bool = False
    is_home_run: bool = False
    is_hit_by_pitch: bool = False
    is_interference: bool = False
    is_reach_base: bool = False
    outs_on_play: int = 0
    runs_on_play: int = 0
    rbi: int = 0
    is_new_pa: bool = True
    pa_index: int = None
    batter_is_starter: bool = None
    pitcher_is_starter: bool = None
    park_id: str = None
    park_name: str = None
    temperature_f: int = None
    wind_speed_mph: int = None
    wind_direction: str = None
    precipitation: str = None
    sky_condition: str = None
    game_pa_count: int = None
    inning_pa_count: int = None
    is_inning_start: bool = False
    is_inning_end: bool = False
    is_game_end: bool = False
    mlb_game_pk: int = None
    snapshot_id: int = None
    snapshot_fetched_at: str = None
    raw_play: dict = None


def lookup_retrosheet_team_id(mlb_team_id: int, conn) -> str:
    """Look up Retrosheet team ID from MLB team ID."""
    if not mlb_team_id:
        return None

    with conn.cursor() as cur:
        cur.execute(
            'SELECT retrosheet_team_id FROM bridge.team_xref WHERE mlb_team_id = %s',
            (mlb_team_id,),
        )
        row = cur.fetchone()
        return row[0] if row else f'MLB{mlb_team_id}'


def lookup_retrosheet_player_id(mlb_player_id: int, conn) -> str:
    """Look up Retrosheet player ID from MLB player ID."""
    if not mlb_player_id:
        return None

    with conn.cursor() as cur:
        cur.execute(
            'SELECT retrosheet_id FROM bridge.player_xref WHERE mlb_id = %s',
            (mlb_player_id,),
        )
        row = cur.fetchone()
        return row[0] if row else f'MLB{mlb_player_id}'


def parse_live_game(feed: dict, snapshot_id: int) -> LiveGame:
    """Parse MLB live feed into LiveGame object with all Retrosheet fields."""
    game_data = feed.get('gameData', {})
    live_data = feed.get('liveData', {})
    game_pk = game_data.get('game', {}).get('pk')

    # Basic game info
    season = game_data.get('game', {}).get('season')
    game_date = game_data.get('datetime', {}).get('dateTime')

    # Team info with ID mapping
    teams = game_data.get('teams', {})
    home_team = teams.get('home', {})
    away_team = teams.get('away', {})

    # Use database connection for ID lookups (will be passed later)
    # For now, use placeholder IDs
    home_team_id = f"MLB{home_team.get('id')}" if home_team.get('id') else None
    away_team_id = f"MLB{away_team.get('id')}" if away_team.get('id') else None

    # Score info
    linescore = live_data.get('linescore', {})
    teams_score = linescore.get('teams', {})
    home_score = teams_score.get('home', {}).get('runs', 0)
    away_score = teams_score.get('away', {}).get('runs', 0)

    # Venue info
    venue = game_data.get('venue', {})
    park_id = f"MLB{venue.get('id')}" if venue.get('id') else None

    # Weather info
    weather = game_data.get('weather', {})
    temperature_f = weather.get('temp')
    wind_speed_mph = weather.get('windSpeed')
    wind_direction = weather.get('windDirection')
    precipitation = weather.get('precipitation')
    sky_condition = weather.get('condition')

    # Game status
    status = live_data.get('gameData', {}).get('status', {})
    detailed_state = status.get('detailedState')
    status_code = status.get('statusCode')

    return LiveGame(
        game_id=f'MLB{game_pk}',
        season=season,
        game_date=game_date.split('T')[0] if game_date else None,
        away_team_id=away_team_id,
        home_team_id=home_team_id,
        park_id=park_id,
        home_score=home_score,
        away_score=away_score,
        source_type='mlb_live',
        mlb_game_pk=game_pk,
        snapshot_id=snapshot_id,
        status_code=status_code,
        detailed_state=detailed_state,
        venue_name=venue.get('name'),
        temperature_f=temperature_f,
        wind_speed_mph=wind_speed_mph,
        wind_direction=wind_direction,
        precipitation=precipitation,
        sky_condition=sky_condition,
        raw_payload=feed,
    )


def parse_live_events(
    feed: dict, game_id: str, snapshot_id: int, conn,
) -> tuple[list[LiveEvent], list[LivePlateAppearance]]:
    """Parse MLB live feed plays into LiveEvent and LivePlateAppearance objects."""
    live_data = feed.get('liveData', {})
    plays = live_data.get('plays', {}).get('allPlays', [])

    events = []
    plate_appearances = []

    # Track plate appearance counters
    game_pa_counter = 0
    half_inning_pa_counters = defaultdict(int)

    for play_idx, play in enumerate(plays):
        # Extract play information
        result = play.get('result', {})
        about = play.get('about', {})
        count = play.get('count', {})

        # Basic event info
        inning = about.get('inning')
        is_bottom = about.get(
            'isTopInning', True,
        )  # MLB API uses isTopInning (True = top of inning)
        event_sequence = about.get('atBatIndex', play_idx)

        # Score before/after
        away_score_before = count.get('awayScore', 0)
        home_score_before = count.get('homeScore', 0)

        # Runners and outs
        runners = play.get('runners', [])
        outs_before = about.get('halfInningOuts', 0)

        # Calculate base state
        start_bases = 0
        for runner in runners:
            if runner.get('movement', {}).get('start'):
                base = runner.get('movement', {}).get('start')
                if base == '1B':
                    start_bases |= 1
                elif base == '2B':
                    start_bases |= 2
                elif base == '3B':
                    start_bases |= 4

        # Calculate end base state and runs scored
        end_bases = 0
        runs_on_play = 0
        for runner in runners:
            movement = runner.get('movement', {})
            if movement.get('end'):
                end_base = movement.get('end')
                if end_base == '1B':
                    end_bases |= 1
                elif end_base == '2B':
                    end_bases |= 2
                elif end_base == '3B':
                    end_bases |= 4
            if movement.get('run', {}).get('isScoringEvent'):
                runs_on_play += 1

        # Count info
        balls = count.get('balls', 0)
        strikes = count.get('strikes', 0)

        # Player info with ID mapping
        matchup = play.get('matchup', {})
        batter = matchup.get('batter', {})
        pitcher = matchup.get('pitcher', {})

        batter_id = (
            lookup_retrosheet_player_id(batter.get('id'), conn) if batter.get('id') else None
        )
        pitcher_id = (
            lookup_retrosheet_player_id(pitcher.get('id'), conn) if pitcher.get('id') else None
        )

        # Teams
        batting_team_id = (
            f"MLB{matchup.get('battingTeam', {}).get('id')}"
            if matchup.get('battingTeam', {}).get('id')
            else None
        )
        fielding_team_id = (
            f"MLB{matchup.get('pitchingTeam', {}).get('id')}"
            if matchup.get('pitchingTeam', {}).get('id')
            else None
        )

        # Event details
        event_type = result.get('type', 'unknown')
        event_desc = result.get('description', '')
        event_code = result.get('eventCode', 0)
        rbi = result.get('rbi', 0)

        # Determine event outcomes
        is_hit = event_type in ['single', 'double', 'triple', 'home_run']
        is_walk = event_type == 'walk'
        is_strikeout = event_type == 'strikeout'
        is_home_run = event_type == 'home_run'
        is_hit_by_pitch = event_type == 'hit_by_pitch'
        is_interference = event_type == 'catcher_interference'

        # Hit value
        hit_value = 0
        if event_type == 'single':
            hit_value = 1
        elif event_type == 'double':
            hit_value = 2
        elif event_type == 'triple':
            hit_value = 3
        elif event_type == 'home_run':
            hit_value = 4

        # Plate appearance logic
        is_at_bat = event_type in [
            'single',
            'double',
            'triple',
            'home_run',
            'strikeout',
            'field_out',
            'force_out',
            'grounded_into_double_play',
            'field_error',
            'fielders_choice',
        ]
        is_plate_appearance = is_at_bat or is_walk or is_hit_by_pitch or is_interference

        # Outs on play
        outs_on_play = 0
        if event_type in [
            'strikeout',
            'field_out',
            'force_out',
            'grounded_into_double_play',
        ]:
            outs_on_play = 1
        elif 'double_play' in event_desc.lower():
            outs_on_play = 2

        # Create LiveEvent
        event = LiveEvent(
            game_id=game_id,
            event_id=event_sequence + 1,
            season=int(feed.get('gameData', {}).get('game', {}).get('season')),
            event_sequence=event_sequence + 1,
            inning=inning,
            is_bottom_inning=not is_bottom,  # Convert MLB's isTopInning to is_bottom_inning
            outs_before=outs_before,
            balls=balls,
            strikes=strikes,
            away_score_before=away_score_before,
            home_score_before=home_score_before,
            batting_team_id=batting_team_id,
            fielding_team_id=fielding_team_id,
            batter_id=batter_id,
            batter_hand=batter.get('batSide', {}).get('code', 'U'),
            pitcher_id=pitcher_id,
            pitcher_hand=pitcher.get('pitchHand', {}).get('code', 'U'),
            event_code=event_code,
            event_text=event_desc,
            is_plate_appearance=is_plate_appearance,
            is_at_bat=is_at_bat,
            hit_value=hit_value,
            is_hit=is_hit,
            is_walk=is_walk,
            is_strikeout=is_strikeout,
            is_home_run=is_home_run,
            outs_on_play=outs_on_play,
            runs_on_play=runs_on_play,
            rbi=rbi,
            start_bases=start_bases,
            end_bases=end_bases,
            mlb_game_pk=feed.get('gameData', {}).get('game', {}).get('pk'),
            snapshot_id=snapshot_id,
            raw_play=play,
        )
        events.append(event)

        # Create LivePlateAppearance if this is a plate appearance
        if is_plate_appearance:
            game_pa_counter += 1
            half_inning_key = f'{inning}_{not is_bottom}'
            half_inning_pa_counters[half_inning_key] += 1

            # Get game info for PA record
            game_data = feed.get('gameData', {})
            teams = game_data.get('teams', {})
            home_team_id = (
                f"MLB{teams.get('home', {}).get('id')}" if teams.get('home', {}).get('id') else None
            )
            away_team_id = (
                f"MLB{teams.get('away', {}).get('id')}" if teams.get('away', {}).get('id') else None
            )

            pa = LivePlateAppearance(
                game_id=game_id,
                plate_appearance_id=event_sequence + 1,
                game_pa_number=game_pa_counter,
                half_inning_pa_number=half_inning_pa_counters[half_inning_key],
                season=int(feed.get('gameData', {}).get('game', {}).get('season')),
                game_date=game_data.get('datetime', {}).get('dateTime', '').split('T')[0],
                event_sequence=event_sequence + 1,
                inning=inning,
                is_bottom_inning=not is_bottom,
                outs_before=outs_before,
                balls=balls,
                strikes=strikes,
                start_bases=start_bases,
                end_bases=end_bases,
                away_score_before=away_score_before,
                home_score_before=home_score_before,
                home_team_id=home_team_id,
                away_team_id=away_team_id,
                batting_team_id=batting_team_id,
                fielding_team_id=fielding_team_id,
                batter_id=batter_id,
                batter_hand=batter.get('batSide', {}).get('code', 'U'),
                pitcher_id=pitcher_id,
                pitcher_hand=pitcher.get('pitchHand', {}).get('code', 'U'),
                event_code=event_code,
                event_text=event_desc,
                is_at_bat=is_at_bat,
                hit_value=hit_value,
                is_hit=is_hit,
                is_walk=is_walk,
                is_strikeout=is_strikeout,
                is_home_run=is_home_run,
                is_hit_by_pitch=is_hit_by_pitch,
                is_interference=is_interference,
                is_reach_base=is_hit or is_walk or is_hit_by_pitch or is_interference,
                outs_on_play=outs_on_play,
                runs_on_play=runs_on_play,
                rbi=rbi,
                mlb_game_pk=feed.get('gameData', {}).get('game', {}).get('pk'),
                snapshot_id=snapshot_id,
                raw_play=play,
            )
            plate_appearances.append(pa)

    return events, plate_appearances


def insert_live_data(
    game: LiveGame,
    events: list[LiveEvent],
    plate_appearances: list[LivePlateAppearance],
    conn,
):
    """Insert live game, events, and plate appearances into database."""

    # Insert game
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO core.live_games (
                game_id, season, game_date, home_team_id, away_team_id, home_team_name, away_team_name,
                park_id, home_score, away_score, is_complete, source_type, mlb_game_pk, snapshot_id,
                snapshot_fetched_at, status_code, detailed_state, venue_name, temperature_f,
                wind_speed_mph, wind_direction, precipitation, sky_condition, raw_payload
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (game_id) DO UPDATE SET
                home_score = EXCLUDED.home_score,
                away_score = EXCLUDED.away_score,
                snapshot_id = EXCLUDED.snapshot_id,
                snapshot_fetched_at = EXCLUDED.snapshot_fetched_at,
                status_code = EXCLUDED.status_code,
                detailed_state = EXCLUDED.detailed_state,
                raw_payload = EXCLUDED.raw_payload,
                updated_at = now()
        """,
            (
                game.game_id,
                game.season,
                game.game_date,
                game.home_team_id,
                game.away_team_id,
                game.home_team_name,
                game.away_team_name,
                game.park_id,
                game.home_score,
                game.away_score,
                game.is_complete,
                game.source_type,
                game.mlb_game_pk,
                game.snapshot_id,
                game.snapshot_fetched_at,
                game.status_code,
                game.detailed_state,
                game.venue_name,
                game.temperature_f,
                game.wind_speed_mph,
                game.wind_direction,
                game.precipitation,
                game.sky_condition,
                Json(game.raw_payload),
            ),
        )

        # Insert events
        if events:
            execute_values(
                cur,
                """
                INSERT INTO core.live_events (
                    game_id, event_id, season, event_sequence, inning, is_bottom_inning, outs_before,
                    balls, strikes, away_score_before, home_score_before, batting_team_id, fielding_team_id,
                    batter_id, batter_hand, pitcher_id, pitcher_hand, event_code, event_text,
                    is_plate_appearance, is_at_bat, hit_value, is_hit, is_walk, is_strikeout, is_home_run,
                    outs_on_play, runs_on_play, rbi, start_bases, end_bases, mlb_game_pk, snapshot_id,
                    raw_play
                ) VALUES %s
                ON CONFLICT (game_id, event_id) DO UPDATE SET
                    balls = EXCLUDED.balls,
                    strikes = EXCLUDED.strikes,
                    away_score_before = EXCLUDED.away_score_before,
                    home_score_before = EXCLUDED.home_score_before,
                    is_hit = EXCLUDED.is_hit,
                    is_walk = EXCLUDED.is_walk,
                    is_strikeout = EXCLUDED.is_strikeout,
                    is_home_run = EXCLUDED.is_home_run,
                    outs_on_play = EXCLUDED.outs_on_play,
                    runs_on_play = EXCLUDED.runs_on_play,
                    rbi = EXCLUDED.rbi,
                    raw_play = EXCLUDED.raw_play,
                    updated_at = now()
            """,
                [
                    (
                        e.game_id,
                        e.event_id,
                        e.season,
                        e.event_sequence,
                        e.inning,
                        e.is_bottom_inning,
                        e.outs_before,
                        e.balls,
                        e.strikes,
                        e.away_score_before,
                        e.home_score_before,
                        e.batting_team_id,
                        e.fielding_team_id,
                        e.batter_id,
                        e.batter_hand,
                        e.pitcher_id,
                        e.pitcher_hand,
                        e.event_code,
                        e.event_text,
                        e.is_plate_appearance,
                        e.is_at_bat,
                        e.hit_value,
                        e.is_hit,
                        e.is_walk,
                        e.is_strikeout,
                        e.is_home_run,
                        e.outs_on_play,
                        e.runs_on_play,
                        e.rbi,
                        e.start_bases,
                        e.end_bases,
                        e.mlb_game_pk,
                        e.snapshot_id,
                        Json(e.raw_play),
                    )
                    for e in events
                ],
            )

        # Insert plate appearances
        if plate_appearances:
            execute_values(
                cur,
                """
                INSERT INTO core.live_plate_appearances (
                    game_id, plate_appearance_id, game_pa_number, half_inning_pa_number, season, game_date,
                    source_type, event_sequence, inning, is_bottom_inning, outs_before, balls, strikes,
                    start_bases, end_bases, away_score_before, home_score_before, home_team_id, away_team_id,
                    batting_team_id, fielding_team_id, batter_id, batter_hand, pitcher_id, pitcher_hand,
                    event_code, event_text, is_at_bat, hit_value, is_hit, is_walk, is_strikeout, is_home_run,
                    is_hit_by_pitch, is_interference, is_reach_base, outs_on_play, runs_on_play, rbi,
                    mlb_game_pk, snapshot_id, raw_play
                ) VALUES %s
                ON CONFLICT (game_id, plate_appearance_id) DO UPDATE SET
                    balls = EXCLUDED.balls,
                    strikes = EXCLUDED.strikes,
                    is_hit = EXCLUDED.is_hit,
                    is_walk = EXCLUDED.is_walk,
                    is_strikeout = EXCLUDED.is_strikeout,
                    is_home_run = EXCLUDED.is_home_run,
                    outs_on_play = EXCLUDED.outs_on_play,
                    runs_on_play = EXCLUDED.runs_on_play,
                    rbi = EXCLUDED.rbi,
                    raw_play = EXCLUDED.raw_play,
                    updated_at = now()
            """,
                [
                    (
                        pa.game_id,
                        pa.plate_appearance_id,
                        pa.game_pa_number,
                        pa.half_inning_pa_number,
                        pa.season,
                        pa.game_date,
                        pa.source_type,
                        pa.event_sequence,
                        pa.inning,
                        pa.is_bottom_inning,
                        pa.outs_before,
                        pa.balls,
                        pa.strikes,
                        pa.start_bases,
                        pa.end_bases,
                        pa.away_score_before,
                        pa.home_score_before,
                        pa.home_team_id,
                        pa.away_team_id,
                        pa.batting_team_id,
                        pa.fielding_team_id,
                        pa.batter_id,
                        pa.batter_hand,
                        pa.pitcher_id,
                        pa.pitcher_hand,
                        pa.event_code,
                        pa.event_text,
                        pa.is_at_bat,
                        pa.hit_value,
                        pa.is_hit,
                        pa.is_walk,
                        pa.is_strikeout,
                        pa.is_home_run,
                        pa.is_hit_by_pitch,
                        pa.is_interference,
                        pa.is_reach_base,
                        pa.outs_on_play,
                        pa.runs_on_play,
                        pa.rbi,
                        pa.mlb_game_pk,
                        pa.snapshot_id,
                        Json(pa.raw_play),
                    )
                    for pa in plate_appearances
                ],
            )


def main():
    parser = argparse.ArgumentParser(
        description='Transform MLB live feed into complete Retrosheet-compatible tables',
    )
    parser.add_argument('--game-pk', type=int, required=True, help='MLB game PK to transform')
    parser.add_argument(
        '--snapshot-id',
        type=int,
        help='Specific snapshot ID to use (latest if not specified)',
    )

    args = parser.parse_args()

    conn = psycopg2.connect(**database_kwargs())

    try:
        # Get the live feed data
        with conn.cursor() as cur:
            if args.snapshot_id:
                cur.execute(
                    """
                    SELECT payload, fetched_at
                    FROM raw_mlb.live_feed_snapshots
                    WHERE game_pk = %s AND id = %s
                """,
                    (args.game_pk, args.snapshot_id),
                )
            else:
                cur.execute(
                    """
                    SELECT payload, fetched_at
                    FROM raw_mlb.live_feed_snapshots
                    WHERE game_pk = %s
                    ORDER BY fetched_at DESC
                    LIMIT 1
                """,
                    (args.game_pk,),
                )

            row = cur.fetchone()
            if not row:
                print(f'No live feed data found for game_pk {args.game_pk}')
                return

            feed, fetched_at = row

        # Parse the data
        snapshot_id = args.snapshot_id
        if not snapshot_id:
            # Get the snapshot ID
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT snapshot_id FROM raw_mlb.live_feed_snapshots
                    WHERE game_pk = %s AND fetched_at = %s
                """,
                    (args.game_pk, fetched_at),
                )
                snapshot_id = cur.fetchone()[0]

        print(f'Transforming game {args.game_pk} (snapshot {snapshot_id})')

        # Parse game data
        game = parse_live_game(feed, snapshot_id)

        # Apply ID mappings
        game.home_team_id = (
            lookup_retrosheet_team_id(
                int(game.home_team_id[3:])
                if game.home_team_id and game.home_team_id.startswith('MLB')
                else None,
                conn,
            )
            or game.home_team_id
        )
        game.away_team_id = (
            lookup_retrosheet_team_id(
                int(game.away_team_id[3:])
                if game.away_team_id and game.away_team_id.startswith('MLB')
                else None,
                conn,
            )
            or game.away_team_id
        )

        # Parse events and plate appearances
        events, plate_appearances = parse_live_events(feed, game.game_id, snapshot_id, conn)

        print(f'Parsed {len(events)} events, {len(plate_appearances)} plate appearances')

        # Insert all data
        insert_live_data(game, events, plate_appearances, conn)
        conn.commit()

        print(f'Successfully transformed MLB game {args.game_pk} into Retrosheet-compatible tables')
        print('- core.live_games: 1 record')
        print(f'- core.live_events: {len(events)} records')
        print(f'- core.live_plate_appearances: {len(plate_appearances)} records')

    except Exception as e:
        print(f'Error transforming live game: {e}')
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == '__main__':
    main()
