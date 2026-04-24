#!/usr/bin/env python3
"""
Orchestrate Complete Feature Population

Master script to populate ALL engineered features in the correct order.
Uses SQL-first approach with wrapper scripts for repeatability.

Execution Order:
    Phase 0: Prerequisites (base_features must be populated)
    Phase 1: Core Engineered Features (005-006)
    Phase 2: Additional Features (007-008)
    Phase 3: Extended Features (009-011)
    Phase 4: Context Features (012-014)
    Phase 5: Final Features (015-017)
    Phase 6: Specialized Features (020-070)
    Phase 7: Verification & Views (099)

Usage:
    # Run all phases
    uv run python scripts/pitch_data/orchestrate_feature_population.py --all

    # Run specific phase
    uv run python scripts/pitch_data/orchestrate_feature_population.py --phase 3

    # Run batch population for remaining rows
    uv run python scripts/pitch_data/orchestrate_feature_population.py --batch --phase 2

    # Verify population status
    uv run python scripts/pitch_data/orchestrate_feature_population.py --verify

    # Dry run (show what would be executed)
    uv run python scripts/pitch_data/orchestrate_feature_population.py --all --dry-run

Author: Agent Cascade
Date: 2026-04-24
"""

import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Tuple

import psycopg2
from psycopg2.extras import RealDictCursor

# Configuration
DB_URL = "postgresql://localhost:5432/retrosheet"
SQL_DIR = Path("/home/cbwinslow/workspace/retrosheet/sql/features")

# Phase definitions: (phase_number, name, description, sql_files)
PHASES: List[Tuple[int, str, str, List[str]]] = [
    (
        0,
        "Prerequisites",
        "Verify base_features exists and has data",
        [],
    ),
    (
        1,
        "Core Engineered Features",
        "Base feature engineering from pitch physics and outcomes",
        [
            "005_build_engineered_features.sql",
            "006_additional_engineered_features.sql",
            "007_populate_additional_features.sql",
        ],
    ),
    (
        2,
        "Additional Features Batch",
        "Batch population of platoon, spin, fatigue, pressure features",
        [
            "008_populate_additional_features_batch.sql",
        ],
    ),
    (
        3,
        "Extended Features",
        "Pitch quality, count leverage, TTOP, game situation",
        [
            "009_more_engineered_features.sql",
            "010_populate_more_features.sql",
        ],
    ),
    (
        4,
        "Extended Features Batch",
        "Batch population of quality scores, RE24, WPA",
        [
            "011_populate_more_features_batch.sql",
        ],
    ),
    (
        5,
        "Context Features Schema",
        "Weather, momentum, umpire, attendance, park schema",
        [
            "012_context_features_schema.sql",
        ],
    ),
    (
        6,
        "Context Features Population",
        "Populate context features from core tables",
        [
            "013_populate_context_features.sql",
        ],
    ),
    (
        7,
        "Context Features Batch",
        "Batch population of weather, momentum, umpire data",
        [
            "014_populate_context_features_batch.sql",
        ],
    ),
    (
        8,
        "Final Features Schema",
        "Markov chains, matchups, postseason, sequence patterns",
        [
            "015_final_features_schema.sql",
        ],
    ),
    (
        9,
        "Final Features Population",
        "Populate Markov, matchup, postseason features",
        [
            "016_populate_final_features.sql",
        ],
    ),
    (
        10,
        "Final Features Batch",
        "Batch population of remaining final features",
        [
            "017_populate_final_features_batch.sql",
        ],
    ),
    (
        11,
        "Specialized Features",
        "Attendance/weather, momentum, umpire, postseason, matchup, stadium",
        [
            "020_attendance_weather_features.sql",
            "030_momentum_features.sql",
            "040_umpire_features.sql",
            "050_postseason_clutch_features.sql",
            "060_batter_pitcher_matchup_features.sql",
            "070_stadium_physics_features.sql",
        ],
    ),
    (
        12,
        "Enhanced Views",
        "Create final feature views for model training",
        [
            "099_enhanced_feature_view.sql",
            "099_phase2_enhanced_feature_view.sql",
            "099_phase3_final_enhanced_view.sql",
        ],
    ),
]


def get_connection():
    """Get database connection."""
    return psycopg2.connect(DB_URL)


def verify_prerequisites(conn) -> Tuple[bool, str]:
    """Verify that base_features exists and has data."""
    with conn.cursor() as cur:
        # Check if base_features exists
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = 'features_pitch'
                AND table_name = 'base_features'
            )
        """)
        if not cur.fetchone()[0]:
            return False, "base_features table does not exist. Run populate_base_features.py first."

        # Check row count
        cur.execute("SELECT COUNT(*) FROM features_pitch.base_features")
        base_count = cur.fetchone()[0]
        if base_count == 0:
            return False, "base_features is empty. Run populate_base_features.py first."

        # Check if engineered_features exists
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = 'features_pitch'
                AND table_name = 'engineered_features'
            )
        """)
        if not cur.fetchone()[0]:
            return False, "engineered_features table does not exist. Phase 1 must be run first."

        return True, f"Prerequisites met. base_features: {base_count:,} rows."


def check_phase_status(conn, phase_num: int) -> Tuple[bool, str]:
    """Check if a phase has been completed."""
    # Map phases to verification queries
    verification_checks = {
        1: "SELECT COUNT(velocity_percentile) FROM features_pitch.engineered_features",
        2: "SELECT COUNT(is_same_handed_matchup) FROM features_pitch.engineered_features",
        3: "SELECT COUNT(pitch_quality_score) FROM features_pitch.engineered_features WHERE pitch_quality_score IS NOT NULL",
        4: "SELECT COUNT(run_expectancy_24) FROM features_pitch.engineered_features WHERE run_expectancy_24 IS NOT NULL",
        5: "SELECT COUNT(temp_extreme_flag) FROM features_pitch.engineered_features WHERE temp_extreme_flag IS NOT NULL",
        6: "SELECT COUNT(batting_team_last_5_win_rate) FROM features_pitch.engineered_features WHERE batting_team_last_5_win_rate IS NOT NULL",
        7: "SELECT COUNT(home_plate_umpire_id) FROM features_pitch.engineered_features WHERE home_plate_umpire_id IS NOT NULL",
        8: "SELECT COUNT(is_postseason) FROM features_pitch.engineered_features WHERE is_postseason IS NOT NULL",
        9: "SELECT COUNT(strike_accumulation_rate) FROM features_pitch.engineered_features WHERE strike_accumulation_rate IS NOT NULL",
        10: "SELECT COUNT(matchup_prior_pa_count) FROM features_pitch.engineered_features WHERE matchup_prior_pa_count IS NOT NULL",
        11: "SELECT COUNT(umpire_consistency_score) FROM features_pitch.engineered_features WHERE umpire_consistency_score IS NOT NULL",
    }

    if phase_num not in verification_checks:
        return False, "No verification query defined"

    try:
        with conn.cursor() as cur:
            cur.execute(verification_checks[phase_num])
            count = cur.fetchone()[0]
            if count > 0:
                return True, f"Phase {phase_num} appears complete ({count:,} rows with features)"
            return False, f"Phase {phase_num} not started (0 rows with features)"
    except psycopg2.Error as e:
        return False, f"Error checking phase: {e}"


def run_sql_file(sql_path: Path, dry_run: bool = False) -> Tuple[bool, str]:
    """Execute a SQL file using psql."""
    if dry_run:
        return True, f"[DRY RUN] Would execute: {sql_path}"

    try:
        result = subprocess.run(
            ["psql", "-d", DB_URL, "-f", str(sql_path), "-v", "ON_ERROR_STOP=1"],
            capture_output=True,
            text=True,
            timeout=3600,  # 1 hour timeout for large operations
        )
        if result.returncode == 0:
            return True, f"✅ {sql_path.name} executed successfully"
        else:
            return False, f"❌ {sql_path.name} failed:\n{result.stderr}"
    except subprocess.TimeoutExpired:
        return False, f"⏱️ {sql_path.name} timed out ( >1 hour)"
    except Exception as e:
        return False, f"❌ {sql_path.name} error: {e}"


def run_phase(phase_num: int, batch_mode: bool = False, dry_run: bool = False) -> bool:
    """Run a specific phase."""
    phase = next((p for p in PHASES if p[0] == phase_num), None)
    if not phase:
        print(f"❌ Phase {phase_num} not found")
        return False

    _, name, description, sql_files = phase

    print(f"\n{'='*70}")
    print(f"PHASE {phase_num}: {name}")
    print(f"Description: {description}")
    print(f"{'='*70}")

    if not sql_files:
        print("No SQL files to execute (prerequisite check only)")
        return True

    success = True
    for sql_file in sql_files:
        sql_path = SQL_DIR / sql_file
        if not sql_path.exists():
            print(f"⚠️  SQL file not found: {sql_path}")
            continue

        ok, msg = run_sql_file(sql_path, dry_run)
        print(msg)
        if not ok:
            success = False
            if not dry_run:
                break

    return success


def verify_population(conn) -> None:
    """Verify feature population status."""
    print("\n" + "="*70)
    print("FEATURE POPULATION VERIFICATION")
    print("="*70)

    checks = [
        ("Total rows", "SELECT COUNT(*) FROM features_pitch.engineered_features"),
        ("Base features (velocity_percentile)", "SELECT COUNT(velocity_percentile) FROM features_pitch.engineered_features"),
        ("Core outcomes (outcome_tier1)", "SELECT COUNT(outcome_tier1) FROM features_pitch.engineered_features"),
        ("Additional features (velocity_change_from_prev)", "SELECT COUNT(velocity_change_from_prev) FROM features_pitch.engineered_features"),
        ("Extended features (pitch_quality_score)", "SELECT COUNT(*) FROM features_pitch.engineered_features WHERE pitch_quality_score IS NOT NULL"),
        ("Context features (temp_extreme_flag)", "SELECT COUNT(*) FROM features_pitch.engineered_features WHERE temp_extreme_flag IS NOT NULL"),
        ("Final features (strike_accumulation_rate)", "SELECT COUNT(*) FROM features_pitch.engineered_features WHERE strike_accumulation_rate IS NOT NULL"),
        ("Matchup features (matchup_prior_pa_count)", "SELECT COUNT(*) FROM features_pitch.engineered_features WHERE matchup_prior_pa_count IS NOT NULL"),
    ]

    with conn.cursor() as cur:
        for name, query in checks:
            try:
                cur.execute(query)
                count = cur.fetchone()[0]
                print(f"  {name}: {count:,}")
            except psycopg2.Error as e:
                print(f"  {name}: Error - {e}")

    # Check for NULL columns
    print("\nColumns with NULL values (need population):")
    cur.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'features_pitch'
          AND table_name = 'engineered_features'
          AND data_type IN ('numeric', 'real', 'integer', 'bigint')
          AND column_name NOT IN ('pitch_id')
        ORDER BY ordinal_position;
    """)
    numeric_cols = [r[0] for r in cur.fetchall()]

    for col in numeric_cols[:20]:  # Check first 20 numeric columns
        cur.execute(f"""
            SELECT COUNT(*) - COUNT({col}) as null_count
            FROM features_pitch.engineered_features
        """)
        null_count = cur.fetchone()[0]
        if null_count > 0:
            print(f"  - {col}: {null_count:,} NULLs")


def main():
    parser = argparse.ArgumentParser(
        description="Orchestrate Complete Feature Population"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all phases from 0 to 12",
    )
    parser.add_argument(
        "--phase",
        type=int,
        choices=range(0, 13),
        help="Run specific phase (0-12)",
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="Run in batch mode (for phases with batch SQL files)",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify feature population status",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be executed without running",
    )
    parser.add_argument(
        "--continue",
        dest="continue_from",
        type=int,
        help="Continue from phase N (skip completed phases)",
    )
    args = parser.parse_args()

    if args.verify:
        conn = get_connection()
        verify_population(conn)
        conn.close()
        return

    if args.dry_run:
        print("[DRY RUN MODE - No changes will be made]")

    # Determine phases to run
    if args.all:
        phases_to_run = list(range(0, 13))
    elif args.phase is not None:
        phases_to_run = [args.phase]
    else:
        parser.print_help()
        return

    # Skip completed phases if --continue specified
    if args.continue_from:
        phases_to_run = [p for p in phases_to_run if p >= args.continue_from]
        print(f"Continuing from phase {args.continue_from}")

    conn = get_connection()

    # Run phases
    start_time = datetime.now()
    total_phases = len(phases_to_run)
    completed = 0

    for phase_num in phases_to_run:
        # Special handling for phase 0 (prerequisites)
        if phase_num == 0:
            ok, msg = verify_prerequisites(conn)
            print(f"\n[Phase 0] Prerequisites: {msg}")
            if not ok:
                print("Prerequisites not met. Exiting.")
                conn.close()
                return
            completed += 1
            continue

        # Check if phase already completed (unless force run)
        if not args.dry_run and args.continue_from is None:
            is_done, msg = check_phase_status(conn, phase_num)
            if is_done:
                print(f"\n[Phase {phase_num}] Already completed: {msg}")
                completed += 1
                continue

        # Run the phase
        success = run_phase(phase_num, args.batch, args.dry_run)
        if not success and not args.dry_run:
            print(f"\n❌ Phase {phase_num} failed. Stopping.")
            break

        completed += 1

    # Summary
    duration = datetime.now() - start_time
    print(f"\n{'='*70}")
    print(f"SUMMARY: {completed}/{total_phases} phases completed")
    print(f"Duration: {duration}")
    print(f"{'='*70}")

    # Final verification if all phases ran
    if completed == total_phases and not args.dry_run:
        verify_population(conn)

    conn.close()


if __name__ == "__main__":
    main()
