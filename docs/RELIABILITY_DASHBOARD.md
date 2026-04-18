# Reliability Dashboard Design

This document describes the design for the command center reliability dashboard for monitoring the Retrosheet Prediction Warehouse.

## Overview

The reliability dashboard provides real-time monitoring of the prediction system's health, performance, and data quality. It enables operators to quickly identify and respond to issues affecting model performance, feature quality, and system reliability.

## Dashboard Components

### 1. Model Calibration Metrics

**Purpose:** Monitor calibration quality of active models across different outcomes.

**Metrics:**
- **Calibration Error:** Mean absolute error between predicted probabilities and observed frequencies
- **Reliability Diagram:** Binned predicted probability vs observed frequency
- **Brier Score:** Proper scoring rule for probability predictions
- **Log Loss:** Logarithmic loss for probability predictions
- **Coverage:** Percentage of predictions within confidence intervals

**Visualizations:**
- Time series of calibration error by outcome
- Reliability diagram with calibration curve
- Brier score trend over time
- Calibration error heatmap by model version

**Thresholds:**
- **Critical:** Calibration error > 0.15
- **Warning:** Calibration error > 0.10
- **Normal:** Calibration error ≤ 0.10

**SQL Queries:**
```sql
-- Calibration error by outcome
SELECT
    model_id,
    model_name,
    model_version,
    outcome_class,
    AVG(ABS(predicted_probability - actual_outcome)) AS calibration_error
FROM predictions.live_pa_predictions p
JOIN core.plate_appearances pa ON p.plate_appearance_id = pa.plate_appearance_id
WHERE p.created_at >= NOW() - INTERVAL '7 days'
GROUP BY model_id, model_name, model_version, outcome_class;
```

### 2. Live Feature Null Rates

**Purpose:** Monitor feature completeness and data quality in live predictions.

**Metrics:**
- **Null Rate:** Percentage of null values per feature
- **Missing Features:** Count of features with null rate > threshold
- **Feature Freshness:** Age of feature data
- **Feature Distribution:** Statistical summary of feature values

**Visualizations:**
- Null rate heatmap by feature
- Time series of null rates
- Feature freshness gauge
- Feature distribution histograms

**Thresholds:**
- **Critical:** Null rate > 10% for any feature
- **Warning:** Null rate > 5% for any feature
- **Normal:** Null rate ≤ 5% for all features

**SQL Queries:**
```sql
-- Null rate by feature
SELECT
    feature_name,
    COUNT(*) FILTER (WHERE feature_value IS NULL) * 100.0 / COUNT(*) AS null_rate
FROM predictions.live_pa_predictions p,
     jsonb_each_text(p.features) AS t(feature_name, feature_value)
WHERE p.created_at >= NOW() - INTERVAL '1 hour'
GROUP BY feature_name
ORDER BY null_rate DESC;
```

### 3. Prediction Latency Metrics

**Purpose:** Monitor prediction request latency and throughput.

**Metrics:**
- **P50 Latency:** Median prediction request time
- **P95 Latency:** 95th percentile prediction request time
- **P99 Latency:** 99th percentile prediction request time
- **Throughput:** Predictions per second
- **Error Rate:** Percentage of failed predictions

**Visualizations:**
- Latency time series with percentiles
- Throughput trend over time
- Error rate time series
- Latency distribution histogram

**Thresholds:**
- **Critical:** P99 latency > 5s or error rate > 5%
- **Warning:** P95 latency > 2s or error rate > 1%
- **Normal:** P95 latency ≤ 2s and error rate ≤ 1%

**SQL Queries:**
```sql
-- Prediction latency
SELECT
    AVG(response_time_ms) AS avg_latency,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY response_time_ms) AS p50_latency,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY response_time_ms) AS p95_latency,
    PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY response_time_ms) AS p99_latency,
    COUNT(*) * 100.0 / SUM(COUNT(*)) OVER () AS error_rate
FROM predictions.live_pa_predictions
WHERE created_at >= NOW() - INTERVAL '1 hour'
  AND error IS NOT NULL;
```

### 4. Drift Detection Alerts

**Purpose:** Monitor feature and prediction drift from training distributions.

**Metrics:**
- **Feature Drift Score:** KL divergence between current and training feature distributions
- **Prediction Drift Score:** KL divergence between current and training prediction distributions
- **Population Stability Index (PSI):** Measure of distribution shift
- **Drift Trend:** Rate of change in drift scores over time

**Visualizations:**
- Drift score heatmap by feature
- Drift score time series
- PSI trend over time
- Feature distribution comparison (training vs current)

**Thresholds:**
- **Critical:** Drift score > 0.2 or PSI > 0.25
- **Warning:** Drift score > 0.1 or PSI > 0.1
- **Normal:** Drift score ≤ 0.1 and PSI ≤ 0.1

**SQL Queries:**
```sql
-- Feature drift detection (simplified)
WITH training_stats AS (
    SELECT
        feature_name,
        AVG(feature_value) AS mean,
        STDDEV(feature_value) AS stddev
    FROM features.plate_appearance_advanced_examples
    WHERE feature_season = 2024
    GROUP BY feature_name
),
current_stats AS (
    SELECT
        feature_name,
        AVG(feature_value) AS mean,
        STDDEV(feature_value) AS stddev
    FROM predictions.live_pa_predictions p,
         jsonb_each_text(p.features) AS t(feature_name, feature_value)
    WHERE p.created_at >= NOW() - INTERVAL '1 day'
    GROUP BY feature_name
)
SELECT
    c.feature_name,
    ABS(c.mean - t.mean) / NULLIF(t.stddev, 0) AS drift_score
FROM current_stats c
JOIN training_stats t ON c.feature_name = t.feature_name;
```

## Dashboard Layout

### Top Row: System Health Summary
- Overall health status (green/yellow/red)
- Active model versions
- Total predictions in last 24h
- Current error rate

### Middle Row: Key Metrics
- Model calibration error (sparkline)
- Feature null rate (gauge)
- Prediction latency (time series)
- Drift score (heatmap)

### Bottom Row: Detailed Views
- Calibration reliability diagram
- Feature null rate breakdown
- Latency distribution
- Drift score by feature

## Implementation

### Frontend (Next.js Command Center)

**Components:**
- `app/dashboard/reliability/page.tsx`: Main dashboard page
- `components/reliability/CalibrationChart.tsx`: Calibration visualization
- `components/reliability/FeatureNullRate.tsx`: Feature null rate display
- `components/reliability/LatencyChart.tsx`: Latency visualization
- `components/reliability/DriftHeatmap.tsx`: Drift score heatmap

**API Routes:**
- `app/api/dashboard/calibration/route.ts`: Calibration metrics
- `app/api/dashboard/feature-nulls/route.ts`: Feature null rates
- `app/api/dashboard/latency/route.ts`: Latency metrics
- `app/api/dashboard/drift/route.ts`: Drift scores

### Backend (PostgreSQL Views)

**Materialized Views:**
```sql
CREATE MATERIALIZED VIEW dashboard.calibration_metrics AS
SELECT
    model_id,
    model_name,
    model_version,
    outcome_class,
    DATE_TRUNC('hour', created_at) AS hour,
    AVG(ABS(predicted_probability - actual_outcome)) AS calibration_error,
    AVG(2 * predicted_probability * (1 - predicted_probability) - (predicted_probability - actual_outcome)^2) AS brier_score
FROM predictions.live_pa_predictions p
JOIN core.plate_appearances pa ON p.plate_appearance_id = pa.plate_appearance_id
GROUP BY model_id, model_name, model_version, outcome_class, DATE_TRUNC('hour', created_at);

CREATE MATERIALIZED VIEW dashboard.feature_null_rates AS
SELECT
    DATE_TRUNC('hour', created_at) AS hour,
    feature_name,
    COUNT(*) FILTER (WHERE feature_value IS NULL) * 100.0 / COUNT(*) AS null_rate
FROM predictions.live_pa_predictions p,
     jsonb_each_text(p.features) AS t(feature_name, feature_value)
GROUP BY DATE_TRUNC('hour', created_at), feature_name;

CREATE MATERIALIZED VIEW dashboard.prediction_latency AS
SELECT
    DATE_TRUNC('minute', created_at) AS minute,
    AVG(response_time_ms) AS avg_latency,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY response_time_ms) AS p50_latency,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY response_time_ms) AS p95_latency,
    PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY response_time_ms) AS p99_latency,
    COUNT(*) FILTER (WHERE error IS NOT NULL) * 100.0 / COUNT(*) AS error_rate
FROM predictions.live_pa_predictions
GROUP BY DATE_TRUNC('minute', created_at);
```

**Refresh Schedule:**
- Calibration metrics: Every 15 minutes
- Feature null rates: Every 5 minutes
- Prediction latency: Every 1 minute

### Alerting

**Alert Channels:**
- **Email:** Critical alerts
- **Slack:** Warning and critical alerts
- **Dashboard:** All alerts (in-app notifications)

**Alert Rules:**
- Calibration error > 0.15 → Critical alert
- Null rate > 10% → Critical alert
- P99 latency > 5s → Critical alert
- Drift score > 0.2 → Warning alert

**Alert Suppression:**
- Maintenance windows configured in dashboard
- Alert grouping to prevent spam
- Escalation policy for repeated alerts

## Security

- **Authentication:** Required to access dashboard
- **Authorization:** Role-based access (admin, operator, viewer)
- **Audit Logging:** All dashboard access logged
- **Rate Limiting:** API rate limits to prevent abuse

## Performance

- **Caching:** Materialized views for expensive queries
- **Query Optimization:** Indexes on timestamp columns
- **Lazy Loading:** Load data on demand, not all at once
- **Pagination:** Limit result sets for large datasets

## Future Enhancements

- [ ] Add model comparison view
- [ ] Implement drill-down capabilities
- [ ] Add historical trend analysis
- [ ] Integrate with incident management system
- [ ] Add custom alert configuration
- [ ] Implement dashboard export functionality
