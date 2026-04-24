#!/usr/bin/env python3
"""
Add standardized sqlfluff-compliant headers to all SQL files.

This script:
1. Finds all .sql files in the project
2. Checks if they already have a proper header (File:/Purpose:/Author:/Date:)
3. Generates and prepends a compliant header if missing
4. Preserves existing content
"""

import re
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path('/home/cbwinslow/workspace/retrosheet')
DATE_STR = datetime.now().strftime('%Y-%m-%d')


def generate_purpose(filepath: Path) -> str:
    """Generate a purpose description from the filename."""
    name = filepath.stem
    parts = name.replace('_', ' ').replace('-', ' ').split()

    # Category based on directory
    parent = filepath.parent.name
    category_map = {
        'core': 'Core database',
        'bridge': 'Bridge table',
        'features': 'Feature engineering',
        'maintenance': 'Database maintenance',
        'mlb': 'MLB live data',
        'external': 'External data',
        'live': 'Live data ingestion',
        'optimization': 'Database optimization',
        'eda': 'Exploratory data analysis',
        'test': 'Test schema',
    }
    category = category_map.get(parent, parent)

    # Clean up the name parts
    cleaned = []
    for p in parts:
        p_lower = p.lower()
        # Skip numeric prefixes
        if p.isdigit():
            continue
        # Expand common abbreviations
        if p_lower == 'xref':
            cleaned.append('cross-reference')
        elif p_lower == 'pa':
            cleaned.append('plate appearance')
        elif p_lower == 'mlb':
            cleaned.append('MLB')
        elif p_lower == 'espn':
            cleaned.append('ESPN')
        elif p_lower == 'gis':
            cleaned.append('GIS')
        elif p_lower == 'pg':
            cleaned.append('PostgreSQL')
        elif p_lower == 'kb':
            cleaned.append('knowledge base')
        else:
            cleaned.append(p.capitalize())

    purpose = ' '.join(cleaned)

    # Determine action verb based on content
    action = 'SQL operations for'
    if 'init' in name.lower() or 'schema' in name.lower():
        action = 'Initialize schema and tables for'
    elif 'procedure' in name.lower() or 'function' in name.lower():
        action = 'Stored procedures and functions for'
    elif 'view' in name.lower():
        action = 'Create views for'
    elif 'index' in name.lower():
        action = 'Create performance indexes for'
    elif 'feature' in name.lower():
        action = 'Build ML features for'
    elif 'model' in name.lower():
        action = 'Define prediction models for'
    elif 'install' in name.lower():
        action = 'Install and configure'
    elif 'monitor' in name.lower():
        action = 'Monitoring and health checks for'
    elif 'validation' in name.lower():
        action = 'Data validation for'
    elif 'register' in name.lower():
        action = 'Register and manage'

    return f'{action} {category} - {purpose}'


def has_proper_header(content: str) -> bool:
    """Check if the file already has all required header fields."""
    first_50_lines = '\n'.join(content.split('\n')[:50])
    has_file = 'File:' in first_50_lines
    has_purpose = 'Purpose:' in first_50_lines
    has_author = 'Author:' in first_50_lines
    has_date = 'Date:' in first_50_lines
    return has_file and has_purpose and has_author and has_date


def extract_existing_purpose(content: str) -> str | None:
    """Try to extract an existing purpose/description from the file."""
    lines = content.split('\n')
    # Look for purpose in existing header
    for line in lines[:30]:
        if 'Purpose:' in line:
            match = re.search(r'Purpose:\s*(.+)', line)
            if match:
                return match.group(1).strip()
    # Look for descriptive line comments at the top
    desc_lines = []
    for line in lines[:10]:
        stripped = line.strip()
        if stripped.startswith('--') and not stripped.startswith('-- ==='):
            desc = stripped[2:].strip()
            if desc and not desc.lower().startswith('file:'):
                desc_lines.append(desc)
    if desc_lines:
        return ' '.join(desc_lines)
    return None


def create_header(filepath: Path, content: str) -> str:
    """Create a sqlfluff-compliant header for the file."""
    rel_path = filepath.relative_to(PROJECT_ROOT)

    # Try to use existing purpose, fall back to generated
    purpose = extract_existing_purpose(content)
    if not purpose:
        purpose = generate_purpose(filepath)

    # Trim purpose to reasonable length
    if len(purpose) > 120:
        purpose = purpose[:117] + '...'

    header_lines = [
        f'-- File: {rel_path}',
        f'-- Purpose: {purpose}',
        '-- Author: Agent Cascade',
        f'-- Date: {DATE_STR}',
        '',
    ]
    return '\n'.join(header_lines)


def process_file(filepath: Path) -> bool:
    """Process a single SQL file. Returns True if modified."""
    content = filepath.read_text(encoding='utf-8')

    if has_proper_header(content):
        return False  # Already has proper header

    # Check if there's already a header we should preserve some of
    header = create_header(filepath, content)

    # Remove old simple line-comment headers (but not block comments with useful info)
    lines = content.split('\n')
    new_lines = []
    skip_count = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        # Skip initial empty lines and simple descriptive comments
        if skip_count == i and (
            stripped == '' or (stripped.startswith('--') and not stripped.startswith('-- File:'))
        ):
            skip_count += 1
            continue
        new_lines.append(line)

    # Rejoin content and ensure single trailing newline
    new_content = header + '\n'.join(new_lines)
    new_content = new_content.rstrip('\n') + '\n'

    filepath.write_text(new_content, encoding='utf-8')
    return True


def main():
    """Main entry point."""
    sql_files = sorted(PROJECT_ROOT.rglob('*.sql'))

    modified = 0
    skipped = 0
    errors = 0

    print(f'Found {len(sql_files)} SQL files')
    print('=' * 60)

    for filepath in sql_files:
        try:
            if process_file(filepath):
                rel = filepath.relative_to(PROJECT_ROOT)
                print(f'  [MODIFIED] {rel}')
                modified += 1
            else:
                skipped += 1
        except Exception as e:
            print(f'  [ERROR] {filepath.relative_to(PROJECT_ROOT)}: {e}')
            errors += 1

    print('=' * 60)
    print(f'Modified: {modified}')
    print(f'Skipped (already have headers): {skipped}')
    print(f'Errors: {errors}')


if __name__ == '__main__':
    main()
