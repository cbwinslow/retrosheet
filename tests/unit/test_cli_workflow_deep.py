"""Deeper workflow tests for baseball CLI and SQL bootstrap orchestration."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from baseball.cli.main import app
from baseball.cli.commands import bootstrap as bootstrap_cmd

runner = CliRunner()


class _FakeCursor:
    def __init__(self, fail_on_sql: str | None = None):
        self.fail_on_sql = fail_on_sql
        self.executed: list[str] = []

    def execute(self, sql: str) -> None:
        self.executed.append(sql)
        if self.fail_on_sql and self.fail_on_sql in sql:
            raise RuntimeError('forced sql failure')

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class _FakeConn:
    def __init__(self, fail_on_sql: str | None = None):
        self.cursor_obj = _FakeCursor(fail_on_sql=fail_on_sql)
        self.rollback_calls = 0
        self.close_calls = 0

    def cursor(self) -> _FakeCursor:
        return self.cursor_obj

    def rollback(self) -> None:
        self.rollback_calls += 1

    def close(self) -> None:
        self.close_calls += 1

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_cli_help_works_even_with_optional_command_skips() -> None:
    result = runner.invoke(app, ['--help'])
    assert result.exit_code == 0
    assert 'Baseball data ingestion and prediction platform' in result.output
    assert 'bootstrap' in result.output


def test_bootstrap_plan_lists_sql_files() -> None:
    result = runner.invoke(app, ['bootstrap', 'plan'])
    assert result.exit_code == 0
    assert 'Bootstrap plan:' in result.output
    assert 'sql/00_admin' in result.output


def test_bootstrap_run_dry_run_is_non_destructive() -> None:
    result = runner.invoke(app, ['bootstrap', 'run', '--dry-run'])
    assert result.exit_code == 0
    assert 'Dry run enabled' in result.output


def test_bootstrap_run_executes_all_files(monkeypatch, tmp_path: Path) -> None:
    sql_dir = tmp_path / 'sql'
    (sql_dir / '00_admin').mkdir(parents=True)
    (sql_dir / '10_raw').mkdir(parents=True)
    (sql_dir / '00_admin' / '0001_test.sql').write_text('SELECT 1;', encoding='utf-8')
    (sql_dir / '10_raw' / '1001_test.sql').write_text('SELECT 2;', encoding='utf-8')

    fake_conn = _FakeConn()
    monkeypatch.setattr(bootstrap_cmd.psycopg2, 'connect', lambda *_args, **_kwargs: fake_conn)

    result = runner.invoke(app, ['bootstrap', 'run', '--sql-root', str(sql_dir)])
    assert result.exit_code == 0
    assert 'Bootstrap complete.' in result.output
    assert len(fake_conn.cursor_obj.executed) == 2


def test_bootstrap_run_stop_on_error_returns_failure(monkeypatch, tmp_path: Path) -> None:
    sql_dir = tmp_path / 'sql'
    (sql_dir / '00_admin').mkdir(parents=True)
    (sql_dir / '00_admin' / '0001_ok.sql').write_text('SELECT 1;', encoding='utf-8')
    (sql_dir / '00_admin' / '0002_fail.sql').write_text('SELECT FAIL_ME;', encoding='utf-8')

    fake_conn = _FakeConn(fail_on_sql='FAIL_ME')
    monkeypatch.setattr(bootstrap_cmd.psycopg2, 'connect', lambda *_args, **_kwargs: fake_conn)

    result = runner.invoke(app, ['bootstrap', 'run', '--sql-root', str(sql_dir), '--stop-on-error'])
    assert result.exit_code == 1
    assert 'Failed' in result.output
    assert fake_conn.rollback_calls == 1
