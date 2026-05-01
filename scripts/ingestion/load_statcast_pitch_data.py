#!/usr/bin/env python3
"""
Load pitch-level Statcast data into PostgreSQL with PostGIS.

Reference: Baseball Savant CSV Documentation
- URL: https://baseballsavant.mlb.com/csv-docs
- Based on pybaseball library schema: https://github.com/jldbc/pybaseball

Usage:
    python scripts/ingestion/load_statcast_pitch_data.py --seasons 2008,2024
    python scripts/ingestion/load_statcast_pitch_data.py --all
"""

import argparse
import os
from pathlib import Path

import pandas as pd
import psycopg2
from sqlalchemy import create_engine, text


ROOT = Path(__file__).resolve().parents[1]
STATCAST_YEARS = list(range(2008, 2026))  # Statcast available from 2008


def get_db_connection():
    """Get database connection."""
    return psycopg2.connect(
        host=os.getenv('PGHOST', 'localhost'),
        port=int(os.getenv('PGPORT', 5432)),
        database=os.getenv('PGDATABASE', 'retrosheet'),
        user=os.getenv('PGUSER', os.getenv('USER')),
    )


def get_database_url():
    """Get SQLAlchemy database URL."""
    # Use psycopg2 driver
    user = os.getenv('PGUSER', os.getenv('USER', 'cbwinslow'))
    host = os.getenv('PGHOST', 'localhost')
    port = os.getenv('PGPORT', '5432')
    db = os.getenv('PGDATABASE', 'retrosheet')
    return f'postgresql+psycopg2://{user}@{host}:{port}/{db}'


# Full Statcast schema based on Baseball Savant documentation
STATCAST_COLUMNS = {
    # Identifiers
    'game_pk': 'INTEGER',
    'game_date': 'TEXT',
    'game_year': 'INTEGER',
    'game_type': 'TEXT',
    # Pitch identifiers
    'at_bat_number': 'INTEGER',
    'pitch_number': 'INTEGER',
    'sv_id': 'TEXT',  # Non-unique play ID
    # Player IDs
    'batter': 'INTEGER',
    'pitcher': 'INTEGER',
    'fielder_2': 'INTEGER',  # Catcher
    'fielder_3': 'INTEGER',  # 1B
    'fielder_4': 'INTEGER',  # 2B
    'fielder_5': 'INTEGER',  # 3B
    'fielder_6': 'INTEGER',  # SS
    'fielder_7': 'INTEGER',  # LF
    'fielder_8': 'INTEGER',  # CF
    'fielder_9': 'INTEGER',  # RF
    # Pitch type
    'pitch_type': 'TEXT',
    'pitch_name': 'TEXT',
    # Release point
    'release_speed': 'REAL',
    'release_spin_rate': 'REAL',
    'release_extension': 'REAL',
    'release_pos_x': 'REAL',
    'release_pos_y': 'REAL',
    'release_pos_z': 'REAL',
    # Movement (pfx = pitch f/x)
    'pfx_x': 'REAL',
    'pfx_z': 'REAL',
    # Velocity components
    'vx0': 'REAL',
    'vy0': 'REAL',
    'vz0': 'REAL',
    # Acceleration
    'ax': 'REAL',
    'ay': 'REAL',
    'az': 'REAL',
    # Plate location
    'plate_x': 'REAL',  # Horizontal from catcher's view (-17 to +17 inches)
    'plate_z': 'REAL',  # Vertical (feet)
    # Strike zone (per batter)
    'sz_top': 'REAL',
    'sz_bot': 'REAL',
    'zone': 'TEXT',
    # Count
    'balls': 'INTEGER',
    'strikes': 'INTEGER',
    # Result
    'type': 'TEXT',  # B=ball, S=strike, X=in play
    'description': 'TEXT',  # Full description
    'events': 'TEXT',  # Event result
    # Batted ball (if in play)
    'bb_type': 'TEXT',  # ground_ball, line_drive, fly_ball, popup
    'hit_distance_sc': 'REAL',
    'launch_speed': 'REAL',
    'launch_angle': 'REAL',
    'hc_x': 'REAL',  # Hit coordinate X
    'hc_y': 'REAL',  # Hit coordinate Y
    # Run values (Statcast)
    'woba_value': 'REAL',
    'woba_denom': 'REAL',
    'babip_value': 'REAL',
    'iso_value': 'REAL',
    'estimated_ba_using_speedangle': 'REAL',
    'estimated_woba_using_speedangle': 'REAL',
    'launch_speed_angle': 'REAL',
    # Game state
    'outs_when_up': 'INTEGER',
    'inning': 'INTEGER',
    'inning_topbot': 'TEXT',  # Top or bottom
    # Score
    'home_score': 'INTEGER',
    'away_score': 'INTEGER',
    'bat_score': 'INTEGER',
    'fld_score': 'INTEGER',
    'post_home_score': 'INTEGER',
    'post_away_score': 'INTEGER',
    'post_bat_score': 'INTEGER',
    'post_fld_score': 'INTEGER',
    # Teams
    'home_team': 'TEXT',
    'away_team': 'TEXT',
    # Run expectancy changes
    'delta_home_win_exp': 'REAL',
    'delta_run_exp': 'REAL',
    'delta_pitcher_run_exp': 'REAL',
    # Player info
    'stand': 'TEXT',  # Batter stance: L or R
    'p_throws': 'TEXT',  # Pitcher hand: L or R
    # Runners
    'on_1b': 'INTEGER',
    'on_2b': 'INTEGER',
    'on_3b': 'INTEGER',
    # Alignment
    'if_fielding_alignment': 'TEXT',
    'of_fielding_alignment': 'TEXT',
    # Advanced (2017+)
    'spin_axis': 'REAL',
    'effective_speed': 'REAL',
    # Pitch tracking (2017+)
    'bat_speed': 'REAL',
    'swing_length': 'REAL',
    'attack_angle': 'REAL',
    'attack_direction': 'REAL',
    'arm_angle': 'REAL',
    # Deprecated but sometimes present
    'spin_dir': 'REAL',
    'spin_rate_deprecated': 'REAL',
    'break_angle_deprecated': 'REAL',
    'break_length_deprecated': 'REAL',
}


def create_statcast_table(engine, schema: str = 'features_pitch'):
    """Create the statcast pitch table with PostGIS geometry."""

    columns_sql = []
    for col, dtype in STATCAST_COLUMNS.items():
        columns_sql.append(f'{col} {dtype}')

    sql = f"""
    CREATE SCHEMA IF NOT EXISTS {schema};

    DROP TABLE IF EXISTS {schema}.statcast_pitches;

    CREATE TABLE {schema}.statcast_pitches (
        id BIGSERIAL PRIMARY KEY,
        {', '.join(columns_sql)},
        location_point geometry(POINT, 4326)
    );

    -- Indexes for common queries
    CREATE INDEX idx_statcast_year ON {schema}.statcast_pitches(game_year);
    CREATE INDEX idx_statcast_game ON {schema}.statcast_pitches(game_pk);
    CREATE INDEX idx_statcast_pitcher ON {schema}.statcast_pitches(pitcher);
    CREATE INDEX idx_statcast_batter ON {schema}.statcast_pitches(batter);
    CREATE INDEX idx_statcast_pitch_type ON {schema}.statcast_pitches(pitch_type);
    CREATE INDEX idx_statcast_location ON {schema}.statcast_pitches USING GIST(location_point);

    -- Comments
    COMMENT ON TABLE {schema}.statcast_pitches IS 'Pitch-level Statcast data. Reference: Baseball Savant CSV Docs. Schema based on pybaseball library.';
    COMMENT ON COLUMN {schema}.statcast_pitches.plate_x IS 'Horizontal position when pitch crosses plate (inches, from catcher view)';
    COMMENT ON COLUMN {schema}.statcast_pitches.plate_z IS 'Vertical position when pitch crosses plate (feet)';
    COMMENT ON COLUMN {schema}.statcast_pitches.sz_top IS 'Top of batters strike zone';
    COMMENT ON COLUMN {schema}.statcast_pitches.sz_bot IS 'Bottom of batters strike zone';
    """

    with engine.connect() as conn:
        conn.execute(text(sql))
        conn.commit()

    print(f'Created table {schema}.statcast_pitches')


def load_statcast_data(
    engine,
    seasons: list[int] | None = None,
    limit: int | None = None,
    batch_size: int = 100000,
):
    """
    Load statcast data from raw_mlb.statcast into normalized table.

    Args:
        engine: SQLAlchemy engine
        seasons: List of seasons to load (e.g., [2023, 2024])
        limit: Limit number of rows per season
        batch_size: Batch size for inserts
    """
    schema = 'features_pitch'
    source_table = 'raw_mlb.statcast'

    if seasons is None:
        seasons = STATCAST_YEARS

    total_loaded = 0

    for year in seasons:
        print(f'\n=== Loading season {year} ===')

        # Query from source
        query = f"""
            SELECT * FROM {source_table}
            WHERE game_year = {year}
        """
        if limit:
            query += f' LIMIT {limit}'

        # Read in chunks
        chunks = pd.read_sql(query, engine, chunksize=batch_size)

        for _i, chunk in enumerate(chunks):
            # Add geometry columns
            if 'plate_x' in chunk.columns and 'plate_z' in chunk.columns:
                chunk['location_point'] = chunk.apply(
                    lambda r: (
                        f'SRID=4326;POINT({r["plate_x"]} {r["plate_z"]})'
                        if pd.notna(r['plate_x']) and pd.notna(r['plate_z'])
                        else None
                    ),
                    axis=1,
                )

            # Load to table
            chunk.to_sql('statcast_pitches', engine, schema=schema, if_exists='append', index=False)

            total_loaded += len(chunk)
            print(f'  Loaded {len(chunk)} rows (total: {total_loaded})')

    print(f'\n=== Total loaded: {total_loaded} ===')
    return total_loaded


def create_analysis_views(engine):
    """Create analysis views for pitch data."""

    views_sql = [
        """
        CREATE OR REPLACE VIEW eda.statcast_pitches_by_type AS
        SELECT
            pitch_type,
            COUNT(*) as total_pitches,
            AVG(plate_x) as avg_plate_x,
            AVG(plate_z) as avg_plate_z,
            AVG(release_speed) as avg_velocity,
            AVG(pfx_x) as avg_horiz_movement,
            AVG(pfx_z) as avg_vert_movement,
            -- Strike zone rate
            SUM(CASE
                WHEN plate_x BETWEEN -8.5 AND 8.5
                AND plate_z BETWEEN sz_bot AND sz_top
                THEN 1 ELSE 0 END)::numeric / COUNT(*) * 100 as in_zone_pct
        FROM features_pitch.statcast_pitches
        WHERE pitch_type IS NOT NULL
        GROUP BY pitch_type
        ORDER BY total_pitches DESC;
        """,
        """
        CREATE OR REPLACE VIEW eda.statcast_pitcher_arsenal AS
        SELECT
            pitcher,
            pitch_type,
            COUNT(*) as pitch_count,
            AVG(release_speed) as avg_velocity,
            AVG(pfx_x) as avg_horiz_movement,
            AVG(pfx_z) as avg_vert_movement
        FROM features_pitch.statcast_pitches
        WHERE pitcher IS NOT NULL AND pitch_type IS NOT NULL
        GROUP BY pitcher, pitch_type
        ORDER BY pitcher, pitch_count DESC;
        """,
        """
        CREATE OR REPLACE VIEW eda.statcast_batter_outcomes AS
        SELECT
            batter,
            pitch_type,
            COUNT(*) as pa,
            SUM(CASE WHEN type = 'X' THEN 1 ELSE 0 END) as in_play,
            SUM(CASE WHEN events LIKE '%home_run%' THEN 1 ELSE 0 END) as home_runs,
            AVG(launch_speed) as avg_exit_velo,
            AVG(launch_angle) as avg_launch_angle
        FROM features_pitch.statcast_pitches
        WHERE batter IS NOT NULL
        GROUP BY batter, pitch_type
        ORDER BY batter, pa DESC;
        """,
    ]

    with engine.connect() as conn:
        for sql in views_sql:
            conn.execute(text(sql))
        conn.commit()

    print('Created analysis views in eda schema')


def main():
    parser = argparse.ArgumentParser(description='Load Statcast pitch data')
    parser.add_argument('--seasons', type=str, help='Comma-separated seasons (e.g., "2023,2024")')
    parser.add_argument('--all', action='store_true', help='Load all available seasons')
    parser.add_argument('--limit', type=int, default=None, help='Limit rows per season')
    parser.add_argument(
        '--create-only',
        action='store_true',
        help='Only create table, do not load data',
    )
    args = parser.parse_args()

    engine = create_engine(get_database_url())

    # Determine seasons
    if args.all:
        seasons = STATCAST_YEARS
    elif args.seasons:
        seasons = [int(y.strip()) for y in args.seasons.split(',')]
    else:
        seasons = [2024]  # Default to latest

    # Create table
    create_statcast_table(engine)

    if not args.create_only:
        # Load data
        load_statcast_data(engine, seasons=seasons, limit=args.limit)

        # Create views
        create_analysis_views(engine)

    print('\nDone!')
    print('Data available in: features_pitch.statcast_pitches')
    print(
        'EDA views: eda.statcast_pitches_by_type, eda.statcast_pitcher_arsenal, eda.statcast_batter_outcomes',
    )


if __name__ == '__main__':
    main()
