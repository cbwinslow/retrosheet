-- File: sql/70_betting/7001_betting_schema.sql
-- Purpose: Betting analysis schema for AI-powered betting strategy
-- Author: Agent Cascade
-- Date: 2026-04-30
-- Depends On: 6001_models_registry.sql, 6010_simulation_schema.sql
-- Called By: baseball bet CLI commands, betting analyzer

-- Betting schema for tracking opportunities, placed bets, and line movements

CREATE SCHEMA IF NOT EXISTS betting;

COMMENT ON SCHEMA betting IS 
'AI-powered betting analysis, opportunity tracking, and line movement detection';

-- ============================================================================
-- Core Tables
-- ============================================================================

-- Betting strategies (AI-generated or user-defined)
CREATE TABLE IF NOT EXISTS betting.strategies (
    strategy_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    created_by VARCHAR(20) DEFAULT 'ai', -- 'ai' or 'user'
    
    -- Strategy parameters
    min_edge NUMERIC(5,4) DEFAULT 0.03,
    min_confidence NUMERIC(5,4) DEFAULT 0.6,
    max_bet_size_percent NUMERIC(5,2) DEFAULT 5.0,  -- Max % of bankroll per bet
    allowed_markets TEXT[] DEFAULT ARRAY['moneyline', 'total'],
    
    -- AI-generated logic (natural language rules)
    selection_criteria TEXT,
    stake_sizing_logic TEXT,
    correlation_rules TEXT,
    
    -- Performance tracking (updated by trigger on bet settlement)
    total_bets INTEGER DEFAULT 0,
    wins INTEGER DEFAULT 0,
    losses INTEGER DEFAULT 0,
    pushes INTEGER DEFAULT 0,
    roi_percent NUMERIC(10,4) DEFAULT 0,
    
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE betting.strategies IS
'Betting strategies with AI-generated rules and performance tracking';

CREATE INDEX idx_strategies_active ON betting.strategies (is_active) 
    WHERE is_active = true;

-- ============================================================================
-- Market Odds Tracking (for line movement detection)
-- ============================================================================

-- Market odds history (tracks opening/current odds across books)
CREATE TABLE IF NOT EXISTS betting.market_odds (
    odds_id BIGSERIAL PRIMARY KEY,
    
    game_id VARCHAR(50) NOT NULL,
    season INTEGER,
    game_date DATE,
    
    -- Market identification
    book VARCHAR(50) NOT NULL,  -- e.g., 'draftkings', 'fanduel', 'pinnacle'
    market_type VARCHAR(50) NOT NULL,  -- moneyline, spread, total, team_total
    
    -- Odds
    odds INTEGER NOT NULL,  -- American odds (+150, -110)
    line NUMERIC(6,2),      -- Spread or total line (e.g., -1.5, 8.5)
    
    -- Line movement tracking
    odds_open INTEGER,      -- Opening odds
    line_open NUMERIC(6,2), -- Opening line
    
    -- Timestamps
    recorded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_opening BOOLEAN DEFAULT FALSE,  -- True if this is the opening line
    
    -- Metadata
    source VARCHAR(50),     -- API source (odds_api, scraping, manual)
    raw_data JSONB          -- Raw response for debugging
);

COMMENT ON TABLE betting.market_odds IS
'Historical odds tracking for line movement analysis and sharp money detection';

CREATE INDEX idx_market_odds_game ON betting.market_odds (game_id, market_type);
CREATE INDEX idx_market_odds_book ON betting.market_odds (book, recorded_at DESC);
CREATE INDEX idx_market_odds_opening ON betting.market_odds (game_id, market_type, book) 
    WHERE is_opening = true;

-- Line movement summary view (for quick lookup)
CREATE OR REPLACE VIEW betting.line_movements AS
WITH opening_lines AS (
    SELECT 
        game_id,
        book,
        market_type,
        odds as open_odds,
        line as open_line,
        recorded_at as opened_at
    FROM betting.market_odds
    WHERE is_opening = true
),
current_lines AS (
    SELECT DISTINCT ON (game_id, book, market_type)
        game_id,
        book,
        market_type,
        odds as current_odds,
        line as current_line,
        recorded_at as updated_at
    FROM betting.market_odds
    WHERE is_opening = false
    ORDER BY game_id, book, market_type, recorded_at DESC
)
SELECT 
    c.game_id,
    c.book,
    c.market_type,
    o.open_odds,
    c.current_odds,
    o.open_line,
    c.current_line,
    c.current_odds - o.open_odds as odds_movement,
    COALESCE(c.current_line, 0) - COALESCE(o.open_line, 0) as line_movement,
    o.opened_at,
    c.updated_at,
    -- Sharp money indicators
    CASE 
        WHEN c.current_odds > o.open_odds AND o.open_odds < 0 THEN 'reverse_favorite'  -- Dog getting bigger
        WHEN c.current_odds < o.open_odds AND o.open_odds > 0 THEN 'reverse_underdog' -- Favorite getting bigger  
        ELSE 'natural'
    END as movement_type,
    -- Steam detection (large movement)
    ABS(c.current_odds - o.open_odds) >= 20 as is_steam
FROM current_lines c
LEFT JOIN opening_lines o ON 
    c.game_id = o.game_id AND 
    c.book = o.book AND 
    c.market_type = o.market_type;

COMMENT ON VIEW betting.line_movements IS
'Line movement summary showing opening vs current odds for steam detection';

-- ============================================================================
-- Betting Opportunities (identified edges)
-- ============================================================================

CREATE TABLE IF NOT EXISTS betting.opportunities (
    opportunity_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    strategy_id INTEGER REFERENCES betting.strategies(strategy_id),
    
    game_id VARCHAR(50) NOT NULL,
    season INTEGER,
    game_date DATE,
    
    -- Market info
    book VARCHAR(50) NOT NULL,
    market_type VARCHAR(50) NOT NULL,
    odds INTEGER NOT NULL,
    line NUMERIC(6,2),
    
    -- Our analysis (from Monte Carlo simulation)
    our_probability NUMERIC(5,4),      -- Model win probability
    implied_probability NUMERIC(5,4),  -- From odds (e.g., -110 = 52.4%)
    edge NUMERIC(5,4),               -- our_prob - implied_prob
    expected_value NUMERIC(10,4),    -- EV per $100 wagered
    kelly_fraction NUMERIC(5,4),     -- Kelly criterion fraction
    confidence_score NUMERIC(5,4),   -- 0-1 model confidence
    
    -- Weather and context
    temperature_f NUMERIC(5,2),
    wind_speed_mph NUMERIC(5,2),
    home_bullpen_fatigue NUMERIC(3,2),
    away_bullpen_fatigue NUMERIC(3,2),
    
    -- Recommendation
    recommendation VARCHAR(20) CHECK (recommendation IN ('strong_buy', 'buy', 'neutral', 'avoid')),
    
    -- AI explanation
    ai_explanation TEXT,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    market_timestamp TIMESTAMP WITH TIME ZONE,  -- When odds were observed
    
    -- Result tracking (filled when bet is placed and settled)
    bet_placed BOOLEAN DEFAULT FALSE,
    bet_id UUID  -- References betting.bets
);

COMMENT ON TABLE betting.opportunities IS
'Identified betting opportunities with edge calculations and AI explanations';

CREATE INDEX idx_opportunities_game ON betting.opportunities (game_id);
CREATE INDEX idx_opportunities_strategy ON betting.opportunities (strategy_id);
CREATE INDEX idx_opportunities_recommendation ON betting.opportunities (recommendation);
CREATE INDEX idx_opportunities_edge ON betting.opportunities (edge) WHERE edge > 0;

-- ============================================================================
-- Placed Bets
-- ============================================================================

CREATE TABLE IF NOT EXISTS betting.bets (
    bet_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    opportunity_id UUID REFERENCES betting.opportunities(opportunity_id),
    
    -- Placement details
    stake NUMERIC(12,2) NOT NULL,
    book VARCHAR(50) NOT NULL,
    placed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    placed_by VARCHAR(50) DEFAULT 'system',  -- system, user, auto
    
    -- Copy of market info at placement (for record keeping)
    odds_at_placement INTEGER,
    line_at_placement NUMERIC(6,2),
    
    -- Outcome (filled later)
    outcome VARCHAR(20) CHECK (outcome IN ('win', 'loss', 'push', 'pending', 'void')),
    profit_loss NUMERIC(12,2),
    settled_at TIMESTAMP WITH TIME ZONE,
    
    -- Settlement source
    settled_by VARCHAR(50),
    settlement_source VARCHAR(50),  -- api, manual, feed
    
    -- Tracking
    notes TEXT
);

COMMENT ON TABLE betting.bets IS
'Record of placed bets with outcome tracking for ROI calculation';

CREATE INDEX idx_bets_outcome ON betting.bets (outcome);
CREATE INDEX idx_bets_placed ON betting.bets (placed_at DESC);
CREATE INDEX idx_bets_opportunity ON betting.bets (opportunity_id);

-- ============================================================================
-- Strategy Backtest Results
-- ============================================================================

CREATE TABLE IF NOT EXISTS betting.backtest_results (
    backtest_id SERIAL PRIMARY KEY,
    strategy_id INTEGER REFERENCES betting.strategies(strategy_id),
    
    backtest_period VARCHAR(50),  -- e.g., '2024-season', 'last-30-days'
    start_date DATE,
    end_date DATE,
    
    initial_bankroll NUMERIC(12,2),
    final_bankroll NUMERIC(12,2),
    
    total_bets INTEGER,
    win_rate NUMERIC(5,4),
    roi_percent NUMERIC(10,4),
    
    -- Risk metrics
    max_drawdown_percent NUMERIC(5,2),
    sharpe_ratio NUMERIC(10,4),
    
    -- AI-generated insights
    ai_summary TEXT,
    recommended_adjustments TEXT[],
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE betting.backtest_results IS
'Historical backtest results for strategy validation with AI insights';

-- ============================================================================
-- Functions
-- ============================================================================

-- Function to calculate implied probability from American odds
CREATE OR REPLACE FUNCTION betting.american_to_implied_prob(odds INTEGER)
RETURNS NUMERIC AS $$
BEGIN
    IF odds > 0 THEN
        -- Positive odds: risk $100 to win $odds
        RETURN 100.0 / (100.0 + odds);
    ELSIF odds < 0 THEN
        -- Negative odds: risk $abs(odds) to win $100
        RETURN ABS(odds) / (ABS(odds) + 100.0);
    ELSE
        RETURN 0.5;  -- Even money
    END IF;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

COMMENT ON FUNCTION betting.american_to_implied_prob IS
'Convert American odds to implied probability (vig-free)';

-- Function to calculate expected value
CREATE OR REPLACE FUNCTION betting.calculate_ev(
    our_prob NUMERIC,
    odds INTEGER,
    stake NUMERIC DEFAULT 100
)
RETURNS NUMERIC AS $$
DECLARE
    implied_prob NUMERIC;
    decimal_odds NUMERIC;
    win_amount NUMERIC;
BEGIN
    implied_prob := betting.american_to_implied_prob(odds);
    
    -- Convert American to decimal odds
    IF odds > 0 THEN
        decimal_odds := 1 + (odds / 100.0);
    ELSE
        decimal_odds := 1 + (100.0 / ABS(odds));
    END IF;
    
    -- EV = (prob_win * win_amount) - (prob_loss * stake)
    win_amount := stake * (decimal_odds - 1);
    RETURN (our_prob * win_amount) - ((1 - our_prob) * stake);
END;
$$ LANGUAGE plpgsql IMMUTABLE;

COMMENT ON FUNCTION betting.calculate_ev IS
'Calculate expected value given our probability and market odds';

-- Function to update strategy performance after bet settlement
CREATE OR REPLACE FUNCTION betting.update_strategy_stats()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.outcome IS NOT NULL AND OLD.outcome IS NULL THEN
        -- Update strategy stats
        UPDATE betting.strategies s
        SET 
            total_bets = total_bets + 1,
            wins = wins + CASE WHEN NEW.outcome = 'win' THEN 1 ELSE 0 END,
            losses = losses + CASE WHEN NEW.outcome = 'loss' THEN 1 ELSE 0 END,
            pushes = pushes + CASE WHEN NEW.outcome = 'push' THEN 1 ELSE 0 END,
            roi_percent = (
                SELECT COALESCE(SUM(profit_loss), 0) / NULLIF(SUM(stake), 0) * 100
                FROM betting.bets b
                JOIN betting.opportunities o ON b.opportunity_id = o.opportunity_id
                WHERE o.strategy_id = s.strategy_id
                AND b.outcome IS NOT NULL
            ),
            updated_at = NOW()
        FROM betting.opportunities o
        WHERE s.strategy_id = o.strategy_id
        AND o.opportunity_id = NEW.opportunity_id;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_update_strategy_stats
    AFTER UPDATE OF outcome ON betting.bets
    FOR EACH ROW
    EXECUTE FUNCTION betting.update_strategy_stats();

COMMENT ON FUNCTION betting.update_strategy_stats IS
'Trigger function to update strategy ROI when bets are settled';

-- ============================================================================
-- Sharp Money Detection View
-- ============================================================================

CREATE OR REPLACE VIEW betting.sharp_opportunities AS
WITH line_moves AS (
    SELECT 
        game_id,
        market_type,
        COUNT(DISTINCT book) as num_books,
        AVG(ABS(odds_movement)) as avg_movement,
        MAX(odds_movement) as max_movement,
        -- Detect reverse line movement
        BOOL_OR(movement_type IN ('reverse_favorite', 'reverse_underdog')) as has_reverse_line
    FROM betting.line_movements
    WHERE is_steam = true
    GROUP BY game_id, market_type
)
SELECT 
    o.opportunity_id,
    o.game_id,
    o.book,
    o.market_type,
    o.odds,
    o.our_probability,
    o.implied_probability,
    o.edge,
    o.recommendation,
    o.ai_explanation,
    lm.has_reverse_line as sharp_money_detected,
    lm.avg_movement as avg_line_move,
    o.created_at
FROM betting.opportunities o
LEFT JOIN line_moves lm ON o.game_id = lm.game_id AND o.market_type = lm.market_type
WHERE o.edge > 0.05  -- Significant edge
AND (lm.has_reverse_line OR lm.avg_movement > 15)  -- Sharp activity or big move
ORDER BY o.edge DESC;

COMMENT ON VIEW betting.sharp_opportunities IS
'Opportunities with detected sharp money or significant line movement';
