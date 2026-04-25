#!/bin/bash
# File: scripts/bridge/populate_all_bridge_tables.sh
# Purpose: Master orchestration script for complete bridge table population
# Author: Agent Cascade
# Date: 2026-04-24
# Called By: Manual execution, cron jobs, CI/CD pipelines

# =============================================================================
# CONFIGURATION
# =============================================================================

set -euo pipefail  # Exit on error, undefined vars, pipe failures

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
SQL_DIR="${PROJECT_ROOT}/sql/bridge"
LOG_DIR="${PROJECT_ROOT}/logs"

# Create log directory
mkdir -p "${LOG_DIR}"

# Log file with timestamp
LOG_FILE="${LOG_DIR}/bridge_population_$(date +%Y%m%d_%H%M%S).log"

# Database connection (use environment variables or defaults)
export PGHOST="${PGHOST:-localhost}"
export PGPORT="${PGPORT:-5432}"
export PGDATABASE="${PGDATABASE:-retrosheet}"
export PGUSER="${PGUSER:-postgres}"

# =============================================================================
# LOGGING FUNCTIONS
# =============================================================================

log() {
    local level="$1"
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[${timestamp}] [${level}] ${message}" | tee -a "${LOG_FILE}"
}

log_info() { log "INFO" "$@"; }
log_warn() { log "WARN" "$@"; }
log_error() { log "ERROR" "$@"; }
log_success() { log "SUCCESS" "$@"; }

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

run_sql_file() {
    local file="$1"
    local description="${2:-SQL file}"
    
    log_info "Executing: ${description}"
    log_info "File: ${file}"
    
    if psql -v ON_ERROR_STOP=1 -f "${file}" >> "${LOG_FILE}" 2>&1; then
        log_success "Completed: ${description}"
        return 0
    else
        log_error "Failed: ${description}"
        return 1
    fi
}

run_sql_command() {
    local command="$1"
    local description="${2:-SQL command}"
    
    log_info "Executing: ${description}"
    
    if psql -v ON_ERROR_STOP=1 -c "${command}" >> "${LOG_FILE}" 2>&1; then
        log_success "Completed: ${description}"
        return 0
    else
        log_error "Failed: ${description}"
        return 1
    fi
}

run_python_script() {
    local script="$1"
    local args="${2:-}"
    local description="${3:-Python script}"
    
    log_info "Executing: ${description}"
    log_info "Script: ${script}"
    
    if python3 "${script}" ${args} >> "${LOG_FILE}" 2>&1; then
        log_success "Completed: ${description}"
        return 0
    else
        log_error "Failed: ${description}"
        return 1
    fi
}

# =============================================================================
# VALIDATION FUNCTIONS
# =============================================================================

validate_prerequisites() {
    log_info "=== VALIDATING PREREQUISITES ==="
    
    # Check database connection
    if ! psql -c "SELECT 1" > /dev/null 2>&1; then
        log_error "Cannot connect to database. Check environment variables:"
        log_error "  PGHOST=${PGHOST}"
        log_error "  PGPORT=${PGPORT}"
        log_error "  PGDATABASE=${PGDATABASE}"
        log_error "  PGUSER=${PGUSER}"
        exit 1
    fi
    log_success "Database connection OK"
    
    # Check required directories
    if [[ ! -d "${SQL_DIR}" ]]; then
        log_error "SQL directory not found: ${SQL_DIR}"
        exit 1
    fi
    log_success "SQL directory found: ${SQL_DIR}"
    
    # Check Python availability
    if ! command -v python3 &> /dev/null; then
        log_error "python3 not found"
        exit 1
    fi
    log_success "Python3 available"
    
    log_success "All prerequisites validated"
}

# =============================================================================
# STAGE 1: CREATE/UPDATE SQL PROCEDURES
# =============================================================================

stage_create_procedures() {
    log_info ""
    log_info "=== STAGE 1: CREATING SQL PROCEDURES ==="
    
    # Create Chadwick register bridge procedures
    run_sql_file \
        "${SQL_DIR}/930_chadwick_register_bridge.sql" \
        "Chadwick Register Bridge Procedures"
    
    # Create Lahman bridge population procedures
    run_sql_file \
        "${SQL_DIR}/931_lahman_bridge_population.sql" \
        "Lahman Bridge Population Procedures"
    
    # Create validation tests
    run_sql_file \
        "${SQL_DIR}/940_bridge_validation_tests.sql" \
        "Bridge Validation Tests"
    
    log_success "All SQL procedures created/updated"
}

# =============================================================================
# STAGE 2: LOAD CHADWICK REGISTER DATA
# =============================================================================

stage_load_chadwick() {
    log_info ""
    log_info "=== STAGE 2: LOADING CHADWICK REGISTER DATA ==="
    
    # Run Python ingestion script
    run_python_script \
        "${SCRIPT_DIR}/ingest_chadwick_register.py" \
        "" \
        "Chadwick Register Ingestion"
    
    log_success "Chadwick Register data loaded"
}

# =============================================================================
# STAGE 3: LOAD LAHMAN DATA FOR GAP-FILL
# =============================================================================

stage_load_lahman() {
    log_info ""
    log_info "=== STAGE 3: LOADING LAHMAN DATA FOR GAP-FILL ==="
    
    # Check if raw_lahman.people has data
    local lahman_count=$(psql -tAc "SELECT COUNT(*) FROM raw_lahman.people" 2>/dev/null || echo "0")
    
    if [[ "${lahman_count}" -eq 0 ]]; then
        log_warn "raw_lahman.people is empty. Skipping Lahman gap-fill."
        log_warn "To load Lahman data, run: scripts/external_data/load_lahman.py"
        return 0
    fi
    
    log_info "Found ${lahman_count} records in raw_lahman.people"
    
    # Load Lahman to staging
    run_sql_command \
        "CALL bridge.load_lahman_to_staging()" \
        "Load Lahman to Staging"
    
    # Run gap-fill procedure
    run_sql_command \
        "CALL bridge.gap_fill_player_xref_from_lahman()" \
        "Gap-Fill from Lahman"
    
    log_success "Lahman gap-fill complete"
}

# =============================================================================
# STAGE 4: POPULATE EXTERNAL BRIDGE TABLES
# =============================================================================

stage_populate_external() {
    log_info ""
    log_info "=== STAGE 4: POPULATING EXTERNAL BRIDGE TABLES ==="
    
    # Populate external player xref (Statcast, BRef, etc.)
    if [[ -f "${SCRIPT_DIR}/populate_external_bridge.py" ]]; then
        run_python_script \
            "${SCRIPT_DIR}/populate_external_bridge.py" \
            "" \
            "External Bridge Population"
    else
        log_warn "populate_external_bridge.py not found, skipping external bridge"
    fi
    
    log_success "External bridge tables populated"
}

# =============================================================================
# STAGE 5: VALIDATION AND TESTING
# =============================================================================

stage_validate() {
    log_info ""
    log_info "=== STAGE 5: VALIDATION AND TESTING ==="
    
    # Run all validation tests
    log_info "Running bridge validation tests..."
    
    local test_results=$(psql -tAc "SELECT jsonb_build_object(
        'total', total_tests,
        'passed', passed_tests,
        'failed', failed_tests,
        'rate', pass_rate,
        'status', status
    ) FROM bridge.get_bridge_test_summary()" 2>/dev/null)
    
    log_info "Test Results: ${test_results}"
    
    # Check for failures
    local failed=$(echo "${test_results}" | grep -o '"failed": [0-9]*' | grep -o '[0-9]*')
    
    if [[ "${failed}" -gt 0 ]]; then
        log_warn "${failed} validation tests failed"
        
        # Show failed tests
        psql -c "SELECT * FROM bridge.run_all_bridge_tests() WHERE passed = false"
    else
        log_success "All validation tests passed"
    fi
    
    # Show coverage report
    log_info ""
    log_info "Coverage Report:"
    psql -c "SELECT * FROM bridge.vw_bridge_coverage_gap_analysis ORDER BY gap_pct DESC"
}

# =============================================================================
# STAGE 6: GENERATE SUMMARY REPORT
# =============================================================================

stage_generate_report() {
    log_info ""
    log_info "=== STAGE 6: GENERATING SUMMARY REPORT ==="
    
    # Get final statistics
    log_info "Final Bridge Table Statistics:"
    
    psql <<EOF
\echo '--- Player Xref ---'
SELECT 
    'player_xref' as table_name,
    COUNT(*) as total,
    COUNT(mlb_id) as with_mlb,
    COUNT(retrosheet_id) as with_retro,
    COUNT(baseball_reference_id) as with_bbref,
    ROUND(COUNT(mlb_id)::numeric / NULLIF(COUNT(*), 0) * 100, 1) as mlb_pct,
    ROUND(COUNT(retrosheet_id)::numeric / NULLIF(COUNT(*), 0) * 100, 1) as retro_pct
FROM bridge.player_xref;

\echo '--- Game Xref ---'
SELECT 
    'game_xref' as table_name,
    COUNT(*) as total,
    COUNT(mlb_game_pk) as with_mlb,
    COUNT(retrosheet_game_id) as with_retro
FROM bridge.game_xref;

\echo '--- Team Xref ---'
SELECT 
    'team_xref' as table_name,
    COUNT(*) as total,
    COUNT(mlb_team_id) as with_mlb,
    COUNT(retrosheet_team_id) as with_retro
FROM bridge.team_xref;

\echo '--- Park Xref ---'
SELECT 
    'park_xref' as table_name,
    COUNT(*) as total,
    COUNT(mlb_venue_id) as with_mlb,
    COUNT(retrosheet_park_id) as with_retro
FROM bridge.park_xref;

\echo '--- Pitch Data Coverage ---'
WITH all_players AS (
    SELECT DISTINCT pitcher_id as player_id FROM features_pitch.base_features
    UNION
    SELECT DISTINCT batter_id as player_id FROM features_pitch.base_features
)
SELECT 
    'pitch_data_players' as table_name,
    COUNT(*) as total_players,
    COUNT(*) FILTER (WHERE px.player_xref_id IS NOT NULL) as linked,
    ROUND(COUNT(*) FILTER (WHERE px.player_xref_id IS NOT NULL)::numeric / 
          NULLIF(COUNT(*), 0) * 100, 1) as coverage_pct
FROM all_players ap
LEFT JOIN bridge.player_xref px ON ap.player_id::text = px.mlb_id::text;
EOF

    log_success "Summary report generated"
}

# =============================================================================
# MAIN EXECUTION
# =============================================================================

print_usage() {
    cat << EOF
Usage: $(basename "$0") [OPTIONS]

Master orchestration script for bridge table population.

OPTIONS:
    -h, --help          Show this help message
    --validate-only     Only run validation tests (skip population)
    --skip-chadwick     Skip Chadwick Register ingestion
    --skip-lahman       Skip Lahman gap-fill
    --skip-external     Skip external bridge population
    --dry-run           Run in dry-run mode (no database changes)

STAGES:
    1. Create/Update SQL procedures
    2. Load Chadwick Register data
    3. Load Lahman data for gap-fill
    4. Populate external bridge tables
    5. Validation and testing
    6. Generate summary report

EXAMPLES:
    $(basename "$0")                    # Full population run
    $(basename "$0") --validate-only   # Only run tests
    $(basename "$0") --skip-lahman     # Skip Lahman processing

EOF
}

main() {
    local validate_only=false
    local skip_chadwick=false
    local skip_lahman=false
    local skip_external=false
    local dry_run=false
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                print_usage
                exit 0
                ;;
            --validate-only)
                validate_only=true
                shift
                ;;
            --skip-chadwick)
                skip_chadwick=true
                shift
                ;;
            --skip-lahman)
                skip_lahman=true
                shift
                ;;
            --skip-external)
                skip_external=true
                shift
                ;;
            --dry-run)
                dry_run=true
                shift
                ;;
            *)
                log_error "Unknown option: $1"
                print_usage
                exit 1
                ;;
        esac
    done
    
    # Header
    log_info "=" 
    log_info "BRIDGE TABLE POPULATION ORCHESTRATOR"
    log_info "=" 
    log_info "Date: $(date)"
    log_info "Log File: ${LOG_FILE}"
    log_info "Project Root: ${PROJECT_ROOT}"
    
    if [[ "${dry_run}" == true ]]; then
        log_info "MODE: DRY RUN (no database changes)"
    fi
    
    if [[ "${validate_only}" == true ]]; then
        log_info "MODE: VALIDATION ONLY"
    fi
    
    log_info "=" 
    
    # Validate prerequisites
    validate_prerequisites
    
    # Run stages
    if [[ "${validate_only}" == true ]]; then
        stage_validate
        stage_generate_report
    else
        # Stage 1: Always run to ensure procedures are up to date
        stage_create_procedures
        
        # Stage 2: Chadwick Register
        if [[ "${skip_chadwick}" == false && "${dry_run}" == false ]]; then
            stage_load_chadwick
        elif [[ "${dry_run}" == true ]]; then
            log_info "Skipping Chadwick load (dry-run mode)"
        fi
        
        # Stage 3: Lahman Gap-Fill
        if [[ "${skip_lahman}" == false && "${dry_run}" == false ]]; then
            stage_load_lahman
        elif [[ "${dry_run}" == true ]]; then
            log_info "Skipping Lahman gap-fill (dry-run mode)"
        fi
        
        # Stage 4: External Bridge
        if [[ "${skip_external}" == false && "${dry_run}" == false ]]; then
            stage_populate_external
        elif [[ "${dry_run}" == true ]]; then
            log_info "Skipping external bridge (dry-run mode)"
        fi
        
        # Stage 5: Validation
        stage_validate
        
        # Stage 6: Summary Report
        stage_generate_report
    fi
    
    # Footer
    log_info ""
    log_info "=" 
    log_info "BRIDGE POPULATION COMPLETE"
    log_info "=" 
    log_info "Log File: ${LOG_FILE}"
    log_info ""
    
    return 0
}

# Run main
main "$@"
