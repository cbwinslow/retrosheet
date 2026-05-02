#!/usr/bin/env python3
"""System bootstrap script for MLB prediction platform.

Sets up the complete system:
1. Database schemas (SQL files)
2. MLB schedule download
3. Cron jobs for ingestion
4. Directory structure
5. Initial data load

Idempotent - safe to run multiple times.

Usage:
    python scripts/bootstrap_system.py --full    # Complete setup
    python scripts/bootstrap_system.py --db     # Database only
    python scripts/bootstrap_system.py --cron   # Cron jobs only
    python scripts/bootstrap_system.py --check  # Verify setup

Author: Agent Cascade
Date: 2026-05-01
"""

from __future__ import annotations

import argparse
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

# Add project root to path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from baseball.core.db import get_db_connection
from baseball.core.time_util import BaseballDateTime, get_season_dates

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)


class SystemBootstrap:
    """Bootstrap the MLB prediction system."""
    
    def __init__(self, dry_run: bool = False) -> None:
        """Initialize bootstrap.
        
        Args:
            dry_run: If True, only show what would be done
        """
        self.dry_run = dry_run
        self.root = ROOT
        self.sql_dir = self.root / 'sql'
        
    def run_full_setup(self) -> bool:
        """Run complete system setup."""
        logger.info('Starting full system bootstrap...')
        
        steps = [
            ('Database connection', self._check_db_connection),
            ('SQL schemas', self._apply_sql_schemas),
            ('Directory structure', self._create_directories),
            ('MLB schedule', self._download_mlb_schedule),
            ('Cron jobs', self._setup_cron_jobs),
            ('Verification', self._verify_setup),
        ]
        
        for name, step_func in steps:
            logger.info(f'\n>>> Step: {name}')
            try:
                if not step_func():
                    logger.error(f'Failed at step: {name}')
                    return False
            except Exception as e:
                logger.exception(f'Error in {name}: {e}')
                return False
        
        logger.info('\n✅ Bootstrap complete!')
        return True
    
    def _check_db_connection(self) -> bool:
        """Verify database connection."""
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute('SELECT version()')
                version = cur.fetchone()[0]
                logger.info(f'PostgreSQL: {version[:50]}...')
            return True
        except Exception as e:
            logger.error(f'Database connection failed: {e}')
            return False
    
    def _apply_sql_schemas(self) -> bool:
        """Apply SQL schemas in order."""
        # SQL files in order of application
        sql_files = [
            # Admin/Control
            '00_admin/000_admin_pipeline_control.sql',
            '00_admin/001_maintenance_schema.sql',
            '00_admin/002_scheduler_schema.sql',
            '00_admin/003_scheduler_jobs_seed.sql',
            
            # Staging
            '20_staging/2000_staging_schema.sql',
            '20_staging/221_stg_mlb_live_events.sql',
            '20_staging/222_stg_mlb_live_pitch_events.sql',
            
            # Core
            '30_core/3000_retrosheet_schema.sql',
            '30_core/3013_core_pitch_sequence_model.sql',
            '30_core/3013b_pitch_sequence_procedures.sql',
            '30_core/313_core_live_pitch_events.sql',
            
            # Bridge
            '40_bridge/100_bridge_tables.sql',
            
            # Features
            '50_features/500_features_run_expectancy.sql',
            
            # Models (HPS + Model Zoo)
            '60_models/600_models_registry.sql',
            '60_models/6005_hierarchical_prediction_schema.sql',
            '60_models/6006_model_registry_schema.sql',
            
            # Serving
            '70_serving/700_serving_predictions.sql',
            
            # External data
            '220_espn_schema.sql',
        ]
        
        conn = get_db_connection()
        
        for sql_file in sql_files:
            path = self.sql_dir / sql_file
            if not path.exists():
                logger.warning(f'SQL file not found: {sql_file}')
                continue
            
            logger.info(f'Applying: {sql_file}')
            
            if self.dry_run:
                continue
            
            try:
                with conn.cursor() as cur:
                    with open(path) as f:
                        cur.execute(f.read())
                conn.commit()
                logger.info(f'  ✅ Applied')
            except Exception as e:
                logger.error(f'  ❌ Failed: {e}')
                # Continue with other files - some may already exist
        
        return True
    
    def _create_directories(self) -> bool:
        """Create necessary directory structure."""
        dirs = [
            self.root / 'data' / 'raw',
            self.root / 'data' / 'processed',
            self.root / 'data' / 'models',
            self.root / 'data' / 'cache',
            self.root / 'logs',
            self.root / 'config',
        ]
        
        for dir_path in dirs:
            if self.dry_run:
                logger.info(f'Would create: {dir_path}')
            else:
                dir_path.mkdir(parents=True, exist_ok=True)
                logger.info(f'Created: {dir_path}')
        
        return True
    
    def _download_mlb_schedule(self) -> bool:
        """Download MLB schedule for current season."""
        logger.info('Downloading MLB schedule...')
        
        season = BaseballDateTime.now().year
        start, end = get_season_dates(season)
        
        logger.info(f'Season {season}: {start.to_short_display()} to {end.to_short_display()}')
        
        if self.dry_run:
            logger.info(f'Would fetch schedule for {season}')
            return True
        
        try:
            # Use existing schedule fetcher
            result = subprocess.run(
                [
                    sys.executable,
                    'scripts/fetch_mlb_schedule.py',
                    '--season', str(season),
                    '--populate',
                ],
                cwd=self.root,
                capture_output=True,
                text=True,
                timeout=120,
            )
            
            if result.returncode == 0:
                logger.info(f'  ✅ Schedule downloaded')
                logger.info(result.stdout[:500])
                return True
            else:
                logger.error(f'  ❌ Failed: {result.stderr}')
                return False
                
        except Exception as e:
            logger.error(f'  ❌ Error: {e}')
            return False
    
    def _setup_cron_jobs(self) -> bool:
        """Setup cron jobs using pg_cron (database-native scheduling)."""
        logger.info('Setting up pg_cron jobs (database-native)...')
        
        if self.dry_run:
            logger.info('Would create pg_cron jobs:')
            logger.info('  - mlb_schedule_daily: 0 6 * * *')
            logger.info('  - mlb_live_ingestion: */5 * * * * (smart polling)')
            logger.info('  - mlb_odds_fetch: */30 * * * *')
            logger.info('  - refresh_materialized_views: 0 * * * *')
            logger.info('  - cleanup_job_history: 0 3 * * *')
            return True
        
        # First ensure pg_cron extension is installed
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM pg_extension WHERE extname = 'pg_cron'")
                if not cur.fetchone():
                    logger.info('Installing pg_cron extension...')
                    try:
                        cur.execute('CREATE EXTENSION IF NOT EXISTS pg_cron')
                        conn.commit()
                        logger.info('pg_cron extension installed')
                    except Exception as e:
                        logger.error(f'Could not install pg_cron: {e}')
                        logger.error('pg_cron requires PostgreSQL superuser or rds_superuser role')
                        logger.error('To enable: Connect as superuser and run: CREATE EXTENSION pg_cron;')
                        return False
        except Exception as e:
            logger.error(f'Error checking pg_cron: {e}')
            return False
        
        # Initialize jobs from scheduler.jobs table using our helper function
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute("SELECT scheduler.try_initialize_scheduler()")
                result = cur.fetchone()[0]
                
                if result.get('success'):
                    jobs = result.get('jobs', [])
                    logger.info(f"Created {len(jobs)} pg_cron jobs:")
                    for job in jobs:
                        status = '✅' if 'created' in job.get('status', '') else '⚠️'
                        logger.info(f"  {status} {job.get('job')}")
                    return True
                else:
                    logger.error(f"Scheduler init failed: {result.get('message')}")
                    return False
                    
        except Exception as e:
            logger.exception(f'Failed to initialize pg_cron jobs: {e}')
            return False
    
    def _verify_setup(self) -> bool:
        """Verify system is properly configured."""
        logger.info('Verifying setup...')
        
        checks = [
            ('Database', self._check_db_connection),
            ('Schemas', self._verify_schemas),
            ('Schedule data', self._verify_schedule_data),
        ]
        
        all_passed = True
        for name, check_func in checks:
            try:
                result = check_func()
                status = '✅' if result else '❌'
                logger.info(f'  {status} {name}')
                if not result:
                    all_passed = False
            except Exception as e:
                logger.error(f'  ❌ {name}: {e}')
                all_passed = False
        
        return all_passed
    
    def _verify_schemas(self) -> bool:
        """Verify key schemas exist."""
        required_schemas = [
            'predictions',
            'models',
            'pitch_sequence',
            'maintenance',
            'raw_espn',
        ]
        
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT schema_name FROM information_schema.schemata"
            )
            existing = {row[0] for row in cur.fetchall()}
        
        missing = set(required_schemas) - existing
        if missing:
            logger.warning(f'Missing schemas: {missing}')
            return False
        
        return True
    
    def _verify_schedule_data(self) -> bool:
        """Verify MLB schedule data exists."""
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT COUNT(*) FROM core.games 
                       WHERE season = EXTRACT(YEAR FROM CURRENT_DATE)"""
                )
                count = cur.fetchone()[0]
                logger.info(f'  Games in database: {count}')
                return count > 0
        except Exception as e:
            logger.error(f'Error checking schedule: {e}')
            return False


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Bootstrap MLB prediction system')
    parser.add_argument('--full', action='store_true', help='Complete setup')
    parser.add_argument('--db', action='store_true', help='Database schemas only')
    parser.add_argument('--cron', action='store_true', help='Cron jobs only')
    parser.add_argument('--check', action='store_true', help='Verify setup')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done')
    parser.add_argument('--schedule-only', action='store_true', help='Download schedule only')
    
    args = parser.parse_args()
    
    bootstrap = SystemBootstrap(dry_run=args.dry_run)
    
    if args.check:
        success = bootstrap._verify_setup()
    elif args.db:
        success = bootstrap._apply_sql_schemas()
    elif args.cron:
        success = bootstrap._setup_cron_jobs()
    elif args.schedule_only:
        success = bootstrap._download_mlb_schedule()
    elif args.full or not any([args.db, args.cron, args.check, args.schedule_only]):
        success = bootstrap.run_full_setup()
    else:
        parser.print_help()
        return 1
    
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
