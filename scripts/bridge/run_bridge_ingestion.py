#!/usr/bin/env python3
"""
Bridge Population Orchestrator Script.

Main entry point for bridge table population with full abstraction layers:
- Validation layer (pre-flight checks)
- Error handling (retry logic, circuit breaker)
- Checkpointing (resumable operations)
- Comprehensive logging

Usage:
    python scripts/bridge/run_bridge_ingestion.py
    python scripts/bridge/run_bridge_ingestion.py --skip-download
    python scripts/bridge/run_bridge_ingestion.py --skip-validation
    python scripts/bridge/run_bridge_ingestion.py --resume <operation_id>
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from mlb_predict.orchestration.bridge_orchestrator import BridgeOrchestrator
from mlb_predict.orchestration.validation import generate_preflight_report
import psycopg2


def setup_logging(log_dir: Path | None = None) -> Path:
    """Setup logging with file and console output."""
    log_dir = log_dir or ROOT / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"bridge_orchestrator_{timestamp}.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout),
        ],
    )
    
    return log_file


def print_summary(results: dict) -> None:
    """Print formatted result summary."""
    print("\n" + "=" * 70)
    if results.get("success"):
        print("✓ BRIDGE INGESTION COMPLETED SUCCESSFULLY")
    else:
        print("✗ BRIDGE INGESTION FAILED")
    print("=" * 70)
    
    print(f"\nOperation ID: {results.get('operation_id')}")
    print(f"Start Time: {results.get('start_time')}")
    if results.get('end_time'):
        print(f"End Time: {results.get('end_time')}")
    
    print("\n--- Stage Results ---")
    for stage in results.get("stages", []):
        status = "✓" if stage.get("success") else "✗"
        duration = stage.get("duration_seconds", 0)
        print(f"  {status} {stage.get('stage')}: {duration:.1f}s")
        
        if stage.get("errors"):
            for error in stage.get("errors"):
                print(f"    Error: {error}")
    
    if results.get("validation"):
        v = results["validation"]
        print(f"\n--- Validation ---")
        print(f"  Passed: {v.get('passed')}")
        print(f"  Errors: {v.get('error_count')}")
        print(f"  Warnings: {v.get('warning_count')}")
    
    if results.get("error"):
        print(f"\n*** ERROR: {results.get('error')} ***")
    
    print("\n" + "=" * 70)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Bridge table population orchestrator with full error handling"
    )
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Skip download if files already exist in temp directory",
    )
    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="Skip validation tests",
    )
    parser.add_argument(
        "--no-checkpoints",
        action="store_true",
        help="Disable checkpointing (not recommended)",
    )
    parser.add_argument(
        "--operation-id",
        type=str,
        help="Custom operation ID for tracking/resuming",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        help="Write results to JSON file",
    )
    parser.add_argument(
        "--report-only",
        action="store_true",
        help="Generate pre-flight data quality report and exit (no ingestion)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would change without committing (simulates all operations)",
    )
    
    args = parser.parse_args()
    
    # Setup logging
    log_file = setup_logging()
    
    # Handle report-only mode
    if args.report_only:
        print("=" * 70)
        print("PRE-FLIGHT DATA QUALITY REPORT MODE")
        print("=" * 70)
        
        db_url = orchestrator.db_url if 'orchestrator' in locals() else None
        conn = psycopg2.connect(db_url) if db_url else psycopg2.connect(
            host="localhost", database="retrosheet"
        )
        
        try:
            report = generate_preflight_report(conn)
            report.print_report()
            
            if args.output_json:
                with open(args.output_json, "w") as f:
                    json.dump(report.to_dict(), f, indent=2)
                print(f"\nReport written to: {args.output_json}")
            
            return 0
        finally:
            conn.close()
    
    print("=" * 70)
    print("BRIDGE TABLE POPULATION ORCHESTRATOR")
    print("=" * 70)
    print(f"Log file: {log_file}")
    print(f"Checkpoints: {'disabled' if args.no_checkpoints else 'enabled'}")
    print(f"Validation: {'disabled' if args.skip_validation else 'enabled'}")
    print(f"Dry-run: {'enabled' if args.dry_run else 'disabled'}")
    print("=" * 70)
    
    # Create orchestrator
    orchestrator = BridgeOrchestrator(
        enable_checkpoints=not args.no_checkpoints,
    )
    
    # Run ingestion
    results = orchestrator.run_chadwick_ingestion(
        skip_download=args.skip_download,
        skip_validation=args.skip_validation,
        operation_id=args.operation_id,
        dry_run=args.dry_run,
    )
    
    # Print summary
    print_summary(results)
    
    # Write JSON output if requested
    if args.output_json:
        with open(args.output_json, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\nResults written to: {args.output_json}")
    
    return 0 if results.get("success") else 1


if __name__ == "__main__":
    sys.exit(main())
