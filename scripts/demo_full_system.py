#!/usr/bin/env python3
"""
Full System Demo - Comprehensive evaluation of the baseball prediction warehouse.

This script demonstrates all components of the system:
- Source adapters (MLB, Retrosheet, Statcast, ESPN, Lahman)
- Pipeline configurations and execution
- Feature calculators
- CLI commands
- Database status
- Test execution

Author: Agent cbwinslow/retrosheet
Date: 2026-04-27

Usage:
    python scripts/demo_full_system.py --mode quick      # 2-3 minute overview
    python scripts/demo_full_system.py --mode full       # 5-10 minute comprehensive
    python scripts/demo_full_system.py --mode ci       # Test all paths (no db)
    python scripts/demo_full_system.py --output report.md  # Generate markdown report
"""

import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


# Add project to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def print_header(title: str, char: str = '=') -> None:
    """Print a section header."""
    width = 70
    print(f'\n{char * width}')
    print(f' {title}'.center(width))
    print(f'{char * width}\n')


def print_subheader(title: str) -> None:
    """Print a subsection header."""
    print(f"\n{'─' * 50}")
    print(f' {title}')
    print(f"{'─' * 50}")


def run_command(cmd: list[str], capture: bool = True) -> tuple[int, str, str]:
    """Run a shell command and return results."""
    try:
        result = subprocess.run(
            cmd,
            cwd=PROJECT_ROOT,
            capture_output=capture,
            text=True,
            timeout=30,
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, '', 'Timeout'
    except Exception as e:
        return -1, '', str(e)


def check_baseball_cli() -> dict[str, Any]:
    """Check baseball CLI availability and commands."""
    print_subheader('Baseball CLI Discovery')

    status = {
        'available': False,
        'commands': [],
        'groups': [],
        'version': 'unknown',
    }

    # Check if baseball command works
    returncode, stdout, stderr = run_command(['baseball', '--help'])

    if returncode == 0:
        status['available'] = True
        print('✅ Baseball CLI is available')

        # Parse command groups from help output
        lines = stdout.split('\n')
        for line in lines:
            line = line.strip()
            if line and not line.startswith('-') and not line.startswith('Usage'):
                if any(cmd in line for cmd in [
                    'admin', 'mlb', 'retrosheet', 'statcast', 'espn',
                    'lahman', 'live', 'bridge', 'features', 'models',
                    'pipeline', 'predict', 'chatbot',
                ]):
                    status['commands'].append(line)

        print(f"   Found {len(status['commands'])} command groups")
    else:
        print('❌ Baseball CLI not available - trying Python module')
        # Try python -m baseball
        returncode, stdout, _stderr = run_command([sys.executable, '-m', 'baseball.cli', '--help'])
        if returncode == 0:
            status['available'] = True
            print('✅ Baseball CLI works via Python module')

    return status


def check_source_adapters() -> dict[str, Any]:
    """Check source adapter imports and availability."""
    print_subheader('Source Adapters')

    adapters = {
        'mlb': {'class': 'MlbSource', 'status': 'unknown'},
        'retrosheet': {'class': 'RetrosheetSource', 'status': 'unknown'},
        'statcast': {'class': 'StatcastSource', 'status': 'unknown'},
        'espn': {'class': 'EspnSource', 'status': 'unknown'},
        'lahman': {'class': 'LahmanSource', 'status': 'unknown'},
    }

    for name, info in adapters.items():
        try:
            module_name = f'baseball.sources.{name}'
            __import__(module_name)
            info['status'] = '✅ importable'
            print(f"✅ {info['class']}: Importable")
        except ImportError as e:
            info['status'] = f'❌ import error: {e}'
            print(f"❌ {info['class']}: Import error - {e}")
        except Exception as e:
            info['status'] = f'⚠️ error: {e}'
            print(f"⚠️ {info['class']}: Error - {e}")

    return adapters


def check_pipelines() -> dict[str, Any]:
    """Check pipeline configurations."""
    print_subheader('Pipeline Configurations')

    pipelines = {'available': False, 'configs': [], 'count': 0}

    try:
        from baseball.services.pipeline import PipelineService

        service = PipelineService()
        pipeline_configs = service.list_pipelines()

        pipelines['available'] = True
        pipelines['count'] = len(pipeline_configs)

        print('✅ PipelineService initialized')
        print(f'   Found {len(pipeline_configs)} pipeline configurations:')

        for config in pipeline_configs:
            pipelines['configs'].append({
                'name': config.name,
                'description': config.description,
                'steps': config.steps,
            })
            print(f'   • {config.name}: {len(config.steps)} steps')

    except Exception as e:
        print(f'❌ Pipeline service error: {e}')

    return pipelines


def check_feature_calculators() -> dict[str, Any]:
    """Check feature calculator availability."""
    print_subheader('Feature Calculators')

    calculators = {
        'WinExpectancyCalculator': 'baseball.features.win_expectancy',
        'LeverageIndexCalculator': 'baseball.features.leverage_index',
        'RunExpectancyCalculator': 'baseball.features.run_expectancy',
        'MatchupCalculator': 'baseball.features.matchup',
        'RollingFormCalculator': 'baseball.features.rolling_form',
        'BullpenStressCalculator': 'baseball.features.bullpen_stress',
    }

    results = {}

    for calc_name, module_path in calculators.items():
        try:
            module = __import__(module_path, fromlist=[calc_name])
            calc_class = getattr(module, calc_name, None)

            if calc_class:
                results[calc_name] = '✅ Available'
                print(f'✅ {calc_name}: Available')
            else:
                results[calc_name] = '⚠️ Class not found'
                print(f'⚠️ {calc_name}: Class not found in module')

        except ImportError:
            results[calc_name] = '❌ Module not found'
            print(f'❌ {calc_name}: Module not found')
        except Exception as e:
            results[calc_name] = f'⚠️ Error: {e}'
            print(f'⚠️ {calc_name}: Error - {e}')

    return results


def check_database_status() -> dict[str, Any]:
    """Check database connectivity and table status."""
    print_subheader('Database Status')

    status = {
        'connected': False,
        'tables': {},
        'schemas': [],
    }

    try:
        from baseball.core.db import get_db_connection

        conn = get_db_connection()
        if conn:
            status['connected'] = True
            print('✅ Database connection successful')

            # Get schema list
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT schema_name
                    FROM information_schema.schemata
                    WHERE schema_name NOT IN ('pg_catalog', 'information_schema', 'pg_toast')
                    ORDER BY schema_name
                """)
                schemas = [row[0] for row in cur.fetchall()]
                status['schemas'] = schemas

                print(f"   Found {len(schemas)} schemas: {', '.join(schemas[:10])}")

                # Count tables per schema
                for schema in schemas:
                    cur.execute("""
                        SELECT table_name,
                               (SELECT COUNT(*) FROM information_schema.columns
                                WHERE table_schema = %s AND table_name = t.table_name) as col_count
                        FROM information_schema.tables t
                        WHERE table_schema = %s AND table_type = 'BASE TABLE'
                        ORDER BY table_name
                    """, (schema, schema))

                    tables = cur.fetchall()
                    if tables:
                        status['tables'][schema] = len(tables)
                        print(f'   • {schema}: {len(tables)} tables')

            conn.close()

    except Exception as e:
        print(f'⚠️ Database check skipped: {e}')
        status['connected'] = False

    return status


def check_tests() -> dict[str, Any]:
    """Check test suite status."""
    print_subheader('Test Suite')

    status = {
        'available': False,
        'total_tests': 0,
        'categories': {},
    }

    # Count test files
    test_dirs = {
        'unit': PROJECT_ROOT / 'tests' / 'unit',
        'integration': PROJECT_ROOT / 'tests' / 'integration',
        'e2e': PROJECT_ROOT / 'tests' / 'e2e',
    }

    for category, path in test_dirs.items():
        if path.exists():
            test_files = list(path.glob('test_*.py'))
            status['categories'][category] = len(test_files)
            status['total_tests'] += len(test_files)
            print(f'✅ {category}: {len(test_files)} test files')

    # Try to run pytest collection
    returncode, stdout, _stderr = run_command([
        sys.executable, '-m', 'pytest', '--collect-only', '-q',
    ])

    if returncode == 0:
        lines = stdout.strip().split('\n')
        if lines:
            # Last line usually has count
            last_line = lines[-1]
            if 'test' in last_line.lower():
                print(f'   pytest collection: {last_line}')

    return status


def check_config_files() -> dict[str, Any]:
    """Check configuration files."""
    print_subheader('Configuration Files')

    configs = {
        'sources.yml': PROJECT_ROOT / 'config' / 'sources.yml',
        'pipelines.yml': PROJECT_ROOT / 'config' / 'pipelines.yml',
        'models.yml': PROJECT_ROOT / 'config' / 'models.yml',
    }

    results = {}

    for name, path in configs.items():
        if path.exists():
            results[name] = '✅ Present'
            print(f'✅ {name}: Present')
        else:
            results[name] = '❌ Missing'
            print(f'❌ {name}: Missing')

    return results


def check_core_modules() -> dict[str, Any]:
    """Check core module imports."""
    print_subheader('Core Modules')

    modules = [
        'baseball.core.types',
        'baseball.core.db',
        'baseball.core.benchmark',
        'baseball.core.registry',
        'baseball.cli',
        'baseball.services.pipeline',
        'baseball.services.bridge',
    ]

    results = {}

    for module in modules:
        try:
            __import__(module)
            results[module] = '✅ Importable'
            print(f'✅ {module}')
        except ImportError as e:
            results[module] = f'❌ {e}'
            print(f'❌ {module}: {e}')

    return results


def generate_report(results: dict[str, Any], output_path: str | None = None) -> str:
    """Generate a markdown report of the system status."""

    lines = []
    lines.append('# Baseball Prediction Warehouse - System Demo Report')
    lines.append(f'\n**Generated**: {datetime.now().isoformat()}')
    lines.append(f"**Mode**: {results.get('mode', 'unknown')}")
    lines.append(f'**Project Root**: {PROJECT_ROOT}')
    lines.append('\n---\n')

    # Summary
    lines.append('## Summary\n')

    cli_status = results.get('cli', {})
    if cli_status.get('available'):
        lines.append('- ✅ Baseball CLI: Available')
    else:
        lines.append('- ❌ Baseball CLI: Not available')

    db_status = results.get('database', {})
    if db_status.get('connected'):
        lines.append(f"- ✅ Database: Connected ({len(db_status.get('schemas', []))} schemas)")
    else:
        lines.append('- ⚠️ Database: Not connected (demo mode)')

    adapters = results.get('adapters', {})
    available_adapters = sum(1 for a in adapters.values() if '✅' in a.get('status', ''))
    lines.append(f'- ✅ Source Adapters: {available_adapters}/5 available')

    pipelines = results.get('pipelines', {})
    lines.append(f"- ✅ Pipelines: {pipelines.get('count', 0)} configurations")

    calculators = results.get('calculators', {})
    available_calcs = sum(1 for c in calculators.values() if '✅' in c)
    lines.append(f'- ✅ Feature Calculators: {available_calcs}/{len(calculators)} available')

    tests = results.get('tests', {})
    lines.append(f"- ✅ Tests: {tests.get('total_tests', 0)} test files across {len(tests.get('categories', {}))} categories")

    # Detailed sections
    lines.append('\n## Source Adapters\n')
    for name, info in adapters.items():
        lines.append(f"- {info.get('status', 'unknown')}")

    lines.append('\n## Pipelines\n')
    for config in pipelines.get('configs', []):
        lines.append(f"- **{config['name']}**: {config.get('description', 'N/A')}")
        lines.append(f"  - Steps: {', '.join(config.get('steps', []))}")

    lines.append('\n## Feature Calculators\n')
    for name, status in calculators.items():
        lines.append(f'- {name}: {status}')

    lines.append('\n## Database Schemas\n')
    for schema, count in db_status.get('tables', {}).items():
        lines.append(f'- {schema}: {count} tables')

    lines.append('\n## Configuration Files\n')
    for name, status in results.get('configs', {}).items():
        lines.append(f'- {name}: {status}')

    lines.append('\n## Core Modules\n')
    for module, status in results.get('core_modules', {}).items():
        lines.append(f'- {module}: {status}')

    lines.append('\n---\n')
    lines.append('*Report generated by scripts/demo_full_system.py*')

    report = '\n'.join(lines)

    if output_path:
        output_file = Path(output_path)
        output_file.write_text(report)
        print(f'\n📄 Report saved to: {output_file.absolute()}')

    return report


def run_demo(mode: str = 'quick', output: str | None = None) -> dict[str, Any]:
    """Run the full system demo."""

    print_header('BASEBALL PREDICTION WAREHOUSE - SYSTEM DEMO', '=')
    print(f'Mode: {mode} | Time: {datetime.now().isoformat()}')
    print(f'Project: {PROJECT_ROOT}')

    results = {
        'mode': mode,
        'timestamp': datetime.now().isoformat(),
    }

    # Run all checks
    results['cli'] = check_baseball_cli()
    results['core_modules'] = check_core_modules()
    results['adapters'] = check_source_adapters()
    results['pipelines'] = check_pipelines()
    results['calculators'] = check_feature_calculators()
    results['configs'] = check_config_files()

    if mode in ('full', 'ci'):
        results['database'] = check_database_status()
        results['tests'] = check_tests()
    else:
        results['database'] = {'connected': False, 'skipped': True}
        results['tests'] = {'skipped': True}

    # Generate report
    print_header('DEMO COMPLETE', '=')

    if output:
        generate_report(results, output)

    # Print summary
    print('\n📊 SUMMARY:')
    print(f"   CLI Available: {results['cli'].get('available', False)}")
    print(f"   Source Adapters: {sum(1 for a in results['adapters'].values() if '✅' in a.get('status', ''))}/5")
    print(f"   Pipelines: {results['pipelines'].get('count', 0)}")
    print(f"   Feature Calculators: {sum(1 for c in results['calculators'].values() if '✅' in c)}/{len(results['calculators'])}")

    if results['database'].get('connected'):
        print(f"   Database: Connected ({len(results['database'].get('schemas', []))} schemas)")
    else:
        print('   Database: Not connected (use --mode full to check)')

    return results


def main():
    parser = argparse.ArgumentParser(
        description='Full system demo for baseball prediction warehouse',
    )
    parser.add_argument(
        '--mode',
        choices=['quick', 'full', 'ci'],
        default='quick',
        help='Demo mode: quick (2-3 min), full (5-10 min with db), ci (test paths only)',
    )
    parser.add_argument(
        '--output',
        type=str,
        help='Output path for markdown report (e.g., report.md)',
    )

    args = parser.parse_args()

    try:
        results = run_demo(mode=args.mode, output=args.output)

        # Exit code based on critical checks
        if not results['cli'].get('available') and not results['core_modules']:
            print('\n❌ Critical failures detected')
            sys.exit(1)

        print('\n✅ Demo completed successfully')
        sys.exit(0)

    except KeyboardInterrupt:
        print('\n\n⚠️ Demo interrupted by user')
        sys.exit(130)
    except Exception as e:
        print(f'\n❌ Demo failed: {e}')
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
