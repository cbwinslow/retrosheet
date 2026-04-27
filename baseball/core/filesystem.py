"""File I/O utilities for the baseball platform.

Author: Agent cbwinslow/retrosheet
Date: 2026-04-26
"""

from pathlib import Path


def ensure_dir(path: str | Path) -> Path:
    """Ensure directory exists, create if necessary.

    Args:
        path: Directory path to ensure exists

    Returns:
        Path object for the directory
    """
    directory = Path(path)
    directory.mkdir(parents=True, exist_ok=True)
    return directory
