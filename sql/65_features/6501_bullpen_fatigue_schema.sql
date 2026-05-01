-- File: sql/65_features/6501_bullpen_fatigue_schema.sql
-- Purpose: Bullpen fatigue tracking schema for reliever workload monitoring
-- Author: Agent Cascade
-- Date: 2026-04-30
-- Depends On: live.game_events, live.rosters
-- Called By: baseball/features/bullpen_fatigue.py, MonteCarloSimulator

-- Bullpen schema for reliever fatigue tracking
-- Based on sabermetric research on pitch count effects and rest recovery

CREATE SCHEMA IF NOT EXISTS bullpen;

COMMENT ON SCHEMA bullpen IS 
'Reliever workload tracking and fatigue calculation for live game predictions';

-- ============================================================================
-- Core Tables
-- ============================================================================

-- Relief appearances (individual outings)
CREATE TABLE IF NOT EXISTS bullpen.appearances (
    appearance_id BIGSERIAL PRIMARY KEY,
    
    -- Identity
    player_id VARCHAR(50) NOT NULL,
    player_name VARCHAR(100),
    team_id VARCHAR(50) NOT NULL,
    
    -- Game context
    game_id VARCHAR(50) NOT NULL,
    game_date DATE NOT NULL,
    season INTEGER NOT NULL,
    
    -- Workload metrics
    pitches INTEGER NOT NULL DEFAULT 0,
    innings_pitched NUMERIC(3,1) DEFAULT 0.0,
    batters_faced INTEGER DEFAULT 0,
    
    -- Stress indicators
    leverage_index NUMERIC(4,2) DEFAULT 1.0,
    is_high_leverage BOOLEAN GENERATED ALWAYS AS (leverage_index > 1.5) STORED,
    inherited_runners INTEGER DEFAULT 0,
    inherited_scored INTEGER DEFAULT 0,
    
    -- Outcome
    runs_allowed INTEGER DEFAULT 0,
    earned_runs INTEGER DEFAULT 0,
    hits_allowed INTEGER DEFAULT 0,
    walks INTEGER DEFAULT 0,
    strikeouts INTEGER DEFAULT 0,
    home_runs_allowed INTEGER DEFAULT 0,
    
    -- Result
    decision VARCHAR(10),  -- W, L, S, H, BS, ND
    game_result VARCHAR(20),  -- win, loss, no_decision
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE bullpen.appearances IS
'Individual relief appearances with workload and stress metrics';

CREATE INDEX idx_appearances_player ON bullpen.appearances (player_id, game_date DESC);
CREATE INDEX idx_appearances_team ON bullpen.appearances (team_id, game_date DESC);
CREATE INDEX idx_appearances_high_leverage ON bullpen.appearances (player_id, game_date) 
    WHERE is_high_leverage = true;

-- Reliever workload summary (rolling window aggregations)
CREATE TABLE IF NOT EXISTS bullpen.reliever_workloads (
    workload_id BIGSERIAL PRIMARY KEY,
    
    -- Identity
    player_id VARCHAR(50) NOT NULL,
    team_id VARCHAR(50) NOT NULL,
    as_of_date DATE NOT NULL,
    
    -- Rolling workload windows
    appearances_last_7 INTEGER DEFAULT 0,
    appearances_last_15 INTEGER DEFAULT 0,
    appearances_last_30 INTEGER DEFAULT 0,
    
    pitches_last_1 INTEGER DEFAULT 0,  -- Yesterday
    pitches_last_3 INTEGER DEFAULT 0,  -- Last 3 days
    pitches_last_7 INTEGER DEFAULT 0,  -- Last week
    pitches_last_15 INTEGER DEFAULT 0, -- Last 2 weeks
    pitches_last_30 INTEGER DEFAULT 0, -- Last month
    
    -- High leverage tracking
    high_leverage_last_7 INTEGER DEFAULT 0,
    high_leverage_last_15 INTEGER DEFAULT 0,
    high_leverage_last_30 INTEGER DEFAULT 0,
    
    -- Rest status
    days_since_last_appearance INTEGER DEFAULT 10,  -- 10 = well rested
    consecutive_days_pitched INTEGER DEFAULT 0,
    
    -- Season totals for context
    season_appearances INTEGER DEFAULT 0,
    season_pitches INTEGER DEFAULT 0,
    season_high_leverage INTEGER DEFAULT 0,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE (player_id, as_of_date)
);

COMMENT ON TABLE bullpen.reliever_workloads IS
'Pre-computed rolling workload aggregations for fatigue calculation';

CREATE INDEX idx_workloads_player_date ON bullpen.reliever_workloads (player_id, as_of_date DESC);
CREATE INDEX idx_workloads_team_date ON bullpen.reliever_workloads (team_id, as_of_date DESC);

-- Daily fatigue scores (computed from workloads)
CREATE TABLE IF NOT EXISTS bullpen.daily_fatigue (
    fatigue_id BIGSERIAL PRIMARY KEY,
    
    -- Identity
    player_id VARCHAR(50) NOT NULL,
    team_id VARCHAR(50) NOT NULL,
    calculation_date DATE NOT NULL,
    
    -- Fatigue components (0-1 scale)
    rest_factor NUMERIC(3,2) DEFAULT 0.0,      -- Based on days since last appearance
    pitch_accumulation_factor NUMERIC(3,2) DEFAULT 0.0,  -- Based on recent pitch counts
    stress_factor NUMERIC(3,2) DEFAULT 0.0,    -- Based on high leverage outings
    
    -- Combined fatigue score
    fatigue_score NUMERIC(3,2) DEFAULT 0.0,    -- 0=fresh, 1=exhausted
    
    -- Performance projections
    velocity_projection NUMERIC(4,3) DEFAULT 1.0,    -- Multiplier (1.0 = normal)
    command_projection NUMERIC(4,3) DEFAULT 1.0,     -- Multiplier (1.0 = normal)
    performance_multiplier NUMERIC(4,3) DEFAULT 1.0, -- Combined projection
    
    -- Status
    availability_status VARCHAR(20) DEFAULT 'available',  -- available, tired, exhausted, injured
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE (player_id, calculation_date)
);

COMMENT ON TABLE bullpen.daily_fatigue IS
'Computed fatigue scores with performance projections';

CREATE INDEX idx_fatigue_player_date ON bullpen.daily_fatigue (player_id, calculation_date DESC);
CREATE INDEX idx_fatigue_team_date ON bullpen.daily_fatigue (team_id, calculation_date DESC);
CREATE INDEX idx_fatigue_available ON bullpen.daily_fatigue (team_id, calculation_date) 
    WHERE availability_status = 'available';

-- Team bullpen status (aggregate view)
CREATE TABLE IF NOT EXISTS bullpen.team_status (
    status_id BIGSERIAL PRIMARY KEY,
    
    team_id VARCHAR(50) NOT NULL,
    calculation_date DATE NOT NULL,
    
    -- Aggregate metrics
    total_relief_pitches INTEGER DEFAULT 0,
    avg_team_fatigue NUMERIC(3,2) DEFAULT 0.0,
    
    -- Availability counts
    available_pitchers INTEGER DEFAULT 0,
    tired_pitchers INTEGER DEFAULT 0,
    exhausted_pitchers INTEGER DEFAULT 0,
    unavailable_pitchers INTEGER DEFAULT 0,
    
    -- Workload distribution
    most_used_last_3 VARCHAR(50),     -- Player ID of most used reliever
    pitches_most_used INTEGER DEFAULT 0,
    
    -- Concern flags
    overworked_flag BOOLEAN DEFAULT FALSE,  -- 3+ high fatigue relievers
    short_bullpen_flag BOOLEAN DEFAULT FALSE,  -- <3 available relievers
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE (team_id, calculation_date)
);

COMMENT ON TABLE bullpen.team_status IS
'Team-level bullpen status for game planning';

CREATE INDEX idx_team_status_date ON bullpen.team_status (team_id, calculation_date DESC);

-- ============================================================================
-- Functions
-- ============================================================================

-- Calculate fatigue score from workload components
CREATE OR REPLACE FUNCTION bullpen.calculate_fatigue_score(
    days_rest INTEGER,
    pitches_last_3 INTEGER,
    high_leverage_count INTEGER
)
RETURNS NUMERIC AS $$
DECLARE
    rest_component NUMERIC;
    pitch_component NUMERIC;
    stress_component NUMERIC;
BEGIN
    -- Rest factor (primary)
    CASE days_rest
        WHEN 0 THEN rest_component := 0.6;
        WHEN 1 THEN rest_component := 0.4;
        WHEN 2 THEN rest_component := 0.2;
        ELSE rest_component := 0.0;
    END CASE;
    
    -- Pitch accumulation (60+ pitches in 3 days = significant)
    pitch_component := LEAST(0.3, pitches_last_3 / 200.0);
    
    -- Stress factor (high leverage outings)
    stress_component := LEAST(0.2, high_leverage_count * 0.05);
    
    -- Combined score (capped at 1.0)
    RETURN LEAST(1.0, rest_component + pitch_component + stress_component);
END;
$$ LANGUAGE plpgsql IMMUTABLE;

COMMENT ON FUNCTION bullpen.calculate_fatigue_score IS
'Calculate fatigue score (0-1) from workload components';

-- Get reliever status for a specific date
CREATE OR REPLACE FUNCTION bullpen.get_reliever_status(
    p_player_id VARCHAR(50),
    p_date DATE
)
RETURNS TABLE (
    player_id VARCHAR(50),
    team_id VARCHAR(50),
    fatigue_score NUMERIC,
    velocity_projection NUMERIC,
    command_projection NUMERIC,
    performance_multiplier NUMERIC,
    availability_status VARCHAR(20),
    days_rest INTEGER,
    pitches_last_3 INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        df.player_id,
        df.team_id,
        df.fatigue_score,
        df.velocity_projection,
        df.command_projection,
        df.performance_multiplier,
        df.availability_status,
        rw.days_since_last_appearance,
        rw.pitches_last_3
    FROM bullpen.daily_fatigue df
    LEFT JOIN bullpen.reliever_workloads rw 
        ON df.player_id = rw.player_id 
        AND df.calculation_date = rw.as_of_date
    WHERE df.player_id = p_player_id
    AND df.calculation_date = p_date;
END;
$$ LANGUAGE plpgsql STABLE;

COMMENT ON FUNCTION bullpen.get_reliever_status IS
'Get complete fatigue status for a reliever on a specific date';

-- Update daily fatigue for all relievers
CREATE OR REPLACE FUNCTION bullpen.update_daily_fatigue(
    p_date DATE DEFAULT CURRENT_DATE
)
RETURNS INTEGER AS $$
DECLARE
    v_count INTEGER := 0;
BEGIN
    -- Insert or update fatigue records for all relievers
    INSERT INTO bullpen.daily_fatigue (
        player_id, team_id, calculation_date,
        rest_factor, pitch_accumulation_factor, stress_factor,
        fatigue_score, velocity_projection, command_projection, 
        performance_multiplier, availability_status
    )
    SELECT 
        rw.player_id,
        rw.team_id,
        p_date,
        -- Rest factor
        CASE 
            WHEN rw.days_since_last_appearance = 0 THEN 0.6
            WHEN rw.days_since_last_appearance = 1 THEN 0.4
            WHEN rw.days_since_last_appearance = 2 THEN 0.2
            ELSE 0.0
        END,
        -- Pitch accumulation factor
        LEAST(0.3, rw.pitches_last_3 / 200.0),
        -- Stress factor
        LEAST(0.2, rw.high_leverage_last_7 * 0.05),
        -- Fatigue score (calculated via function)
        bullpen.calculate_fatigue_score(
            rw.days_since_last_appearance,
            rw.pitches_last_3,
            rw.high_leverage_last_7
        ),
        -- Performance projections
        1.0 - (bullpen.calculate_fatigue_score(
            rw.days_since_last_appearance,
            rw.pitches_last_3,
            rw.high_leverage_last_7
        ) * 0.5),  -- Velocity projection
        1.0 - (bullpen.calculate_fatigue_score(
            rw.days_since_last_appearance,
            rw.pitches_last_3,
            rw.high_leverage_last_7
        ) * 0.3),  -- Command projection
        -- Performance multiplier
        (1.0 - (bullpen.calculate_fatigue_score(
            rw.days_since_last_appearance,
            rw.pitches_last_3,
            rw.high_leverage_last_7
        ) * 0.5)) * 0.4 + 
        (1.0 - (bullpen.calculate_fatigue_score(
            rw.days_since_last_appearance,
            rw.pitches_last_3,
            rw.high_leverage_last_7
        ) * 0.3)) * 0.6,
        -- Availability status
        CASE 
            WHEN bullpen.calculate_fatigue_score(
                rw.days_since_last_appearance,
                rw.pitches_last_3,
                rw.high_leverage_last_7
            ) > 0.8 THEN 'exhausted'
            WHEN bullpen.calculate_fatigue_score(
                rw.days_since_last_appearance,
                rw.pitches_last_3,
                rw.high_leverage_last_7
            ) > 0.5 THEN 'tired'
            ELSE 'available'
        END
    FROM bullpen.reliever_workloads rw
    WHERE rw.as_of_date = p_date
    ON CONFLICT (player_id, calculation_date) 
    DO UPDATE SET
        rest_factor = EXCLUDED.rest_factor,
        pitch_accumulation_factor = EXCLUDED.pitch_accumulation_factor,
        stress_factor = EXCLUDED.stress_factor,
        fatigue_score = EXCLUDED.fatigue_score,
        velocity_projection = EXCLUDED.velocity_projection,
        command_projection = EXCLUDED.command_projection,
        performance_multiplier = EXCLUDED.performance_multiplier,
        availability_status = EXCLUDED.availability_status,
        updated_at = NOW();
    
    GET DIAGNOSTICS v_count = ROW_COUNT;
    RETURN v_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION bullpen.update_daily_fatigue IS
'Batch update fatigue scores for all relievers on a given date';

-- Get team bullpen status
CREATE OR REPLACE FUNCTION bullpen.get_team_bullpen_status(
    p_team_id VARCHAR(50),
    p_date DATE
)
RETURNS TABLE (
    team_id VARCHAR(50),
    calculation_date DATE,
    available_count INTEGER,
    tired_count INTEGER,
    exhausted_count INTEGER,
    avg_fatigue NUMERIC,
    warm_body_count INTEGER  -- Available + tired (usable pitchers)
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        df.team_id,
        p_date,
        COUNT(*) FILTER (WHERE df.availability_status = 'available')::INTEGER,
        COUNT(*) FILTER (WHERE df.availability_status = 'tired')::INTEGER,
        COUNT(*) FILTER (WHERE df.availability_status = 'exhausted')::INTEGER,
        AVG(df.fatigue_score),
        COUNT(*) FILTER (WHERE df.availability_status IN ('available', 'tired'))::INTEGER
    FROM bullpen.daily_fatigue df
    WHERE df.team_id = p_team_id
    AND df.calculation_date = p_date
    GROUP BY df.team_id;
END;
$$ LANGUAGE plpgsql STABLE;

COMMENT ON FUNCTION bullpen.get_team_bullpen_status IS
'Get aggregate bullpen status for a team';

-- ============================================================================
-- Views
-- ============================================================================

-- Current fatigue view (most recent for each reliever)
CREATE OR REPLACE VIEW bullpen.current_fatigue AS
SELECT DISTINCT ON (player_id)
    df.*,
    rw.appearances_last_7,
    rw.pitches_last_7,
    rw.high_leverage_last_7
FROM bullpen.daily_fatigue df
LEFT JOIN bullpen.reliever_workloads rw 
    ON df.player_id = rw.player_id 
    AND df.calculation_date = rw.as_of_date
ORDER BY player_id, calculation_date DESC;

COMMENT ON VIEW bullpen.current_fatigue IS
'Latest fatigue status for all relievers';

-- High fatigue alerts (relievers to avoid)
CREATE OR REPLACE VIEW bullpen.fatigue_alerts AS
SELECT 
    df.player_id,
    df.player_name,
    df.team_id,
    df.fatigue_score,
    df.availability_status,
    df.pitches_last_3,
    df.days_since_last_appearance,
    df.calculation_date,
    CASE 
        WHEN df.fatigue_score > 0.8 THEN 'CRITICAL: Do not use'
        WHEN df.fatigue_score > 0.6 THEN 'WARNING: High fatigue'
        WHEN df.fatigue_score > 0.4 THEN 'CAUTION: Moderate fatigue'
        ELSE 'OK'
    END as alert_level
FROM bullpen.current_fatigue df
WHERE df.fatigue_score > 0.4  -- Only show concerning fatigue levels
ORDER BY df.fatigue_score DESC;

COMMENT ON VIEW bullpen.fatigue_alerts IS
'Relievers with elevated fatigue for game planning';

-- ============================================================================
-- Triggers
-- ============================================================================

-- Auto-update reliever workloads when new appearances are added
CREATE OR REPLACE FUNCTION bullpen.update_workloads_on_appearance()
RETURNS TRIGGER AS $$
BEGIN
    -- Update or insert workload record for the player
    INSERT INTO bullpen.reliever_workloads (
        player_id, team_id, as_of_date,
        appearances_last_7, pitches_last_7,
        high_leverage_last_7, days_since_last_appearance
    )
    SELECT 
        NEW.player_id,
        NEW.team_id,
        NEW.game_date,
        COUNT(*) FILTER (WHERE a.game_date BETWEEN NEW.game_date - 7 AND NEW.game_date),
        COALESCE(SUM(a.pitches) FILTER (WHERE a.game_date BETWEEN NEW.game_date - 7 AND NEW.game_date), 0),
        COUNT(*) FILTER (WHERE a.is_high_leverage AND a.game_date BETWEEN NEW.game_date - 7 AND NEW.game_date),
        NEW.game_date - MAX(a_prev.game_date)
    FROM bullpen.appearances a
    LEFT JOIN bullpen.appearances a_prev 
        ON a_prev.player_id = NEW.player_id 
        AND a_prev.game_date < NEW.game_date
    WHERE a.player_id = NEW.player_id
    AND a.game_date <= NEW.game_date
    ON CONFLICT (player_id, as_of_date) DO UPDATE SET
        appearances_last_7 = EXCLUDED.appearances_last_7,
        pitches_last_7 = EXCLUDED.pitches_last_7,
        high_leverage_last_7 = EXCLUDED.high_leverage_last_7,
        days_since_last_appearance = EXCLUDED.days_since_last_appearance,
        updated_at = NOW();
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_update_workloads
    AFTER INSERT ON bullpen.appearances
    FOR EACH ROW
    EXECUTE FUNCTION bullpen.update_workloads_on_appearance();

COMMENT ON FUNCTION bullpen.update_workloads_on_appearance IS
'Auto-update workload aggregations when new appearances are recorded';
