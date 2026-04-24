#!/usr/bin/env python3
"""
Populate MLB pitches table from raw game feeds and demonstrate enhanced features.
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


def populate_pitches_table():
    """Populate the mlb.pitches table with Statcast data."""
    print('⚾ Populating MLB pitches table...')

    conn = psycopg2.connect(**database_kwargs())
    try:
        with conn.cursor() as cur:
            # Clear existing data
            cur.execute('TRUNCATE TABLE mlb.pitches;')

            # Insert pitch data from raw feeds
            cur.execute("""
                INSERT INTO mlb.pitches (
                    game_pk, event_index, pitch_index, pitch_number,
                    pitch_type_code, pitch_type_description, pitch_call_code,
                    plate_x, plate_z, start_speed, spin_rate
                )
                SELECT
                    lfs.game_pk,
                    (play->>'atBatIndex')::int as event_index,
                    (event->>'pitchNumber')::int - 1 as pitch_index,
                    (event->>'pitchNumber')::int as pitch_number,
                    event->'details'->'type'->>'code' as pitch_type_code,
                    event->'details'->'type'->>'description' as pitch_type_description,
                    event->'details'->'call'->>'code' as pitch_call_code,
                    (event->'pitchData'->'coordinates'->>'pX')::numeric as plate_x,
                    (event->'pitchData'->'coordinates'->>'pZ')::numeric as plate_z,
                    (event->'pitchData'->>'startSpeed')::numeric as start_speed,
                    (event->'pitchData'->'breaks'->>'spinRate')::int as spin_rate
                FROM raw_mlb.live_feed_snapshots lfs,
                     jsonb_array_elements(lfs.payload->'liveData'->'plays'->'allPlays') as play,
                     jsonb_array_elements(play->'playEvents') as event
                WHERE lfs.http_status = 200
                  AND event->>'type' = 'pitch'
                  AND event->'pitchData' IS NOT NULL
                  AND event->>'pitchNumber' IS NOT NULL
                ON CONFLICT (game_pk, event_index, pitch_index) DO NOTHING;
            """)

            # Check how many pitches we inserted
            cur.execute('SELECT COUNT(*) FROM mlb.pitches;')
            pitch_count = cur.fetchone()[0]

            print(f'✅ Inserted {pitch_count} pitches with Statcast data')

            # Show some statistics
            cur.execute("""
                SELECT
                    COUNT(*) as total_pitches,
                    ROUND(AVG(start_speed), 1) as avg_velocity,
                    ROUND(AVG(spin_rate), 0) as avg_spin,
                    COUNT(*) FILTER (WHERE plate_x IS NOT NULL) as pitches_with_location,
                    COUNT(DISTINCT pitch_type_code) as pitch_types
                FROM mlb.pitches
                WHERE start_speed IS NOT NULL AND spin_rate IS NOT NULL;
            """)

            stats = cur.fetchone()
            if stats and stats[1] is not None:
                print(f'   Average velocity: {stats[1]} mph')
                print(f'   Average spin rate: {stats[2]} rpm')
                print(f'   Pitches with location: {stats[3]}')
                print(f'   Unique pitch types: {stats[4]}')
            else:
                print('   No pitch data found with valid statistics')

        conn.commit()

    finally:
        conn.close()


def create_enhanced_features():
    """Create enhanced feature set with Statcast and matchup data."""
    print('🔬 Creating enhanced feature set...')

    conn = psycopg2.connect(**database_kwargs())
    try:
        with conn.cursor() as cur:
            # Create enhanced training dataset
            cur.execute("""
                CREATE TABLE IF NOT EXISTS mlb_models.win_probability_training_enhanced AS
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

                    -- Statcast pitch features (NEW)
                    COALESCE(p.start_speed, 90.0) as pitch_velocity,
                    COALESCE(p.spin_rate, 2200) as pitch_spin_rate,
                    CASE
                        WHEN p.plate_x IS NOT NULL AND p.plate_z IS NOT NULL THEN
                            POWER(p.plate_x - 0, 2) + POWER(p.plate_z - 2.5, 2)
                        ELSE 10.0
                    END as pitch_distance_from_center,

                    -- Matchup history (NEW)
                    COALESCE(mh.plate_appearances, 0) as matchup_pa,
                    COALESCE(mh.avg, 0.200) as matchup_avg,
                    COALESCE(mh.slg, 0.300) as matchup_slg,

                    -- Advanced player metrics (NEW)
                    COALESCE(bs.avg_exit_velocity, 88.0) as batter_exit_velocity,
                    COALESCE(bs.avg_launch_angle, 12.0) as batter_launch_angle,
                    COALESCE(bs.sprint_speed, 27.0) as batter_sprint_speed,

                    -- Pitcher advanced metrics (NEW)
                    COALESCE(ps.k_per_9, 8.0) as pitcher_k_per_9,
                    COALESCE(ps.avg_exit_velocity, 88.0) as pitcher_exit_velocity_allowed

                FROM mlb_features.game_state_features gsf
                -- Join to get latest pitch for this event
                LEFT JOIN mlb.pitches p ON gsf.game_id LIKE '%' || p.game_pk::text || '%'
                    AND gsf.event_sequence = p.event_index
                    AND p.pitch_index = (
                        SELECT MAX(p2.pitch_index) FROM mlb.pitches p2
                        WHERE p2.game_pk = p.game_pk AND p2.event_index = p.event_index
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
                LEFT JOIN mlb_features.batter_pitcher_matchups mh ON gsf.batter_id = mh.batter_id
                    AND gsf.pitcher_id = mh.pitcher_id AND gsf.season = mh.season

                WHERE gsf.season BETWEEN 2020 AND 2023
                  AND gsf.data_source = 'mlb'
                  AND gsf.inning <= 9;  -- Focus on regulation innings
            """)

            # Check enhanced dataset size
            cur.execute('SELECT COUNT(*) FROM mlb_models.win_probability_training_enhanced;')
            enhanced_count = cur.fetchone()[0]

            print(f'✅ Created enhanced dataset with {enhanced_count} samples')

            # Show feature comparison
            cur.execute("""
                SELECT
                    'Basic Model' as model,
                    15 as features,
                    0.847 as auc,
                    408814 as samples
                UNION ALL
                SELECT
                    'Enhanced Model' as model,
                    20 as features,
                    NULL as auc,  -- To be calculated
                    COUNT(*) as samples
                FROM mlb_models.win_probability_training_enhanced;
            """)

            print('\n📊 Feature Comparison:')
            print('Model         | Features | AUC   | Samples')
            print('-' * 40)
            for row in cur.fetchall():
                auc_str = '.3f' if row[2] else 'TBD'
                print('14')

        conn.commit()

    finally:
        conn.close()


def main():
    print('🚀 MLB Enhanced Feature Engineering')
    print('=' * 50)

    # Populate pitches table
    populate_pitches_table()

    # Create enhanced features
    create_enhanced_features()

    print('\n🎯 Enhanced Features Added:')
    print('✅ Statcast: Pitch velocity, spin rate, location')
    print('✅ Matchups: Batter vs. pitcher history')
    print('✅ Advanced: Exit velocity, launch angle, sprint speed')
    print('✅ Context: Pitcher K/9, quality of contact allowed')

    print('\n📈 Expected Performance Improvement:')
    print('• Current AUC: 0.847')
    print('• With Statcast: +0.03 → 0.88')
    print('• With Matchups: +0.02 → 0.90')
    print('• With Advanced: +0.01 → 0.91')
    print('• Realistic Target: 0.89-0.93 AUC')


if __name__ == '__main__':
    main()
