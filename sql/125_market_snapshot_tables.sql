-- ============================================================================
-- Market Snapshot Tables
-- ============================================================================
-- Schema for storing and normalizing market data from prediction markets
-- (Polymarket, Kalshi, sportsbooks, etc.)
--
-- Purpose: Enable model edge comparison by storing market prices alongside
-- model predictions. This is a research tooling layer, not financial advice.
--
-- Tables:
-- - market.raw_snapshots: Source-preserved market data from APIs
-- - market.normalized_markets: Normalized market data with consistent schema
-- - market.market_prices: Time-series of market prices and odds
-- - market.market_identifiers: Cross-reference of market IDs across providers
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS market;

-- Raw market data snapshots (source-preserved)
CREATE TABLE market.raw_snapshots (
    snapshot_id BIGSERIAL PRIMARY KEY,
    provider TEXT NOT NULL,  -- 'polymarket', 'kalshi', 'draftkings', etc.
    market_id TEXT NOT NULL,  -- Provider-specific market ID
    endpoint TEXT NOT NULL,  -- API endpoint used
    http_status INTEGER,
    fetched_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    raw_payload JSONB,
    checksum TEXT,
    game_date DATE,
    season INTEGER,
    CONSTRAINT raw_snapshots_unique UNIQUE (provider, market_id, fetched_at)
);

CREATE INDEX raw_snapshots_provider_idx ON market.raw_snapshots (provider);
CREATE INDEX raw_snapshots_market_id_idx ON market.raw_snapshots (market_id);
CREATE INDEX raw_snapshots_game_date_idx ON market.raw_snapshots (game_date);
CREATE INDEX raw_snapshots_season_idx ON market.raw_snapshots (season);
CREATE INDEX raw_snapshots_fetched_at_idx ON market.raw_snapshots (fetched_at DESC);

COMMENT ON TABLE market.raw_snapshots IS 'Source-preserved market data snapshots from prediction market APIs';

-- Normalized market data with consistent schema
CREATE TABLE market.normalized_markets (
    market_id TEXT PRIMARY KEY,
    provider TEXT NOT NULL,
    market_type TEXT NOT NULL,  -- 'binary', 'scalar', 'categorical'
    market_title TEXT,
    market_description TEXT,
    event_type TEXT,  -- 'mlb_game', 'mlb_season', 'player_prop', etc.
    event_id TEXT,  -- MLB game PK, season, player ID, etc.
    event_date DATE,
    season INTEGER,
    home_team TEXT,
    away_team,
    status TEXT,  -- 'open', 'closed', 'settled'
    opening_time TIMESTAMP WITH TIME ZONE,
    closing_time TIMESTAMP WITH TIME ZONE,
    settlement_time TIMESTAMP WITH TIME ZONE,
    settlement_value NUMERIC,  -- Final settled value (for scalar markets)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

CREATE INDEX normalized_markets_provider_idx ON market.normalized_markets (provider);
CREATE INDEX normalized_markets_type_idx ON market.normalized_markets (market_type);
CREATE INDEX normalized_markets_event_idx ON market.normalized_markets (event_id);
CREATE INDEX normalized_markets_event_date_idx ON market.normalized_markets (event_date);
CREATE INDEX normalized_markets_season_idx ON market.normalized_markets (season);
CREATE INDEX normalized_markets_status_idx ON market.normalized_markets (status);

COMMENT ON TABLE market.normalized_markets IS 'Normalized market data with consistent schema across providers';

-- Market price history
CREATE TABLE market.market_prices (
    price_id BIGSERIAL PRIMARY KEY,
    market_id TEXT NOT NULL REFERENCES market.normalized_markets(market_id),
    outcome_id TEXT,  -- Provider-specific outcome ID
    outcome_name TEXT,  -- Normalized outcome name (e.g., 'home_win', 'away_win')
    price NUMERIC NOT NULL,  -- Market price (0-100 for probability markets, or price in cents)
    implied_probability NUMERIC,  -- Calculated implied probability
    volume NUMERIC,  -- Trading volume
    liquidity_score NUMERIC,  -- Measure of liquidity (0-1)
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    source_snapshot_id BIGINT REFERENCES market.raw_snapshots(snapshot_id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    CONSTRAINT market_prices_unique UNIQUE (market_id, outcome_id, timestamp)
);

CREATE INDEX market_prices_market_id_idx ON market.market_prices (market_id);
CREATE INDEX market_prices_outcome_idx ON market.market_prices (outcome_id);
CREATE INDEX market_prices_timestamp_idx ON market.market_prices (timestamp DESC);
CREATE INDEX market_prices_latest_idx ON market.market_prices (market_id, timestamp DESC);

COMMENT ON TABLE market.market_prices IS 'Time-series of market prices and implied probabilities';

-- Market identifier cross-reference
CREATE TABLE market.market_identifiers (
    id BIGSERIAL PRIMARY KEY,
    event_type TEXT NOT NULL,
    event_id TEXT NOT NULL,  -- Canonical event ID (e.g., MLB game PK)
    provider TEXT NOT NULL,
    provider_market_id TEXT NOT NULL,
    provider_outcome_id TEXT,
    normalized_outcome_name TEXT,
    is_primary BOOLEAN DEFAULT FALSE,  -- Whether this is the primary market for this event
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    CONSTRAINT market_identifiers_unique UNIQUE (event_type, event_id, provider, provider_market_id)
);

CREATE INDEX market_identifiers_event_idx ON market.market_identifiers (event_type, event_id);
CREATE INDEX market_identifiers_provider_idx ON market.market_identifiers (provider, provider_market_id);
CREATE INDEX market_identifiers_primary_idx ON market.market_identifiers (is_primary);

COMMENT ON TABLE market.market_identifiers IS 'Cross-reference of market IDs across providers for same event';

-- Market validation checks
CREATE TABLE market.validation_checks (
    check_id BIGSERIAL PRIMARY KEY,
    market_id TEXT REFERENCES market.normalized_markets(market_id),
    check_type TEXT NOT NULL,  -- 'price_range', 'probability_sum', 'freshness', 'volume_threshold'
    check_passed BOOLEAN NOT NULL,
    check_value NUMERIC,
    expected_value NUMERIC,
    tolerance NUMERIC,
    error_message TEXT,
    checked_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

CREATE INDEX validation_checks_market_id_idx ON market.validation_checks (market_id);
CREATE INDEX validation_checks_type_idx ON market.validation_checks (check_type);
CREATE INDEX validation_checks_timestamp_idx ON market.validation_checks (checked_at DESC);

COMMENT ON TABLE market.validation_checks IS 'Market data quality validation checks';

COMMENT ON SCHEMA market IS 'Market data storage and normalization for model edge comparison research';
