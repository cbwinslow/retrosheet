#!/usr/bin/env python3
"""Convert block-comment /* */ SQL headers to line-comment -- format."""

import re
from pathlib import Path

PROJECT_ROOT = Path("/home/cbwinslow/workspace/retrosheet")


def convert_file(filepath: Path) -> bool:
    """Convert a block comment header to line comment format."""
    content = filepath.read_text(encoding="utf-8")

    # Check if file starts with block comment
    if not content.strip().startswith("/*"):
        return False

    # Extract header fields from block comment
    file_match = re.search(r"File:\s*(.+)", content)
    purpose_match = re.search(r"Purpose:\s*(.+)", content)
    author_match = re.search(r"Author:\s*(.+)", content)
    date_match = re.search(r"Date:\s*(.+)", content)

    file_val = file_match.group(1).strip() if file_match else str(filepath.relative_to(PROJECT_ROOT))
    purpose_val = purpose_match.group(1).strip() if purpose_match else ""
    author_val = author_match.group(1).strip() if author_match else "Agent Cascade"
    date_val = date_match.group(1).strip() if date_match else "2026-04-24"

    # Find the end of the block comment
    block_end = content.find("*/")
    if block_end == -1:
        return False

    # Everything after the block comment
    rest = content[block_end + 2:].lstrip("\n")

    # Build new line-comment header
    new_header = f"""-- File: {file_val}
-- Purpose: {purpose_val}
-- Author: {author_val}
-- Date: {date_val}

"""

    new_content = new_header + rest
    filepath.write_text(new_content, encoding="utf-8")
    return True


def main():
    sql_files = sorted(PROJECT_ROOT.rglob("*.sql"))
    modified = 0

    for filepath in sql_files:
        try:
            if convert_file(filepath):
                print(f"  [CONVERTED] {filepath.relative_to(PROJECT_ROOT)}")
                modified += 1
        except Exception as e:
            print(f"  [ERROR] {filepath.relative_to(PROJECT_ROOT)}: {e}")

    print(f"\nConverted: {modified}")


if __name__ == "__main__":
    main()
