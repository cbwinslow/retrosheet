#!/bin/bash
# LLM Sub-Agent Linter Fix Orchestrator
# Delegates linting fixes to multi-GPU CodeLlama-34B

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
SUBAGENT="${SCRIPT_DIR}/llm_subagent.py"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=========================================="
echo "  LLM Sub-Agent Linter Fix System"
echo "  Using: CodeLlama-34B on 3x GPUs"
echo "=========================================="
echo ""

# Check LLM availability
echo "🔍 Checking LLM Sub-Agent..."
if [ ! -f "$SUBAGENT" ]; then
    echo -e "${RED}✗ Sub-Agent not found at ${SUBAGENT}${NC}"
    exit 1
fi

cd "$PROJECT_ROOT"

# Get current error count
echo "📊 Analyzing current errors..."
python3 "$SUBAGENT" analyze 2>&1 | tee /tmp/llm_analysis.txt

echo ""
echo "=========================================="
echo "  Fix Strategy (Easiest First)"
echo "=========================================="
echo ""

# Priority order: easiest/most automatable first
FIX_ORDER=(
    "Q000:Bad quotes"      # Simple quote replacement
    "W293:Trailing ws"     # Delete trailing whitespace
    "COM812:Missing comma" # Add trailing commas
    "UP006:Annotations"      # Type annotation updates
    "ANN001:Missing args"   # Function arg annotations
    "ANN201:Return types"   # Return type annotations
    "DTZ005:Timezone"       # Datetime timezone fixes
)

# Check if user wants to fix specific rule or batch
if [ -n "$1" ]; then
    TARGET_RULE="$1"
    echo "🎯 Target rule: ${TARGET_RULE}"
    echo ""
    read -p "Run dry-run first? [Y/n]: " dry_run
    
    if [[ "$dry_run" =~ ^[Nn]$ ]]; then
        echo -e "${YELLOW}⚠ Applying fixes for ${TARGET_RULE}${NC}"
        python3 "$SUBAGENT" fix-apply "$TARGET_RULE"
    else
        echo -e "${GREEN}🔍 Dry-run for ${TARGET_RULE}${NC}"
        python3 "$SUBAGENT" fix "$TARGET_RULE"
        echo ""
        read -p "Apply these fixes? [y/N]: " apply
        if [[ "$apply" =~ ^[Yy]$ ]]; then
            python3 "$SUBAGENT" fix-apply "$TARGET_RULE"
        fi
    fi
else
    # Batch mode - show menu
    echo "Available fix batches:"
    for i in "${!FIX_ORDER[@]}"; do
        rule="${FIX_ORDER[$i]%%:*}"
        desc="${FIX_ORDER[$i]#*:}"
        count=$(grep -c "^\s*${rule}:" /tmp/llm_analysis.txt 2>/dev/null || echo "0")
        echo "  $((i+1)). ${rule} - ${desc} (${count} errors)"
    done
    echo "  a. Auto-fix all (safe rules only)"
    echo "  q. Quit"
    echo ""
    read -p "Select option [1-7/a/q]: " choice
    
    case "$choice" in
        [1-7])
            idx=$((choice-1))
            rule="${FIX_ORDER[$idx]%%:*}"
            echo ""
            read -p "Run dry-run for ${rule}? [Y/n]: " dry_run
            if [[ "$dry_run" =~ ^[Nn]$ ]]; then
                python3 "$SUBAGENT" fix-apply "$rule"
            else
                python3 "$SUBAGENT" fix "$rule"
            fi
            ;;
        a|A)
            echo -e "${GREEN}🤖 Auto-fixing safe rules...${NC}"
            # Q000 and W293 are safest for auto-fix
            for rule in Q000 W293; do
                echo "Processing ${rule}..."
                python3 "$SUBAGENT" fix-apply "$rule"
            done
            ;;
        q|Q)
            echo "Exiting."
            exit 0
            ;;
        *)
            echo "Invalid option"
            exit 1
            ;;
    esac
fi

echo ""
echo "=========================================="
echo "  Running Ruff to verify fixes..."
echo "=========================================="
uv run ruff check . --output-format=concise 2>&1 | tail -5

echo ""
echo -e "${GREEN}✓ LLM Sub-Agent fix session complete${NC}"
