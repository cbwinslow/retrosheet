#!/usr/bin/env python3
"""
Unified Pitch-Level Modeling Pipeline

Complete workflow: base_features → engineered_features → trained_model

Usage:
    python scripts/pipeline_pitch_modeling.py --full
    python scripts/pipeline_pitch_modeling.py --skip-population --skip-engineered
    python scripts/pipeline_pitch_modeling.py --seasons 2020-2024
"""

import argparse
import logging
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from baseball.utils.logging_config import get_logger

logger = get_logger(__name__)


def run_script(script_name: str, args: list[str]) -> bool:
    """Run a script with arguments."""
    cmd = [sys.executable, f"scripts/{script_name}"] + args
    logger.info(f"Running: {' '.join(cmd)}")
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        logger.error(f"Script failed: {script_name}")
        logger.error(result.stderr)
        return False
    
    print(result.stdout)
    return True


def main():
    parser = argparse.ArgumentParser(
        description='Complete pitch-level modeling pipeline'
    )
    parser.add_argument(
        '--full', '-f',
        action='store_true',
        help='Run complete pipeline (all steps)'
    )
    parser.add_argument(
        '--seasons', '-s',
        default='2015-2025',
        help='Season range (e.g., 2015-2025)'
    )
    parser.add_argument(
        '--skip-population', '-sp',
        action='store_true',
        help='Skip base_features population'
    )
    parser.add_argument(
        '--skip-engineered', '-se',
        action='store_true',
        help='Skip engineered features'
    )
    parser.add_argument(
        '--skip-training', '-st',
        action='store_true',
        help='Skip model training'
    )
    parser.add_argument(
        '--train-only',
        action='store_true',
        help='Only run training (skip data prep)'
    )
    
    args = parser.parse_args()
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    if args.train_only:
        args.skip_population = True
        args.skip_engineered = True
    
    start_time = datetime.now()
    version_tag = f"v1.0_{start_time.strftime('%Y%m%d')}"
    
    print(f"\n{'='*70}")
    print("PITCH-LEVEL MODELING PIPELINE")
    print(f"{'='*70}")
    print(f"Start time: {start_time}")
    print(f"Version: {version_tag}")
    print(f"Seasons: {args.seasons}")
    print(f"{'='*70}\n")
    
    success = True
    
    # Step 1: Populate base_features
    if not args.skip_population and success:
        print("\n" + "="*70)
        print("STEP 1: Populate base_features")
        print("="*70)
        
        start, end = args.seasons.split('-')
        seasons = list(range(int(start), int(end) + 1))
        
        success = run_script(
            'populate_pitch_base_features.py',
            ['--seasons'] + [str(s) for s in seasons] + ['--batch-size', '100000']
        )
        
        if not success:
            logger.error("Step 1 failed: base_features population")
    
    # Step 2: Build engineered features
    if not args.skip_engineered and success:
        print("\n" + "="*70)
        print("STEP 2: Build engineered features")
        print("="*70)
        
        # Use most recent version
        success = run_script(
            'build_pitch_engineered_features.py',
            ['--version', version_tag, '--batch-size', '50000']
        )
        
        if not success:
            logger.error("Step 2 failed: engineered features")
    
    # Step 3: Train model
    if not args.skip_training and success:
        print("\n" + "="*70)
        print("STEP 3: Train Two-Tier XGBoost")
        print("="*70)
        
        # Default train/val split
        start, end = args.seasons.split('-')
        mid = (int(start) + int(end)) // 2
        
        train_seasons = f"{start}-{mid}"
        val_seasons = f"{mid+1}-{end}"
        
        success = run_script(
            'train_pitch_xgboost_two_tier.py',
            [
                '--train-seasons', train_seasons,
                '--val-seasons', val_seasons,
                '--version-tag', version_tag
            ]
        )
        
        if not success:
            logger.error("Step 3 failed: model training")
    
    # Summary
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    print(f"\n{'='*70}")
    print("PIPELINE SUMMARY")
    print(f"{'='*70}")
    print(f"Status: {'✓ SUCCESS' if success else '✗ FAILED'}")
    print(f"Duration: {duration/60:.1f} minutes")
    print(f"Version: {version_tag}")
    
    if not args.skip_population:
        print(f"  ✓ base_features populated")
    if not args.skip_engineered:
        print(f"  ✓ engineered_features built")
    if not args.skip_training:
        print(f"  ✓ XGBoost model trained")
    
    print(f"{'='*70}\n")
    
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
