-- File: sql/features/003_pitch_flexible_mart.sql
-- Purpose: Create flexible feature mart schema for pitch-level data
-- Author: Agent Cascade
-- Date: 2026-04-24
CREATE TABLE IF NOT EXISTS features_pitch.base_features (
    -- ========================================================================
    -- IDENTITY & LINKAGE
    -- ========================================================================
    pitch_id BIGSERIAL PRIMARY KEY,
    game_pk INTEGER NOT NULL,
    at_bat_number INTEGER,
    pitch_number SMALLINT,
    game_year SMALLINT,
    game_date DATE,
    sv_id VARCHAR(50), -- Statcast video ID
    
    -- Canonical player IDs (via bridge tables)
    batter_id INTEGER,
    pitcher_id INTEGER,
    player_name VARCHAR(100),
    
    -- Team context
    home_team VARCHAR(3),
    away_team VARCHAR(3),
    inning_topbot VARCHAR(3), -- 'Top' or 'Bot'
    
    -- ========================================================================
    -- PITCH IDENTIFICATION (all pitch types preserved)
    -- ========================================================================
    pitch_type VARCHAR(2), -- FF, SL, CH, CU, etc.
    pitch_name VARCHAR(50), -- Four-Seam Fastball, Slider, etc.
    description VARCHAR(100), -- called_strike, swinging_strike, etc.
    events VARCHAR(50), -- single, double, home_run, etc.
    type VARCHAR(1), -- B (ball), S (strike), X (in play)
    
    -- ========================================================================
    -- PITCH PHYSICS (all fields preserved)
    -- ========================================================================
    start_speed REAL, -- Alternative to release_speed
    release_speed REAL,
    effective_speed REAL,
    release_spin_rate REAL,
    spin_axis REAL,
    spin_rate_deprecated REAL, -- Legacy field preserved
    
    -- Release point (all three coordinates)
    release_pos_x REAL,
    release_pos_y REAL,
    release_pos_z REAL,
    release_extension REAL,
    
    -- Movement (pfx = perceived from z=40ft to front of plate)
    pfx_x REAL, -- Horizontal movement
    pfx_z REAL, -- Vertical movement
    
    -- Velocity components (for physics calculations)
    vx0 REAL,
    vy0 REAL,
    vz0 REAL,
    ax REAL,
    ay REAL,
    az REAL,
    
    -- ========================================================================
    -- PLATE LOCATION & ZONE (all fields preserved)
    -- ========================================================================
    plate_x REAL, -- Horizontal position (-17 to +17 inches, 0 = center)
    plate_z REAL, -- Vertical position (feet from ground)
    zone SMALLINT, -- 1-9 strike zone grid, 11-14 for balls
    sz_top REAL, -- Top of strike zone for batter
    sz_bot REAL, -- Bottom of strike zone for batter
    
    -- PostGIS geometry (separate column for spatial indexing)
    location GEOMETRY(POINT, 4326), -- Derived from plate_x, plate_z
    
    -- ========================================================================
    -- GAME STATE (all context fields preserved)
    -- ========================================================================
    balls SMALLINT,
    strikes SMALLINT,
    outs_when_up SMALLINT,
    inning SMALLINT,
    
    -- Base state (3 booleans)
    on_1b BOOLEAN,
    on_2b BOOLEAN,
    on_3b BOOLEAN,
    
    -- Score (all variations preserved)
    home_score SMALLINT,
    away_score SMALLINT,
    bat_score SMALLINT,
    fld_score SMALLINT,
    post_home_score SMALLINT,
    post_away_score SMALLINT,
    post_bat_score SMALLINT,
    post_fld_score SMALLINT,
    
    -- Plate appearance number in game
    at_bat_number_pitchfx INTEGER, -- Alternative sequencing
    
    -- ========================================================================
    -- BATTER-PITCHER ATTRIBUTES (all fields preserved)
    -- ========================================================================
    stand VARCHAR(1), -- L or R (batter)
    p_throws VARCHAR(1), -- L or R (pitcher)
    
    -- ========================================================================
    -- HIT DATA (all batted ball fields preserved)
    -- ========================================================================
    hc_x REAL, -- Hit coordinate X (from Statcast)
    hc_y REAL, -- Hit coordinate Y
    hit_location SMALLINT, -- Field position code
    bb_type VARCHAR(20), -- Batted ball type (ground_ball, fly_ball, etc.)
    
    -- Launch metrics
    launch_speed REAL,
    launch_angle REAL,
    launch_speed_angle REAL,
    hit_distance_sc INTEGER, -- Hit distance
    
    -- Estimated stats (xStats from Statcast)
    estimated_ba REAL, -- Expected batting average
    estimated_slg REAL, -- Expected slugging
    estimated_woba REAL, -- Expected wOBA
    
    -- ========================================================================
    -- PLATE DISCIPLINE (all fields preserved)
    -- ========================================================================
    woba_value REAL,
    woba_denom REAL,
    babip_value REAL,
    iso_value REAL,
    
    -- ========================================================================
    -- WIN PROBABILITY (all delta fields preserved)
    -- ========================================================================
    delta_home_win_exp REAL,
    delta_run_exp REAL,
    home_win_exp REAL,
    bat_win_exp REAL,
    
    -- ========================================================================
    -- FIELDING POSITIONS (all fielder IDs preserved)
    -- ========================================================================
    fielder_2 INTEGER, -- Catcher
    fielder_3 INTEGER, -- 1B
    fielder_4 INTEGER, -- 2B
    fielder_5 INTEGER, -- 3B
    fielder_6 INTEGER, -- SS
    fielder_7 INTEGER, -- LF
    fielder_8 INTEGER, -- CF
    fielder_9 INTEGER, -- RF
    
    -- Fielding alignment
    if_fielding_alignment VARCHAR(20),
    of_fielding_alignment VARCHAR(20),
    
    -- ========================================================================
    -- DATA QUALITY & METADATA
    -- ========================================================================
    quality_flag VARCHAR(20) DEFAULT 'normal',
    -- ^ From 001_pitch_data_quality.sql: normal, extreme_outlier_low, 
    --   high_passed_ball, wide_wild_pitch
    
    -- Lineage tracking
    source_table VARCHAR(50) DEFAULT 'features_pitch.locations',
    source_row_id BIGINT, -- Original locations.pitch_id
    
    -- Reproducibility
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    data_version INTEGER DEFAULT 1, -- Schema version
    ingestion_batch_id VARCHAR(50) -- For tracking bulk loads
);

-- ============================================================================
-- INDEXES FOR PERFORMANCE
-- ============================================================================
-- Core lookup indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_base_features_game_year 
    ON features_pitch.base_features(game_year);
    
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_base_features_batter 
    ON features_pitch.base_features(batter_id);
    
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_base_features_pitcher 
    ON features_pitch.base_features(pitcher_id);
    
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_base_features_game_atbat 
    ON features_pitch.base_features(game_pk, at_bat_number);
    
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_base_features_quality 
    ON features_pitch.base_features(quality_flag) 
    WHERE quality_flag = 'normal';
    
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_base_features_location 
    ON features_pitch.base_features USING GIST(location);
    
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_base_features_pitch_type 
    ON features_pitch.base_features(pitch_type);

-- ============================================================================
-- 2. FEATURE REGISTRY - Metadata-driven feature selection
-- ============================================================================
-- This table enables "SELECT * FROM features WHERE model = 'xgboost'" style
-- queries. It documents every field and its usage across model families.

CREATE TABLE IF NOT EXISTS features_pitch.feature_registry (
    feature_id SERIAL PRIMARY KEY,
    
    -- Location
    schema_name VARCHAR(50) NOT NULL DEFAULT 'features_pitch',
    table_name VARCHAR(100) NOT NULL,
    column_name VARCHAR(100) NOT NULL,
    
    -- Classification
    feature_category VARCHAR(50), 
    -- ^ 'identity', 'physics', 'location', 'context', 'outcome', 
    --   'engineered', 'quality', 'metadata'
    
    feature_type VARCHAR(20), 
    -- ^ 'numeric', 'categorical', 'boolean', 'spatial', 'jsonb', 'array'
    
    -- Usage flags
    is_default BOOLEAN DEFAULT FALSE, 
    -- ^ Included by default in generic training queries
    
    is_engineered BOOLEAN DEFAULT FALSE,
    -- ^ Derived from other columns
    
    is_nullable BOOLEAN DEFAULT TRUE,
    
    -- Documentation
    description TEXT,
    units VARCHAR(30), -- 'mph', 'inches', 'feet', 'rpm', etc.
    source_column VARCHAR(100), 
    -- ^ If engineered: source column name
    
    derivation_sql TEXT, 
    -- ^ SQL to derive this feature (if engineered)
    
    -- Model family assignments (array for multiple models)
    model_usage VARCHAR[] DEFAULT '{}',
    -- ^ e.g., ARRAY['xgboost', 'lstm', 'multitask', 'swing']
    
    -- Data quality metrics (updated periodically)
    null_percentage REAL,
    unique_percentage REAL,
    correlation_with_target REAL,
    importance_score REAL, -- From SHAP analysis
    
    -- Statistical summary (JSONB for flexibility)
    data_quality JSONB DEFAULT '{}',
    -- ^ {null_pct: 0.02, unique_pct: 0.95, mean: 92.5, std: 3.2, ...}
    
    -- Versioning
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- Unique constraint
    UNIQUE(schema_name, table_name, column_name)
);

-- Index for fast model-based queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_feature_registry_model 
    ON features_pitch.feature_registry USING GIN(model_usage);
    
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_feature_registry_default 
    ON features_pitch.feature_registry(is_default) 
    WHERE is_default = TRUE;

-- ============================================================================
-- 3. ENGINEERED FEATURES - Additive derived metrics
-- ============================================================================
-- These are computed from base_features and stored separately to:
-- - Enable NULL-free storage for derived values
-- - Support different refresh schedules
-- - Allow easy extension without schema migrations

CREATE TABLE IF NOT EXISTS features_pitch.engineered_features (
    pitch_id BIGINT PRIMARY KEY REFERENCES features_pitch.base_features(pitch_id),
    
    -- ========================================================================
    -- VELOCITY CATEGORIZATION
    -- ========================================================================
    velocity_category VARCHAR(10), 
    -- ^ 'slow' (<80), 'medium' (80-90), 'fast' (90-95), 'elite' (>95)
    
    velocity_percentile REAL, 
    -- ^ 0-100 percentile for this pitch type and season
    
    velocity_diff_from_avg REAL,
    -- ^ Difference from pitcher's average for this type
    
    -- ========================================================================
    -- ZONE CLASSIFICATION (Statcast-based)
    -- ========================================================================
    zone_region VARCHAR(20),
    -- ^ Statcast zones: 'heart' (1-2-3), 'shadow' (4-5-6-7-8-9),
    --   'chase' (11-12-13-14), 'waste' (outside all)
    
    is_in_zone BOOLEAN, -- True if zone in (1,2,3,4,5,6,7,8,9)
    is_in_shadow_zone BOOLEAN, -- Borderline calls
    is_in_chase_zone BOOLEAN, -- Just outside zone
    
    distance_from_zone_center REAL,
    -- ^ Euclidean distance from center of strike zone
    
    -- ========================================================================
    -- OUTCOME BINARIES (for classification targets)
    -- ========================================================================
    is_strike BOOLEAN,
    is_swing BOOLEAN,
    is_whiff BOOLEAN, -- Swing and miss
    is_called_strike BOOLEAN,
    is_foul BOOLEAN,
    is_foul_tip BOOLEAN,
    is_ball_in_play BOOLEAN,
    is_hit BOOLEAN,
    is_single BOOLEAN,
    is_double BOOLEAN,
    is_triple BOOLEAN,
    is_home_run BOOLEAN,
    is_xbh BOOLEAN, -- Extra base hit
    is_out BOOLEAN,
    is_ground_ball BOOLEAN,
    is_fly_ball BOOLEAN,
    is_line_drive BOOLEAN,
    is_popup BOOLEAN,
    is_hard_hit BOOLEAN, -- launch_speed >= 95 mph
    is_barrel BOOLEAN, -- Barrel classification from Statcast
    
    -- Tier 1 classification target
    outcome_tier1 VARCHAR(20), 
    -- ^ 'ball', 'strike', 'ball_in_play'
    
    -- Tier 2 classification target (if ball_in_play)
    outcome_tier2 VARCHAR(20),
    -- ^ 'single', 'double', 'triple', 'home_run', 'out'
    
    -- Swing decision target
    swing_decision VARCHAR(10),
    -- ^ 'swing', 'take'
    
    -- ========================================================================
    -- DERIVED PHYSICS METRICS
    -- ========================================================================
    horizontal_break REAL, -- pfx_x normalized to pitch hand
    vertical_break REAL, -- pfx_z with gravity adjustment
    approach_angle REAL, -- Derived from release to plate trajectory
    spin_efficiency REAL, -- Spin contributing to movement
    induced_vertical_break REAL, -- IVB for fastballs
    horizontal_release_deviation REAL, -- From pitcher avg
    
    -- Plate appearance relative metrics
    release_velocity_diff REAL, -- From pitcher's season avg
    
    -- ========================================================================
    -- SEQUENCE CONTEXT (within plate appearance)
    -- ========================================================================
    pa_pitch_count SMALLINT, -- Which pitch in the PA (1, 2, 3, ...)
    pitches_remaining_pa INTEGER, -- Estimated pitches left in PA
    
    -- Previous pitch context
    prev_pitch_type VARCHAR(2),
    prev_pitch_result VARCHAR(50),
    prev_plate_x REAL,
    prev_plate_z REAL,
    prev_velocity REAL,
    prev_break_x REAL,
    prev_break_z REAL,
    time_since_prev_pitch REAL, -- Seconds (if available)
    
    -- Sequence patterns
    prev_was_strike BOOLEAN,
    prev_was_ball BOOLEAN,
    prev_was_swing BOOLEAN,
    
    -- Count progression
    count_started_this_pa BOOLEAN, -- Is this the first pitch?
    is_full_count BOOLEAN, -- 3-2 count
    is_two_strike BOOLEAN,
    is_three_ball BOOLEAN,
    
    -- ========================================================================
    -- PITCHER CONTEXT
    -- ========================================================================
    pitcher_arsenal_index REAL,
    -- ^ How "signature" is this pitch for the pitcher (0-1)
    
    pitcher_repertoire_depth REAL,
    -- ^ Number of distinct pitch types this pitcher throws
    
    -- Pitch usage in this game
    game_pitch_count INTEGER, -- How many pitches in this game so far
    pitch_usage_pct_this_game REAL, -- % of this pitch type in game
    
    -- ========================================================================
    -- BATTER CONTEXT
    -- ========================================================================
    batter_performance_vs_type REAL, -- Historical OPS vs this pitch type
    batter_swing_rate_vs_type REAL, -- Historical swing rate
    batter_whiff_rate_vs_type REAL, -- Historical whiff rate
    
    -- Hot/cold zones
    is_batter_hot_zone BOOLEAN, -- Is this in batter's hot zone?
    is_batter_cold_zone BOOLEAN, -- Is this in batter's cold zone?
    
    -- ========================================================================
    -- GAME CONTEXT
    -- ========================================================================
    score_diff INTEGER, -- bat_score - fld_score
    score_diff_bucket VARCHAR(10), -- 'blowout_ahead', 'close', etc.
    is_late_game BOOLEAN, -- Inning > 7
    is_high_leverage BOOLEAN, -- Based on win probability change potential
    
    -- Base state encoding (for faster joins)
    base_state_code SMALLINT, -- 0-7 binary encoding
    base_state_name VARCHAR(20), -- 'bases_empty', 'runners_on', etc.
    
    -- Count encoding (for aggregation)
    count_code VARCHAR(5), -- '0-0', '1-2', '3-1', etc.
    
    -- ========================================================================
    -- MATCHUP HISTORY
    -- ========================================================================
    times_faced_this_game INTEGER, -- How many times batter has faced pitcher
    total_pitches_in_matchup INTEGER, -- Cumulative count
    
    -- ========================================================================
    -- METADATA
    -- ========================================================================
    engineered_at TIMESTAMP DEFAULT NOW(),
    engineer_version INTEGER DEFAULT 1,
    
    -- Data lineage
    source_calculations JSONB DEFAULT '{}'
    -- ^ Which calculations contributed to this row
);

-- Indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_engineered_outcome_tier1 
    ON features_pitch.engineered_features(outcome_tier1);
    
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_engineered_outcome_tier2 
    ON features_pitch.engineered_features(outcome_tier2);
    
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_engineered_swing 
    ON features_pitch.engineered_features(swing_decision);
    
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_engineered_pitch_type 
    ON features_pitch.engineered_features(prev_pitch_type);

-- ============================================================================
-- 4. SEQUENTIAL FEATURES - For LSTM/Transformer models
-- ============================================================================
-- Stores sliding windows and sequences for sequential models
-- JSONB enables variable-length sequences

CREATE TABLE IF NOT EXISTS features_pitch.sequential_features (
    sequence_id BIGSERIAL PRIMARY KEY,
    
    -- Identity
    pa_id BIGINT, -- game_pk * 1000 + at_bat_number (composite key)
    game_pk INTEGER NOT NULL,
    at_bat_number INTEGER NOT NULL,
    batter_id INTEGER,
    pitcher_id INTEGER,
    game_year SMALLINT,
    
    -- Sequence metadata
    sequence_position SMALLINT, -- Which pitch in sequence (1, 2, 3, ...)
    total_pa_pitches SMALLINT, -- Total pitches in this PA
    pitches_before SMALLINT,
    pitches_after SMALLINT,
    
    -- The pitch itself (foreign key to base_features)
    pitch_id BIGINT REFERENCES features_pitch.base_features(pitch_id),
    
    -- ========================================================================
    -- CONTEXT WINDOWS (JSONB for flexibility)
    -- ========================================================================
    -- Sliding windows of prior pitches (as arrays of pitch data)
    window_2pitch JSONB, -- Last 2 pitches
    window_3pitch JSONB, -- Last 3 pitches
    window_5pitch JSONB, -- Last 5 pitches (may span PAs)
    
    -- Full context
    full_pa_sequence JSONB, -- All pitches in this plate appearance
    
    -- Pre-computed sequence features (extracted from JSONB for indexing)
    pitch_type_sequence VARCHAR[], -- ['FF', 'SL', 'CH']
    velocity_sequence REAL[], -- [92.5, 85.3, 78.1]
    result_sequence VARCHAR[], -- ['called_strike', 'foul', 'swinging_strike']
    
    -- Sequence analytics
    pitches_since_last_fastball SMALLINT,
    pitches_since_last_breaking SMALLINT,
    pitches_since_last_offspeed SMALLINT,
    
    velocity_trend REAL, -- Slope of velocity over window
    location_variance_x REAL, -- Variance in plate_x
    location_variance_z REAL, -- Variance in plate_z
    
    -- Pattern detection
    location_pattern VARCHAR(20), 
    -- ^ 'inside_outside', 'high_low', 'cluster', 'spread', 'sequence'
    
    is_fastball_setup BOOLEAN, -- Was prev pitch fastball?
    is_offspeed_setup BOOLEAN, -- Was prev pitch offspeed?
    
    -- Count progression within sequence
    count_sequence VARCHAR[], -- ['0-0', '0-1', '1-1', '1-2']
    
    -- ========================================================================
    -- METADATA
    -- ========================================================================
    created_at TIMESTAMP DEFAULT NOW(),
    sequence_version INTEGER DEFAULT 1
);

-- Indexes for sequence lookups
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sequential_game_atbat 
    ON features_pitch.sequential_features(game_pk, at_bat_number);
    
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sequential_pitch 
    ON features_pitch.sequential_features(pitch_id);
    
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sequential_position 
    ON features_pitch.sequential_features(sequence_position);
    
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sequential_type_seq 
    ON features_pitch.sequential_features USING GIN(pitch_type_sequence);

-- ============================================================================
-- 5. PLAYER ROLLING CONTEXT - Updated nightly
-- ============================================================================
-- Stores rolling statistics for batters and pitchers
-- Enables "batter's last 30 days performance" type features

CREATE TABLE IF NOT EXISTS features_pitch.player_context (
    -- Composite key
    player_id INTEGER,
    season SMALLINT,
    game_date DATE,
    role VARCHAR(10) CHECK (role IN ('batter', 'pitcher')),
    window_type VARCHAR(20) CHECK (window_type IN ('30day', 'season', 'career')),
    
    PRIMARY KEY (player_id, season, game_date, role, window_type),
    
    -- ========================================================================
    -- SAMPLE COUNTS
    -- ========================================================================
    pa_count INTEGER, -- Plate appearances
    bip_count INTEGER, -- Balls in play
    ab_count INTEGER, -- At bats
    
    -- ========================================================================
    -- OUTCOME RATES (rolling averages)
    -- ========================================================================
    k_rate REAL,
    bb_rate REAL,
    hr_rate REAL,
    hit_rate REAL,
    xbh_rate REAL,
    single_rate REAL,
    double_rate REAL,
    triple_rate REAL,
    
    -- Batted ball rates
    gb_rate REAL, -- Ground ball rate
    fb_rate REAL, -- Fly ball rate
    ld_rate REAL, -- Line drive rate
    popup_rate REAL,
    
    -- Quality rates
    hard_hit_rate REAL,
    sweet_spot_rate REAL,
    barrel_rate REAL,
    
    -- ========================================================================
    -- QUALITY METRICS
    -- ========================================================================
    avg_launch_speed REAL,
    avg_launch_angle REAL,
    avg_hit_distance REAL,
    
    -- Estimated stats
    avg_estimated_woba REAL,
    avg_estimated_ba REAL,
    avg_estimated_slg REAL,
    
    -- Plate discipline
    zone_rate REAL, -- Pitches in zone
    swing_rate REAL, -- Swing percentage
    o_swing_rate REAL, -- Swing rate outside zone (chase)
    z_swing_rate REAL, -- Swing rate inside zone
    contact_rate REAL,
    whiff_rate REAL,
    
    -- ========================================================================
    -- PITCHER-SPECIFIC
    -- ========================================================================
    avg_velocity REAL,
    avg_spin_rate REAL,
    avg_effective_speed REAL,
    
    -- Outcome rates
    strike_rate REAL, -- Called + swinging strikes
    called_strike_rate REAL,
    swinging_strike_rate REAL,
    foul_rate REAL,
    ball_in_play_rate REAL,
    
    -- Pitch mix (JSONB for flexibility - varies by pitcher)
    pitch_mix JSONB,
    -- ^ {'FF': 0.45, 'SL': 0.25, 'CH': 0.20, 'CB': 0.10}
    
    pitch_mix_entropy REAL, -- Diversity of pitch usage
    primary_pitch VARCHAR(2), -- Most used pitch type
    secondary_pitch VARCHAR(2), -- Second most used
    
    -- Arsenal depth
    arsenal_size INTEGER, -- Number of distinct pitch types
    arsenal_quality_score REAL, -- Composite metric
    
    -- ========================================================================
    -- MATCHUP-SPECIFIC (when role context)
    -- ========================================================================
    vs_righty_pa INTEGER,
    vs_lefty_pa INTEGER,
    vs_righty_ops REAL,
    vs_lefty_ops REAL,
    
    -- ========================================================================
    -- TEMPORAL METADATA
    -- ========================================================================
    first_game_date DATE, -- First game in window
    last_game_date DATE, -- Last game in window
    days_active INTEGER, -- Days with games played
    games_count INTEGER, -- Games played
    
    -- Data freshness
    calculated_at TIMESTAMP DEFAULT NOW(),
    calculation_version INTEGER DEFAULT 1,
    
    -- Data quality
    sample_size_note VARCHAR(50) -- 'adequate', 'small_sample', etc.
);

-- Indexes for player context lookups
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_player_context_lookup 
    ON features_pitch.player_context(player_id, season, role, window_type);
    
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_player_context_date 
    ON features_pitch.player_context(game_date);
    
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_player_context_season 
    ON features_pitch.player_context(season, role);

-- ============================================================================
-- 6. MODEL TRAINING SETS - Versioned, reproducible training data
-- ============================================================================
-- Stores materialized training sets for specific models
-- Enables reproducibility: "train the same model on the same data"

CREATE TABLE IF NOT EXISTS features_pitch.model_training_set (
    training_id BIGSERIAL PRIMARY KEY,
    
    -- ========================================================================
    -- MODEL IDENTIFICATION
    -- ========================================================================
    model_name VARCHAR(50) NOT NULL,
    model_version VARCHAR(20) NOT NULL,
    model_family VARCHAR(20), -- 'xgboost', 'lstm', 'multitask', 'swing', 'ensemble'
    
    -- ========================================================================
    -- DATA IDENTIFICATION
    -- ========================================================================
    pitch_id BIGINT REFERENCES features_pitch.base_features(pitch_id),
    game_year SMALLINT,
    
    -- ========================================================================
    -- FEATURE VECTOR (PostgreSQL array for efficiency)
    -- ========================================================================
    feature_names TEXT[], -- Column names for interpretability
    feature_vector REAL[], -- Aligned 1:1 with feature_names
    feature_count INTEGER, -- Number of features (for validation)
    
    -- Normalization parameters (if applied)
    normalization_method VARCHAR(20), -- 'standard', 'minmax', 'robust', 'none'
    normalization_params JSONB, -- {means: [...], stds: [...]}
    
    -- ========================================================================
    -- TARGET VARIABLES (multiple targets supported)
    -- ========================================================================
    -- Primary target
    target_type VARCHAR(30), 
    -- ^ 'outcome_tier1', 'outcome_tier2', 'pitch_type', 'swing', 
    --   'location_x', 'location_z', 'sequence_next'
    
    target_label VARCHAR(50), -- Class label
    target_value REAL, -- For regression targets or class index
    target_onehot REAL[], -- One-hot encoded (for classification)
    
    -- Secondary targets (multi-task learning)
    secondary_targets JSONB,
    -- ^ {pitch_type: 'FF', plate_x: -0.5, plate_z: 2.1}
    
    -- ========================================================================
    -- TRAIN/VAL/TEST SPLIT
    -- ========================================================================
    split_set VARCHAR(10) CHECK (split_set IN ('train', 'val', 'test')),
    split_method VARCHAR(20), -- 'season', 'random', 'stratified', 'game'
    split_seed INTEGER, -- For reproducible random splits
    fold_number INTEGER, -- For k-fold cross validation
    
    -- Stratification group (for stratified sampling)
    stratify_group VARCHAR(50),
    -- ^ e.g., '2023_fastball_0-0' for season+type+count stratification
    
    -- ========================================================================
    -- REPRODUCIBILITY & LINEAGE
    -- ========================================================================
    -- Data state
    data_hash VARCHAR(64), -- Hash of source data state (SHA-256)
    feature_query_hash VARCHAR(64), -- Hash of query used to generate
    
    -- Feature configuration
    feature_config_id INTEGER,
    -- ^ References features_pitch.feature_registry configuration snapshot
    
    -- Data versions
    base_features_version INTEGER,
    engineered_features_version INTEGER,
    player_context_version INTEGER,
    
    -- Source query (stored for inspection)
    source_query TEXT,
    
    -- Timing
    created_at TIMESTAMP DEFAULT NOW(),
    materialized_at TIMESTAMP, -- When row was actually computed
    
    -- Uniqueness constraint: one row per model version per pitch
    UNIQUE(model_name, model_version, pitch_id)
);

-- Indexes for training set queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_training_model 
    ON features_pitch.model_training_set(model_name, model_version, split_set);
    
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_training_game_year 
    ON features_pitch.model_training_set(game_year);
    
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_training_pitch 
    ON features_pitch.model_training_set(pitch_id);

-- ============================================================================
-- 7. PITCH SEQUENCES AGGREGATE - For sequence-level analysis
-- ============================================================================
-- One row per plate appearance with full pitch sequence

CREATE TABLE IF NOT EXISTS features_pitch.pitch_sequences (
    sequence_id BIGSERIAL PRIMARY KEY,
    
    -- Identity
    pa_id BIGINT, -- game_pk * 1000 + at_bat_number
    game_pk INTEGER NOT NULL,
    at_bat_number INTEGER NOT NULL,
    game_year SMALLINT,
    
    batter_id INTEGER,
    pitcher_id INTEGER,
    
    -- Sequence metadata
    pitches_in_pa SMALLINT,
    sequence_outcome VARCHAR(50), -- Final outcome of PA
    
    -- Full sequence (array of pitch_ids in order)
    pitch_sequence INTEGER[], -- [pitch_id_1, pitch_id_2, ...]
    
    -- Sequence-level features
    sequence_duration_seconds REAL, -- Time from first to last pitch
    avg_velocity REAL,
    velocity_range REAL, -- Max - min
    pitch_type_count SMALLINT, -- Distinct types used
    
    -- Pattern flags
    started_with_fastball BOOLEAN,
    started_with_offspeed BOOLEAN,
    finished_with_swinging_strike BOOLEAN,
    finished_with_called_strike BOOLEAN,
    finished_with_ball_in_play BOOLEAN,
    
    -- Sequence type
    sequence_classification VARCHAR(30),
    -- ^ 'quick_out', 'battle', 'strikeout_sequence', 'walk_sequence', etc.
    
    -- Summary stats
    strikes_thrown SMALLINT,
    balls_thrown SMALLINT,
    swings_induced SMALLINT,
    whiffs_induced SMALLINT,
    fouls_induced SMALLINT,
    
    -- Pre-computed JSONB for full analysis
    sequence_details JSONB,
    -- ^ Complete pitch data for each position
    
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sequences_game_atbat 
    ON features_pitch.pitch_sequences(game_pk, at_bat_number);
    
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sequences_pitcher 
    ON features_pitch.pitch_sequences(pitcher_id);
    
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sequences_outcome 
    ON features_pitch.pitch_sequences(sequence_outcome);

-- ============================================================================
-- VIEWS: Pre-built Training Feature Sets
-- ============================================================================

-- View: Default XGBoost training features (joins all relevant tables)
CREATE OR REPLACE VIEW features_pitch.vw_xgboost_base AS
SELECT 
    bf.pitch_id,
    bf.game_year,
    bf.game_pk,
    bf.at_bat_number,
    
    -- Core physics
    bf.release_speed,
    bf.release_spin_rate,
    bf.spin_axis,
    bf.pfx_x,
    bf.pfx_z,
    bf.plate_x,
    bf.plate_z,
    bf.zone,
    bf.sz_top,
    bf.sz_bot,
    
    -- Release point
    bf.release_pos_x,
    bf.release_pos_y,
    bf.release_pos_z,
    bf.release_extension,
    
    -- Game state
    bf.balls,
    bf.strikes,
    bf.outs_when_up,
    bf.inning,
    bf.inning_topbot,
    bf.on_1b,
    bf.on_2b,
    bf.on_3b,
    bf.bat_score,
    bf.fld_score,
    bf.home_score,
    bf.away_score,
    
    -- Handedness
    bf.stand,
    bf.p_throws,
    
    -- Identifiers
    bf.pitch_type,
    bf.batter_id,
    bf.pitcher_id,
    
    -- Engineered features (joined)
    ef.velocity_category,
    ef.zone_region,
    ef.is_in_zone,
    ef.is_strike,
    ef.is_swing,
    ef.is_whiff,
    ef.is_ball_in_play,
    ef.is_hit,
    ef.is_hard_hit,
    ef.outcome_tier1,
    ef.outcome_tier2,
    ef.swing_decision,
    ef.pa_pitch_count,
    ef.prev_pitch_type,
    ef.count_code,
    ef.score_diff,
    ef.is_late_game,
    ef.base_state_code,
    
    -- Player context (batter)
    bpc.k_rate as batter_k_rate,
    bpc.bb_rate as batter_bb_rate,
    bpc.avg_estimated_woba as batter_woba,
    bpc.hard_hit_rate as batter_hard_hit_pct,
    bpc.swing_rate as batter_swing_rate,
    bpc.whiff_rate as batter_whiff_rate,
    bpc.o_swing_rate as batter_chase_rate,
    
    -- Player context (pitcher)
    ppc.avg_velocity as pitcher_avg_velocity,
    ppc.zone_rate as pitcher_zone_pct,
    ppc.strike_rate as pitcher_strike_pct,
    ppc.swing_rate as pitcher_swing_pct,
    ppc.whiff_rate as pitcher_whiff_pct,
    ppc.k_rate as pitcher_k_rate,
    ppc.bb_rate as pitcher_bb_rate,
    ppc.pitch_mix as pitcher_mix,
    ppc.arsenal_size as pitcher_arsenal_size,
    
    -- Quality flag
    bf.quality_flag

FROM features_pitch.base_features bf
LEFT JOIN features_pitch.engineered_features ef USING (pitch_id)
LEFT JOIN features_pitch.player_context bpc 
    ON bpc.player_id = bf.batter_id 
    AND bpc.season = bf.game_year 
    AND bpc.role = 'batter'
    AND bpc.window_type = 'season'
    AND bpc.game_date = bf.game_date
LEFT JOIN features_pitch.player_context ppc 
    ON ppc.player_id = bf.pitcher_id 
    AND ppc.season = bf.game_year 
    AND ppc.role = 'pitcher'
    AND ppc.window_type = 'season'
    AND ppc.game_date = bf.game_date
WHERE bf.quality_flag IN ('normal', 'high_passed_ball');

-- ============================================================================
-- FUNCTIONS: Dynamic Feature Selection
-- ============================================================================

-- Function: Generate training query based on feature registry
CREATE OR REPLACE FUNCTION features_pitch.generate_training_query(
    p_model_name VARCHAR,
    p_feature_categories VARCHAR[] DEFAULT ARRAY['physics', 'location', 'context'],
    p_include_engineered BOOLEAN DEFAULT TRUE,
    p_include_player_context BOOLEAN DEFAULT TRUE
)
RETURNS TEXT AS $$
DECLARE
    v_base_columns TEXT;
    v_sql TEXT;
BEGIN
    -- Get base feature columns from registry
    SELECT STRING_AGG(
        'bf.' || fr.column_name,
        ', ' ORDER BY fr.feature_id
    )
    INTO v_base_columns
    FROM features_pitch.feature_registry fr
    WHERE fr.table_name = 'base_features'
      AND fr.feature_category = ANY(p_feature_categories);
    
    -- Build complete query
    v_sql := format(
        'SELECT %s FROM features_pitch.base_features bf 
         WHERE bf.quality_flag = ''normal''
         AND bf.game_year BETWEEN 2015 AND 2024',
        v_base_columns
    );
    
    RETURN v_sql;
END;
$$ LANGUAGE plpgsql;

-- Function: Get feature statistics from registry
CREATE OR REPLACE FUNCTION features_pitch.get_feature_stats(
    p_table_name VARCHAR,
    p_column_name VARCHAR
)
RETURNS JSONB AS $$
DECLARE
    v_stats JSONB;
BEGIN
    SELECT data_quality INTO v_stats
    FROM features_pitch.feature_registry
    WHERE table_name = p_table_name
      AND column_name = p_column_name;
    
    RETURN v_stats;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- TRIGGERS: Automatic timestamp updates
-- ============================================================================

-- Trigger function for updated_at
CREATE OR REPLACE FUNCTION features_pitch.update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply to tables with updated_at
CREATE TRIGGER IF NOT EXISTS trg_base_features_update
    BEFORE UPDATE ON features_pitch.base_features
    FOR EACH ROW
    EXECUTE FUNCTION features_pitch.update_timestamp();

CREATE TRIGGER IF NOT EXISTS trg_feature_registry_update
    BEFORE UPDATE ON features_pitch.feature_registry
    FOR EACH ROW
    EXECUTE FUNCTION features_pitch.update_timestamp();

-- ============================================================================
-- INITIAL POPULATION: Feature Registry
-- ============================================================================
-- Populate feature_registry with all base_features columns

INSERT INTO features_pitch.feature_registry 
    (schema_name, table_name, column_name, feature_category, feature_type, 
     is_default, is_nullable, description, model_usage)
VALUES
    -- Identity columns
    ('features_pitch', 'base_features', 'pitch_id', 'identity', 'numeric', 
     FALSE, FALSE, 'Primary key for pitch', ARRAY['all']),
    ('features_pitch', 'base_features', 'game_pk', 'identity', 'numeric', 
     FALSE, FALSE, 'MLB game identifier', ARRAY['all']),
    ('features_pitch', 'base_features', 'batter_id', 'identity', 'numeric', 
     FALSE, FALSE, 'Canonical batter player ID', ARRAY['all']),
    ('features_pitch', 'base_features', 'pitcher_id', 'identity', 'numeric', 
     FALSE, FALSE, 'Canonical pitcher player ID', ARRAY['all']),
    
    -- Physics - Core (default for all models)
    ('features_pitch', 'base_features', 'release_speed', 'physics', 'numeric', 
     TRUE, TRUE, 'Pitch velocity at release', ARRAY['xgboost', 'lstm', 'multitask', 'swing']),
    ('features_pitch', 'base_features', 'release_spin_rate', 'physics', 'numeric', 
     TRUE, TRUE, 'Spin rate in RPM', ARRAY['xgboost', 'lstm', 'multitask']),
    ('features_pitch', 'base_features', 'spin_axis', 'physics', 'numeric', 
     TRUE, TRUE, 'Spin axis in degrees', ARRAY['xgboost', 'lstm']),
    ('features_pitch', 'base_features', 'pfx_x', 'physics', 'numeric', 
     TRUE, TRUE, 'Horizontal movement', ARRAY['xgboost', 'lstm', 'multitask']),
    ('features_pitch', 'base_features', 'pfx_z', 'physics', 'numeric', 
     TRUE, TRUE, 'Vertical movement', ARRAY['xgboost', 'lstm', 'multitask']),
    
    -- Release point
    ('features_pitch', 'base_features', 'release_pos_x', 'physics', 'numeric', 
     TRUE, TRUE, 'Horizontal release position', ARRAY['xgboost', 'lstm']),
    ('features_pitch', 'base_features', 'release_pos_z', 'physics', 'numeric', 
     TRUE, TRUE, 'Vertical release position', ARRAY['xgboost', 'lstm']),
    ('features_pitch', 'base_features', 'release_extension', 'physics', 'numeric', 
     TRUE, TRUE, 'Release extension feet', ARRAY['xgboost']),
    
    -- Location - Core
    ('features_pitch', 'base_features', 'plate_x', 'location', 'numeric', 
     TRUE, TRUE, 'Horizontal plate location', ARRAY['xgboost', 'lstm', 'multitask', 'swing']),
    ('features_pitch', 'base_features', 'plate_z', 'location', 'numeric', 
     TRUE, TRUE, 'Vertical plate location', ARRAY['xgboost', 'lstm', 'multitask', 'swing']),
    ('features_pitch', 'base_features', 'zone', 'location', 'numeric', 
     TRUE, TRUE, 'Strike zone grid (1-9, 11-14)', ARRAY['xgboost', 'lstm', 'swing']),
    ('features_pitch', 'base_features', 'sz_top', 'location', 'numeric', 
     TRUE, TRUE, 'Top of strike zone', ARRAY['xgboost']),
    ('features_pitch', 'base_features', 'sz_bot', 'location', 'numeric', 
     TRUE, TRUE, 'Bottom of strike zone', ARRAY['xgboost']),
    
    -- Context - Core
    ('features_pitch', 'base_features', 'balls', 'context', 'numeric', 
     TRUE, FALSE, 'Current ball count', ARRAY['xgboost', 'lstm', 'multitask', 'swing']),
    ('features_pitch', 'base_features', 'strikes', 'context', 'numeric', 
     TRUE, FALSE, 'Current strike count', ARRAY['xgboost', 'lstm', 'multitask', 'swing']),
    ('features_pitch', 'base_features', 'outs_when_up', 'context', 'numeric', 
     TRUE, FALSE, 'Current outs', ARRAY['xgboost', 'lstm', 'multitask']),
    ('features_pitch', 'base_features', 'inning', 'context', 'numeric', 
     TRUE, FALSE, 'Inning number', ARRAY['xgboost', 'lstm']),
    ('features_pitch', 'base_features', 'inning_topbot', 'context', 'categorical', 
     TRUE, FALSE, 'Top or bottom of inning', ARRAY['xgboost', 'lstm']),
    ('features_pitch', 'base_features', 'on_1b', 'context', 'boolean', 
     TRUE, FALSE, 'Runner on first', ARRAY['xgboost', 'lstm']),
    ('features_pitch', 'base_features', 'on_2b', 'context', 'boolean', 
     TRUE, FALSE, 'Runner on second', ARRAY['xgboost', 'lstm']),
    ('features_pitch', 'base_features', 'on_3b', 'context', 'boolean', 
     TRUE, FALSE, 'Runner on third', ARRAY['xgboost', 'lstm']),
    ('features_pitch', 'base_features', 'bat_score', 'context', 'numeric', 
     TRUE, FALSE, 'Batting team score', ARRAY['xgboost', 'lstm']),
    ('features_pitch', 'base_features', 'fld_score', 'context', 'numeric', 
     TRUE, FALSE, 'Fielding team score', ARRAY['xgboost', 'lstm']),
    
    -- Handedness
    ('features_pitch', 'base_features', 'stand', 'context', 'categorical', 
     TRUE, FALSE, 'Batter hand (L/R)', ARRAY['xgboost', 'lstm', 'multitask', 'swing']),
    ('features_pitch', 'base_features', 'p_throws', 'context', 'categorical', 
     TRUE, FALSE, 'Pitcher hand (L/R)', ARRAY['xgboost', 'lstm', 'multitask', 'swing']),
    
    -- Pitch identification
    ('features_pitch', 'base_features', 'pitch_type', 'outcome', 'categorical', 
     TRUE, TRUE, 'Pitch type code', ARRAY['lstm', 'multitask']),
    ('features_pitch', 'base_features', 'description', 'outcome', 'categorical', 
     TRUE, TRUE, 'Pitch result description', ARRAY['xgboost']),
    
    -- Outcome (for training)
    ('features_pitch', 'base_features', 'events', 'outcome', 'categorical', 
     FALSE, TRUE, 'Plate appearance event', ARRAY['xgboost']),
    
    -- Hit data (for BIP models)
    ('features_pitch', 'base_features', 'launch_speed', 'outcome', 'numeric', 
     FALSE, TRUE, 'Exit velocity', ARRAY['xgboost', 'tier2']),
    ('features_pitch', 'base_features', 'launch_angle', 'outcome', 'numeric', 
     FALSE, TRUE, 'Launch angle', ARRAY['xgboost', 'tier2']),
    ('features_pitch', 'base_features', 'hit_distance_sc', 'outcome', 'numeric', 
     FALSE, TRUE, 'Hit distance', ARRAY['xgboost', 'tier2']),
    
    -- Quality (filtering)
    ('features_pitch', 'base_features', 'quality_flag', 'quality', 'categorical', 
     FALSE, FALSE, 'Data quality classification', ARRAY['all']),
    
    -- Spatial (for GIS queries)
    ('features_pitch', 'base_features', 'location', 'location', 'spatial', 
     FALSE, TRUE, 'PostGIS geometry point', ARRAY['gis'])
ON CONFLICT (schema_name, table_name, column_name) DO UPDATE SET
    feature_category = EXCLUDED.feature_category,
    feature_type = EXCLUDED.feature_type,
    is_default = EXCLUDED.is_default,
    model_usage = EXCLUDED.model_usage;

-- ============================================================================
-- COMMENTS: Document the schema
-- ============================================================================

COMMENT ON TABLE features_pitch.base_features IS 
'Complete preservation of all 118 Statcast fields with versioning. 
All raw pitch data lives here. No data is ever deleted or overwritten.
See feature_registry for metadata on each column.';

COMMENT ON TABLE features_pitch.feature_registry IS 
'Metadata catalog for all features in the pitch feature mart.
Enables dynamic feature selection queries based on model family.
Update this table when adding new features or changing defaults.';

COMMENT ON TABLE features_pitch.engineered_features IS 
'Derived features computed from base_features. 
Additive only - never modify existing columns, only add new ones.
All engineered features documented in feature_registry with is_engineered=TRUE.';

COMMENT ON TABLE features_pitch.sequential_features IS 
'Sliding window sequences for LSTM/Transformer models.
JSONB columns enable variable-length sequences.
Pre-computed sequence features extracted for indexing.';

COMMENT ON TABLE features_pitch.player_context IS 
'Rolling player statistics updated nightly.
Windows: 30day, season, career.
Roles: batter, pitcher.
Join to base_features on player_id + season + game_date.';

COMMENT ON TABLE features_pitch.model_training_set IS 
'Materialized training sets for reproducibility.
Each row is one training example with feature vector and targets.
Versioned by model_name, model_version.
data_hash enables "reproduce this exact training run".';

COMMENT ON TABLE features_pitch.pitch_sequences IS 
'One row per plate appearance with full pitch sequence.
Enables sequence-level analysis and sequence outcome prediction.';

-- ============================================================================
-- END OF SCHEMA
-- ============================================================================

