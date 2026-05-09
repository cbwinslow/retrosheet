"""Tests for bootstrap SQL plan collection."""

from pathlib import Path

from baseball.cli.commands.bootstrap import _collect_sql_files


def test_collect_sql_files_excludes_maintenance_by_default() -> None:
    files = _collect_sql_files(Path('sql'), include_maintenance=False)
    assert files
    assert all(path.parent.name != 'maintenance' for path in files)


def test_collect_sql_files_can_include_maintenance() -> None:
    files = _collect_sql_files(Path('sql'), include_maintenance=True)
    assert files
    assert any(path.parent.name == 'maintenance' for path in files)
