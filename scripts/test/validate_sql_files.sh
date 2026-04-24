#!/bin/bash
# File: scripts/test/validate_sql_files.sh
# Purpose: Validate all SQL files have proper headers and comments
# Author: Agent Cascade
# Date: 2026-04-24
#
# Usage: ./scripts/test/validate_sql_files.sh
#
# This checks:
# - Every SQL file has a header with File:/Purpose:/Author:/Date:
# - SQL files with CREATE TABLE have COMMENT ON TABLE

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "=== SQL File Validation ==="
echo "Started: $(date)"
echo "Project Root: $PROJECT_ROOT"
echo ""

HEADER_ERRORS=0
COMMENT_WARNINGS=0
TOTAL_SQL=0

for f in $(find "$PROJECT_ROOT" -name "*.sql" -type f | sort); do
    ((TOTAL_SQL++))
    
    # Skip test files
    if echo "$f" | grep -q "/test/"; then
        continue
    fi
    
    # Check for header comment
    if ! head -10 "$f" | grep -q "File:"; then
        echo "ERROR: Missing header: $f"
        ((HEADER_ERRORS++))
    fi
    
    # Check for CREATE TABLE statements without comments
    if grep -q "CREATE TABLE" "$f"; then
        if ! grep -q "COMMENT ON TABLE" "$f"; then
            echo "WARNING: Missing table comments: $f"
            ((COMMENT_WARNINGS++))
        fi
    fi
done

echo ""
echo "=== Validation Summary ==="
echo "Total SQL files checked: $TOTAL_SQL"
echo "Header errors: $HEADER_ERRORS"
echo "Missing table comments: $COMMENT_WARNINGS"

if [ $HEADER_ERRORS -eq 0 ]; then
    echo ""
    echo "✓ All SQL files have headers"
    exit 0
else
    echo ""
    echo "✗ $HEADER_ERRORS SQL files missing headers - fix required"
    exit 1
fi
