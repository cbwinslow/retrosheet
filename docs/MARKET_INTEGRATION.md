# Market Integration Documentation

This document describes the market data integration architecture for the Retrosheet Prediction Warehouse.

## Overview

The market integration layer enables research comparison between model predictions and prediction market prices (Polymarket, Kalshi, sportsbooks). This is a **research tooling layer** and should not be used for financial advice.

## Architecture

### Data Flow

1. **Market Data Ingestion** (`scripts/ingest_market_data.py`)
   - Fetches market data from provider APIs
   - Stores raw responses in `market.raw_snapshots`
   - Normalizes data to `market.normalized_markets`

2. **Price Tracking** (`scripts/track_market_prices.py`)
   - Polls market prices at regular intervals
   - Stores price history in `market.market_prices`
   - Calculates implied probabilities

3. **Edge Detection** (SQL views in `sql/126_model_edge_comparison.sql`)
   - Joins model predictions with market prices
   - Calculates model edge (model probability - market implied probability)
   - Categorizes edges and calculates Kelly Criterion sizing

4. **Alerting** (`scripts/market_monitor.py`)
   - Monitors for edges exceeding thresholds
   - Generates alerts for large edges
   - Tracks edge statistics over time

## Schema

### market.raw_snapshots
Source-preserved API responses from market providers.

### market.normalized_markets
Normalized market data with consistent schema across providers.

### market.market_prices
Time-series of market prices and implied probabilities.

### market.market_identifiers
Cross-reference of market IDs across providers for the same event.

### market.validation_checks
Data quality validation checks.

## Views

### market.model_market_join
Joins model predictions with market prices within a 1-hour window.

### market.edge_calculations
Calculates model edge vs market with categorization and Kelly sizing.

### market.edge_summaries
Aggregated edge statistics by model and market provider.

### market.edge_tracking
Tracks edge statistics over time by model and market.

### market.edge_alerts
Prioritized edge detection alerts based on edge size and Kelly fraction.

## Edge Calculation

### Model Edge
```
model_edge = model_probability - market_implied_probability
```

### Edge Categories
- **Large**: |edge| >= 10%
- **Medium**: |edge| >= 5%
- **Small**: |edge| >= 2%
- **Negligible**: |edge| < 2%

### Edge Direction
- **Model over market**: model_edge > 0
- **Market over model**: model_edge < 0
- **No edge**: model_edge = 0

### Kelly Criterion (Simplified)
```
kelly_fraction = model_edge / market_implied_probability
```
Note: This is a simplified calculation assuming even-money bets. Real Kelly sizing requires market odds and risk parameters.

## Monitoring Scripts

### scripts/market_monitor.py
Monitors market data and generates alerts for edges exceeding thresholds.

**Features:**
- Real-time edge monitoring
- Alert generation for large edges
- Market data freshness checks
- Anomaly detection
- Data quality reporting

**Usage:**
```bash
python3 scripts/market_monitor.py --threshold 0.05 --interval 300
```

### scripts/ingest_market_data.py
Ingests market data from provider APIs.

**Features:**
- Multi-provider support (Polymarket, Kalshi, sportsbooks)
- Automatic normalization
- Validation checks
- Error handling and retry logic

**Usage:**
```bash
python3 scripts/ingest_market_data.py --provider polymarket --event-id <GAME_PK>
```

### scripts/track_market_prices.py
Tracks market prices over time.

**Features:**
- Periodic price polling
- Price history storage
- Implied probability calculation
- Volume tracking

**Usage:**
```bash
python3 scripts/track_market_prices.py --market-id <MARKET_ID> --interval 60
```

## Validation Checks

### Price Range Validation
- Ensures prices are within valid ranges (0-100 for probability markets)
- Flags outliers for review

### Probability Sum Validation
- For binary markets, ensures probabilities sum to 1.0 (within tolerance)
- Flags arbitrage opportunities

### Freshness Validation
- Checks that market data is recent (within configurable threshold)
- Flags stale data

### Volume Threshold Validation
- Ensures sufficient trading volume before using price data
- Flags low-liquidity markets

## Anomaly Detection

### Price Spikes
- Detects sudden large price movements
- Flags potential data errors or market events

### Arbitrage Opportunities
- Detects price discrepancies across providers
- Flags potential arbitrage (research only, not financial advice)

### Model-Market Divergence
- Tracks persistent divergence between model and market
- Flags potential model drift or market inefficiency

## Data Quality Reports

### Market Data Freshness
- Percentage of markets with fresh data
- Average age of market data
- Stale market count

### Price Distribution
- Distribution of prices across markets
- Outlier detection
- Volume statistics

### Edge Distribution
- Distribution of model edges
- Edge category breakdown
- Kelly fraction statistics

## Security and Privacy

- API keys stored in environment variables (never committed)
- All market data treated as read-only for research
- No automated trading or financial recommendations
- Market data used solely for model validation and research

## Limitations

- Market data availability varies by provider and event type
- Implied probabilities may not reflect true probabilities (market inefficiencies, fees)
- Kelly Criterion calculation is simplified and should not be used for actual betting
- Edge detection is for research purposes only, not financial advice

## Future Work

- [ ] Implement actual ingestion scripts for Polymarket and Kalshi APIs
- [ ] Add sportsbook API integrations (DraftKings, FanDuel, etc.)
- [ ] Implement more sophisticated Kelly Criterion calculations
- [ ] Add backtesting of edge-based strategies (research only)
- [ ] Create visualization dashboard for edge tracking
- [ ] Add machine learning for anomaly detection
