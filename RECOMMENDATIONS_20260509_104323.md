# Recommendations Log (UTC)

## Project Readiness Suggestions
1. Add a `tests/integration/test_bootstrap_postgres.py` suite that runs the SQL bootstrap against ephemeral Postgres (e.g., docker service in CI) to catch SQL-level incompatibilities early.
2. Add golden-file snapshots for `baseball --help` and critical subcommand help outputs to detect accidental CLI regressions during refactors.
3. Build a dependency audit script that maps each command group to required pip extras and validates importability before runtime.
4. Add a unified QA command (`baseball test run --workflow core-cli`) to run the exact smoke + deep workflow tests for rapid agent handoff verification.
5. Introduce failure telemetry standardization for CLI commands (structured JSON log with command, parameters, exception, stack trace, and environment info).

## Current Status Assessment
- Core CLI is now much more resilient than before due to lazy sub-app registration and explicit bootstrap workflow testing.
- The project is in a better handoff state for a follow-up coding agent, especially around DB bootstrap and command-level diagnostics.
