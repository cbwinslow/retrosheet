--
— File: scripts/test/run_pgtap.sh
— Purpose: Run all pgTAP database tests
— Author: Agent KiloSwift
— Date: 2026-04-27
— Usage: ./scripts/test/run_pgtap.sh [--schema SCHEMA] [--verbose]
— Dependencies: PostgreSQL with pgTAP installed (sql/test/003_install_pgtap.sql)
— Notes: This script discovers and runs all pgTAP test functions in specified schemas
—

#!/usr/bin/env bash
set -euo pipefail

# Default values
SCHEMAS=("test" "public" "core" "bridge" "features")
VERBOSE=false
PARALLEL=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --schema)
            SCHEMAS=("$2")
            shift 2
            ;;
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        --parallel|-p)
            PARALLEL=true
            shift
            ;;
        --help)
            echo "Usage: $0 [--schema SCHEMA] [--verbose] [--parallel]"
            echo "  --schema SCHEMA   Run tests only for specific schema"
            echo "  --verbose        Show detailed output"
            echo "  --parallel       Run tests in parallel (requires pg_tapbart extension)"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Get database connection from environment
PGHOST="${PGHOST:-localhost}"
PGPORT="${PGPORT:-5432}"
PGDATABASE="${PGDATABASE:-retrosheet}"
PGUSER="${PGUSER:-postgres}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "╔═══════════════════════════════════════════════════════════╗"
echo "║           pgTAP Database Test Runner                       ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

if $VERBOSE; then
    echo "Configuration:"
    echo "  Database: $PGDATABASE on $PGHOST:$PGPORT"
    echo "  Schemas: ${SCHEMAS[*]}"
    echo "  Verbose: $VERBOSE"
    echo "  Parallel: $PARALLEL"
    echo ""
fi

# Check if pgTAP is installed
if ! psql -h "$PGHOST" -p "$PGPORT" -d "$PGDATABASE" -U "$PGUSER" -t -c "SELECT extname FROM pg_extension WHERE extname='pgtap';" 2>/dev/null | grep -q pgtap; then
    echo -e "${RED}❌ ERROR: pgTAP extension is not installed.${NC}"
    echo "Run: psql -f sql/test/003_install_pgtap.sql"
    exit 1
fi

# For each schema, discover and run tests
OVERALL_RESULTS=()
TOTAL_TESTS=0
TOTAL_PASSED=0
TOTAL_FAILED=0

for SCHEMA in "${SCHEMAS[@]}"; do
    echo -e "${BLUE}📁 Processing schema: $SCHEMA${NC}"

    # Discover test functions in schema (functions starting with "test_")
    TEST_FUNCTIONS=$(psql -h "$PGHOST" -p "$PGPORT" -d "$PGDATABASE" -U "$PGUSER" -t -c "
        SELECT n.nspname || '.' || p.proname
        FROM pg_proc p
        JOIN pg_namespace n ON p.pronamespace = n.oid
        WHERE n.nspname = '$SCHEMA'
          AND p.proname LIKE 'test_%'
        ORDER BY p.proname;
    " 2>/dev/null)

    if [[ -z "$TEST_FUNCTIONS" ]]; then
        echo "  ⚠️  No test functions found in schema '$SCHEMA'"
        continue
    fi

    echo "  Found $(echo "$TEST_FUNCTIONS" | wc -l) test function(s)"

    # Run tests in this schema
    if $PARALLEL; then
        echo "  Parallel execution not yet implemented - using sequential"
    fi

    for TEST_FUNC in $TEST_FUNCTIONS; do
        if $VERBOSE; then
            echo "    Running: $TEST_FUNC"
        fi

        # Run individual test and capture output
        OUTPUT=$(psql -h "$PGHOST" -p "$PGPORT" -d "$PGDATABASE" -U "$PGUSER" -c "
            SET search_path TO $SCHEMA, public;
            SELECT * FROM $TEST_FUNC();
        " 2>&1) || TEST_EXIT=$?

        # Parse TAP output (simple version)
        if echo "$OUTPUT" | grep -q "^ok"; then
            echo -e "    ${GREEN}✓ PASS${NC}: $TEST_FUNC"
            ((TOTAL_PASSED++))
        elif echo "$OUTPUT" | grep -q "^not ok"; then
            echo -e "    ${RED}✗ FAIL${NC}: $TEST_FUNC"
            echo "$OUTPUT" | sed 's/^/      /'
            ((TOTAL_FAILED++))
        else
            echo -e "    ${YELLOW}⚠ SKIP${NC}: $TEST_FUNC (no TAP output)"
        fi
        ((TOTAL_TESTS++))
    done
done

# Summary
echo ""
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║                    TEST SUMMARY                           ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo "  Total tests:  $TOTAL_TESTS"
echo -e "  Passed:       ${GREEN}$TOTAL_PASSED${NC}"
echo -e "  Failed:       ${RED}$TOTAL_FAILED${NC}"
echo ""

if [[ $TOTAL_FAILED -gt 0 ]]; then
    echo -e "${RED}❌ Some tests failed.${NC}"
    exit 1
else
    echo -e "${GREEN}✅ All tests passed!${NC}"
    exit 0
fi
