#!/usr/bin/env python3
"""LLM Sub-Agent for automated code fixing using multi-GPU llama.cpp."""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


# Configuration
LLAMA_CPP_DIR = Path('/home/cbwinslow/llama.cpp')
MODEL_PATH = LLAMA_CPP_DIR / 'models/codellama-34b.Q6_K.gguf'
LLAMA_SIMPLE = LLAMA_CPP_DIR / 'build/bin/llama-simple'

# CUDA Environment
CUDA_ENV = {
    'PATH': '/usr/local/cuda-11.8/bin:' + os.environ.get('PATH', ''),
    'LD_LIBRARY_PATH': '/usr/local/cuda-11.8/lib64:'
    + str(LLAMA_CPP_DIR / 'build/bin')
    + ':'
    + os.environ.get('LD_LIBRARY_PATH', ''),
    'CUDA_VISIBLE_DEVICES': '0,1,2',
}


class LLMSubAgent:
    """Sub-agent that delegates fixing tasks to local LLM."""

    def __init__(self):
        self.model_loaded = False
        self._verify_setup()

    def _verify_setup(self) -> None:
        """Verify llama.cpp and model are available."""
        if not LLAMA_SIMPLE.exists():
            raise RuntimeError(f'llama-simple not found at {LLAMA_SIMPLE}')
        if not MODEL_PATH.exists():
            raise RuntimeError(f'Model not found at {MODEL_PATH}')
        print(f'✓ LLM Sub-Agent ready: {MODEL_PATH.name}')

    def _call_llm(self, prompt: str, max_tokens: int = 500) -> str:
        """Call the LLM with a prompt."""
        cmd = [
            str(LLAMA_SIMPLE),
            '-m',
            str(MODEL_PATH),
            '-ts',
            '0.35,0.35,0.30',  # Optimized for K80/K80/K40
            '-ngl',
            '48',
            '--temp',
            '0.1',
            '-n',
            str(max_tokens),
            '-p',
            prompt,
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env={**os.environ, **CUDA_ENV},
            timeout=300,
        )

        # Extract generated text after prompt
        output = result.stdout
        if prompt in output:
            output = output.split(prompt)[-1]
        return output.strip()

    def fix_python_file(self, filepath: str, rule: str, line_no: int, context: str) -> str:
        """Fix a specific error in a Python file."""
        prompt = f"""You are a Python code linter fixer. Fix this code to resolve Ruff rule {rule}.

File: {filepath}
Line: {line_no}
Context:
{context}

Provide ONLY the corrected line(s). No explanation, no markdown, just the fixed code."""

        return self._call_llm(prompt, max_tokens=200)

    def batch_fix(self, errors: list[dict[str, Any]], dry_run: bool = True) -> dict[str, Any]:
        """Fix a batch of errors."""
        results = {'fixed': 0, 'failed': 0, 'skipped': 0, 'details': []}

        for err in errors[:20]:  # Limit to 20 per batch for testing
            filepath = err.get('file', '')
            line_no = err.get('line', 0)
            rule = err.get('rule', '')

            # Get context
            context = self._get_line_context(filepath, line_no)
            if not context:
                results['skipped'] += 1
                continue

            print(f'\n🔧 Fixing {filepath}:{line_no} ({rule})')

            try:
                fixed_code = self.fix_python_file(filepath, rule, line_no, context)

                if dry_run:
                    print(f'   Would fix: {fixed_code[:80]}...')
                    results['details'].append(
                        {
                            'file': filepath,
                            'line': line_no,
                            'rule': rule,
                            'suggestion': fixed_code,
                            'applied': False,
                        }
                    )
                else:
                    if self._apply_fix(filepath, line_no, fixed_code):
                        print('   ✓ Applied')
                        results['fixed'] += 1
                    else:
                        print('   ✗ Failed to apply')
                        results['failed'] += 1

            except Exception as e:
                print(f'   ✗ Error: {e}')
                results['failed'] += 1

        return results

    def _get_line_context(self, filepath: str, lineno: int, context: int = 3) -> str:
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

    def _apply_fix(self, filepath: str, lineno: int, fixed_code: str) -> bool:
        """Apply a fix to a file."""
        try:
            with open(filepath) as f:
                lines = f.readlines()

            if lineno <= len(lines):
                lines[lineno - 1] = fixed_code + '\n'
                with open(filepath, 'w') as f:
                    f.writelines(lines)
                return True
        except Exception:
            pass
        return False


def get_ruff_errors(rule: str | None = None, path: str = '.') -> list[dict[str, Any]]:
    """Get Ruff errors."""
    cmd = ['ruff', 'check', path, '--output-format=json']
    if rule:
        cmd.extend(['--select', rule])

    result = subprocess.run(cmd, capture_output=True, text=True)
    try:
        errors = json.loads(result.stdout)
        return [
            {
                'file': e.get('filename', ''),
                'line': e.get('location', {}).get('row', 0),
                'col': e.get('location', {}).get('column', 0),
                'rule': e.get('code', ''),
                'message': e.get('message', ''),
            }
            for e in errors
        ]
    except json.JSONDecodeError:
        return []


def main():
    if len(sys.argv) < 2:
        print('Usage: llm_subagent.py <command> [args]')
        print('Commands:')
        print('  analyze              - Show error breakdown')
        print('  fix <RULE>           - Fix specific rule (dry-run)')
        print('  fix-apply <RULE>     - Fix and apply changes')
        sys.exit(1)

    command = sys.argv[1]
    agent = LLMSubAgent()

    if command == 'analyze':
        print('\n=== Analyzing Ruff Errors ===')
        errors = get_ruff_errors()
        print(f'Total errors: {len(errors)}')

        # Count by rule
        rule_counts = {}
        for e in errors:
            rule = e['rule']
            rule_counts[rule] = rule_counts.get(rule, 0) + 1

        print('\nTop 10 error types:')
        for rule, count in sorted(rule_counts.items(), key=lambda x: -x[1])[:10]:
            print(f'  {rule}: {count}')

    elif command == 'fix' and len(sys.argv) >= 3:
        rule = sys.argv[2]
        print(f'\n=== Fixing {rule} (Dry Run) ===')
        errors = get_ruff_errors(rule)
        print(f'Found {len(errors)} errors with rule {rule}')
        results = agent.batch_fix(errors, dry_run=True)
        print(
            f'\nSummary: {results["fixed"]} would be fixed, {results["failed"]} failed, {results["skipped"]} skipped'
        )

    elif command == 'fix-apply' and len(sys.argv) >= 3:
        rule = sys.argv[2]
        print(f'\n=== Fixing {rule} (APPLYING) ===')
        errors = get_ruff_errors(rule)
        print(f'Found {len(errors)} errors with rule {rule}')
        results = agent.batch_fix(errors, dry_run=False)
        print(
            f'\nSummary: {results["fixed"]} fixed, {results["failed"]} failed, {results["skipped"]} skipped'
        )

    else:
        print(f'Unknown command: {command}')
        sys.exit(1)


if __name__ == '__main__':
    main()
