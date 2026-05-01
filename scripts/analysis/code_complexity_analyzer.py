#!/usr/bin/env python3
"""
File: scripts/analysis/code_complexity_analyzer.py
Purpose: Analyze Python code complexity using AST and report metrics
Author: Agent KiloSwift
Date: 2026-04-27
Usage: uv run python scripts/analysis/code_complexity_analyzer.py --path scripts/
Dependencies: ast (stdlib), radon (optional for advanced metrics)
"""

import argparse
import ast
import sys
from collections import defaultdict
from pathlib import Path


PROJECT_ROOT = Path(__file__).parent.parent.parent

def complexity_for_function(node: ast.FunctionDef) -> int:
    """Calculate cyclomatic complexity for a function."""
    complexity = 1  # Base complexity
    for child in ast.walk(node):
        if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
            complexity += 1
        elif isinstance(child, ast.BoolOp):
            # Each and/or adds a branch
            complexity += len(child.values) - 1
    return complexity

def analyze_file(filepath: Path) -> list[dict]:
    """Analyze a single Python file and return metrics for each function/class."""
    try:
        with open(filepath) as f:
            tree = ast.parse(f.read(), filename=str(filepath))
    except SyntaxError as e:
        print(f'⚠️  Syntax error in {filepath}: {e}')
        return []

    results = []
    relpath = filepath.relative_to(PROJECT_ROOT)

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            complexity = complexity_for_function(node)
            lines = node.end_lineno - node.lineno + 1 if node.end_lineno else 0
            results.append({
                'file': str(relpath),
                'name': node.name,
                'type': 'function',
                'lineno': node.lineno,
                'lines': lines,
                'complexity': complexity,
                'args': len(node.args.args),
            })
        elif isinstance(node, ast.ClassDef):
            methods = [
                m.name for m in node.body if isinstance(m, ast.FunctionDef)
            ]
            results.append({
                'file': str(relpath),
                'name': node.name,
                'type': 'class',
                'lineno': node.lineno,
                'methods': len(methods),
                'method_names': ', '.join(methods[:5]),
            })

    return results

def analyze_directory(root: Path, exclude_dirs: list[str] | None = None) -> tuple[list[dict], dict]:
    """Recursively analyze all Python files under root."""
    if exclude_dirs is None:
        exclude_dirs = ['.git', '__pycache__', '.venv', 'node_modules', '.mypy_cache']

    all_results = []
    summary = defaultdict(int)

    for pyfile in root.rglob('*.py'):
        if any(part in exclude_dirs for part in pyfile.parts):
            continue
        file_results = analyze_file(pyfile)
        all_results.extend(file_results)
        summary['total_files'] += 1
        summary['total_functions'] += len([r for r in file_results if r['type'] == 'function'])
        summary['total_classes'] += len([r for r in file_results if r['type'] == 'class'])

    return all_results, dict(summary)

def print_report(results: list[dict], summary: dict):
    """Print formatted complexity report."""
    print('=' * 60)
    print('Code Complexity Analysis Report')
    print('=' * 60)
    print(f"Files analyzed:  {summary.get('total_files', 0)}")
    print(f"Functions:       {summary.get('total_functions', 0)}")
    print(f"Classes:         {summary.get('total_classes', 0)}")
    print()

    # Sort functions by complexity
    functions = [r for r in results if r['type'] == 'function']
    functions.sort(key=lambda x: (-x['complexity'], x['lines']))

    if functions:
        print('Top 20 most complex functions:')
        print(f"{'Rank':<6} {'Complexity':<12} {'Lines':<8} {'File':<35} {'Function':<30}")
        print('-' * 95)
        for rank, fn in enumerate(functions[:20], 1):
            status = '⚠️  HIGH' if fn['complexity'] > 10 else 'OK'
            print(f"{rank:<6} {fn['complexity']:<12} {fn['lines']:<8} {fn['file']:<35} {fn['name']:<30} {status}")

    print()

    # Classes summary
    classes = [r for r in results if r['type'] == 'class']
    if classes:
        print(f"{'Class':<35} {'Methods':<8} {'File':<35}")
        print('-' * 78)
        for cls in sorted(classes, key=lambda x: -x.get('methods', 0))[:15]:
            print(f"{cls['name']:<35} {cls.get('methods', 0):<8} {cls['file']:<35}")

    # Summary statistics
    if functions:
        avg_complexity = sum(f['complexity'] for f in functions) / len(functions)
        max_complexity = max(f['complexity'] for f in functions)
        avg_lines = sum(f['lines'] for f in functions if f['lines'] > 0) / len(functions)
        print(f'\nAverage complexity: {avg_complexity:.2f}')
        print(f'Max complexity: {max_complexity}')
        print(f'Average function length: {avg_lines:.1f} lines')

        # High-risk functions (complexity > 15)
        high_risk = [f for f in functions if f['complexity'] > 15]
        if high_risk:
            print(f'\n⚠️  HIGH RISK: {len(high_risk)} functions have complexity > 15 (should refactor)')
            for fn in high_risk[:5]:
                print(f"   {fn['file']}:{fn['lineno']} - {fn['name']} (complexity={fn['complexity']})")

def main():
    parser = argparse.ArgumentParser(description='Analyze Python code complexity')
    parser.add_argument('--path', type=Path, default=PROJECT_ROOT, help='Path to analyze (default: project root)')
    parser.add_argument('--json', action='store_true', help='Output JSON instead of formatted report')
    parser.add_argument('--exclude', nargs='+', default=['.git', '__pycache__', '.venv'], help='Directories to exclude')
    args = parser.parse_args()

    results, summary = analyze_directory(args.path, args.exclude)

    if args.json:
        import json
        print(json.dumps({'results': results, 'summary': summary}, indent=2))
    else:
        print_report(results, summary)

    return 0

if __name__ == '__main__':
    sys.exit(main())
