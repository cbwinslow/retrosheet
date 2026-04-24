#!/bin/bash
# Batch Feature Population Runner
#
# Runs batch SQL files in a loop until all rows are processed.
# Includes progress tracking, resume capability, and error handling.
#
# Usage:
#   ./batch_feature_runner.sh --sql-file sql/features/008_populate_additional_features_batch.sql
#   ./batch_feature_runner.sh --sql-file sql/features/011_populate_more_features_batch.sql --max-iterations 50
#   ./batch_feature_runner.sh --sql-file sql/features/014_populate_context_features_batch.sql --batch-size 50000
#
# Author: Agent Cascade
# Date: 2026-04-24

set -e

# Configuration
DB_URL="postgresql://localhost:5432/retrosheet"
LOG_DIR="logs/batch_operations"
DEFAULT_BATCH_SIZE=100000
DEFAULT_MAX_ITERATIONS=100
DEFAULT_SLEEP_SECONDS=2

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging setup
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/batch_$(date +%Y%m%d_%H%M%S).log"

log() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] SUCCESS:${NC} $1" | tee -a "$LOG_FILE"
}

log_warning() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1" | tee -a "$LOG_FILE"
}

# Function to get unprocessed row count
get_unprocessed_count() {
    local sql_file=$1
    local check_column=""

    # Determine which column to check based on SQL file
    case "$sql_file" in
        *008_populate_additional_features_batch*)
            check_column="is_same_handed_matchup"
            ;;
        *011_populate_more_features_batch*)
            check_column="pitch_quality_score"
            ;;
        *014_populate_context_features_batch*)
            check_column="temp_extreme_flag"
            ;;
        *017_populate_final_features_batch*)
            check_column="strike_accumulation_rate"
            ;;
        *)
            # Try to extract from SQL file comment
            check_column=$(grep -oP 'WHERE \K\w+ IS NULL' "$sql_file" | head -1 | awk '{print $1}')
            ;;
    esac

    if [ -z "$check_column" ]; then
        echo "1000000"  # Default high count
        return
    fi

    # Query unprocessed count
    psql -d "$DB_URL" -t -c "
        SELECT COUNT(*) 
        FROM features_pitch.engineered_features 
        WHERE $check_column IS NULL
    " 2>/dev/null | xargs
}

# Function to run SQL batch
run_batch() {
    local sql_file=$1
    local iteration=$2

    log "Running iteration $iteration: $sql_file"

    # Execute SQL and capture output
    if psql -d "$DB_URL" -v ON_ERROR_STOP=1 -f "$sql_file" >> "$LOG_FILE" 2>&1; then
        log_success "Iteration $iteration completed"
        return 0
    else
        log_error "Iteration $iteration failed"
        return 1
    fi
}

# Function to show progress
show_progress() {
    local iteration=$1
    local unprocessed=$2
    local total=$3
    local percent=$4

    printf "\r${BLUE}Iteration: %d${NC} | Unprocessed: %s | Total: %s | Progress: %.1f%%" \
        "$iteration" "$unprocessed" "$total" "$percent"
}

# Main function
main() {
    local SQL_FILE=""
    local MAX_ITERATIONS=$DEFAULT_MAX_ITERATIONS
    local BATCH_SIZE=$DEFAULT_BATCH_SIZE
    local SLEEP_SECONDS=$DEFAULT_SLEEP_SECONDS

    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --sql-file)
                SQL_FILE="$2"
                shift 2
                ;;
            --max-iterations)
                MAX_ITERATIONS="$2"
                shift 2
                ;;
            --batch-size)
                BATCH_SIZE="$2"
                shift 2
                ;;
            --sleep)
                SLEEP_SECONDS="$2"
                shift 2
                ;;
            --help)
                echo "Usage: $0 --sql-file <file> [options]"
                echo ""
                echo "Options:"
                echo "  --sql-file <file>        SQL file to run repeatedly"
                echo "  --max-iterations <n>     Maximum iterations (default: $DEFAULT_MAX_ITERATIONS)"
                echo "  --batch-size <n>         Not used - SQL file determines batch size"
                echo "  --sleep <seconds>        Sleep between iterations (default: $DEFAULT_SLEEP_SECONDS)"
                echo "  --help                   Show this help message"
                exit 0
                ;;
            *)
                echo "Unknown option: $1"
                exit 1
                ;;
        esac
    done

    # Validate inputs
    if [ -z "$SQL_FILE" ]; then
        log_error "--sql-file is required"
        exit 1
    fi

    if [ ! -f "$SQL_FILE" ]; then
        log_error "SQL file not found: $SQL_FILE"
        exit 1
    fi

    log "=================================================="
    log "Batch Feature Population Runner"
    log "SQL File: $SQL_FILE"
    log "Max Iterations: $MAX_ITERATIONS"
    log "Log File: $LOG_FILE"
    log "=================================================="

    # Get initial counts
    local total_rows
    total_rows=$(psql -d "$DB_URL" -t -c "SELECT COUNT(*) FROM features_pitch.engineered_features" | xargs)
    log "Total rows in engineered_features: $total_rows"

    local unprocessed
    unprocessed=$(get_unprocessed_count "$SQL_FILE")
    log "Initial unprocessed rows: $unprocessed"

    if [ "$unprocessed" -eq 0 ]; then
        log_success "All rows already processed!"
        exit 0
    fi

    # Run batches
    local iteration=0
    local last_unprocessed=$unprocessed
    local stalled_count=0

    while [ "$unprocessed" -gt 0 ] && [ "$iteration" -lt "$MAX_ITERATIONS" ]; do
        iteration=$((iteration + 1))

        # Calculate progress
        local processed=$((total_rows - unprocessed))
        local percent=0
        if [ "$total_rows" -gt 0 ]; then
            percent=$(echo "scale=1; $processed * 100 / $total_rows" | bc)
        fi

        show_progress "$iteration" "$unprocessed" "$total_rows" "$percent"

        # Run the batch
        if ! run_batch "$SQL_FILE" "$iteration"; then
            echo  # Newline after progress
            log_error "Batch failed at iteration $iteration"
            log_error "Check log file: $LOG_FILE"
            exit 1
        fi

        # Get new unprocessed count
        unprocessed=$(get_unprocessed_count "$SQL_FILE")

        # Check for stall (no progress made)
        if [ "$unprocessed" -eq "$last_unprocessed" ]; then
            stalled_count=$((stalled_count + 1))
            if [ "$stalled_count" -ge 3 ]; then
                echo  # Newline after progress
                log_warning "Progress stalled for 3 iterations"
                log_warning "Unprocessed rows stuck at: $unprocessed"
                break
            fi
        else
            stalled_count=0
        fi

        last_unprocessed=$unprocessed

        # Sleep between iterations
        if [ "$SLEEP_SECONDS" -gt 0 ] && [ "$unprocessed" -gt 0 ]; then
            sleep "$SLEEP_SECONDS"
        fi
    done

    echo  # Newline after progress

    # Final summary
    log "=================================================="
    log "BATCH RUN COMPLETE"
    log "Iterations: $iteration"
    log "Remaining unprocessed: $unprocessed"

    if [ "$unprocessed" -eq 0 ]; then
        log_success "All rows processed successfully!"
    elif [ "$iteration" -ge "$MAX_ITERATIONS" ]; then
        log_warning "Reached max iterations ($MAX_ITERATIONS)"
        log_warning "Remaining unprocessed: $unprocessed rows"
    else
        log_warning "Stopped with $unprocessed unprocessed rows"
    fi

    log "Log saved to: $LOG_FILE"
    log "=================================================="
}

# Run main
main "$@"
