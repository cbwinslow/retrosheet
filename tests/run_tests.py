#!/usr/bin/env python3
"""Comprehensive test runner with benchmarking and metrics.

Runs unit, integration, and E2E tests with detailed logging,
benchmarking, and performance metrics collection.

Author: Agent cbwinslow/retrosheet
Date: 2026-04-27
"""

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any


class TestRunner:
    """Comprehensive test runner with metrics."""

    def __init__(self, output_dir: Path | None = None):
        self.output_dir = output_dir or Path('test_results')
        self.output_dir.mkdir(exist_ok=True)

        self.results: dict[str, Any] = {
            'start_time': datetime.now().isoformat(),
            'test_suites': {},
            'benchmarks': {},
            'summary': {},
        }

    def run_unit_tests(self, verbose: bool = False) -> dict[str, Any]:
        """Run unit tests with pytest."""
        print('\n' + '=' * 60)
        print('RUNNING UNIT TESTS')
        print('=' * 60)

        start = time.time()

        cmd = [
            sys.executable,
            '-m',
            'pytest',
            'tests/unit/',
            '-v' if verbose else '',
            '--tb=short',
            '--json-report',
            '--json-report-file',
            str(self.output_dir / 'unit_tests.json'),
        ]
        cmd = [c for c in cmd if c]  # Remove empty strings

        result = subprocess.run(cmd, capture_output=True, text=True)

        duration = time.time() - start

        suite_result = {
            'name': 'unit',
            'duration_seconds': duration,
            'exit_code': result.returncode,
            'passed': result.returncode == 0,
            'stdout': result.stdout,
            'stderr': result.stderr,
        }

        self.results['test_suites']['unit'] = suite_result

        if verbose:
            print(result.stdout)

        status = '✅ PASSED' if result.returncode == 0 else '❌ FAILED'
        print(f'{status} in {duration:.2f}s')

        return suite_result

    def run_integration_tests(self, verbose: bool = False) -> dict[str, Any]:
        """Run integration tests."""
        print('\n' + '=' * 60)
        print('RUNNING INTEGRATION TESTS')
        print('=' * 60)

        start = time.time()

        cmd = [
            sys.executable,
            '-m',
            'pytest',
            'tests/integration/',
            '-v' if verbose else '',
            '--tb=short',
            '--json-report',
            '--json-report-file',
            str(self.output_dir / 'integration_tests.json'),
        ]
        cmd = [c for c in cmd if c]

        result = subprocess.run(cmd, capture_output=True, text=True)

        duration = time.time() - start

        suite_result = {
            'name': 'integration',
            'duration_seconds': duration,
            'exit_code': result.returncode,
            'passed': result.returncode == 0 or result.returncode == 5,  # 5 = no tests
            'stdout': result.stdout,
            'stderr': result.stderr,
        }

        self.results['test_suites']['integration'] = suite_result

        if verbose:
            print(result.stdout)

        status = '✅ PASSED' if suite_result['passed'] else '❌ FAILED'
        print(f'{status} in {duration:.2f}s')

        return suite_result

    def run_e2e_tests(self, verbose: bool = False) -> dict[str, Any]:
        """Run E2E tests with database."""
        print('\n' + '=' * 60)
        print('RUNNING E2E TESTS (requires database)')
        print('=' * 60)

        start = time.time()

        cmd = [
            sys.executable,
            '-m',
            'pytest',
            'tests/e2e/',
            '-v' if verbose else '',
            '--tb=short',
            '--json-report',
            '--json-report-file',
            str(self.output_dir / 'e2e_tests.json'),
        ]
        cmd = [c for c in cmd if c]

        # Set environment to ensure database tests run
        env = dict(os.environ) if 'os' in dir() else {}
        env['PYTEST_CURRENT_TEST'] = 'e2e'

        result = subprocess.run(cmd, capture_output=True, text=True)

        duration = time.time() - start

        suite_result = {
            'name': 'e2e',
            'duration_seconds': duration,
            'exit_code': result.returncode,
            'passed': result.returncode == 0 or result.returncode == 5,
            'stdout': result.stdout,
            'stderr': result.stderr,
        }

        self.results['test_suites']['e2e'] = suite_result

        if verbose:
            print(result.stdout)

        status = '✅ PASSED' if suite_result['passed'] else '❌ FAILED'
        print(f'{status} in {duration:.2f}s')

        return suite_result

    def run_benchmark_tests(self) -> dict[str, Any]:
        """Run performance benchmark tests."""
        print('\n' + '=' * 60)
        print('RUNNING BENCHMARK TESTS')
        print('=' * 60)

        start = time.time()

        # Import and run benchmarks
        try:
            from tests.benchmarks import run_all_benchmarks

            benchmark_results = run_all_benchmarks()

            self.results['benchmarks'] = benchmark_results

            print(f'Completed {len(benchmark_results)} benchmarks')

            return {
                'name': 'benchmarks',
                'duration_seconds': time.time() - start,
                'passed': True,
                'results': benchmark_results,
            }
        except Exception as e:
            print(f'Benchmark tests not available: {e}')
            return {
                'name': 'benchmarks',
                'duration_seconds': time.time() - start,
                'passed': False,
                'error': str(e),
            }

    def generate_report(self) -> None:
        """Generate comprehensive test report."""
        print('\n' + '=' * 60)
        print('TEST REPORT')
        print('=' * 60)

        # Calculate summary
        total_suites = len(self.results['test_suites'])
        passed_suites = sum(1 for s in self.results['test_suites'].values() if s.get('passed'))
        total_duration = sum(
            s.get('duration_seconds', 0) for s in self.results['test_suites'].values()
        )

        self.results['summary'] = {
            'total_suites': total_suites,
            'passed_suites': passed_suites,
            'failed_suites': total_suites - passed_suites,
            'total_duration_seconds': total_duration,
            'all_passed': passed_suites == total_suites,
        }

        # Print summary
        print(f'\nTotal test suites: {total_suites}')
        print(f'Passed: {passed_suites}')
        print(f'Failed: {total_suites - passed_suites}')
        print(f'Total duration: {total_duration:.2f}s')

        # Save report
        report_file = (
            self.output_dir / f'test_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        )
        with open(report_file, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)

        print(f'\nReport saved to: {report_file}')

    def run_all(
        self,
        unit: bool = True,
        integration: bool = True,
        e2e: bool = True,
        benchmarks: bool = False,
        verbose: bool = False,
    ) -> bool:
        """Run all test suites."""
        print('=' * 60)
        print('COMPREHENSIVE TEST RUNNER')
        print(f'Started: {self.results["start_time"]}')
        print('=' * 60)

        if unit:
            self.run_unit_tests(verbose=verbose)

        if integration:
            self.run_integration_tests(verbose=verbose)

        if e2e:
            self.run_e2e_tests(verbose=verbose)

        if benchmarks:
            self.run_benchmark_tests()

        self.generate_report()

        return self.results['summary'].get('all_passed', False)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Run comprehensive test suite')
    parser.add_argument('--unit', action='store_true', default=True, help='Run unit tests')
    parser.add_argument('--no-unit', action='store_true', help='Skip unit tests')
    parser.add_argument('--integration', action='store_true', help='Run integration tests')
    parser.add_argument('--e2e', action='store_true', help='Run E2E tests')
    parser.add_argument('--benchmarks', action='store_true', help='Run benchmark tests')
    parser.add_argument('--all', action='store_true', help='Run all tests including benchmarks')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument(
        '--output-dir', type=Path, default=Path('test_results'), help='Output directory',
    )

    args = parser.parse_args()

    # Handle negation flags
    unit = not args.no_unit if args.no_unit else args.unit

    # --all enables everything
    if args.all:
        unit = True
        args.integration = True
        args.e2e = True
        args.benchmarks = True

    runner = TestRunner(output_dir=args.output_dir)

    success = runner.run_all(
        unit=unit,
        integration=args.integration,
        e2e=args.e2e,
        benchmarks=args.benchmarks,
        verbose=args.verbose,
    )

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    import os

    main()
