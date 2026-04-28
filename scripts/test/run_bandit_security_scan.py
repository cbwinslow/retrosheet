#!/usr/bin/env python3
"""
File: scripts/test/run_bandit_security_scan.py
Purpose: Run Bandit security scanner on Python code and generate report
Author: Agent KiloSwift
Date: 2026-04-27
Usage: uv run python scripts/test/run_bandit_security_scan.py --output bandit-report.html
Dependencies: bandit
"""

import argparse
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).parent.parent.parent

def parse_args():
    parser = argparse.ArgumentParser(description='Run Bandit security scan on Python code')
    parser.add_argument('--output', type=Path, default=PROJECT_ROOT / 'bandit-report.html', help='Output report file (HTML or JSON)')
    parser.add_argument('--format', choices=['html', 'json', 'txt'], default='html', help='Report format')
    parser.add_argument('--severity', type=int, default=1, help='Minimum severity level (1=low, 2=medium, 3=high)')
    parser.add_argument('--confidence', type=int, default=1, help='Minimum confidence level (1=low, 2=medium, 3=high)')
    parser.add_argument('--skip-tests', nargs='+', default=[], help='Test IDs to skip (e.g., B101, B201)')
    parser.add_argument('--exit-zero', action='store_true', help='Always exit with code 0 (CI-friendly)')
    return parser.parse_args()

def ensure_bandit_installed():
    """Ensure bandit is installed, try to install if missing."""
    try:
        import bandit  # noqa: F401
        return True
    except ImportError:
        print('📦 bandit not found. Attempting to install...')
        result = subprocess.run(['uv', 'add', '--dev', 'bandit'], capture_output=True, text=True)
        if result.returncode != 0:
            print('❌ Failed to install bandit automatically.')
            print('   Please run: uv add --dev bandit')
            return False
        print('✅ bandit installed.')
        return True

def main():
    args = parse_args()

    if not ensure_bandit_installed():
        return 1

    print('🔒 Running Bandit security scan...')
    print(f'   Severity level: >= {args.severity}')
    print(f'   Confidence level: >= {args.confidence}')
    print(f'   Output format: {args.format}')
    print()

    # Build bandit command
    cmd = [
        'bandit', '-r', str(PROJECT_ROOT),
        '-f', args.format,
        '-o', str(args.output),
        '--severity-level', str(args.severity),
        '--confidence-level', str(args.confidence),
    ]

    # Skip tests if specified
    for test_id in args.skip_tests:
        cmd.extend(['-s', test_id])

    # Exclude common false positives
    exclude_dirs = [
        '.venv', 'venv', '__pycache__', 'node_modules',
        '.git', 'data', 'docs', 'sql', 'tmp', 'tmp*',
        'scripts/vector',
    ]
    for d in exclude_dirs:
        cmd.extend(['-x', d])

    # Run bandit
    result = subprocess.run(cmd, capture_output=True, text=True)

    # Exit code handling
    bandit_exit_code = result.returncode
    if bandit_exit_code == 0:
        print('✅ No security issues found.')
    elif bandit_exit_code == 1:
        print('⚠️  Security issues found. See report for details.')
    elif bandit_exit_code == 2:
        print('❌ Invalid command-line options or configuration error.')
        print(result.stderr)
        return 2
    else:
        print(f'❌ Bandit exited with code {bandit_exit_code}')
        print(result.stderr)
        return bandit_exit_code

    print(f'\n📊 Report generated: {args.output}')

    # Also print summary to stdout
    if args.format == 'txt':
        print(result.stdout)

    return 0 if args.exit_zero else bandit_exit_code

if __name__ == '__main__':
    sys.exit(main())
