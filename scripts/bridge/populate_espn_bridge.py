#!/usr/bin/env python3
"""
Populate ESPN Bridge Tables
Extracts ESPN player and team IDs from raw_espn tables and creates cross-reference mappings.

Usage:
    python3 scripts/bridge/populate_espn_bridge.py

Dependencies:
    - raw_espn.game_snapshots must contain ESPN game data
    - bridge.player_xref must be populated (from Chadwick Register)
    - bridge.team_xref must be populated (from Chadwick Register)

Note: ESPN uses integer IDs that match MLBAM IDs, so we can use existing bridge tables for mapping.
"""

import os

import psycopg2
from dotenv import load_dotenv
from psycopg2 import Error

load_dotenv()


def get_db_connection():
    """Get PostgreSQL connection from environment variables."""
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        return psycopg2.connect(db_url)
    else:
        return psycopg2.connect(
            host=os.getenv("PGHOST", "localhost"),
            port=os.getenv("PGPORT", "5432"),
            database=os.getenv("PGDATABASE", "retrosheet"),
            user=os.getenv("PGUSER", os.getenv("USER")),
            password=os.getenv("PGPASSWORD"),
        )


def populate_espn_player_xref():
    """Populate bridge.external_player_xref for ESPN using bridge.player_xref mlb_id mappings.

    ESPN player IDs are integer MLBAM IDs, so we can match them directly via bridge.player_xref.mlb_id.
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Extract ESPN player IDs from raw_espn.game_snapshots
            # Match to Retrosheet IDs via bridge.player_xref.mlb_id
            cur.execute("""
                INSERT INTO bridge.external_player_xref (external_source, external_player_id, retrosheet_player_id)
                SELECT DISTINCT 
                    'espn' as external_source,
                    (player_data->'id')::text as external_player_id,
                    px.retrosheet_id as retrosheet_player_id
                FROM (
                    -- Extract player IDs from game snapshots (leaders/athletes)
                    SELECT 
                        jsonb_array_elements(raw_payload->'events'->0->'competitors') as competitor
                    FROM raw_espn.game_snapshots
                    WHERE raw_payload IS NOT NULL
                ) comp
                CROSS JOIN jsonb_array_elements(comp.competitor->'leaders') as leader_data
                CROSS JOIN jsonb_array_elements(comp.competitor->'roster') as player_data
                JOIN (
                    SELECT mlb_id, retrosheet_id 
                    FROM bridge.player_xref 
                    WHERE mlb_id IS NOT NULL 
                    AND retrosheet_id IS NOT NULL 
                    AND retrosheet_id != ''
                ) px ON (player_data->'player'->>'id')::int = px.mlb_id
                WHERE (player_data->'player'->>'id') IS NOT NULL
                ON CONFLICT (external_source, external_player_id) DO UPDATE SET
                    retrosheet_player_id = EXCLUDED.retrosheet_player_id
            """)

            player_count = cur.rowcount
            conn.commit()
            print(f"Populated {player_count} ESPN player mappings in bridge.external_player_xref")
            return player_count
    except Error as e:
        print(f"Error populating ESPN player_xref: {e}")
        conn.rollback()
        return 0
    finally:
        conn.close()


def populate_espn_team_xref():
    """Populate bridge.external_team_xref for ESPN using bridge.team_xref mlb_team_id mappings.

    ESPN team IDs are integer MLB team IDs, so we can match them directly via bridge.team_xref.mlb_team_id.
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Extract ESPN team IDs from raw_espn.game_snapshots
            # Match to Retrosheet IDs via bridge.team_xref.mlb_team_id
            cur.execute("""
                INSERT INTO bridge.external_team_xref (external_source, external_team_id, retrosheet_team_id)
                SELECT DISTINCT 
                    'espn' as external_source,
                    (team_data->'id')::text as external_team_id,
                    tx.retrosheet_team_id as retrosheet_team_id
                FROM raw_espn.game_snapshots
                CROSS JOIN jsonb_array_elements(raw_payload->'events'->0->'competitors') as competitor
                CROSS JOIN jsonb_array_elements(competitor->'team') as team_data
                JOIN (
                    SELECT mlb_team_id, retrosheet_team_id 
                    FROM bridge.team_xref 
                    WHERE mlb_team_id IS NOT NULL 
                    AND retrosheet_team_id IS NOT NULL 
                    AND retrosheet_team_id != ''
                ) tx ON (team_data->>'id')::int = tx.mlb_team_id
                WHERE raw_payload IS NOT NULL
                AND (team_data->>'id') IS NOT NULL
                ON CONFLICT (external_source, external_team_id) DO UPDATE SET
                    retrosheet_team_id = EXCLUDED.retrosheet_team_id
            """)

            team_count = cur.rowcount
            conn.commit()
            print(f"Populated {team_count} ESPN team mappings in bridge.external_team_xref")
            return team_count
    except Error as e:
        print(f"Error populating ESPN team_xref: {e}")
        conn.rollback()
        return 0
    finally:
        conn.close()


def populate_espn_coach_xref():
    """Populate bridge.coach_xref.espn_coach_id from ESPN data.

    Note: ESPN coach data location in JSON needs to be determined.
    This is a placeholder for future implementation.
    """
    print("ESPN coach ID mapping not yet implemented - JSON structure needs investigation")
    return 0


def populate_espn_umpire_xref():
    """Populate bridge.umpire_xref.espn_umpire_id from ESPN data.

    Note: ESPN umpire data location in JSON needs to be determined.
    This is a placeholder for future implementation.
    """
    print("ESPN umpire ID mapping not yet implemented - JSON structure needs investigation")
    return 0


def main():
    print("Populating ESPN bridge tables...")

    player_count = populate_espn_player_xref()
    team_count = populate_espn_team_xref()
    coach_count = populate_espn_coach_xref()
    umpire_count = populate_espn_umpire_xref()

    print("\nSummary:")
    print(f"  Players: {player_count}")
    print(f"  Teams: {team_count}")
    print(f"  Coaches: {coach_count}")
    print(f"  Umpires: {umpire_count}")
    print(f"  Total: {player_count + team_count + coach_count + umpire_count}")


if __name__ == "__main__":
    main()
