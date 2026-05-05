"""Bridge service - wraps existing bridge population scripts.

Author: Agent cbwinslow/retrosheet
Date: 2026-04-26

This service wraps the existing scripts/bridge/populate_bridge_tables.py
and related scripts, preserving working logic while adding the new
baseball CLI interface for ID resolution and cross-referencing.
"""

import subprocess
import sys
from pathlib import Path

import psycopg2

from baseball.core.db import get_database_url


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class BridgeService:
    """Bridge service that wraps existing population scripts."""

    def __init__(self) -> None:
        """Initialize bridge service."""

    def populate_all(
        self,
        dry_run: bool = False,
        verbose: bool = False,
    ) -> dict[str, bool]:
        """Populate all bridge tables.

        Wraps: scripts/bridge/populate_bridge_tables.py

        Args:
            dry_run: Show what would be done without executing
            verbose: Show detailed output

        Returns:
            Dictionary of table names to success status
        """
        cmd = [
            sys.executable,
            'scripts/bridge/populate_bridge_tables.py',
        ]

        if dry_run:
            cmd.append('--dry-run')
        if verbose:
            cmd.append('--verbose')

        try:
            result = subprocess.run(
                cmd,
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=3600,  # 1 hour timeout
            )

            # Parse which tables were populated
            success = result.returncode == 0
            output = (
                result.stdout
                if verbose
                else result.stdout[-500:]
                if len(result.stdout) > 500
                else result.stdout
            )

            return {
                'players': success,
                'teams': success,
                'games': success,
                'parks': success,
                'coaches': success,
                'umpires': success,
                'output': output,
                'success': success,
            }
        except Exception as e:
            return {
                'players': False,
                'teams': False,
                'games': False,
                'parks': False,
                'coaches': False,
                'umpires': False,
                'error': str(e),
                'success': False,
            }

    def populate_players(
        self,
        dry_run: bool = False,
        verbose: bool = False,
    ) -> bool:
        """Populate player_xref bridge table.

        Wraps: scripts/bridge/ingest_chadwick_register.py
        """
        cmd = [
            sys.executable,
            'scripts/bridge/ingest_chadwick_register.py',
        ]

        if verbose:
            cmd.append('--verbose')

        try:
            result = subprocess.run(
                cmd,
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=600,  # 10 minute timeout
            )

            return result.returncode == 0
        except Exception:
            return False

    def populate_games(
        self,
        season: int | None = None,
        dry_run: bool = False,
    ) -> bool:
        """Populate game_xref bridge table.

        Wraps: scripts/bridge/populate_game_xref.py
        """
        cmd = [
            sys.executable,
            'scripts/bridge/populate_game_xref.py',
        ]

        if season:
            cmd.extend(['--season', str(season)])
        if dry_run:
            cmd.append('--dry-run')

        try:
            result = subprocess.run(
                cmd,
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=600,
            )
            return result.returncode == 0
        except Exception:
            return False

    def populate_teams(
        self,
        dry_run: bool = False,
    ) -> bool:
        """Populate team_xref bridge table.

        Wraps: scripts/bridge/populate_season_aware_team_xref.py
        """
        cmd = [
            sys.executable,
            'scripts/bridge/populate_season_aware_team_xref.py',
        ]

        if dry_run:
            cmd.append('--dry-run')

        try:
            result = subprocess.run(
                cmd,
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=300,
            )
            return result.returncode == 0
        except Exception:
            return False

    def resolve_id(
        self,
        source: str,
        source_id: str,
        entity_type: str = 'player',
    ) -> dict | None:
        """Resolve a source ID to canonical ID using bridge tables.

        Args:
            source: Source system (retrosheet, mlb, espn, statcast)
            source_id: ID in the source system
            entity_type: Type of entity (player, team, game, park)

        Returns:
            Dictionary with canonical_id and confidence, or None if not found
        """
        try:
            conn = psycopg2.connect(get_database_url())
            with conn.cursor() as cur:
                # Build query based on entity type
                if entity_type == 'player':
                    table = 'bridge.player_xref'
                    id_col = 'player_id'
                elif entity_type == 'team':
                    table = 'bridge.team_xref'
                    id_col = 'team_id'
                elif entity_type == 'game':
                    table = 'bridge.game_xref'
                    id_col = 'game_id'
                elif entity_type == 'park':
                    table = 'bridge.park_xref'
                    id_col = 'park_id'
                else:
                    return None

                # Check if source column exists
                source_col = f'{source}_id'
                cur.execute(
                    f"""
                    SELECT {id_col}, confidence
                    FROM {table}
                    WHERE {source_col} = %s
                    LIMIT 1
                """,
                    (source_id,),
                )

                row = cur.fetchone()
                if row:
                    return {
                        'canonical_id': row[0],
                        'confidence': row[1] if len(row) > 1 else 1.0,
                    }

            conn.close()
            return None
        except Exception as e:
            return {'error': str(e)}

    def lookup_canonical(
        self,
        canonical_id: str,
        entity_type: str = 'player',
    ) -> dict | None:
        """Look up all source IDs for a canonical ID.

        Args:
            canonical_id: Canonical ID
            entity_type: Type of entity

        Returns:
            Dictionary mapping source names to IDs
        """
        try:
            conn = psycopg2.connect(get_database_url())
            with conn.cursor() as cur:
                if entity_type == 'player':
                    cur.execute(
                        """
                        SELECT retrosheet_id, mlb_id, espn_id, statcast_id
                        FROM bridge.player_xref
                        WHERE player_id = %s
                    """,
                        (canonical_id,),
                    )
                elif entity_type == 'team':
                    cur.execute(
                        """
                        SELECT retrosheet_id, mlb_id, espn_id
                        FROM bridge.team_xref
                        WHERE team_id = %s
                    """,
                        (canonical_id,),
                    )
                elif entity_type == 'game':
                    cur.execute(
                        """
                        SELECT retrosheet_id, mlb_id
                        FROM bridge.game_xref
                        WHERE game_id = %s
                    """,
                        (canonical_id,),
                    )
                else:
                    return None

                row = cur.fetchone()
                if row:
                    return {
                        'retrosheet': row[0],
                        'mlb': row[1],
                        'espn': row[2] if len(row) > 2 else None,
                        'statcast': row[3] if len(row) > 3 else None,
                    }

            conn.close()
            return None
        except Exception as e:
            return {'error': str(e)}

    def find_matches(
        self,
        source_a: str,
        source_b: str,
        entity_type: str,
        limit: int = 50,
        min_confidence: float = 0.5,
    ) -> dict:
        """Find matches between two source systems.

        Args:
            source_a: First source system (retrosheet, mlb, espn, statcast)
            source_b: Second source system
            entity_type: Type of entity (player, team, game, park)
            limit: Maximum number of matches to return
            min_confidence: Minimum confidence threshold

        Returns:
            Dictionary with matches and statistics
        """
        try:
            conn = psycopg2.connect(get_database_url())
            with conn.cursor() as cur:
                # Build query based on entity type
                if entity_type == 'player':
                    table = 'bridge.player_xref'
                    name_cols = 'first_name, last_name'
                elif entity_type == 'team':
                    table = 'bridge.team_xref'
                    name_cols = 'name'
                elif entity_type == 'game':
                    table = 'bridge.game_xref'
                    name_cols = 'game_date'
                elif entity_type == 'park':
                    table = 'bridge.park_xref'
                    name_cols = 'name'
                else:
                    return {'error': f'Unsupported entity type: {entity_type}'}

                # Validate source systems
                valid_sources = ['retrosheet', 'mlb', 'espn', 'statcast']
                if source_a not in valid_sources or source_b not in valid_sources:
                    return {'error': f'Invalid source system. Valid: {valid_sources}'}

                # Get total counts for statistics
                cur.execute(f"""
                    SELECT 
                        COUNT({source_a}_id) as {source_a}_total,
                        COUNT({source_b}_id) as {source_b}_total,
                        COUNT(*) as total_records
                    FROM {table}
                    WHERE {source_a}_id IS NOT NULL AND {source_b}_id IS NOT NULL
                """)
                
                stats_row = cur.fetchone()
                stats = {
                    f'{source_a}_total': stats_row[0] if stats_row else 0,
                    f'{source_b}_total': stats_row[1] if stats_row else 0,
                    'total_records': stats_row[2] if stats_row else 0,
                }

                # Find matches between the two sources
                match_query = f"""
                    SELECT 
                        {source_a}_id,
                        {source_b}_id,
                        player_id as canonical_id,
                        confidence,
                        {name_cols}
                    FROM {table}
                    WHERE {source_a}_id IS NOT NULL 
                    AND {source_b}_id IS NOT NULL
                    AND confidence >= %s
                    ORDER BY confidence DESC
                    LIMIT %s
                """ if entity_type == 'player' else f"""
                    SELECT 
                        {source_a}_id,
                        {source_b}_id,
                        team_id as canonical_id,
                        confidence,
                        {name_cols}
                    FROM {table}
                    WHERE {source_a}_id IS NOT NULL 
                    AND {source_b}_id IS NOT NULL
                    AND confidence >= %s
                    ORDER BY confidence DESC
                    LIMIT %s
                """ if entity_type == 'team' else f"""
                    SELECT 
                        {source_a}_id,
                        {source_b}_id,
                        game_id as canonical_id,
                        confidence,
                        {name_cols}
                    FROM {table}
                    WHERE {source_a}_id IS NOT NULL 
                    AND {source_b}_id IS NOT NULL
                    AND confidence >= %s
                    ORDER BY confidence DESC
                    LIMIT %s
                """ if entity_type == 'park' else f"""
                    SELECT 
                        {source_a}_id,
                        {source_b}_id,
                        park_id as canonical_id,
                        confidence,
                        {name_cols}
                    FROM {table}
                    WHERE {source_a}_id IS NOT NULL 
                    AND {source_b}_id IS NOT NULL
                    AND confidence >= %s
                    ORDER BY confidence DESC
                    LIMIT %s
                """

                cur.execute(match_query, (min_confidence, limit))
                rows = cur.fetchall()

                # Format results
                matches = []
                for row in rows:
                    match = {
                        f'{source_a}_id': row[0],
                        f'{source_b}_id': row[1],
                        'canonical_id': row[2],
                        'confidence': float(row[3]) if row[3] else 0.0,
                    }
                    
                    # Add name information based on entity type
                    if entity_type == 'player' and len(row) > 4:
                        match['first_name'] = row[4] if len(row) > 4 else ''
                        match['last_name'] = row[5] if len(row) > 5 else ''
                        match['name'] = f"{match['first_name']} {match['last_name']}".strip()
                    elif entity_type in ['team', 'park'] and len(row) > 4:
                        match['name'] = row[4] if len(row) > 4 else ''
                    elif entity_type == 'game' and len(row) > 4:
                        match['date'] = row[4] if len(row) > 4 else ''
                    
                    matches.append(match)

                # Calculate match rate
                match_rate = 0.0
                if stats['total_records'] > 0:
                    match_rate = len(matches) / stats['total_records'] * 100

                stats['match_rate'] = match_rate

            conn.close()
            return {
                'matches': matches,
                'stats': stats,
                'source_a': source_a,
                'source_b': source_b,
                'entity_type': entity_type,
            }

        except Exception as e:
            return {'error': str(e)}

    def get_coverage_stats(self) -> dict:
        """Get bridge table coverage statistics."""
        try:
            conn = psycopg2.connect(get_database_url())
            with conn.cursor() as cur:
                # Get counts from each bridge table
                stats = {}
                tables = [
                    ('bridge.player_xref', 'players'),
                    ('bridge.team_xref', 'teams'),
                    ('bridge.game_xref', 'games'),
                    ('bridge.park_xref', 'parks'),
                ]

                for table, name in tables:
                    try:
                        cur.execute(f'SELECT COUNT(*) FROM {table}')
                        total = cur.fetchone()[0]

                        cur.execute(f"""
                            SELECT COUNT(*)
                            FROM {table}
                            WHERE mlb_id IS NOT NULL
                        """)
                        with_mlb = cur.fetchone()[0]

                        stats[name] = {
                            'total': total,
                            'with_mlb_id': with_mlb,
                            'coverage_pct': round(with_mlb / total * 100, 2) if total > 0 else 0,
                        }
                    except Exception as e:
                        stats[name] = {'error': str(e)}

            conn.close()
            return stats
        except Exception as e:
            return {'error': str(e)}
