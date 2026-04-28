#!/usr/bin/env python3
"""
File: scripts/analysis/generate_schema_diagram.py
Purpose: Generate database schema diagrams using graphviz from PostgreSQL metadata
Author: Agent KiloSwift
Date: 2026-04-27
Usage: uv run python scripts/analysis/generate_schema_diagram.py --schema core --output schema_core.png
Dependencies: graphviz, psycopg
Notes: Generates ERD-style diagrams of database schemas automatically
"""

import argparse

This script introspects PostgreSQL database metadata to create
Entity-Relationship Diagrams (ERD) showing tables, columns,
relationships, and optionally data types.
"""

import argparse
import subprocess
import sys
from pathlib import Path

import pandas as pd

from baseball.core.db import get_db_connection

def check_graphviz() -> bool:
    """Check if graphviz dot executable is available."""
    try:
        subprocess.run(['dot', '-V'], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def get_schema_tables(conn, schema: str) -> pd.DataFrame:
    """Get all tables in a schema."""
    query = f"""
        SELECT
            t.table_name,
            t.table_type,
            pg_size_pretty(pg_total_relation_size(format('"%s"."%s"', t.table_schema, t.table_name))) as size
        FROM information_schema.tables t
        WHERE t.table_schema = '{schema}'
        ORDER BY t.table_name;
    """
    return pd.read_sql(query, conn)

def get_table_columns(conn, schema: str, table: str) -> pd.DataFrame:
    """Get column information for a table."""
    query = f"""
        SELECT
            c.column_name,
            c.data_type,
            c.is_nullable,
            c.column_default,
            pg_catalog.col_description(format('"%s"."%s"', '{schema}', '{table}')::regclass::oid, c.ordinal_position) as description
        FROM information_schema.columns c
        WHERE c.table_schema = '{schema}'
          AND c.table_name = '{table}'
        ORDER BY c.ordinal_position;
    """
    return pd.read_sql(query, conn)

def get_foreign_keys(conn, schema: str) -> pd.DataFrame:
    """Get foreign key relationships within schema."""
    query = f"""
        SELECT
            tc.constraint_name,
            kcu.table_name as source_table,
            kcu.column_name as source_column,
            ccu.table_schema as target_schema,
            ccu.table_name as target_table,
            ccu.column_name as target_column
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
            ON tc.constraint_name = kcu.constraint_name
            AND tc.table_schema = kcu.table_schema
        JOIN information_schema.constraint_column_usage ccu
            ON tc.constraint_name = ccu.constraint_name
            AND tc.table_schema = ccu.table_schema
        WHERE tc.constraint_type = 'FOREIGN KEY'
          AND tc.table_schema = '{schema}'
        ORDER BY tc.constraint_name;
    """
    return pd.read_sql(query, conn)

def generate_dot_schema(conn, schema: str, output_file: Path,
                       include_columns: bool = True,
                       include_types: bool = True,
                       include_sizes: bool = False) -> str:
    """Generate Graphviz DOT representation of schema."""

    # Start DOT graph
    dot_lines = [
        f'digraph "{schema}" {{',
        f'  label="Schema: {schema}";',
        '  rankdir=LR;',  # Left to right layout
        '  node [shape=plaintext, fontname="Helvetica"];',
        '',
    ]

    tables = get_schema_tables(conn, schema)

    for _, table in tables.iterrows():
        table_name = table['table_name']
        table_type = table['table_type']
        table_size = table['size'] if include_sizes else ''

        # Build table label with HTML-like formatting
        label_lines = [
            f'<table border="1" cellborder="0" cellspacing="0" cellpadding="4">',
            f'<tr><td colspan="3" bgcolor="#e8e8e8"><b>{table_name}</b><br/>[{table_type}]</td></tr>'
            if table_type == 'VIEW' else
            f'<tr><td colspan="3" bgcolor="#e8e8e8"><b>{table_name}</b>{f" ({table_size})" if table_size else ""}</td></tr>'
        ]

        if include_columns:
            cols_df = get_table_columns(conn, schema, table_name)
            for _, col in cols_df.iterrows():
                col_name = col['column_name']
                data_type = col['data_type'] if include_types else ''
                nullable = 'NULL' if col['is_nullable'] == 'YES' else 'NOT NULL'
                pk_marker = '🔑' if col['column_name'] in get_primary_keys(conn, schema, table_name) else ''
                label_lines.append(
                    f'<tr><td align="left">{col_name} {pk_marker}</td>'
                    f'<td align="left">{data_type}</td>'
                    f'<td align="left">{nullable}</td></tr>'
                )

        label_lines.append('</table>')
        label = '\n'.join(label_lines)

        dot_lines.append(f'  {schema}_{table_name} [label=<{label}>];')
        dot_lines.append('')

    # Add foreign key relationships
    fks = get_foreign_keys(conn, schema)
    for _, fk in fks.iterrows():
        src = f'{schema}_{fk["source_table"]}'
        tgt = f'{fk["target_schema"]}_{fk["target_table"]}'
        # Create edge with label showing columns
        edge_label = f'{fk["source_column"]} → {fk["target_column"]}'
        dot_lines.append(f'  {src} -> {tgt} [label="{edge_label}", style=solid, arrowhead=normal];')

    dot_lines.append('}')
    return '\n'.join(dot_lines)

def get_primary_keys(conn, schema: str, table: str) -> list:
    """Get primary key columns for a table."""
    query = f"""
        SELECT kcu.column_name
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
            ON tc.constraint_name = kcu.constraint_name
            AND tc.table_schema = kcu.table_schema
        WHERE tc.constraint_type = 'PRIMARY KEY'
          AND tc.table_schema = '{schema}'
          AND tc.table_name = '{table}'
        ORDER BY kcu.ordinal_position;
    """
    result = pd.read_sql(query, conn)
    return result['column_name'].tolist()

def main():
    parser = argparse.ArgumentParser(description="Generate database schema diagrams")
    parser.add_argument(
        "--schema",
        required=True,
        help="Schema name to diagram (e.g., core, bridge, features)"
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Output file path (PNG, PDF, SVG, etc.)"
    )
    parser.add_argument(
        "--format",
        choices=['png', 'pdf', 'svg'],
        default='png',
        help="Output format (default: png)"
    )
    parser.add_argument(
        "--no-columns",
        action='store_true',
        help="Don't include column details"
    )
    parser.add_argument(
        "--no-types",
        action='store_true',
        help="Don't include data types"
    )
    parser.add_argument(
        "--show-sizes",
        action='store_true',
        help="Show table sizes"
    )
    args = parser.parse_args()

    # Check graphviz
    if not check_graphviz():
        print("❌ ERROR: Graphviz 'dot' executable not found.")
        print("Install graphviz:")
        print("  Ubuntu/Debian: sudo apt-get install graphviz")
        print("  macOS: brew install graphviz")
        print("  Windows: choco install graphviz")
        return 1

    # Ensure output directory exists
    args.output.parent.mkdir(parents=True, exist_ok=True)

    # Connect to database
    try:
        conn = get_db_connection()
    except Exception as e:
        print(f"❌ ERROR: Could not connect to database: {e}")
        return 1

    print(f"Generating schema diagram for '{args.schema}'...")

    # Generate DOT file
    dot_content = generate_dot_schema(
        conn,
        args.schema,
        args.output,
        include_columns=not args.no_columns,
        include_types=not args.no_types,
        include_sizes=args.show_sizes
    )

    # Write intermediate DOT file (for debugging)
    dot_file = args.output.with_suffix('.dot')
    dot_file.write_text(dot_content)
    print(f"   DOT file: {dot_file}")

    # Render diagram using graphviz
    output_format = args.format or args.output.suffix.lstrip('.')
    try:
        subprocess.run(
            ['dot', f'-T{output_format}', str(dot_file), '-o', str(args.output)],
            check=True,
            capture_output=True
        )
        print(f"✅ Diagram generated: {args.output}")
    except subprocess.CalledProcessError as e:
        print(f"❌ ERROR: Graphviz failed: {e.stderr.decode()}")
        return 1

    conn.close()
    return 0

if __name__ == "__main__":
    sys.exit(main())
