"""
sample_queries.py
=================
Usage examples for mlb_pbp_collector.py

Run examples:
    python sample_queries.py                  # runs all examples (uses cached data where possible)
    python sample_queries.py --game 745461    # single game by gamePk
    python sample_queries.py --team Yankees   # all Yankees games in date range
"""

from __future__ import annotations
import argparse
import sys
import pandas as pd

# ── optional pretty-print
try:
    from tabulate import tabulate
    def show(df: pd.DataFrame, n: int = 20, title: str = "") -> None:
        if title:
            print(f"\n{'='*60}\n{title}\n{'='*60}")
        print(tabulate(df.head(n), headers="keys", tablefmt="psql", showindex=False))
        print(f"  ... ({len(df):,} total rows)\n")
except ImportError:
    def show(df: pd.DataFrame, n: int = 20, title: str = "") -> None:
        if title:
            print(f"\n{'='*60}\n{title}\n{'='*60}")
        print(df.head(n).to_string(index=False))
        print(f"  ... ({len(df):,} total rows)\n")


from mlb_pbp_collector import (
    collect_season,
    query_game,
    get_game_ids_for_team,
    RETRO_EVENT_MAP,
)


# ---------------------------------------------------------------------------
# Example 1 — Single game by gamePk (fastest path)
# ---------------------------------------------------------------------------

def example_single_game(game_pk: int) -> pd.DataFrame:
    """
    Fetch and display play-by-play for one MLB game.

    gamePk lookup tip: visit
        https://statsapi.mlb.com/api/v1/schedule?sportId=1&date=2025-04-10
    and find the gamePk in the JSON.
    """
    print(f"\n[Example 1] Single game: gamePk={game_pk}")
    df = query_game(game_pk)

    if df.empty:
        print("  No data returned — game may not have played yet.")
        return df

    # Show key columns
    view_cols = [
        "inning", "inning_half", "outs_before", "batter_name",
        "pitcher_name", "event_type", "pitch_sequence",
        "runner_1b", "runner_2b", "runner_3b",
        "release_speed", "launch_speed", "launch_angle",
    ]
    show(df[[c for c in view_cols if c in df.columns]],
         title=f"Game {game_pk} — Full Play-by-Play")
    return df


# ---------------------------------------------------------------------------
# Example 2 — Filter for extra-base hits with Statcast metrics
# ---------------------------------------------------------------------------

def example_extra_base_hits(df: pd.DataFrame) -> pd.DataFrame:
    """Show all XBH events with Statcast data from a PBP DataFrame."""
    xbh_events = {"double", "triple", "home_run"}
    xbh = df[df["event_type"].str.lower().isin(xbh_events)].copy()

    cols = [
        "game_date", "batter_name", "pitcher_name",
        "event_type", "launch_speed", "launch_angle",
        "hit_distance_sc", "estimated_woba_using_speedangle",
        "inning", "inning_half",
    ]
    show(xbh[[c for c in cols if c in xbh.columns]],
         title="Extra-Base Hits with Statcast Metrics")
    return xbh


# ---------------------------------------------------------------------------
# Example 3 — Pitch-type breakdown for a pitcher
# ---------------------------------------------------------------------------

def example_pitcher_pitch_mix(df: pd.DataFrame, pitcher_name: str) -> pd.DataFrame:
    """Aggregate pitch type usage for a specific pitcher."""
    pitcher_df = df[df["pitcher_name"].str.lower().str.contains(
        pitcher_name.lower(), na=False
    )].copy()

    if pitcher_df.empty:
        print(f"  Pitcher '{pitcher_name}' not found in dataset.")
        return pd.DataFrame()

    mix = (
        pitcher_df.groupby("pitch_type")
        .agg(
            count=("pitch_type", "size"),
            avg_velo=("release_speed", lambda x: pd.to_numeric(x, errors="coerce").mean()),
            avg_spin=("spin_rate",     lambda x: pd.to_numeric(x, errors="coerce").mean()),
        )
        .reset_index()
        .sort_values("count", ascending=False)
    )
    mix["pct"] = (mix["count"] / mix["count"].sum() * 100).round(1)
    show(mix, title=f"Pitch Mix — {pitcher_name}")
    return mix


# ---------------------------------------------------------------------------
# Example 4 — Runner-state situation counts (Retrosheet-style leverage)
# ---------------------------------------------------------------------------

def example_runner_situations(df: pd.DataFrame) -> pd.DataFrame:
    """
    Count events by base-out state (Retrosheet convention).
    State key: e.g. "1__" = runner on 1B only, "_23" = 2B+3B loaded.
    """
    def base_state(row) -> str:
        b1 = "1" if str(row.get("runner_1b", "")).strip() else "_"
        b2 = "2" if str(row.get("runner_2b", "")).strip() else "_"
        b3 = "3" if str(row.get("runner_3b", "")).strip() else "_"
        return b1 + b2 + b3

    df = df.copy()
    df["base_state"] = df.apply(base_state, axis=1)
    df["outs_before"] = pd.to_numeric(df["outs_before"], errors="coerce")

    situation = (
        df.groupby(["base_state", "outs_before"])
        .agg(
            plate_appearances=("batter_id", "count"),
            runs_scored=("runs_scored", lambda x: pd.to_numeric(x, errors="coerce").sum()),
            hr=("event_type", lambda x: (x.str.lower() == "home_run").sum()),
            k=("event_type",  lambda x: (x.str.lower() == "strikeout").sum()),
        )
        .reset_index()
        .sort_values("plate_appearances", ascending=False)
    )
    show(situation, n=24, title="Event Counts by Base-Out State (Retrosheet-style)")
    return situation


# ---------------------------------------------------------------------------
# Example 5 — Batch: one day of all games, save to CSV
# ---------------------------------------------------------------------------

def example_one_day(game_date: str = "2025-04-10") -> pd.DataFrame:
    """
    Pull every game on a given date and save a structured CSV.
    Demonstrates the full collect_season() pipeline.
    """
    print(f"\n[Example 5] All games on {game_date}")
    out_path = f"mlb_pbp_{game_date}.csv"
    df = collect_season(
        season=2025,
        start_date=game_date,
        end_date=game_date,
        output_csv=out_path,
        merge_statcast=True,
    )
    if not df.empty:
        print(f"  Saved {len(df):,} rows to {out_path}")
        show(df[["game_date","home_team","away_team","inning","batter_name",
                 "event_type","retro_event_code"]].head(30),
             title="Sample rows from collected day")
    return df


# ---------------------------------------------------------------------------
# Example 6 — Query by team name
# ---------------------------------------------------------------------------

def example_team_games(team_name: str = "Yankees",
                        start_date: str = "2025-04-01",
                        end_date:   str = "2025-04-15") -> pd.DataFrame:
    """
    Collect PBP for all games involving a specific team in a date window.
    """
    print(f"\n[Example 6] {team_name} games {start_date} → {end_date}")
    games = get_game_ids_for_team(team_name, 2025, start_date, end_date)
    if not games:
        print("  No games found.")
        return pd.DataFrame()

    print(f"  Found {len(games)} games:")
    for g in games:
        print(f"    gamePk={g['game_pk']}  {g['away_team']} @ {g['home_team']}  ({g['game_date']})")

    all_dfs = []
    for g in games:
        df = query_game(g["game_pk"])
        if not df.empty:
            all_dfs.append(df)

    if not all_dfs:
        return pd.DataFrame()

    combined = pd.concat(all_dfs, ignore_index=True)
    out_path = f"mlb_{team_name}_{start_date}_{end_date}.csv"
    combined.to_csv(out_path, index=False)
    print(f"  Saved {len(combined):,} rows → {out_path}")

    # Quick team stats
    team_hits = combined[combined["event_type"].str.lower().isin(
        ["single","double","triple","home_run"]
    )]
    print(f"\n  {team_name} hits in window: {len(team_hits)}")
    show(
        team_hits[["game_date","batter_name","event_type","launch_speed","inning"]],
        title=f"{team_name} — All Hits",
    )
    return combined


# ---------------------------------------------------------------------------
# Example 7 — High-leverage at-bats (runners on, 2 outs, late innings)
# ---------------------------------------------------------------------------

def example_high_leverage(df: pd.DataFrame) -> pd.DataFrame:
    """
    Filter for classic high-leverage situations:
    - Inning 7+ (or extra innings)
    - 2 outs
    - At least one runner on base
    """
    df = df.copy()
    df["outs_before"] = pd.to_numeric(df["outs_before"], errors="coerce")
    df["inning"]      = pd.to_numeric(df["inning"],      errors="coerce")

    has_runner = (
        df["runner_1b"].astype(str).str.strip().ne("") |
        df["runner_2b"].astype(str).str.strip().ne("") |
        df["runner_3b"].astype(str).str.strip().ne("")
    )

    high_lev = df[
        (df["inning"] >= 7) &
        (df["outs_before"] == 2) &
        has_runner
    ].copy()

    cols = [
        "game_date", "inning", "inning_half", "batter_name",
        "pitcher_name", "runner_1b", "runner_2b", "runner_3b",
        "event_type", "pitch_sequence", "runs_scored",
    ]
    show(high_lev[[c for c in cols if c in high_lev.columns]],
         title="High-Leverage At-Bats (7th+, 2 outs, runners on)")
    return high_lev


# ---------------------------------------------------------------------------
# Example 8 — Load saved CSV and filter
# ---------------------------------------------------------------------------

def example_load_and_filter(csv_path: str, event_filter: str = "home_run") -> pd.DataFrame:
    """
    Load a previously saved CSV and filter by event type.
    Demonstrates downstream analysis workflow.

    >>> df = example_load_and_filter("mlb_pbp_2025-04-10.csv", "home_run")
    """
    import os
    if not os.path.exists(csv_path):
        print(f"  File not found: {csv_path}")
        return pd.DataFrame()

    df = pd.read_csv(csv_path, dtype=str)
    filtered = df[df["event_type"].str.lower() == event_filter.lower()]

    show(
        filtered[["game_date","batter_name","pitcher_name",
                  "event_type","launch_speed","launch_angle",
                  "hit_distance_sc","inning"]],
        title=f"Filtered: event_type == '{event_filter}' from {csv_path}",
    )
    return filtered


# ---------------------------------------------------------------------------
# CSV Schema reference
# ---------------------------------------------------------------------------

COLUMN_REFERENCE = """
CSV Column Reference
====================

GAME CONTEXT
  game_pk             MLB Stats API primary game key (integer)
  game_date           ISO date  YYYY-MM-DD
  home_team           Full team name
  away_team           Full team name
  venue               Stadium name

RETROSHEET-STYLE IDs
  retro_game_id       HHH + YYYYMMDD + game# (e.g. NYY202504100)
  retro_event_id      retro_game_id + _NNNN sequence number

INNING / SITUATION
  inning              Integer (1-9+)
  inning_half         "top" or "bottom"
  outs_before         Outs at start of play (0, 1, 2)
  balls               Ball count when play ended
  strikes             Strike count when play ended

BATTER / PITCHER
  batter_id           MLBAM player ID
  batter_name         Full name
  pitcher_id          MLBAM player ID
  pitcher_name        Full name
  stand               Batter handedness: L / R / S
  p_throws            Pitcher hand: L / R

RUNNERS  (MLBAM IDs; blank string = base empty)
  runner_1b
  runner_2b
  runner_3b

PITCH DATA  (last pitch of at-bat)
  pitch_type          Abbreviation: FF, SL, CU, CH, SI, etc.
  pitch_desc          Human description (e.g. "Called Strike")
  release_speed       mph
  spin_rate           rpm
  plate_x             Horizontal location at plate (ft, catcher view)
  plate_z             Vertical location at plate (ft)
  zone                Statcast zone 1-14

STATCAST BATTED BALL  (merged from Baseball Savant via pybaseball)
  launch_speed        Exit velocity (mph)
  launch_angle        Degrees
  hit_distance_sc     Projected distance (ft)
  estimated_ba_using_speedangle   xBA
  estimated_woba_using_speedangle xwOBA

EVENT OUTCOME
  event_type          MLB canonical event (e.g. "single", "strikeout")
  event_desc          Full description string
  hit_location        Fielder zone (1-9+)
  is_out              1 if out recorded, else 0
  rbi                 RBI on this play
  runs_scored         Runs that scored on this play
  pitch_sequence      Retrosheet-style pitch codes (e.g. "CBFS X")

RETROSHEET MAPPING
  retro_event_cd      Retrosheet numeric event code (0-23)
  retro_event_code    Retrosheet alpha code (e.g. "K", "S", "HR")
  retro_bat_event_fl  1 if batter plate appearance event, else 0
"""


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="MLB Play-by-Play sample queries"
    )
    parser.add_argument("--game",   type=int,  help="Run single-game example with this gamePk")
    parser.add_argument("--team",   type=str,  help="Run team-games example with this team name")
    parser.add_argument("--date",   type=str,  default="2025-04-10",
                        help="Date for one-day batch example (YYYY-MM-DD)")
    parser.add_argument("--csv",    type=str,  help="Path to existing CSV to load and filter")
    parser.add_argument("--schema", action="store_true", help="Print column reference")
    args = parser.parse_args()

    if args.schema:
        print(COLUMN_REFERENCE)
        sys.exit(0)

    if args.game:
        df = example_single_game(args.game)
        if not df.empty:
            example_extra_base_hits(df)
            example_runner_situations(df)
            example_high_leverage(df)
        sys.exit(0)

    if args.team:
        example_team_games(args.team)
        sys.exit(0)

    if args.csv:
        example_load_and_filter(args.csv)
        sys.exit(0)

    # Default: run one-day batch
    df = example_one_day(args.date)
    if not df.empty:
        example_extra_base_hits(df)
        example_runner_situations(df)
        example_high_leverage(df)


if __name__ == "__main__":
    main()
