#!/usr/bin/env python3
"""
File: scripts/analysis/visualize_dependencies.py
Purpose: Generate dependency graph of Python modules and SQL scripts using AST
Author: Agent KiloSwift
Date: 2026-04-27
Usage: uv run python scripts/analysis/visualize_dependencies.py --output deps.png
Dependencies: graphviz, ast (stdlib)
Notes: Parses Python import statements and SQL includes to build dependency graph
"""

import argparse

This script creates a visual representation of module dependencies:
- Python imports (regular, from ... import)
- SQL file inclusion/organization (ordered by prefix)
- Script execution order hints
"""

import argparse
import ast
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple

import graphviz

PROJECT_ROOT = Path(__file__).parent.parent.parent

def parse_python_imports(filepath: Path) -> List[Tuple[str, str]]:
    """Extract import statements from Python file using AST.
    
    Returns list of (source_module, imported_name) tuples.
    """
    try:
        with open(filepath, 'r') as f:
            content = f.read()
        tree = ast.parse(content)
    except Exception:
        return []

    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append((alias.name.split('.')[0], alias.name))
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ''
            if module:
                module = module.split('.')[0]
                for alias in node.names:
                    imports.append((module, f"{module}.{alias.name}"))
    return imports

def get_sql_file_order(sql_dir: Path) -> List[Path]:
    """Get SQL files in execution order based on filename prefixes."""
    sql_files = list(sql_dir.rglob('*.sql'))
    # Sort by numeric prefix (001, 002, ...)
    def sort_key(path: Path):
        parts = path.parts
        filename = path.name
        # Extract leading number if present
        import re
        match = re.match(r'^(\d+)', filename)
        prefix = int(match.group(1)) if match else 9999
        return (prefix, str(path))
    return sorted(sql_files, key=sort_key)

def build_python_dependency_graph(root: Path) -> graphviz.Digraph:
    """Build dependency graph of Python modules."""
    dot = graphviz.Digraph(comment='Python Module Dependencies')
    dot.attr(rankdir='LR', fontname='Helvetica')
    dot.attr('node', shape='box', style='rounded', fontname='Helvetica')

    modules: Dict[str, Set[str]] = {}

    # Walk through Python files
    py_files = list(root.rglob('*.py'))
    for pyfile in py_files:
        # Skip virtual env and hidden dirs
        if any(part.startswith('.') for part in pyfile.parts):
            continue
        if 'venv' in pyfile.parts or '__pycache__' in pyfile.parts:
            continue

        module_name = pyfile.relative_to(root).with_suffix('').as_posix().replace('/', '.')
        imports = parse_python_imports(pyfile)

        for src, full_import in imports:
            # Only include project-local modules
            if src in ('baseball', 'mlb_predict', 'scripts', 'tests', 'retrosheet', 'bridge', 'core', 'features', 'models', 'prediction_framework'):
                if module_name not in modules:
                    modules[module_name] = set()
                modules[module_name].add(src)

    # Add nodes and edges
    seen = set()
    for module, deps in modules.items():
        if module not in seen:
            dot.node(module, module)
            seen.add(module)
        for dep in deps:
            if dep not in seen:
                dot.node(dep, dep)
                seen.add(dep)
            dot.edge(dep, module)

    return dot

def build_sql_dependency_graph(sql_dir: Path) -> graphviz.Digraph:
    """Build graph of SQL file execution order."""
    dot = graphviz.Digraph(comment='SQL File Execution Order')
    dot.attr(rankdir='TB', fontname='Helvetica')  # Top to bottom
    dot.attr('node', shape='note', style='', fontname='Courier')

    ordered_files = get_sql_file_order(sql_dir)
    prev_category = None

    for i, sqlfile in enumerate(ordered_files):
        # Get relative path for label
        relpath = sqlfile.relative_to(PROJECT_ROOT)
        label = f"{relpath}<br/><font point-size='8'>(Order: {i+1})</font>"

        # Categorize by directory
        category = sqlfile.parent.name
        node_id = f"sql_{i}"

        dot.node(node_id, label=f'<{label}>')

        # Connect sequentially within category
        if i > 0:
            dot.edge(f"sql_{i-1}", node_id, style='dashed', weight='1')

    return dot

def build_combined_graph(root: Path, sql_dir: Path) -> graphviz.Digraph:
    """Build combined graph showing Python→SQL dependencies."""
    dot = graphviz.Digraph(comment='Combined Dependency Graph')
    dot.attr(rankdir='LR', fontname='Helvetica')
    dot.attr('node', shape='box', style='rounded', fontname='Helvetica')

    # Cluster for Python modules
    with dot.subgraph(name='cluster_python') as c:
        c.attr(label='Python Modules', style='dashed')
        py_deps = build_python_dependency_graph(root)
        # Copy nodes from py_deps (can't directly merge subgraphs easily)
        # Approach: copy node definitions
        pass

    # Cluster for SQL files
    with dot.subgraph(name='cluster_sql') as c:
        c.attr(label='SQL Scripts', style='dashed')
        sql_files = get_sql_file_order(sql_dir)
        for i, sqlfile in enumerate(sql_files):
            relpath = sqlfile.relative_to(PROJECT_ROOT)
            node_id = f"sql_{sqlfile.name}"
            c.node(node_id, f"{sqlfile.name}", shape='note', fontsize='10')

    # Connect Python → SQL via script usage patterns
    # Scan Python files for SQL file references
    py_files = list(root.rglob('*.py'))
    for pyfile in py_files:
        if any(part.startswith('.') for part in pyfile.parts):
            continue
        try:
            with open(pyfile) as f:
                content = f.read()
            # Look for SQL file references
            for sqlfile in sql_files:
                if sqlfile.name in content:
                    py_mod = pyfile.relative_to(root).with_suffix('').as_posix().replace('/', '.')
                    dot.edge(py_mod, f"sql_{sqlfile.name}", style='dotted')
        except Exception:
            pass

    return dot

def main():
    parser = argparse.ArgumentParser(description="Generate dependency graphs")
    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=PROJECT_ROOT / "docs" / "dependency_graph.png",
        help="Output image file path"
    )
    parser.add_argument(
        "--type",
        choices=['python', 'sql', 'combined'],
        default='python',
        help="Graph type: python imports, sql order, or combined"
    )
    parser.add_argument(
        "--format",
        choices=['png', 'pdf', 'svg'],
        default='png',
        help="Output format (default: png)"
    )
    parser.add_argument(
        "--show",
        action='store_true',
        help="Open the generated image after creation"
    )
    args = parser.parse_args()

    if not check_graphviz():
        print("❌ ERROR: Graphviz required. Install: brew install graphviz (macOS) or apt-get install graphviz (Ubuntu)")
        return 1

    args.output.parent.mkdir(parents=True, exist_ok=True)

    print(f"Generating {args.type} dependency graph...")

    if args.type == 'python':
        dot = build_python_dependency_graph(PROJECT_ROOT)
    elif args.type == 'sql':
        dot = build_sql_dependency_graph(PROJECT_ROOT / 'sql')
    else:  # combined
        dot = build_combined_graph(PROJECT_ROOT, PROJECT_ROOT / 'sql')

    # Render
    try:
        dot.render(
            filename=str(args.output.with_suffix('')),
            format=args.format,
            cleanup=True,
            view=args.show
        )
        print(f"✅ Graph generated: {args.output}")
        return 0
    except Exception as e:
        print(f"❌ ERROR: Graphviz rendering failed: {e}")
        return 1

def check_graphviz() -> bool:
    """Check if graphviz is available."""
    import subprocess
    try:
        subprocess.run(['dot', '-V'], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

if __name__ == "__main__":
    sys.exit(main())
