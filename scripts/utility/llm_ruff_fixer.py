#!/usr/bin/env python3
"""LLM-powered Ruff error fixer using compiled llama.cpp with multi-GPU support."""

import os
import re
import subprocess
import sys
from pathlib import Path


# Configuration
LLAMA_CPP_DIR = Path('/home/cbwinslow/llama.cpp')
MODEL_PATH = LLAMA_CPP_DIR / 'models/codellama-34b.Q6_K.gguf'
LLAMA_SIMPLE = LLAMA_CPP_DIR / 'build/bin/llama-simple'

# Environment for CUDA
CUDA_ENV = {
    'PATH': '/usr/local/cuda-11.8/bin:' + os.environ.get('PATH', ''),
    'LD_LIBRARY_PATH': '/usr/local/cuda-11.8/lib64:' + str(LLAMA_CPP_DIR / 'build/bin') + ':' + os.environ.get('LD_LIBRARY_PATH', ''),
}


def get_ruff_errors(rule: str, path: str = '.') -> list:
    """Get list of files and line numbers with specific Ruff errors."""
    result = subprocess.run(
        ['ruff', 'check', path, '--select', rule, '--output-format=concise'],
        capture_output=True,
        text=True,
    )
    errors = []
    for line in result.stdout.split('\n'):
        match = re.match(r'^(.+\.py):(\d+):(\d+):\s+(\w+)', line)
        if match:
            errors.append({
                'file': match.group(1),
                'line': int(match.group(2)),
                'col': int(match.group(3)),
                'rule': match.group(4),
            })
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
            result.append(f'{marker}{i+1}: {lines[i]}')
        return ''.join(result)
    except Exception:
        return ''


def fix_with_llm(code_context: str, error_rule: str) -> str:
    """Use llama.cpp to fix the code."""

    prompt = f"""You are a Python code fixer. Fix this code to resolve Ruff error {error_rule}.

Code context:
{code_context}

Provide ONLY the fixed line(s). No explanation."""

    cmd = [
        str(LLAMA_SIMPLE),
        '-m', str(MODEL_PATH),
        '-ts', '0.34,0.33,0.33',  # Multi-GPU split
        '-ngl', '48',  # All layers on GPU
        '--temp', '0.1',
        '-n', '100',
        '-p', prompt,
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        env={**os.environ, **CUDA_ENV},
        timeout=300,
    )

    # Parse output to get just the generated text
    output = result.stdout
    # Remove prompt from output
    if prompt in output:
        output = output.split(prompt)[-1]
    return output.strip()


def main():
    if len(sys.argv) < 2:
        print('Usage: llm_ruff_fixer.py <RUFF_RULE> [path]')
        print('Example: llm_ruff_fixer.py EM101')
        sys.exit(1)

    rule = sys.argv[1]
    path = sys.argv[2] if len(sys.argv) > 2 else '.'

    print(f'Finding {rule} errors...')
    errors = get_ruff_errors(rule, path)
    print(f'Found {len(errors)} errors')

    if not errors:
        print('No errors to fix!')
        return

    fixed = 0
    for err in errors[:5]:  # Limit to 5 per run for testing
        print(f"\n{'='*60}")
        print(f"Fixing {err['file']}:{err['line']} ({err['rule']})")
        print(f"{'='*60}")

        context = get_line_context(err['file'], err['line'])
        print(f'Context:\n{context}')

        try:
            fixed_code = fix_with_llm(context, err['rule'])
            print(f'\nLLM Suggestion:\n{fixed_code}')

            # TODO: Validate and apply fix
            fixed += 1
        except Exception as e:
            print(f'Error: {e}')

    print(f'\nProcessed {fixed} errors')


if __name__ == '__main__':
    main()
