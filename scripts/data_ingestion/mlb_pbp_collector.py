"""
mlb_pbp_collector.py
====================
Downloads play-by-play data for the 2025 MLB season by combining:
  - MLB Stats API  (statsapi.mlb.com/api/v1/game/{pk}/playByPlay)
    → at-bat level events, pitch sequences, runners, count, inning context
  - pybaseball Statcast (Baseball Savant)
    → advanced pitch & batted-ball metrics merged on game/batter/inning

Output CSV column groups
------------------------
GAME CONTEXT     : game_pk, game_date, home_team, away_team, venue
RETRO-STYLE IDs  : retro_game_id, retro_event_id
INNING/SITUATION : inning, inning_half, outs_after, balls, strikes
BATTER/PITCHER   : batter_id, batter_name, pitcher_id, pitcher_name, stand, p_throws
RUNNERS (before) : runner_1b_id, runner_2b_id, runner_3b_id (MLBAM IDs; blank = empty)
PITCH DATA       : pitch_type, pitch_desc, release_speed, spin_rate,
                   plate_x, plate_z, zone
STATCAST         : launch_speed, launch_angle, hit_distance_sc,
                   estimated_ba_using_speedangle, estimated_woba_using_speedangle
EVENT            : event_type, event_desc, hit_location, is_out, rbi,
                   runs_scored, pitch_sequence
RETROSHEET MAP   : retro_event_cd, retro_event_code, retro_bat_event_fl

Dependencies
------------
    pip install MLB-StatsAPI pybaseball pandas requests tabulate

Data Sources
------------
  - MLB Stats API:   https://statsapi.mlb.com  (free, no auth required)
  - Baseball Savant: https://baseballsavant.mlb.com  (via pybaseball)
  - Retrosheet:      https://www.retrosheet.org  (column mapping reference)
"""

from __future__ import annotations

import logging
import time
from pathlib import Path

import pandas as pd
import requests


try:
    from pybaseball import cache as pb_cache, statcast

    pb_cache.enable()
    PYBASEBALL_AVAILABLE = True
except ImportError:
    PYBASEBALL_AVAILABLE = False
    logging.warning(
        'pybaseball not installed — Statcast metrics will be empty. Run: pip install pybaseball',
    )

# ---------------------------------------------------------------------------
# Retrosheet event-code mapping
# Reference: https://www.retrosheet.org/eventfile.htm
# Maps MLB Stats API eventType strings → (numeric_code, alpha_code)
# ---------------------------------------------------------------------------
RETRO_EVENT_MAP: dict[str, tuple[int, str]] = {
    'strikeout': (3, 'K'),
    'walk': (14, 'W'),
    'intent_walk': (15, 'IW'),
    'hit_by_pitch': (16, 'HP'),
    'single': (20, 'S'),
    'double': (21, 'D'),
    'triple': (22, 'T'),
    'home_run': (23, 'HR'),
    'field_out': (2, 'F'),
    'grounded_into_double_play': (2, 'GDP'),
    'force_out': (2, 'FO'),
    'fielders_choice_out': (2, 'FC'),
    'fielders_choice': (4, 'FC'),
    'sac_fly': (9, 'SF'),
    'sac_fly_double_play': (9, 'SFDP'),
    'sac_bunt': (8, 'SH'),
    'sac_bunt_double_play': (8, 'SHDP'),
    'double_play': (2, 'DP'),
    'triple_play': (2, 'TP'),
    'caught_stealing_2b': (6, 'CS2'),
    'caught_stealing_3b': (6, 'CS3'),
    'caught_stealing_home': (6, 'CSH'),
    'pickoff_caught_stealing_2b': (6, 'POCS2'),
    'pickoff_caught_stealing_3b': (6, 'POCS3'),
    'pickoff_caught_stealing_home': (6, 'POCSH'),
    'stolen_base_2b': (4, 'SB2'),
    'stolen_base_3b': (4, 'SB3'),
    'stolen_base_home': (4, 'SBH'),
    'wild_pitch': (4, 'WP'),
    'passed_ball': (4, 'PB'),
    'error': (18, 'E'),
    'pickoff_1b': (6, 'PO1'),
    'pickoff_2b': (6, 'PO2'),
    'pickoff_3b': (6, 'PO3'),
    'balk': (4, 'BK'),
    'catcher_interf': (17, 'CI'),
    'fan_interference': (17, 'INT'),
    'game_advisory': (0, 'NP'),
    'no_play': (0, 'NP'),
    'other_out': (2, 'O'),
    'runner_double_play': (2, 'DP'),
    'runner_out': (2, 'O'),
}

# Events that represent true plate appearances (batter_event = True in Retrosheet)
BAT_EVENTS = {
    'strikeout',
    'walk',
    'intent_walk',
    'hit_by_pitch',
    'single',
    'double',
    'triple',
    'home_run',
    'field_out',
    'grounded_into_double_play',
    'force_out',
    'fielders_choice_out',
    'fielders_choice',
    'sac_fly',
    'sac_fly_double_play',
    'sac_bunt',
    'sac_bunt_double_play',
    'double_play',
    'triple_play',
    'runner_double_play',
    'error',
    'catcher_interf',
    'fan_interference',
    'other_out',
    'runner_out',
}

MLB_API_BASE = 'https://statsapi.mlb.com/api/v1'
RATE_LIMIT_SLEEP = 0.3  # seconds between game API calls


# ---------------------------------------------------------------------------
# Pitch description → Retrosheet pitch sequence code
# MLB Stats API "details.code" maps directly to Retrosheet codes
# ---------------------------------------------------------------------------
PITCH_CODE_MAP: dict[str, str] = {
    'B': 'B',  # ball
    'I': 'I',  # intentional ball
    'P': 'P',  # pitchout
    'V': 'V',  # automatic ball
    'C': 'C',  # called strike
    'S': 'S',  # swinging strike
    'W': 'W',  # swinging strike (blocked)
    'T': 'T',  # foul tip (strike)
    'K': 'K',  # strike (unknown type)
    'F': 'F',  # foul ball
    'R': 'R',  # foul (bunt attempt)
    'L': 'L',  # foul bunt (strike)
    'O': 'O',  # foul tip caught (3rd strike)
    'X': 'X',  # in play (out)
    'E': 'E',  # in play (error on fielder)
    'D': 'D',  # in play (double)
    'G': 'G',  # ground ball double play
    'M': 'M',  # missed bunt attempt
    'Q': 'Q',  # swinging pitchout
    '*': '*',  # blocked ball (no swing)
    '+': '+',  # preceding runner going
    '.': '.',  # non-batter play
    '1': '1',  # pickoff to 1B
    '2': '2',  # pickoff to 2B
    '3': '3',  # pickoff to 3B
    '>': '>',  # runner going on pitch
    'N': 'N',  # no pitch
}


def _build_pitch_sequence(play_events: list[dict]) -> str:
    """Build a Retrosheet-style pitch sequence string from playEvents."""
    codes = []
    for evt in play_events:
        if not evt.get('isPitch', False):
            continue
        code = evt.get('details', {}).get('code', '?')
        codes.append(PITCH_CODE_MAP.get(code, code))
    return ''.join(codes)


# ---------------------------------------------------------------------------
# Runner state reconstruction
# ---------------------------------------------------------------------------


def _extract_runner_state_before(runners: list[dict]) -> dict[str, str]:
    """
    Determine which runners were on base BEFORE this play by looking at
    originBase / start fields in runner movement records.

    Returns {'runner_1b_id': ..., 'runner_2b_id': ..., 'runner_3b_id': ...}
    where values are MLBAM player IDs as strings, or '' if base was empty.
    """
    base_map: dict[str, str] = {'1B': '', '2B': '', '3B': ''}
    for runner in runners:
        movement = runner.get('movement', {})
        details = runner.get('details', {})
        # originBase / start tell us where runner was before the play
        origin = movement.get('originBase') or movement.get('start')
        if origin and origin in base_map:
            pid = details.get('runner', {}).get('id', '')
            if pid:
                base_map[origin] = str(pid)
    return {
        'runner_1b_id': base_map['1B'],
        'runner_2b_id': base_map['2B'],
        'runner_3b_id': base_map['3B'],
    }


def _extract_runner_names_before(runners: list[dict]) -> dict[str, str]:
    """Same as above but returns player names for readability."""
    base_map: dict[str, str] = {'1B': '', '2B': '', '3B': ''}
    for runner in runners:
        movement = runner.get('movement', {})
        details = runner.get('details', {})
        origin = movement.get('originBase') or movement.get('start')
        if origin and origin in base_map:
            name = details.get('runner', {}).get('fullName', '')
            if name:
                base_map[origin] = name
    return {
        'runner_1b': base_map['1B'],
        'runner_2b': base_map['2B'],
        'runner_3b': base_map['3B'],
    }


def _count_runs_scored(runners: list[dict]) -> int:
    """Count runners that scored on this play (movement.end == 'score')."""
    return sum(1 for r in runners if r.get('movement', {}).get('end') == 'score')


# ---------------------------------------------------------------------------
# Schedule helpers
# ---------------------------------------------------------------------------


def _get_schedule(season: int, game_type: str = 'R') -> list[dict]:
    """
    Return a list of game metadata dicts for the given season.
    Each dict has: game_pk, game_date, home_team, away_team, venue.
    """
    # Note: do NOT pass a 'fields' filter — it strips nested keys unpredictably
    url = (
        f'{MLB_API_BASE}/schedule?sportId=1&season={season}&gameType={game_type}&hydrate=team,venue'
    )
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    data = r.json()
    games = []
    for d in data.get('dates', []):
        for g in d.get('games', []):
            home = g.get('teams', {}).get('home', {})
            away = g.get('teams', {}).get('away', {})
            # team name lives under .team.name when hydrated, else .name directly
            home_name = (home.get('team') or home).get('name', 'Home')
            away_name = (away.get('team') or away).get('name', 'Away')
            games.append(
                {
                    'game_pk': g['gamePk'],
                    'game_date': g['gameDate'][:10],
                    'home_team': home_name,
                    'away_team': away_name,
                    'venue': g.get('venue', {}).get('name', ''),
                },
            )
    return games


def _get_team_abbr(team_name: str) -> str:
    """Derive a 3-letter abbreviation from a full team name."""
    words = [w for w in team_name.split() if w]
    return words[-1][:3].upper() if words else 'UNK'


# ---------------------------------------------------------------------------
# Play-by-Play API call
# ---------------------------------------------------------------------------


def _get_play_by_play(game_pk: int) -> list[dict]:
    """
    Fetch allPlays from /api/v1/game/{gamePk}/playByPlay.
    Returns list of play dicts; empty list if game has no data yet.
    """
    url = f'{MLB_API_BASE}/game/{game_pk}/playByPlay'
    r = requests.get(url, timeout=30)
    if r.status_code == 404:
        return []
    r.raise_for_status()
    return r.json().get('allPlays', [])


def _get_game_metadata_from_feed(game_pk: int) -> dict:
    """Pull home/away/venue/date from the live feed's gameData."""
    url = f'{MLB_API_BASE}/game/{game_pk}/feed/live?fields=gameData,teams,home,away,name,venue,datetime,officialDate'
    try:
        r = requests.get(url, timeout=20)
        if r.ok:
            gd = r.json().get('gameData', {})
            return {
                'game_pk': game_pk,
                'game_date': gd.get('datetime', {}).get('officialDate', ''),
                'home_team': gd.get('teams', {}).get('home', {}).get('name', 'Home'),
                'away_team': gd.get('teams', {}).get('away', {}).get('name', 'Away'),
                'venue': gd.get('venue', {}).get('name', ''),
            }
    except Exception:
        pass
    return {
        'game_pk': game_pk,
        'game_date': '',
        'home_team': 'Home',
        'away_team': 'Away',
        'venue': '',
    }


# ---------------------------------------------------------------------------
# Core: parse one play into a flat row
# ---------------------------------------------------------------------------


def _parse_play(play: dict, game_meta: dict, event_idx: int) -> dict:
    """
    Convert one allPlays entry into a flat dict suitable for a CSV row.

    Parameters
    ----------
    play       : single entry from allPlays
    game_meta  : dict with game_pk, game_date, home_team, away_team, venue, home_abbr
    event_idx  : 1-based sequential event number within the game
    """
    about = play.get('about', {})
    matchup = play.get('matchup', {})
    result = play.get('result', {})
    count = play.get('count', {})  # final count AFTER play
    runners = play.get('runners', [])
    play_events = play.get('playEvents', [])

    # Pitch events only
    pitch_events = [e for e in play_events if e.get('isPitch', False)]
    last_pitch = pitch_events[-1] if pitch_events else {}
    lp_details = last_pitch.get('details', {})
    lp_pitch_data = last_pitch.get('pitchData', {})
    lp_coords = lp_pitch_data.get('coordinates', {})
    lp_breaks = lp_pitch_data.get('breaks', {})

    # Event type → Retrosheet mapping
    event_type = (result.get('eventType') or '').lower()
    retro_cd, retro_code = RETRO_EVENT_MAP.get(event_type, (0, '??'))
    bat_event_fl = event_type in BAT_EVENTS

    # Runner state (before this play)
    runner_ids = _extract_runner_state_before(runners)
    runner_names = _extract_runner_names_before(runners)

    # Retro-style identifiers
    game_date_nodash = game_meta.get('game_date', '').replace('-', '')
    home_abbr = game_meta.get('home_abbr', 'UNK')
    retro_game_id = f'{home_abbr}{game_date_nodash}0'
    retro_event_id = f'{retro_game_id}_{event_idx:04d}'

    # Outs: use count.outs which reflects outs AFTER this at-bat ends
    outs_after = count.get('outs', '')

    return {
        # Game context
        'game_pk': game_meta['game_pk'],
        'game_date': game_meta.get('game_date', ''),
        'home_team': game_meta.get('home_team', ''),
        'away_team': game_meta.get('away_team', ''),
        'venue': game_meta.get('venue', ''),
        # Retrosheet IDs
        'retro_game_id': retro_game_id,
        'retro_event_id': retro_event_id,
        # Inning / situation
        'inning': about.get('inning', ''),
        'inning_half': about.get('halfInning', ''),  # "top" / "bottom"
        'outs_after': outs_after,
        'balls': count.get('balls', ''),
        'strikes': count.get('strikes', ''),
        # Batter / Pitcher
        'batter_id': matchup.get('batter', {}).get('id', ''),
        'batter_name': matchup.get('batter', {}).get('fullName', ''),
        'pitcher_id': matchup.get('pitcher', {}).get('id', ''),
        'pitcher_name': matchup.get('pitcher', {}).get('fullName', ''),
        'stand': matchup.get('batSide', {}).get('code', ''),
        'p_throws': matchup.get('pitchHand', {}).get('code', ''),
        # Runners BEFORE play (IDs and names)
        **runner_ids,
        **runner_names,
        # Pitch data (last pitch of at-bat)
        'pitch_type': lp_details.get('type', {}).get('code', '')
        if isinstance(lp_details.get('type'), dict)
        else lp_details.get('type', ''),
        'pitch_desc': lp_details.get('description', ''),
        'release_speed': lp_pitch_data.get('startSpeed', ''),
        'spin_rate': lp_breaks.get('spinRate', ''),
        'plate_x': lp_coords.get('pX', ''),
        'plate_z': lp_coords.get('pZ', ''),
        'zone': lp_pitch_data.get('zone', ''),
        # Statcast (populated later by merge)
        'launch_speed': '',
        'launch_angle': '',
        'hit_distance_sc': '',
        'estimated_ba_using_speedangle': '',
        'estimated_woba_using_speedangle': '',
        # Event outcome
        'event_type': result.get('eventType', ''),
        'event_desc': result.get('description', ''),
        'hit_location': result.get('hitLocation', ''),
        'is_out': int(bool(result.get('isOut', False))),
        'rbi': result.get('rbi', 0) or 0,
        'runs_scored': _count_runs_scored(runners),
        'pitch_sequence': _build_pitch_sequence(play_events),
        # Retrosheet mapping
        'retro_event_cd': retro_cd,
        'retro_event_code': retro_code,
        'retro_bat_event_fl': int(bat_event_fl),
    }


# ---------------------------------------------------------------------------
# Statcast merge
# ---------------------------------------------------------------------------


def _load_statcast(start_dt: str, end_dt: str) -> pd.DataFrame | None:
    """Pull Statcast data via pybaseball for a date window."""
    if not PYBASEBALL_AVAILABLE:
        return None
    try:
        logging.info(f'  Pulling Statcast {start_dt} → {end_dt} …')
        df = statcast(start_dt=start_dt, end_dt=end_dt)
        return df if df is not None and not df.empty else None
    except Exception as exc:
        logging.warning(f'  Statcast pull failed: {exc}')
        return None


def _merge_statcast(pbp_df: pd.DataFrame, sc_df: pd.DataFrame) -> pd.DataFrame:
    """
    Merge Statcast batted-ball columns into the PBP frame.

    Statcast is pitch-level; PBP is at-bat-level, so we take the
    last pitch per at-bat from Statcast (highest pitch_number).

    Join key: game_pk + batter (MLBAM ID) + inning + inning_half
    """
    wanted_sc = [
        'game_pk',
        'batter',
        'inning',
        'inning_topbot',
        'launch_speed',
        'launch_angle',
        'hit_distance_sc',
        'estimated_ba_using_speedangle',
        'estimated_woba_using_speedangle',
    ]
    sc = sc_df[[c for c in wanted_sc if c in sc_df.columns]].copy()

    # Keep last pitch per at-bat
    if 'pitch_number' in sc_df.columns and 'at_bat_number' in sc_df.columns:
        sc = (
            sc_df.sort_values('pitch_number')
            .groupby(
                ['game_pk', 'batter', 'inning', 'inning_topbot', 'at_bat_number'], as_index=False,
            )
            .last()[[c for c in wanted_sc + ['at_bat_number'] if c in sc_df.columns]]
        )

    sc = sc.rename(
        columns={
            'batter': '_sc_batter',
            'inning_topbot': '_sc_half',
        },
    )
    sc['game_pk'] = sc['game_pk'].astype(str)
    sc['_sc_batter'] = sc['_sc_batter'].astype(str)
    sc['inning'] = sc['inning'].astype(str)
    # Normalize top/bot labeling
    sc['_sc_half'] = (
        sc['_sc_half'].str.lower().map({'top': 'top', 'bot': 'bottom', 'bottom': 'bottom'})
    )

    pbp_df = pbp_df.copy()
    pbp_df['game_pk'] = pbp_df['game_pk'].astype(str)
    pbp_df['batter_id'] = pbp_df['batter_id'].astype(str)
    pbp_df['inning'] = pbp_df['inning'].astype(str)

    merged = pbp_df.merge(
        sc,
        left_on=['game_pk', 'batter_id', 'inning', 'inning_half'],
        right_on=['game_pk', '_sc_batter', 'inning', '_sc_half'],
        how='left',
        suffixes=('', '_sc'),
    )

    # Copy merged Statcast values into named columns, drop temps
    for col in [
        'launch_speed',
        'launch_angle',
        'hit_distance_sc',
        'estimated_ba_using_speedangle',
        'estimated_woba_using_speedangle',
    ]:
        sc_col = f'{col}_sc' if f'{col}_sc' in merged.columns else col
        if sc_col in merged.columns and sc_col != col:
            merged[col] = merged[sc_col].fillna('').astype(str).replace('nan', '')
            merged.drop(columns=[sc_col], inplace=True)

    for tmp in ['_sc_batter', '_sc_half', 'at_bat_number']:
        if tmp in merged.columns:
            merged.drop(columns=[tmp], inplace=True)

    return merged


# ---------------------------------------------------------------------------
# Public: collect a single game
# ---------------------------------------------------------------------------


def collect_game(
    game_pk: int,
    game_meta: dict | None = None,
    statcast_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """
    Download and parse play-by-play for one game.

    Parameters
    ----------
    game_pk      : MLB Stats API game primary key
    game_meta    : optional dict {game_pk, game_date, home_team, away_team, venue};
                   fetched automatically if not supplied
    statcast_df  : optional pre-loaded Statcast DataFrame to merge (avoids repeat pulls)

    Returns
    -------
    pd.DataFrame with one row per at-bat/event
    """
    if game_meta is None:
        game_meta = _get_game_metadata_from_feed(game_pk)

    game_meta['home_abbr'] = _get_team_abbr(game_meta.get('home_team', 'UNK'))

    logging.info(
        f"Collecting game {game_pk}: "
        f"{game_meta.get('away_team', '?')} @ {game_meta.get('home_team', '?')} "
        f"({game_meta.get('game_date', '?')})",
    )

    all_plays = _get_play_by_play(game_pk)
    if not all_plays:
        logging.warning(f'  No plays found for game {game_pk} (game may not have started)')
        return pd.DataFrame()

    rows = [_parse_play(play, game_meta, i + 1) for i, play in enumerate(all_plays)]
    df = pd.DataFrame(rows)

    if statcast_df is not None and not statcast_df.empty:
        df = _merge_statcast(df, statcast_df)

    return df


# ---------------------------------------------------------------------------
# Public: batch collect a season / date range
# ---------------------------------------------------------------------------


def collect_season(
    season: int = 2025,
    start_date: str | None = None,
    end_date: str | None = None,
    game_type: str = 'R',
    output_csv: str | None = None,
    max_games: int | None = None,
    merge_statcast_data: bool = True,
) -> pd.DataFrame:
    """
    Download PBP data for every game in the season (or a filtered window).

    Parameters
    ----------
    season              : MLB season year
    start_date          : ISO date string "YYYY-MM-DD" (inclusive)
    end_date            : ISO date string "YYYY-MM-DD" (inclusive)
    game_type           : "R" regular season, "P" postseason, "S" spring training
    output_csv          : path to save output CSV; skipped if None
    max_games           : cap number of games processed (useful for testing)
    merge_statcast_data : if True (and pybaseball available), merge Statcast metrics

    Returns
    -------
    pd.DataFrame with all PBP rows across requested games
    """
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s  %(levelname)-8s  %(message)s',
    )

    logging.info(f'Fetching {season} schedule (type={game_type}) …')
    schedule = _get_schedule(season, game_type)

    if start_date:
        schedule = [g for g in schedule if g['game_date'] >= start_date]
    if end_date:
        schedule = [g for g in schedule if g['game_date'] <= end_date]
    if max_games:
        schedule = schedule[:max_games]

    if not schedule:
        logging.warning('No games matched the filter criteria.')
        return pd.DataFrame()

    logging.info(f'Processing {len(schedule)} games …')

    # Group by date for efficient Statcast batch pulls
    by_date: dict[str, list[dict]] = {}
    for g in schedule:
        by_date.setdefault(g['game_date'], []).append(g)

    all_frames: list[pd.DataFrame] = []

    for gdate in sorted(by_date):
        sc_df = None
        if merge_statcast_data and PYBASEBALL_AVAILABLE:
            sc_df = _load_statcast(gdate, gdate)
            time.sleep(RATE_LIMIT_SLEEP)

        for meta in by_date[gdate]:
            try:
                df = collect_game(meta['game_pk'], meta, sc_df)
                if not df.empty:
                    all_frames.append(df)
            except Exception as exc:
                logging.exception(f"  Failed game {meta['game_pk']}: {exc}")
            time.sleep(RATE_LIMIT_SLEEP)

    if not all_frames:
        logging.warning('No data collected.')
        return pd.DataFrame()

    result = pd.concat(all_frames, ignore_index=True)
    result = _enforce_column_order(result)

    if output_csv:
        out = Path(output_csv)
        out.parent.mkdir(parents=True, exist_ok=True)
        result.to_csv(out, index=False)
        logging.info(f'Saved {len(result):,} rows → {out.resolve()}')

    return result


# ---------------------------------------------------------------------------
# Column order enforcement
# ---------------------------------------------------------------------------

COLUMN_ORDER = [
    'game_pk',
    'game_date',
    'home_team',
    'away_team',
    'venue',
    'retro_game_id',
    'retro_event_id',
    'inning',
    'inning_half',
    'outs_after',
    'balls',
    'strikes',
    'batter_id',
    'batter_name',
    'pitcher_id',
    'pitcher_name',
    'stand',
    'p_throws',
    'runner_1b_id',
    'runner_2b_id',
    'runner_3b_id',
    'runner_1b',
    'runner_2b',
    'runner_3b',
    'pitch_type',
    'pitch_desc',
    'release_speed',
    'spin_rate',
    'plate_x',
    'plate_z',
    'zone',
    'launch_speed',
    'launch_angle',
    'hit_distance_sc',
    'estimated_ba_using_speedangle',
    'estimated_woba_using_speedangle',
    'event_type',
    'event_desc',
    'hit_location',
    'is_out',
    'rbi',
    'runs_scored',
    'pitch_sequence',
    'retro_event_cd',
    'retro_event_code',
    'retro_bat_event_fl',
]


def _enforce_column_order(df: pd.DataFrame) -> pd.DataFrame:
    ordered = [c for c in COLUMN_ORDER if c in df.columns]
    extra = [c for c in df.columns if c not in ordered]
    return df[ordered + extra]


# ---------------------------------------------------------------------------
# Convenience helpers for sample_queries.py
# ---------------------------------------------------------------------------


def get_game_ids_for_team(
    team_name: str,
    season: int = 2025,
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[dict]:
    """Return schedule entries where home or away team matches team_name (case-insensitive partial match)."""
    schedule = _get_schedule(season)
    results = []
    needle = team_name.lower()
    for g in schedule:
        if needle in g['home_team'].lower() or needle in g['away_team'].lower():
            if start_date and g['game_date'] < start_date:
                continue
            if end_date and g['game_date'] > end_date:
                continue
            results.append(g)
    return results


def query_game(game_pk: int, merge_statcast_data: bool = True) -> pd.DataFrame:
    """
    One-liner to fetch PBP for a single game by gamePk.

    Example
    -------
    >>> df = query_game(778498)
    >>> print(df[["inning","batter_name","event_type","pitch_sequence"]].head(20))
    """
    meta = _get_game_metadata_from_feed(game_pk)
    sc_df = None
    if merge_statcast_data and PYBASEBALL_AVAILABLE and meta.get('game_date'):
        sc_df = _load_statcast(meta['game_date'], meta['game_date'])
    df = collect_game(game_pk, meta, sc_df)
    return _enforce_column_order(df) if not df.empty else df


# ---------------------------------------------------------------------------
# CLI entry point — quick smoke-test
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    import sys

    logging.basicConfig(level=logging.INFO, format='%(asctime)s  %(levelname)-8s  %(message)s')

    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        # Usage: python mlb_pbp_collector.py 778498
        pk = int(sys.argv[1])
        df = query_game(pk)
    else:
        # Usage: python mlb_pbp_collector.py 2025-04-01
        target_date = sys.argv[1] if len(sys.argv) > 1 else '2025-04-01'
        df = collect_season(
            season=2025,
            start_date=target_date,
            end_date=target_date,
            max_games=3,
            output_csv=f'mlb_pbp_{target_date}.csv',
        )

    if not df.empty:
        show_cols = [
            'game_date',
            'inning',
            'inning_half',
            'batter_name',
            'event_type',
            'pitch_sequence',
            'retro_event_code',
            'runs_scored',
        ]
        print(df[[c for c in show_cols if c in df.columns]].head(25).to_string(index=False))
        print(f'\nTotal rows: {len(df):,}  |  Columns: {len(df.columns)}')
