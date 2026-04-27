"""SQL file execution utility for the baseball platform.

Author: Agent cbwinslow/retrosheet
Date: 2026-04-26
"""

from pathlib import Path


def read_sql(sql_path: str | Path) -> str:
    """Read SQL file content from path.

    Args:
        sql_path: Path to SQL file

    Returns:
        SQL file content as string
    """
    path = Path(sql_path)
    return path.read_text(encoding='utf-8')
