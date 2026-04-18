-- ============================================================================
-- Model Edge Comparison Views
-- ============================================================================
-- Analysis views joining model outputs to market prices for edge detection
--
-- Purpose: Enable research comparison between model predictions and market prices
-- This is a research tooling layer, not financial advice.
--
-- Views:
-- - market.model_market_join: Join model predictions with market prices
-- - market.edge_calculations: Calculate model edge vs market
-- - market.edge_summaries: Aggregated edge statistics
-- - market.edge_tracking: Track edges over time
-- ============================================================================

-- Join model predictions with market prices
CREATE OR REPLACE VIEW market.model_market_join AS
SELECT
    m.game_id,
    m.plate_appearance_id,
    m.model_id,
    m.model_name,
    m.model_version,
    m.predicted_outcome,
    m.class_probabilities,
    m.derived_probabilities,
    mp.market_id,
    mp.provider,
    mp.outcome_name,
    mp.price AS market_price,
    mp.implied_probability AS market_implied_probability,
    mp.timestamp AS market_timestamp,
    m.created_at AS prediction_timestamp,
    -- Calculate edge (model probability - market implied probability)
    (m.class_probabilities->>mp.outcome_name::text)::NUMERIC - mp.implied_probability AS model_edge
FROM predictions.live_pa_predictions m
INNER JOIN market.market_identifiers mi
    ON m.game_id = mi.event_id
    AND mi.event_type = 'mlb_game'
INNER JOIN market.market_prices mp
    ON mi.provider_market_id = mp.market_id
    AND mi.provider_outcome_id = mp.outcome_id
WHERE mp.timestamp >= m.created_at - INTERVAL '1 hour'
  AND mp.timestamp <= m.created_at + INTERVAL '1 hour';

COMMENT ON VIEW market.model_market_join IS 'Join model predictions with market prices within 1-hour window';

-- Edge calculations with thresholds
CREATE OR REPLACE VIEW market.edge_calculations AS
SELECT
    game_id,
    plate_appearance_id,
    model_id,
    model_name,
    model_version,
    outcome_name,
    provider,
    model_edge,
    market_price,
    market_implied_probability,
    model_probability,
    -- Edge categorization
    CASE
        WHEN ABS(model_edge) >= 0.10 THEN 'large'
        WHEN ABS(model_edge) >= 0.05 THEN 'medium'
        WHEN ABS(model_edge) >= 0.02 THEN 'small'
        ELSE 'negligible'
    END AS edge_category,
    -- Edge direction
    CASE
        WHEN model_edge > 0 THEN 'model_over_market'
        WHEN model_edge < 0 THEN 'market_over_model'
        ELSE 'no_edge'
    END AS edge_direction,
    -- Kelly Criterion sizing (simplified, assumes even-money bet)
    CASE
        WHEN model_edge > 0 THEN (model_edge / market_implied_probability)
        ELSE 0
    END AS kelly_fraction,
    market_timestamp,
    prediction_timestamp
FROM (
    SELECT
        mj.*,
        (mj.class_probabilities->>mj.outcome_name::text)::NUMERIC AS model_probability
    FROM market.model_market_join mj
) sub;

COMMENT ON VIEW market.edge_calculations IS 'Calculate model edge vs market with categorization and Kelly sizing';

-- Edge summaries by model and market
CREATE OR REPLACE VIEW market.edge_summaries AS
SELECT
    model_id,
    model_name,
    model_version,
    provider,
    outcome_name,
    COUNT(*) AS total_predictions,
    AVG(model_edge) AS avg_edge,
    STDDEV(model_edge) AS stddev_edge,
    MIN(model_edge) AS min_edge,
    MAX(model_edge) AS max_edge,
    SUM(CASE WHEN ABS(model_edge) >= 0.10 THEN 1 ELSE 0 END) AS large_edge_count,
    SUM(CASE WHEN ABS(model_edge) >= 0.05 THEN 1 ELSE 0 END) AS medium_edge_count,
    SUM(CASE WHEN ABS(model_edge) >= 0.02 THEN 1 ELSE 0 END) AS small_edge_count,
    AVG(kelly_fraction) AS avg_kelly_fraction,
    MAX(market_timestamp) AS latest_market_timestamp
FROM market.edge_calculations
GROUP BY model_id, model_name, model_version, provider, outcome_name;

COMMENT ON VIEW market.edge_summaries IS 'Aggregated edge statistics by model and market provider';

-- Track edges over time
CREATE OR REPLACE VIEW market.edge_tracking AS
SELECT
    DATE_TRUNC('day', market_timestamp) AS edge_date,
    model_id,
    model_name,
    provider,
    outcome_name,
    COUNT(*) AS daily_predictions,
    AVG(model_edge) AS daily_avg_edge,
    AVG(kelly_fraction) AS daily_avg_kelly,
    SUM(CASE WHEN model_edge > 0 THEN 1 ELSE 0 END) AS positive_edge_count,
    SUM(CASE WHEN model_edge < 0 THEN 1 ELSE 0 END) AS negative_edge_count,
    MAX(market_timestamp) AS latest_timestamp
FROM market.edge_calculations
GROUP BY DATE_TRUNC('day', market_timestamp), model_id, model_name, provider, outcome_name
ORDER BY edge_date DESC, model_id, provider;

COMMENT ON VIEW market.edge_tracking IS 'Track edge statistics over time by model and market';

-- Model-implied odds calculation
CREATE OR REPLACE FUNCTION market.calculate_model_implied_odds(
    p_model_id INTEGER,
    p_outcome_name TEXT
)
RETURNS TABLE (
    outcome_name TEXT,
    model_probability NUMERIC,
    model_implied_odds NUMERIC,
    model_implied_price NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        key AS outcome_name,
        value::NUMERIC AS model_probability,
        CASE
            WHEN value::NUMERIC > 0 THEN 1 / value::NUMERIC
            ELSE NULL
        END AS model_implied_odds,
        CASE
            WHEN value::NUMERIC > 0 THEN (1 / value::NUMERIC) * 100
            ELSE NULL
        END AS model_implied_price
    FROM (
        SELECT
            jsonb_each_text(class_probabilities) AS (key, value)
        FROM predictions.live_pa_predictions
        WHERE model_id = p_model_id
        LIMIT 1
    ) sub
    WHERE key = p_outcome_name OR p_outcome_name IS NULL;
END;
$$ LANGUAGE plpgsql STABLE;

COMMENT ON FUNCTION market.calculate_model_implied_odds IS 'Calculate model-implied odds from probability outputs';

-- Edge detection threshold view
CREATE OR REPLACE VIEW market.edge_alerts AS
SELECT
    game_id,
    plate_appearance_id,
    model_id,
    model_name,
    outcome_name,
    provider,
    model_edge,
    edge_category,
    edge_direction,
    kelly_fraction,
    market_timestamp,
    prediction_timestamp,
    -- Alert priority based on edge size and Kelly fraction
    CASE
        WHEN ABS(model_edge) >= 0.10 AND kelly_fraction > 0.05 THEN 'high'
        WHEN ABS(model_edge) >= 0.05 AND kelly_fraction > 0.02 THEN 'medium'
        WHEN ABS(model_edge) >= 0.02 THEN 'low'
        ELSE 'none'
    END AS alert_priority
FROM market.edge_calculations
WHERE ABS(model_edge) >= 0.02  -- Only include edges above minimum threshold
ORDER BY ABS(model_edge) DESC, kelly_fraction DESC;

COMMENT ON VIEW market.edge_alerts IS 'Edge detection alerts prioritized by edge size and Kelly fraction';
