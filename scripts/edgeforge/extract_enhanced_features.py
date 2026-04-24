#!/usr/bin/env python3
"""
Extract Statcast pitch data from existing MLB feeds into enhanced features schema.
This runs separately from the main pipeline.
"""

import os

import psycopg2


def database_kwargs():
    return {
        'host': os.environ.get('PGHOST', 'localhost'),
        'port': os.environ.get('PGPORT', '5432'),
        'dbname': os.environ.get('PGDATABASE', 'retrosheet'),
        'user': os.environ.get('PGUSER', 'postgres'),
        'password': os.environ.get('PGPASSWORD', ''),
    }


def extract_statcast_pitches():
    """Extract Statcast pitch data from existing MLB game feeds."""
    print('⚾ Extracting Statcast pitch data from existing feeds...')

    conn = psycopg2.connect(**database_kwargs())
    try:
        with conn.cursor() as cur:
            # Extract pitch data from raw MLB feeds
            cur.execute("""
                INSERT INTO mlb_enhanced.statcast_pitches (
                    game_pk, event_sequence, pitch_number,
                    pitch_type_code, pitch_type_description, pitch_call_code,
                    plate_x, plate_z, start_speed, spin_rate,
                    break_horizontal, break_vertical, extension
                )
                SELECT
                    lfs.game_pk::bigint,
                    (play->>'atBatIndex')::int as event_sequence,
                    (event->>'pitchNumber')::int as pitch_number,
                    event->'details'->'type'->>'code' as pitch_type_code,
                    event->'details'->'type'->>'description' as pitch_type_description,
                    event->'details'->'call'->>'code' as pitch_call_code,
                    (event->'pitchData'->'coordinates'->>'pX')::numeric as plate_x,
                    (event->'pitchData'->'coordinates'->>'pZ')::numeric as plate_z,
                    (event->'pitchData'->>'startSpeed')::numeric as start_speed,
                    (event->'pitchData'->'breaks'->>'spinRate')::int as spin_rate,
                    (event->'pitchData'->'breaks'->>'breakHorizontal')::numeric as break_horizontal,
                    (event->'pitchData'->'breaks'->>'breakVerticalInduced')::numeric as break_vertical,
                    (event->'pitchData'->>'extension')::numeric as extension
                FROM raw_mlb.live_feed_snapshots lfs,
                     jsonb_array_elements(lfs.payload->'liveData'->'plays'->'allPlays') as play,
                     jsonb_array_elements(play->'playEvents') as event
                WHERE lfs.http_status = 200
                  AND event->>'type' = 'pitch'
                  AND event->'pitchData' IS NOT NULL
                  AND event->>'pitchNumber' IS NOT NULL
                  AND event->'pitchData'->>'startSpeed' IS NOT NULL
                ON CONFLICT (game_pk, event_sequence, pitch_number) DO NOTHING;
            """)

            # Check how many pitches we extracted
            cur.execute('SELECT COUNT(*) FROM mlb_enhanced.statcast_pitches;')
            pitch_count = cur.fetchone()[0]

            print(f'✅ Extracted {pitch_count} Statcast pitches')

            if pitch_count > 0:
                # Show some statistics
                cur.execute("""
                    SELECT
                        COUNT(*) as total_pitches,
                        ROUND(AVG(start_speed), 1) as avg_velocity,
                        ROUND(AVG(spin_rate), 0) as avg_spin,
                        COUNT(DISTINCT pitch_type_code) as pitch_types,
                        ROUND(AVG(plate_x), 2) as avg_plate_x,
                        ROUND(AVG(plate_z), 2) as avg_plate_z
                    FROM mlb_enhanced.statcast_pitches
                    WHERE start_speed IS NOT NULL AND spin_rate IS NOT NULL;
                """)

                stats = cur.fetchone()
                if stats:
                    print(f'   Average velocity: {stats[1]} mph')
                    print(f'   Average spin rate: {stats[2]} rpm')
                    print(f'   Unique pitch types: {stats[3]}')
                    print(f'   Average plate position: ({stats[4]}, {stats[5]})')

        conn.commit()

    finally:
        conn.close()


def extract_matchup_history():
    """Extract batter-pitcher matchup history from existing events."""
    print('🤝 Extracting batter-pitcher matchup history...')

    conn = psycopg2.connect(**database_kwargs())
    try:
        with conn.cursor() as cur:
            # Aggregate matchup data from existing live events
            cur.execute("""
                INSERT INTO mlb_enhanced.batter_pitcher_history (
                    batter_id, pitcher_id, season,
                    total_pa, hits, home_runs, walks, strikeouts,
                    avg, slg, obp, ops
                )
                SELECT
                    e.batter_id::text,
                    e.pitcher_id::text,
                    EXTRACT(YEAR FROM g.game_date::date)::int as season,
                    COUNT(*) as total_pa,
                    COUNT(CASE WHEN e.is_hit THEN 1 END) as hits,
                    COUNT(CASE WHEN e.is_home_run THEN 1 END) as home_runs,
                    COUNT(CASE WHEN e.is_walk THEN 1 END) as walks,
                    COUNT(CASE WHEN e.is_strikeout THEN 1 END) as strikeouts,
                    ROUND(AVG(e.is_hit::int)::numeric, 3) as avg,
                    ROUND(
                        (COUNT(CASE WHEN e.is_hit THEN 1 END)
                       + COUNT(CASE WHEN e.hit_value = 2 THEN 1 END)
                       + 2 * COUNT(CASE WHEN e.hit_value = 3 THEN 1 END)
                       + 3 * COUNT(CASE WHEN e.is_home_run THEN 1 END))::numeric
                        / NULLIF(COUNT(CASE WHEN e.is_at_bat THEN 1 END), 0),
                        3
                    ) as slg,
                    ROUND(
                        (COUNT(CASE WHEN e.is_hit OR e.is_walk THEN 1 END))::numeric
                        / NULLIF(COUNT(*), 0),
                        3
                    ) as obp,
                    ROUND(
                        (COUNT(CASE WHEN e.is_hit OR e.is_walk THEN 1 END))::numeric
                        / NULLIF(COUNT(*), 0)
                      + (COUNT(CASE WHEN e.is_hit THEN 1 END)
                       + COUNT(CASE WHEN e.hit_value = 2 THEN 1 END)
                       + 2 * COUNT(CASE WHEN e.hit_value = 3 THEN 1 END)
                       + 3 * COUNT(CASE WHEN e.is_home_run THEN 1 END))::numeric
                        / NULLIF(COUNT(CASE WHEN e.is_at_bat THEN 1 END), 0),
                        3
                    ) as ops
                FROM core.live_events e
                JOIN core.live_games g ON e.game_id = g.game_id
                WHERE e.batter_id IS NOT NULL
                  AND e.pitcher_id IS NOT NULL
                  AND e.is_plate_appearance = true
                  AND EXTRACT(YEAR FROM g.game_date::date) >= 2020
                GROUP BY e.batter_id, e.pitcher_id, season
                HAVING COUNT(*) >= 3  -- At least 3 plate appearances
                ON CONFLICT (batter_id, pitcher_id, season) DO UPDATE SET
                    total_pa = EXCLUDED.total_pa,
                    hits = EXCLUDED.hits,
                    home_runs = EXCLUDED.home_runs,
                    walks = EXCLUDED.walks,
                    strikeouts = EXCLUDED.strikeouts,
                    avg = EXCLUDED.avg,
                    slg = EXCLUDED.slg,
                    obp = EXCLUDED.obp,
                    ops = EXCLUDED.ops;
            """)

            # Check matchup stats
            cur.execute('SELECT COUNT(*) FROM mlb_enhanced.batter_pitcher_history;')
            matchup_count = cur.fetchone()[0]

            print(f'✅ Extracted {matchup_count} batter-pitcher matchups')

        conn.commit()

    finally:
        conn.close()


def create_enhanced_training_dataset():
    """Create enhanced training dataset with new features."""
    print('🔬 Creating enhanced training dataset...')

    conn = psycopg2.connect(**database_kwargs())
    try:
        with conn.cursor() as cur:
            # Create enhanced training table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS mlb_enhanced.win_probability_training_enhanced AS
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
                    gsf.batting_team_wins,

                    -- Basic player features
                    COALESCE(bs.batting_avg, 0.250) as batter_avg,
                    COALESCE(ps.era, 4.00) as pitcher_era,
                    COALESCE(ts.win_pct, 0.500) as team_win_pct,

                    -- Enhanced Statcast features
                    COALESCE(sp.start_speed, 92.0) as pitch_velocity,
                    COALESCE(sp.spin_rate, 2400) as pitch_spin_rate,
                    CASE
                        WHEN sp.plate_x IS NOT NULL AND sp.plate_z IS NOT NULL THEN
                            POWER(sp.plate_x - 0, 2) + POWER(sp.plate_z - 2.5, 2)
                        ELSE 10.0
                    END as pitch_distance_from_center,

                    -- Enhanced matchup features
                    COALESCE(mh.total_pa, 0) as matchup_pa,
                    COALESCE(mh.avg, 0.220) as matchup_avg,
                    COALESCE(mh.slg, 0.350) as matchup_slg,

                    -- Enhanced player metrics (placeholder for now)
                    88.0 as batter_exit_velocity,  -- Will populate with real data
                    12.0 as batter_launch_angle,
                    27.0 as batter_sprint_speed,
                    8.5 as pitcher_k_per_9

                FROM mlb_features.game_state_features gsf
                -- Join to latest pitch for this event
                LEFT JOIN mlb_enhanced.statcast_pitches sp ON gsf.game_id LIKE '%' || sp.game_pk::text || '%'
                    AND gsf.event_sequence = sp.event_sequence
                    AND sp.pitch_number = (
                        SELECT MAX(sp2.pitch_number)
                        FROM mlb_enhanced.statcast_pitches sp2
                        WHERE sp2.game_pk = sp.game_pk AND sp2.event_sequence = sp.event_sequence
                    )
                -- Player season stats
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
                  AND gsf.inning <= 9;
            """)

            # Check enhanced dataset size
            cur.execute('SELECT COUNT(*) FROM mlb_enhanced.win_probability_training_enhanced;')
            enhanced_count = cur.fetchone()[0]

            print(f'✅ Created enhanced dataset with {enhanced_count} samples')

        conn.commit()

    finally:
        conn.close()


def main():
    print('🚀 MLB Enhanced Features Extraction')
    print('=' * 50)
    print('📍 Separate schema: mlb_enhanced (no impact on current pipeline)')

    # Extract enhanced features
    extract_statcast_pitches()
    extract_matchup_history()
    create_enhanced_training_dataset()

    print('\n' + '=' * 50)
    print('✅ ENHANCED FEATURES READY')
    print('=' * 50)
    print('• Statcast pitch physics extracted')
    print('• Batter-pitcher matchup history built')
    print('• Enhanced training dataset created')
    print('• Current pipeline completely unaffected')

    print('\n🎯 Ready to train enhanced model!')
    print('Next: Train new model with 20+ features vs current 15')


if __name__ == '__main__':
    main()
