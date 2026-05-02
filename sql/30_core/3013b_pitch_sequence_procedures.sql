-- File: sql/30_core/3013b_pitch_sequence_procedures.sql
-- Purpose: Stored procedures for pitch sequence parsing, validation, and training row generation
-- Author: Agent Cascade
-- Date: 2026-05-01
-- Dependencies: 3013_core_pitch_sequence_model.sql (must be run first)

CREATE SCHEMA IF NOT EXISTS pitch_sequence;

-- ============================================================================
-- PITCH SEQUENCE PARSING FUNCTIONS
-- ============================================================================

-- Function: Parse pitch sequence and return individual pitches with counts
-- Returns a set of rows with running ball/strike counts for each pitch
CREATE OR REPLACE FUNCTION pitch_sequence.parse_sequence(
    p_game_id TEXT,
    p_plate_appearance_id TEXT,
    p_pitch_seq_tx TEXT
) RETURNS TABLE (
    game_id TEXT,
    plate_appearance_id TEXT,
    pitch_index INTEGER,
    raw_symbol CHAR(1),
    symbol_meaning TEXT,
    symbol_group TEXT,
    is_pitch_symbol BOOLEAN,
    pre_pitch_balls INTEGER,
    pre_pitch_strikes INTEGER,
    post_pitch_balls INTEGER,
    post_pitch_strikes INTEGER,
    is_terminal_pitch BOOLEAN,
    is_valid_transition BOOLEAN
) AS $$
DECLARE
    v_balls INTEGER := 0;
    v_strikes INTEGER := 0;
    v_symbol CHAR(1);
    v_ref RECORD;
    v_index INTEGER := 0;
BEGIN
    -- Iterate through each character in the pitch sequence
    FOR v_symbol IN SELECT SUBSTRING(p_pitch_seq_tx, i, 1)
                      FROM generate_series(1, LENGTH(p_pitch_seq_tx)) AS i
    LOOP
        v_index := v_index + 1;
        
        -- Get symbol reference info
        SELECT * INTO v_ref
        FROM features.pitch_sequence_symbol_reference
        WHERE symbol = v_symbol;
        
        -- Return current pitch state
        game_id := p_game_id;
        plate_appearance_id := p_plate_appearance_id;
        pitch_index := v_index;
        raw_symbol := v_symbol;
        symbol_meaning := COALESCE(v_ref.symbol_meaning, 'unknown');
        symbol_group := COALESCE(v_ref.symbol_group, 'unknown_symbol');
        is_pitch_symbol := COALESCE(v_ref.is_pitch_symbol, FALSE);
        pre_pitch_balls := v_balls;
        pre_pitch_strikes := v_strikes;
        
        -- Calculate post-pitch counts
        IF v_ref.is_pitch_symbol AND v_ref.counts_toward_ball THEN
            post_pitch_balls := LEAST(v_balls + 1, 4);
            post_pitch_strikes := v_strikes;
        ELSIF v_ref.is_pitch_symbol AND v_ref.counts_toward_strike THEN
            -- Handle foul balls with 2 strikes (don't increment)
            IF v_ref.symbol_group = 'foul' AND v_strikes >= 2 THEN
                post_pitch_balls := v_balls;
                post_pitch_strikes := v_strikes;
            ELSE
                post_pitch_balls := v_balls;
                post_pitch_strikes := LEAST(v_strikes + 1, 3);
            END IF;
        ELSE
            post_pitch_balls := v_balls;
            post_pitch_strikes := v_strikes;
        END IF;
        
        -- Determine if terminal (in play, walk, or strikeout)
        is_terminal_pitch := COALESCE(v_ref.is_ball_in_play_symbol, FALSE)
            OR (post_pitch_balls >= 4)
            OR (post_pitch_strikes >= 3);
        
        -- Validate transition
        is_valid_transition := (
            post_pitch_balls <= 4 AND
            post_pitch_strikes <= 3 AND
            (post_pitch_balls > pre_pitch_balls OR post_pitch_strikes > pre_pitch_strikes OR NOT v_ref.is_pitch_symbol)
        );
        
        RETURN NEXT;
        
        -- Update counts for next iteration
        v_balls := post_pitch_balls;
        v_strikes := post_pitch_strikes;
    END LOOP;
    
    RETURN;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION pitch_sequence.parse_sequence IS 
'Parse a Retrosheet pitch sequence string and return individual pitches with running ball/strike counts.
Handles all pitch symbols including balls, strikes, fouls, pickoffs, and markers.
Foul balls with 2 strikes do not increment the strike count.
Returns pre-pitch and post-pitch counts for each symbol.';

-- ============================================================================
-- TRAINING ROW GENERATION
-- ============================================================================

-- Materialized View: Pitch-level training rows with full context
CREATE MATERIALIZED VIEW IF NOT EXISTS pitch_sequence.training_rows AS
WITH parsed AS (
    SELECT 
        pse.game_id,
        pse.plate_appearance_id,
        pse.season,
        pse.game_date,
        pse.inning,
        pse.is_bottom_inning,
        pse.outs_before,
        pse.start_bases,
        pse.batting_team_id,
        pse.fielding_team_id,
        pse.batter_id,
        pse.batter_hand,
        pse.pitcher_id,
        pse.pitcher_hand,
        pse.event_code,
        pse.outcome_class,
        pse.outcome_group,
        pse.is_ball_in_play,
        pse.pitch_seq_tx,
        parse.pitch_index,
        parse.raw_symbol,
        parse.symbol_meaning,
        parse.symbol_group,
        parse.is_pitch_symbol,
        parse.pre_pitch_balls,
        parse.pre_pitch_strikes,
        parse.post_pitch_balls,
        parse.post_pitch_strikes,
        parse.is_terminal_pitch,
        parse.is_valid_transition
    FROM features.pitch_sequence_examples pse
    CROSS JOIN LATERAL pitch_sequence.parse_sequence(
        pse.game_id, 
        pse.plate_appearance_id, 
        pse.pitch_seq_tx
    ) parse
    WHERE pse.is_pitch_symbol  -- Only include actual pitch symbols
)
SELECT 
    parsed.*,
    -- Derived features for modeling
    CASE 
        WHEN parsed.pre_pitch_balls = 0 AND parsed.pre_pitch_strikes = 0 THEN '0-0'
        WHEN parsed.pre_pitch_balls = 1 AND parsed.pre_pitch_strikes = 0 THEN '1-0'
        WHEN parsed.pre_pitch_balls = 0 AND parsed.pre_pitch_strikes = 1 THEN '0-1'
        WHEN parsed.pre_pitch_balls = 2 AND parsed.pre_pitch_strikes = 0 THEN '2-0'
        WHEN parsed.pre_pitch_balls = 1 AND parsed.pre_pitch_strikes = 1 THEN '1-1'
        WHEN parsed.pre_pitch_balls = 0 AND parsed.pre_pitch_strikes = 2 THEN '0-2'
        WHEN parsed.pre_pitch_balls = 3 AND parsed.pre_pitch_strikes = 0 THEN '3-0'
        WHEN parsed.pre_pitch_balls = 2 AND parsed.pre_pitch_strikes = 1 THEN '2-1'
        WHEN parsed.pre_pitch_balls = 1 AND parsed.pre_pitch_strikes = 2 THEN '1-2'
        WHEN parsed.pre_pitch_balls = 3 AND parsed.pre_pitch_strikes = 1 THEN '3-1'
        WHEN parsed.pre_pitch_balls = 2 AND parsed.pre_pitch_strikes = 2 THEN '2-2'
        WHEN parsed.pre_pitch_balls = 3 AND parsed.pre_pitch_strikes = 2 THEN '3-2'
        ELSE CONCAT(parsed.pre_pitch_balls, '-', parsed.pre_pitch_strikes)
    END AS count_label,
    -- Is this a two-strike situation?
    (parsed.pre_pitch_strikes >= 2) AS is_two_strike,
    -- Is this a three-ball situation?
    (parsed.pre_pitch_balls >= 3) AS is_three_ball,
    -- Pitch type categorization for modeling
    CASE 
        WHEN parsed.symbol_group IN ('ball', 'intentional_ball', 'pitchout', 'awarded_ball') THEN 'ball'
        WHEN parsed.symbol_group IN ('called_strike', 'swinging_strike', 'foul', 'foul_tip', 'foul_bunt', 'automatic_strike') THEN 'strike'
        WHEN parsed.symbol_group IN ('in_play', 'in_play_pitchout') THEN 'in_play'
        WHEN parsed.symbol_group IN ('hit_by_pitch') THEN 'hbp'
        ELSE 'other'
    END AS pitch_category,
    -- Next pitch prediction target (for training next-pitch models)
    LEAD(parsed.raw_symbol) OVER (
        PARTITION BY parsed.game_id, parsed.plate_appearance_id 
        ORDER BY parsed.pitch_index
    ) AS next_pitch_symbol,
    -- Terminal outcome for the PA
    CASE 
        WHEN parsed.is_terminal_pitch THEN parsed.outcome_class
        ELSE NULL
    END AS terminal_outcome
FROM parsed;

-- Index for efficient querying
CREATE UNIQUE INDEX IF NOT EXISTS training_rows_pk 
ON pitch_sequence.training_rows (game_id, plate_appearance_id, pitch_index);

CREATE INDEX IF NOT EXISTS training_rows_context_idx 
ON pitch_sequence.training_rows (season, count_label, pitch_category);

CREATE INDEX IF NOT EXISTS training_rows_player_idx 
ON pitch_sequence.training_rows (season, batter_id, pitcher_id);

CREATE INDEX IF NOT EXISTS training_rows_terminal_idx 
ON pitch_sequence.training_rows (game_id, plate_appearance_id) 
WHERE is_terminal_pitch;

-- ============================================================================
-- VALIDATION PROCEDURES
-- ============================================================================

-- Function: Validate pitch sequence count transitions
-- Returns any invalid transitions found
CREATE OR REPLACE FUNCTION pitch_sequence.validate_transitions(
    p_game_id TEXT DEFAULT NULL,
    p_plate_appearance_id TEXT DEFAULT NULL,
    p_season INTEGER DEFAULT NULL
) RETURNS TABLE (
    game_id TEXT,
    plate_appearance_id TEXT,
    pitch_index INTEGER,
    raw_symbol CHAR(1),
    pre_pitch_balls INTEGER,
    pre_pitch_strikes INTEGER,
    post_pitch_balls INTEGER,
    post_pitch_strikes INTEGER,
    expected_balls INTEGER,
    expected_strikes INTEGER,
    validation_error TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        tr.game_id,
        tr.plate_appearance_id,
        tr.pitch_index,
        tr.raw_symbol,
        tr.pre_pitch_balls,
        tr.pre_pitch_strikes,
        tr.post_pitch_balls,
        tr.post_pitch_strikes,
        -- Expected counts based on symbol type
        CASE 
            WHEN tr.symbol_group IN ('ball', 'intentional_ball', 'awarded_ball') 
                THEN LEAST(tr.pre_pitch_balls + 1, 4)
            ELSE tr.pre_pitch_balls
        END AS expected_balls,
        CASE 
            WHEN tr.symbol_group IN ('called_strike', 'swinging_strike', 'automatic_strike') 
                THEN LEAST(tr.pre_pitch_strikes + 1, 3)
            WHEN tr.symbol_group IN ('foul', 'foul_tip', 'foul_bunt') AND tr.pre_pitch_strikes < 2
                THEN LEAST(tr.pre_pitch_strikes + 1, 3)
            WHEN tr.symbol_group IN ('foul', 'foul_tip', 'foul_bunt') AND tr.pre_pitch_strikes >= 2
                THEN tr.pre_pitch_strikes  -- Foul with 2 strikes doesn't increment
            ELSE tr.pre_pitch_strikes
        END AS expected_strikes,
        'Count mismatch' AS validation_error
    FROM pitch_sequence.training_rows tr
    WHERE tr.is_pitch_symbol
        AND (
            tr.post_pitch_balls != CASE 
                WHEN tr.symbol_group IN ('ball', 'intentional_ball', 'awarded_ball') 
                    THEN LEAST(tr.pre_pitch_balls + 1, 4)
                ELSE tr.pre_pitch_balls
            END
            OR
            tr.post_pitch_strikes != CASE 
                WHEN tr.symbol_group IN ('called_strike', 'swinging_strike', 'automatic_strike') 
                    THEN LEAST(tr.pre_pitch_strikes + 1, 3)
                WHEN tr.symbol_group IN ('foul', 'foul_tip', 'foul_bunt') AND tr.pre_pitch_strikes < 2
                    THEN LEAST(tr.pre_pitch_strikes + 1, 3)
                WHEN tr.symbol_group IN ('foul', 'foul_tip', 'foul_bunt') AND tr.pre_pitch_strikes >= 2
                    THEN tr.pre_pitch_strikes
                ELSE tr.pre_pitch_strikes
            END
        )
        AND (p_game_id IS NULL OR tr.game_id = p_game_id)
        AND (p_plate_appearance_id IS NULL OR tr.plate_appearance_id = p_plate_appearance_id)
        AND (p_season IS NULL OR tr.season = p_season);
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION pitch_sequence.validate_transitions IS 
'Validate pitch sequence count transitions and return any errors.
Checks that ball/strike counts increment correctly based on pitch symbols.
Validates foul ball handling with 2 strikes.
Optional filters: game_id, plate_appearance_id, season.';

-- ============================================================================
-- AGGREGATION AND SUMMARY PROCEDURES
-- ============================================================================

-- View: Pitch sequence coverage summary
CREATE OR REPLACE VIEW pitch_sequence.coverage_summary AS
SELECT 
    tr.season,
    COUNT(*) AS total_pitches,
    COUNT(DISTINCT tr.plate_appearance_id) AS total_plate_appearances,
    COUNT(DISTINCT tr.game_id) AS total_games,
    COUNT(*) FILTER (WHERE tr.is_valid_transition) AS valid_pitches,
    COUNT(*) FILTER (WHERE NOT tr.is_valid_transition) AS invalid_pitches,
    ROUND(AVG(tr.pitch_index)::numeric, 2) AS avg_pitches_per_pa,
    COUNT(*) FILTER (WHERE tr.symbol_group = 'unknown_symbol') AS unknown_symbols,
    -- Terminal pitch distribution
    COUNT(*) FILTER (WHERE tr.is_terminal_pitch) AS terminal_pitches,
    COUNT(*) FILTER (WHERE tr.terminal_outcome = 'walk') AS walks,
    COUNT(*) FILTER (WHERE tr.terminal_outcome = 'strikeout') AS strikeouts,
    COUNT(*) FILTER (WHERE tr.terminal_outcome IN ('single', 'double', 'triple', 'home_run')) AS hits,
    COUNT(*) FILTER (WHERE tr.is_ball_in_play AND tr.terminal_outcome = 'out') AS outs_in_play
FROM pitch_sequence.training_rows tr
GROUP BY tr.season
ORDER BY tr.season;

-- View: Symbol frequency distribution
CREATE OR REPLACE VIEW pitch_sequence.symbol_distribution AS
SELECT 
    tr.season,
    tr.raw_symbol,
    tr.symbol_meaning,
    tr.symbol_group,
    COUNT(*) AS frequency,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (PARTITION BY tr.season), 2) AS pct_of_season
FROM pitch_sequence.training_rows tr
WHERE tr.is_pitch_symbol
GROUP BY tr.season, tr.raw_symbol, tr.symbol_meaning, tr.symbol_group
ORDER BY tr.season, frequency DESC;

-- View: Count state distribution (for Markov modeling)
CREATE OR REPLACE VIEW pitch_sequence.count_distribution AS
SELECT 
    tr.season,
    tr.count_label,
    tr.pitch_category,
    COUNT(*) AS frequency,
    COUNT(*) FILTER (WHERE tr.is_terminal_pitch) AS terminal_frequency,
    -- Next pitch distribution
    MODE() WITHIN GROUP (ORDER BY tr.next_pitch_symbol) AS most_common_next_symbol,
    -- Terminal outcome when count ends
    MODE() WITHIN GROUP (ORDER BY tr.terminal_outcome) FILTER (WHERE tr.is_terminal_pitch) AS most_common_terminal_outcome
FROM pitch_sequence.training_rows tr
GROUP BY tr.season, tr.count_label, tr.pitch_category
ORDER BY tr.season, tr.count_label, frequency DESC;

-- ============================================================================
-- REFRESH PROCEDURE
-- ============================================================================

-- Procedure: Refresh all pitch sequence materialized views
CREATE OR REPLACE PROCEDURE pitch_sequence.refresh_all()
LANGUAGE plpgsql
AS $$
BEGIN
    -- Refresh in dependency order
    REFRESH MATERIALIZED VIEW features.pitch_sequence_examples;
    REFRESH MATERIALIZED VIEW pitch_sequence.training_rows;
    
    RAISE NOTICE 'Pitch sequence materialized views refreshed successfully';
END;
$$;

COMMENT ON PROCEDURE pitch_sequence.refresh_all() IS 
'Refresh all pitch sequence materialized views in dependency order.
Should be run after new data is ingested.';

-- Grant permissions
GRANT USAGE ON SCHEMA pitch_sequence TO PUBLIC;
GRANT SELECT ON ALL TABLES IN SCHEMA pitch_sequence TO PUBLIC;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA pitch_sequence TO PUBLIC;
GRANT EXECUTE ON ALL PROCEDURES IN SCHEMA pitch_sequence TO PUBLIC;
