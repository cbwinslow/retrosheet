#!/usr/bin/env python3
"""
SQL file maintenance utility - unified tool for SQL header and comment management.

Author: Agent cbwinslow/retrosheet
Date: 2026-04-26

This script consolidates functionality from:
- add_sql_headers.py (add standardized headers)
- add_table_comments.py (add table comments)
- apply_accurate_headers.py (apply human-reviewed purposes)
- fix_sql_headers.py (fix headers from SQL content analysis)

Usage:
    python scripts/utility/sql_maintenance.py add-headers [--check]
    python scripts/utility/sql_maintenance.py add-comments [--dry-run]
    python scripts/utility/sql_maintenance.py fix-headers [--use-content]
    python scripts/utility/sql_maintenance.py check-all
"""

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path('/home/cbwinslow/workspace/retrosheet')
DATE_STR = datetime.now().strftime('%Y-%m-%d')

# Accurate purposes from apply_accurate_headers.py (subset of most common)
ACCURATE_PURPOSES = {
    'sql/core/001_init.sql': 'Initialize core database schemas and raw landing tables',
    'sql/core/010_core_games_events.sql': 'Create core games, events, teams, players tables',
    'sql/bridge/900_bridge_monitoring_views.sql': 'Monitoring views for bridge table counts and quality',
    'sql/bridge/999_master_bridge_population_procedure.sql': 'Master procedure to populate all bridge tables',
}

# Known table comments from add_table_comments.py (most common tables)
KNOWN_COMMENTS = {
    'core.plate_appearances': 'Enriched plate appearance records with game state',
    'raw_retrosheet.biofile': 'Player biographical and career metadata from Retrosheet',
    'raw_retrosheet.teams_reference': 'Team reference data with league and active seasons',
    'raw_statcast.events': 'Statcast pitch-level events with physics data',
    'raw_espn.game_snapshots': 'ESPN API game snapshot data',
}


def generate_purpose(filepath: Path) -> str:
    """Generate a purpose description from the filename."""
    name = filepath.stem
    parts = name.replace('_', ' ').replace('-', ' ').split()
    parent = filepath.parent.name

    category_map = {
        'core': 'Core database',
        'bridge': 'Bridge table',
        'features': 'Feature engineering',
        'external': 'External data',
        'live': 'Live data ingestion',
    }
    category = category_map.get(parent, parent)

    cleaned = []
    for p in parts:
        if p.isdigit():
            continue
        p_lower = p.lower()
        if p_lower == 'xref':
            cleaned.append('cross-reference')
        elif p_lower == 'pa':
            cleaned.append('plate appearance')
        elif p_lower == 'mlb':
            cleaned.append('MLB')
        elif p_lower == 'espn':
            cleaned.append('ESPN')
        else:
            cleaned.append(p.capitalize())

    purpose = ' '.join(cleaned)
    action = 'SQL operations for'

    if 'init' in name.lower() or 'schema' in name.lower():
        action = 'Initialize schema and tables for'
    elif 'procedure' in name.lower():
        action = 'Stored procedures for'
    elif 'view' in name.lower():
        action = 'Create views for'
    elif 'feature' in name.lower():
        action = 'Build ML features for'

    return f'{action} {category} - {purpose}'


def has_proper_header(content: str) -> bool:
    """Check if file has required header fields."""
    first_50 = '\n'.join(content.split('\n')[:50])
    return all(field in first_50 for field in ['File:', 'Purpose:', 'Author:', 'Date:'])


def add_header_to_file(filepath: Path, check_only: bool = False) -> bool:
    """Add standardized header to a SQL file if missing."""
    content = filepath.read_text(encoding='utf-8')

    if has_proper_header(content):
        return True

    if check_only:
        print(f'  Missing header: {filepath}')
        return False

    # Generate header
    relative_path = filepath.relative_to(PROJECT_ROOT)
    purpose = ACCURATE_PURPOSES.get(str(relative_path), generate_purpose(filepath))

    header = f"""--
-- File: {relative_path}
-- Purpose: {purpose}
-- Author: Agent cbwinslow/retrosheet
-- Date: {DATE_STR}
--

"""

    new_content = header + content
    filepath.write_text(new_content, encoding='utf-8')
    print(f'  Added header: {filepath}')
    return True


def extract_tables(content: str) -> list[str]:
    """Extract table names from CREATE TABLE statements."""
    tables = []
    pattern = re.compile(
        r'CREATE\s+(?:TABLE|MATERIALIZED\s+VIEW)\s+(?:IF\s+NOT\s+EXISTS\s+)?'
        r'([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)?)',
        re.IGNORECASE,
    )
    for match in pattern.finditer(content):
        tables.append(match.group(1))
    return tables


def generate_comment(table_name: str) -> str:
    """Generate comment for a table based on known mappings or patterns."""
    if table_name in KNOWN_COMMENTS:
        return KNOWN_COMMENTS[table_name]

    parts = table_name.split('.')
    name = parts[1] if len(parts) == 2 else table_name
    clean_name = name.replace('_', ' ')

    if 'snapshot' in name.lower():
        return f'Raw {clean_name} with source-preserved JSON payloads'
    if 'raw_' in name.lower():
        return f'Source-preserved {clean_name} data'
    if 'bridge' in name.lower() or 'xref' in name.lower():
        return f'Cross-reference mapping table for {clean_name}'
    if 'feature' in name.lower():
        return f'ML feature table for {clean_name}'

    return f'{clean_name} data table'


def add_comments_to_file(filepath: Path, dry_run: bool = False) -> int:
    """Add COMMENT ON statements to a SQL file for missing table comments."""
    content = filepath.read_text(encoding='utf-8')
    tables = extract_tables(content)

    if not tables:
        return 0

    added = 0
    comments_section = []

    for table in tables:
        comment_stmt = f"COMMENT ON TABLE {table} IS '{generate_comment(table)}';"
        if comment_stmt not in content:
            comments_section.append(comment_stmt)
            added += 1

    if comments_section and not dry_run:
        # Add comments at the end of the file
        new_content = (
            content.rstrip() + '\n\n-- Table comments\n' + '\n'.join(comments_section) + '\n'
        )
        filepath.write_text(new_content, encoding='utf-8')
        print(f'  Added {len(comments_section)} comments: {filepath}')

    return added


def fix_header_from_content(filepath: Path) -> bool:
    """Fix SQL header by analyzing actual SQL content."""
    content = filepath.read_text(encoding='utf-8')

    if has_proper_header(content):
        return True

    # Extract operations from content
    operations = []

    # Find CREATE statements
    create_pattern = re.compile(
        r'CREATE\s+(?:OR\s+REPLACE\s+)?'
        r'(TABLE|VIEW|INDEX|PROCEDURE|FUNCTION|MATERIALIZED\s+VIEW)',
        re.IGNORECASE,
    )
    for match in create_pattern.finditer(content):
        operations.append(match.group(1).upper())

    if not operations:
        return add_header_to_file(filepath)

    # Generate purpose from operations
    unique_ops = list(dict.fromkeys(operations))  # preserve order, remove dups
    if len(unique_ops) == 1:
        purpose = f'Create {unique_ops[0].lower()} for database objects'
    else:
        purpose = f'Create {", ".join(op.lower() for op in unique_ops[:3])} for database objects'

    relative_path = filepath.relative_to(PROJECT_ROOT)
    header = f"""--
-- File: {relative_path}
-- Purpose: {purpose}
-- Author: Agent cbwinslow/retrosheet
-- Date: {DATE_STR}
--

"""

    new_content = header + content
    filepath.write_text(new_content, encoding='utf-8')
    print(f'  Fixed header: {filepath}')
    return True


def cmd_add_headers(args):
    """Add standardized headers to SQL files."""
    print('Adding SQL headers...')
    sql_files = list(PROJECT_ROOT.rglob('*.sql'))

    fixed = 0
    already_ok = 0

    for filepath in sql_files:
        if 'node_modules' in str(filepath) or '.venv' in str(filepath):
            continue

        if has_proper_header(filepath.read_text(encoding='utf-8')):
            already_ok += 1
        else:
            if add_header_to_file(filepath, check_only=args.check):
                fixed += 1

    print(f'\nSummary: {fixed} files updated, {already_ok} already have headers')
    return 0


def cmd_add_comments(args):
    """Add table comments to SQL files."""
    print('Adding table comments...')
    sql_files = list(PROJECT_ROOT.rglob('*.sql'))

    total_added = 0
    for filepath in sql_files:
        if 'node_modules' in str(filepath) or '.venv' in str(filepath):
            continue

        added = add_comments_to_file(filepath, dry_run=args.dry_run)
        if added:
            total_added += added
            if args.dry_run:
                print(f'  Would add {added} comments: {filepath}')

    print(f'\nSummary: {total_added} comments added')
    return 0


def cmd_fix_headers(args):
    """Fix headers by analyzing SQL content."""
    print('Fixing SQL headers from content...')
    sql_files = list(PROJECT_ROOT.rglob('*.sql'))

    fixed = 0
    for filepath in sql_files:
        if 'node_modules' in str(filepath) or '.venv' in str(filepath):
            continue

        if fix_header_from_content(filepath):
            fixed += 1

    print(f'\nSummary: {fixed} files processed')
    return 0


def cmd_check_all(args):
    """Check all SQL files for headers and comments."""
    print('Checking all SQL files...')
    sql_files = list(PROJECT_ROOT.rglob('*.sql'))

    missing_headers = 0
    missing_comments = 0
    ok_files = 0

    for filepath in sql_files:
        if 'node_modules' in str(filepath) or '.venv' in str(filepath):
            continue

        content = filepath.read_text(encoding='utf-8')
        has_header = has_proper_header(content)
        has_comments = 'COMMENT ON' in content[:2000]  # Check near the top

        if not has_header:
            missing_headers += 1
            print(f'  Missing header: {filepath}')
        elif not has_comments and 'CREATE TABLE' in content:
            missing_comments += 1
        else:
            ok_files += 1

    print('\nSummary:')
    print(f'  OK: {ok_files} files')
    print(f'  Missing headers: {missing_headers} files')
    print(f'  Missing comments: {missing_comments} files')
    return 0


def main():
    parser = argparse.ArgumentParser(
        description='SQL file maintenance utility',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/utility/sql_maintenance.py add-headers
  python scripts/utility/sql_maintenance.py add-headers --check
  python scripts/utility/sql_maintenance.py add-comments --dry-run
  python scripts/utility/sql_maintenance.py fix-headers
  python scripts/utility/sql_maintenance.py check-all
""",
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to run')

    # add-headers
    headers_parser = subparsers.add_parser(
        'add-headers', help='Add standardized headers to SQL files',
    )
    headers_parser.add_argument('--check', action='store_true', help='Only check, do not modify')

    # add-comments
    comments_parser = subparsers.add_parser('add-comments', help='Add table comments to SQL files')
    comments_parser.add_argument('--dry-run', action='store_true', help='Show what would be added')

    # fix-headers
    subparsers.add_parser('fix-headers', help='Fix headers by analyzing SQL content')

    # check-all
    subparsers.add_parser('check-all', help='Check all SQL files for issues')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    commands = {
        'add-headers': cmd_add_headers,
        'add-comments': cmd_add_comments,
        'fix-headers': cmd_fix_headers,
        'check-all': cmd_check_all,
    }

    return commands[args.command](args)


if __name__ == '__main__':
    sys.exit(main())
