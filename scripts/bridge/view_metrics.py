#!/usr/bin/env python3
"""
View operation metrics and generate reports.

Usage:
    python scripts/bridge/view_metrics.py
    python scripts/bridge/view_metrics.py --days 30
    python scripts/bridge/view_metrics.py --operation-type chadwick_ingestion
    python scripts/bridge/view_metrics.py --json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


# Add project root to path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from mlb_predict.orchestration.metrics import MetricsReporter


def main() -> int:
    parser = argparse.ArgumentParser(description='View operation metrics')
    parser.add_argument(
        '--days',
        type=int,
        default=7,
        help='Number of days to include (default: 7)',
    )
    parser.add_argument(
        '--operation-type',
        type=str,
        help='Filter by operation type (e.g., chadwick_ingestion)',
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output as JSON',
    )

    args = parser.parse_args()

    reporter = MetricsReporter()

    if args.operation_type:
        # Show details for specific operation type
        metrics = reporter.load_recent_metrics(
            operation_type=args.operation_type,
            days=args.days,
        )

        if args.json:
            print(json.dumps([m.to_dict() for m in metrics], indent=2))
        else:
            print(f'\nRecent {args.operation_type} operations (last {args.days} days):')
            print('=' * 70)
            for m in metrics[:10]:  # Show last 10
                status = '✓' if m.success else '✗'
                print(f'  {status} {m.operation_id} - {m.duration_seconds:.1f}s - {m.records_processed:,} records')
                if m.error_count > 0:
                    print(f'      Errors: {m.error_count}, Retries: {m.retry_count}')
    else:
        # Show summary
        if args.json:
            summary = reporter.generate_summary(days=args.days)
            print(json.dumps(summary, indent=2))
        else:
            reporter.print_summary(days=args.days)

    return 0


if __name__ == '__main__':
    sys.exit(main())
