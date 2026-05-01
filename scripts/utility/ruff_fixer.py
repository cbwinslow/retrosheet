#!/usr/bin/env python3
"""Use Ollama to fix Ruff linting errors automatically."""

import re
import subprocess
import sys


def get_ruff_errors(rule: str, path: str = '.') -> list:
    """Get list of files and line numbers with specific Ruff errors."""
    result = subprocess.run(
        ['ruff', 'check', path, '--select', rule, '--output-format=concise'],
        capture_output=True,
        text=True,
    )
    errors = []
    for line in result.stdout.split('\n'):
        # Parse: file.py:123:45: RULE message
        match = re.match(r'^(.+\.py):(\d+):(\d+):\s+(\w+)', line)
        if match:
            errors.append(
                {
                    'file': match.group(1),
                    'line': int(match.group(2)),
                    'col': int(match.group(3)),
                    'rule': match.group(4),
                },
            )
    return errors


def get_line_context(filepath: str, lineno: int, context: int = 3) -> str:
    """Get surrounding lines for context."""
    try:
        with open(filepath) as f:
            lines = f.readlines()
        start = max(0, lineno - context - 1)
        end = min(len(lines), lineno + context)
        result = []
        for i in range(start, end):
            marker = '>>> ' if i == lineno - 1 else '    '
            result.append(f'{marker}{i + 1}: {lines[i]}')
        return ''.join(result)
    except Exception:
        return ''


def fix_with_ollama(code_context: str, error_rule: str, error_msg: str) -> str:
    """Use Ollama to fix the code."""
    prompt = f"""Fix this Python code to resolve Ruff lint error {error_rule}.

Error: {error_msg}

Code context:
{code_context}

Return ONLY the fixed code (the corrected line or lines). Do not include explanations.
"""

    result = subprocess.run(
        ['ollama', 'run', 'llama3.2', '--nowordwrap'],
        input=prompt,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return result.stdout.strip()


def apply_fix(filepath: str, lineno: int, fixed_code: str) -> bool:
    """Apply the fixed code to the file."""
    try:
        with open(filepath) as f:
            lines = f.readlines()

        # Replace the specific line
        if lineno <= len(lines):
            lines[lineno - 1] = fixed_code + '\n'
            with open(filepath, 'w') as f:
                f.writelines(lines)
            return True
    except Exception as e:
        print(f'Error applying fix to {filepath}:{lineno}: {e}')
    return False


def main():
    if len(sys.argv) < 2:
        print('Usage: ruff_fixer.py <RUFF_RULE> [path]')
        print('Example: ruff_fixer.py EM101')
        sys.exit(1)

    rule = sys.argv[1]
    path = sys.argv[2] if len(sys.argv) > 2 else '.'

    print(f'Finding {rule} errors...')
    errors = get_ruff_errors(rule, path)
    print(f'Found {len(errors)} errors')

    fixed = 0
    for err in errors[:10]:  # Limit to 10 per run
        print(f'\nFixing {err["file"]}:{err["line"]}...')
        context = get_line_context(err['file'], err['line'])

        fixed_code = fix_with_ollama(context, err['rule'], '')
        print(f'  Suggested: {fixed_code[:60]}...')

        # Validate syntax
        try:
            compile(fixed_code, '<string>', 'exec')
            if apply_fix(err['file'], err['line'], fixed_code):
                print('  ✓ Applied')
                fixed += 1
        except SyntaxError:
            print('  ✗ Syntax error in suggested fix, skipping')

    print(f'\nFixed {fixed} errors')


if __name__ == '__main__':
    main()
