#!/usr/bin/env python3
"""
EdgeForge: Extract Statcast features from MLB data for betting edge analysis.
Focus on high-value features for win probability and prop betting.
"""

import os
import psycopg2
import pandas as pd
from psycopg2.extras import execute_values


def database_kwargs():
    return {
        "host": os.environ.get("PGHOST", "localhost"),
        "port": os.environ.get("PGPORT", "5432"),
        "dbname": os.environ.get("PGDATABASE", "retrosheet"),
        "user": os.environ.get("PGUSER", "postgres"),
        "password": os.environ.get("PGPASSWORD", ""),
    }


def extract_statcast_features():
    """Extract high-value Statcast features for betting analysis."""
    print("⚾ EdgeForge: Extracting Statcast features for betting edge...")

    conn = psycopg2.connect(**database_kwargs())

    # Extract pitch-level features that matter for betting
    query = """
    SELECT
        lfs.game_pk::bigint as game_pk,
        (play->>'atBatIndex')::int as event_sequence,
        (event->>'pitchNumber')::int as pitch_number,
        event->'details'->'type'->>'code' as pitch_type,
        event->'details'->'call'->>'code' as pitch_call,
        (event->'pitchData'->>'startSpeed')::numeric as velocity,
        CASE WHEN (event->'pitchData'->'breaks'->>'spinRate')::int < 10000
             THEN (event->'pitchData'->'breaks'->>'spinRate')::int
             ELSE NULL END as spin_rate,
        (event->'pitchData'->'coordinates'->>'pX')::numeric as plate_x,
        (event->'pitchData'->'coordinates'->>'pZ')::numeric as plate_z,
        (event->'pitchData'->'breaks'->>'breakHorizontal')::numeric as break_x,
        (event->'pitchData'->'breaks'->>'breakVerticalInduced')::numeric as break_z,
        CASE
            WHEN event->'pitchData'->'coordinates'->>'pX' IS NOT NULL
             AND event->'pitchData'->'coordinates'->>'pZ' IS NOT NULL
            THEN sqrt(power((event->'pitchData'->'coordinates'->>'pX')::numeric, 2) +
                     power((event->'pitchData'->'coordinates'->>'pZ')::numeric - 2.5, 2))
            ELSE NULL
        END as distance_from_center,
        event->>'isPitch' = 'true' as is_pitch
    FROM raw_mlb.live_feed_snapshots lfs,
         jsonb_array_elements(lfs.payload->'liveData'->'plays'->'allPlays') play,
         jsonb_array_elements(play->'playEvents') event
    WHERE lfs.http_status = 200
      AND event->>'type' = 'pitch'
      AND event->'pitchData' IS NOT NULL
      AND event->'pitchData'->>'startSpeed' IS NOT NULL
    LIMIT 10000  -- Start with smaller sample for testing
    """

    try:
        df = pd.read_sql_query(query, conn)

        if len(df) > 0:
            # Insert into enhanced features table
            with conn.cursor() as cur:
                execute_values(
                    cur,
                    """
                    INSERT INTO mlb_enhanced.statcast_pitches (
                        game_pk, event_sequence, pitch_number,
                        pitch_type_code, pitch_call_code,
                        start_speed, spin_rate, plate_x, plate_z,
                        break_horizontal, break_vertical
                    ) VALUES %s
                    ON CONFLICT (game_pk, event_sequence, pitch_number) DO NOTHING
                """,
                    [
                        (
                            row.game_pk,
                            row.event_sequence,
                            row.pitch_number,
                            row.pitch_type,
                            row.pitch_call,
                            row.velocity,
                            None
                            if pd.isna(row.spin_rate)
                            or (
                                isinstance(row.spin_rate, (int, float))
                                and row.spin_rate > 10000
                            )
                            else row.spin_rate,
                            row.plate_x,
                            row.plate_z,
                            row.break_x,
                            row.break_z,
                        )
                        for row in df.itertuples()
                    ],
                )

            conn.commit()

            print(f"✅ Extracted {len(df)} Statcast pitches")
            print(".1f")
            # Show pitch type distribution
            pitch_dist = df["pitch_type"].value_counts().head(5)
            print("Top pitch types:")
            for pitch_type, count in pitch_dist.items():
                print(f"  {pitch_type}: {count}")

        else:
            print("❌ No Statcast data found")

    finally:
        conn.close()


def build_matchup_features():
    """Build batter-pitcher matchup features for edge analysis."""
    print("🤝 Building matchup features for betting edges...")

    conn = psycopg2.connect(**database_kwargs())

    try:
        with conn.cursor() as cur:
            # Calculate matchup statistics
            cur.execute("""
                WITH matchup_stats AS (
                    SELECT
                        e.batter_id,
                        e.pitcher_id,
                        EXTRACT(YEAR FROM g.game_date::date)::int as season,
                        COUNT(*) as plate_appearances,
                        COUNT(CASE WHEN e.is_hit THEN 1 END) as hits,
                        COUNT(CASE WHEN e.is_home_run THEN 1 END) as home_runs,
                        COUNT(CASE WHEN e.is_walk THEN 1 END) as walks,
                        COUNT(CASE WHEN e.is_strikeout THEN 1 END) as strikeouts,
                        ROUND(AVG(e.is_hit::int)::numeric, 3) as avg,
                        ROUND(AVG(CASE WHEN e.is_at_bat THEN e.is_hit::int END)::numeric, 3) as batting_avg,
                        ROUND(
                            (COUNT(CASE WHEN e.is_hit THEN 1 END) +
                             COUNT(CASE WHEN e.hit_value = 2 THEN 1 END) +
                             2 * COUNT(CASE WHEN e.hit_value = 3 THEN 1 END) +
                             3 * COUNT(CASE WHEN e.is_home_run THEN 1 END))::numeric
                            / NULLIF(COUNT(CASE WHEN e.is_at_bat THEN 1 END), 0),
                            3
                        ) as slg
                    FROM core.live_events e
                    JOIN core.live_games g ON e.game_id = g.game_id
                    WHERE e.batter_id IS NOT NULL
                      AND e.pitcher_id IS NOT NULL
                      AND e.is_plate_appearance = true
                      AND EXTRACT(YEAR FROM g.game_date::date) >= 2020
                    GROUP BY e.batter_id, e.pitcher_id, EXTRACT(YEAR FROM g.game_date::date)::int
                    HAVING COUNT(*) >= 5  -- Minimum matchups for significance
                )
                INSERT INTO mlb_enhanced.batter_pitcher_history (
                    batter_id, pitcher_id, season,
                    total_pa, hits, home_runs, walks, strikeouts,
                    avg, slg
                )
                SELECT
                    batter_id, pitcher_id, season,
                    plate_appearances, hits, home_runs, walks, strikeouts,
                    batting_avg, slg
                FROM matchup_stats
                ON CONFLICT (batter_id, pitcher_id, season) DO UPDATE SET
                    total_pa = EXCLUDED.total_pa,
                    hits = EXCLUDED.hits,
                    home_runs = EXCLUDED.home_runs,
                    walks = EXCLUDED.walks,
                    strikeouts = EXCLUDED.strikeouts,
                    avg = EXCLUDED.avg,
                    slg = EXCLUDED.slg;
            """)

            # Get matchup counts
            cur.execute("SELECT COUNT(*) FROM mlb_enhanced.batter_pitcher_history;")
            matchup_count = cur.fetchone()[0]

            print(f"✅ Built {matchup_count} batter-pitcher matchups")

            # Show some high-value matchups
            cur.execute("""
                SELECT batter_id, pitcher_id, total_pa, avg, slg
                FROM mlb_enhanced.batter_pitcher_history
                WHERE total_pa >= 20
                ORDER BY avg DESC
                LIMIT 5;
            """)

            print("Top batter-pitcher matchups:")
            for row in cur.fetchall():
                print(".3f")

        conn.commit()

    finally:
        conn.close()


def create_betting_features_dataset():
    """Create enhanced dataset optimized for betting edge analysis."""
    print("🎯 Creating betting-optimized feature dataset...")

    conn = psycopg2.connect(**database_kwargs())

    try:
        with conn.cursor() as cur:
            # Create betting-focused training dataset
            cur.execute("""
                CREATE TABLE IF NOT EXISTS mlb_enhanced.betting_features AS
                SELECT
                    gsf.game_id,
                    gsf.event_sequence,
                    gsf.season,
                    gsf.inning,
                    gsf.is_bottom_inning,
                    gsf.outs_before,
                    gsf.balls,
                    gsf.strikes,
                    gsf.score_diff,
                    gsf.runners_on_base,
                    gsf.batting_team_wins as target,

                    -- Core betting features
                    COALESCE(bs.batting_avg, 0.250) as batter_avg,
                    COALESCE(ps.era, 4.00) as pitcher_era,
                    COALESCE(ts.win_pct, 0.500) as team_win_pct,

                    -- Statcast pitch features (high betting value)
                    COALESCE(sp.start_speed, 92.0) as pitch_velocity,
                    COALESCE(sp.spin_rate, 2400) as pitch_spin_rate,
                    CASE
                        WHEN sp.plate_x IS NOT NULL AND sp.plate_z IS NOT NULL THEN
                            POWER(sp.plate_x, 2) + POWER(sp.plate_z - 2.5, 2)
                        ELSE 10.0
                    END as pitch_distance_from_zone,

                    -- Matchup edges (key for betting)
                    COALESCE(mh.total_pa, 0) as matchup_experience,
                    COALESCE(mh.avg, 0.220) as matchup_avg_vs_pitcher,
                    COALESCE(mh.slg, 0.350) as matchup_slg_vs_pitcher,

                    -- Situational betting factors
                    CASE WHEN gsf.inning >= 7 THEN 1 ELSE 0 END as high_leverage,
                    CASE WHEN abs(gsf.score_diff) <= 1 THEN 1 ELSE 0 END as close_game,
                    CASE WHEN gsf.runners_on_base > 0 THEN 1 ELSE 0 END as runners_on

                FROM mlb_features.game_state_features gsf
                -- Get latest pitch for this event
                LEFT JOIN mlb_enhanced.statcast_pitches sp ON gsf.game_id LIKE '%' || sp.game_pk::text || '%'
                    AND gsf.event_sequence = sp.event_sequence
                    AND sp.pitch_number = (
                        SELECT MAX(sp2.pitch_number)
                        FROM mlb_enhanced.statcast_pitches sp2
                        WHERE sp2.game_pk = sp.game_pk AND sp2.event_sequence = sp.event_sequence
                    )
                -- Player stats
                LEFT JOIN mlb_features.player_season_stats bs ON gsf.batter_id = bs.player_id
                    AND gsf.season = bs.season AND bs.is_batter = true
                LEFT JOIN mlb_features.player_season_stats ps ON gsf.pitcher_id = ps.player_id
                    AND gsf.season = ps.season AND ps.is_batter = false
                -- Team stats
                LEFT JOIN mlb_features.team_season_stats ts ON gsf.batting_team_id = ts.team_id
                    AND gsf.season = ts.season
                -- Matchup history
                LEFT JOIN mlb_enhanced.batter_pitcher_history mh ON gsf.batter_id = mh.batter_id
                    AND gsf.pitcher_id = mh.pitcher_id AND gsf.season = mh.season

                WHERE gsf.season BETWEEN 2020 AND 2023
                  AND gsf.data_source = 'mlb'
                  AND gsf.inning <= 9
                  AND gsf.batting_team_wins IS NOT NULL;
            """)

            # Get dataset statistics
            cur.execute("""
                SELECT
                    COUNT(*) as total_samples,
                    AVG(target::int)::numeric as win_rate,
                    COUNT(DISTINCT game_id) as unique_games,
                    COUNT(DISTINCT season) as seasons
                FROM mlb_enhanced.betting_features;
            """)

            stats = cur.fetchone()
            print(f"✅ Created betting dataset: {stats[0]} samples")
            print(".3f")
        conn.commit()

    finally:
        conn.close()


def main():
    print("🎯 EdgeForge: Building MLB Betting Intelligence Platform")
    print("=" * 60)
    print("📊 Focus: Calibrated edges over hype")
    print("🎲 Features: Statcast + matchups + situational factors")
    print("💰 Goal: Monetizable betting intelligence")

    # Extract enhanced features
    extract_statcast_features()
    build_matchup_features()
    create_betting_features_dataset()

    print("\n" + "=" * 60)
    print("✅ ENHANCED BETTING FEATURES READY")
    print("=" * 60)
    print("• Statcast pitch physics extracted")
    print("• Batter-pitcher matchup edges calculated")
    print("• Betting-optimized feature set created")
    print("• Ready for model training and market comparison")

    print("\n🎲 Next: Train enhanced model + market calibration")
    print("💰 Path to monetization: Premium picks + edge alerts")


if __name__ == "__main__":
    main()
