#!/usr/bin/env python3
"""
File: scripts/analysis/analyze_query_plan.py
Purpose: Analyze PostgreSQL query plans with graphviz visualization
Author: Agent KiloSwift
Date: 2026-04-27
Usage: uv run python scripts/analysis/analyze_query_plan.py --sql "SELECT * FROM core.games" --explain
Dependencies: graphviz, psycopg
Notes: Generates visual query plan tree with cost estimates and row counts
"""
#!/usr/bin/env python3
"""
Analyze PostgreSQL query plans and generate visual representations.

Uses EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) to get query plan,
then renders as graphviz tree showing:
- Node types (Seq Scan, Index Scan, Hash Join, etc.)
- Estimated vs actual rows
- Costs
- Buffer usage
- Join conditions
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

import graphviz

from baseball.core.db import get_db_connection

def explain_query(conn, sql: str, analyze: bool = False, buffers: bool = False) -> dict:
    """Run EXPLAIN on SQL query and return JSON plan."""
    with conn.cursor() as cur:
        explain_sql = "EXPLAIN (FORMAT JSON"
        if analyze:
            explain_sql += ", ANALYZE"
        if buffers:
            explain_sql += ", BUFFERS"
        explain_sql += f") {sql}"
        cur.execute(explain_sql)
        result = cur.fetchone()[0]
        if isinstance(result, str):
            result = json.loads(result)
    return result

def render_plan_node(node: dict, dot: graphviz.Digraph, parent_id: str = None, node_id: str = "root"):
    """Recursively render EXPLAIN node and children to graphviz."""
    node_type = node.get('Node Type', 'Unknown')
    actual_rows = node.get('Actual Rows', 'N/A')
    estimated_rows = node.get('Plan Rows', 'N/A')
    cost = node.get('Total Cost', node.get('Startup Cost', 0) + node.get('Total Cost', 0))
    width = max(node.get('Actual Width', 0), node.get('Plan Width', 0))

    # Build node label
    label_parts = [
        f"<b>{node_type}</b>",
        f"Rows: est={estimated_rows} act={actual_rows}",
        f"Cost: {cost:.1f}",
        f"Width: {width} bytes"
    ]

    # Add relation info for scans
    if 'Relation Name' in node:
        label_parts.append(f"Table: {node['Relation Name']}")
    if 'Index Name' in node:
        label_parts.append(f"Index: {node['Index Name']}")

    # Add filter/condition
    if 'Filter' in node:
        label_parts.append(f"Filter: {node['Filter'][:50]}...")

    label = '<br/>'.join(label_parts).replace('\n', '<br/>')

    # Color coding by node type
    color_map = {
        'Seq Scan': '#ffcccb',
        'Index Scan': '#c1ffc1',
        'Index Only Scan': '#c1ffc1',
        'Hash Join': '#c5d9f9',
        'Merge Join': '#c5d9f9',
        'Nested Loop': '#e6ccf9',
        'Bitmap Scan': '#ffd8b1',
        'CTE Scan': '#ffffcc',
        'Materialize': '#d3d3d3',
    }

    color = color_map.get(node_type, '#f0f0f0')

    dot.node(node_id, f'<{label}>', style='filled', fillcolor=color)

    # Connect to parent
    if parent_id:
        dot.edge(parent_id, node_id)

    # Recurse for child plans
    children = node.get('Plans', [])
    for i, child in enumerate(children):
        child_id = f"{node_id}_c{i}"
        render_plan_node(child, dot, node_id, child_id)

def generate_query_plan_diagram(plan: dict, output_path: Path):
    """Generate graphviz diagram from EXPLAIN JSON plan."""
    dot = graphviz.Digraph(comment='Query Execution Plan')
    dot.attr(rankdir='TB', fontname='Helvetica')
    dot.attr('node', shape='box', style='rounded, filled', fontsize='10')

    render_plan_node(plan[0], dot)

    # Render
    output_format = output_path.suffix.lstrip('.') or 'png'
    try:
        dot.render(str(output_path.with_suffix('')), format=output_format, cleanup=True)
        print(f"✅ Query plan diagram generated: {output_path}")
    except Exception as e:
        print(f"❌ Error rendering diagram: {e}")
        print(f"   Ensure graphviz is installed: brew install graphviz")
        return 1

    return 0

def main():
    parser = argparse.ArgumentParser(description="Visualize PostgreSQL query execution plan")
    parser.add_argument("--sql", required=True, help="SQL query to analyze")
    parser.add_argument("--output", type=Path, default=Path("query_plan"), help="Output file (without extension)")
    parser.add_argument("--analyze", action='store_true', help="Run with ANALYZE to get actual execution stats")
    parser.add_argument("--buffers", action='store_true', help="Include buffer usage statistics")
    parser.add_argument("--format", choices=['png', 'pdf', 'svg'], default='png', help="Output format")
    args = parser.parse_args()

    # Check graphviz
    try:
        subprocess.run(['dot', '-V'], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ ERROR: Graphviz required. Install: brew install graphviz or apt-get install graphviz")
        return 1

    # Connect to DB
    try:
        conn = get_db_connection()
    except Exception as e:
        print(f"❌ ERROR: Could not connect: {e}")
        return 1

    print(f"Analyzing query: {args.sql[:80]}...")
    plan = explain_query(conn, args.sql, analyze=args.analyze, buffers=args.buffers)

    # Print textual plan
    print("\n📊 EXPLAIN Output (JSON):")
    print(json.dumps(plan, indent=2)[:1000])  # Truncate for readability

    # Generate diagram
    output_file = args.output.with_suffix(f'.{args.format}')
    return generate_query_plan_diagram(plan, output_file)

if __name__ == "__main__":
    sys.exit(main())
