# Validation Report Templates

This document provides templates for validation reports used throughout the prediction warehouse.

## Model Validation Report Template

### Purpose
Document model performance, calibration quality, and validation results for model promotion decisions.

### Template

```markdown
# Model Validation Report: {model_name} v{model_version}

**Date:** {validation_date}
**Validated By:** {validator_name}
**Model ID:** {model_id}

## Executive Summary

{brief_summary_of_findings}

## Model Metadata

- **Model Name:** {model_name}
- **Model Version:** {model_version}
- **Model Family:** {model_family}
- **Feature Set:** {feature_set}
- **Training Period:** {train_start_date} to {train_end_date}
- **Validation Period:** {validation_start_date} to {validation_end_date}
- **Training Examples:** {n_train_examples}
- **Validation Examples:** {n_validation_examples}

## Performance Metrics

### Overall Metrics

| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| Log Loss | {log_loss} | {log_loss_threshold} | {status} |
| Brier Score | {brier_score} | {brier_threshold} | {status} |
| Accuracy | {accuracy} | {accuracy_threshold} | {status} |
| Top-3 Accuracy | {top3_accuracy} | {top3_threshold} | {status} |

### Per-Class Metrics

| Class | Precision | Recall | F1-Score | Support |
|-------|-----------|--------|----------|---------|
| {class_1} | {precision_1} | {recall_1} | {f1_1} | {support_1} |
| {class_2} | {precision_2} | {recall_2} | {f1_2} | {support_2} |
| ... | ... | ... | ... | ... |

## Calibration Analysis

### Overall Calibration

- **Expected Calibration Error (ECE):** {ece_value}
- **ECE Threshold:** {ece_threshold}
- **Status:** {calibration_status}

### Per-Class Calibration

| Class | ECE | Confidence Gap | Status |
|-------|-----|----------------|--------|
| {class_1} | {ece_1} | {gap_1} | {status_1} |
| {class_2} | {ece_2} | {gap_2} | {status_2} |
| ... | ... | ... | ... |

### Subgroup Analysis

**Two-Strike Count:**
- ECE: {two_strike_ece}
- Confidence Gap: {two_strike_gap}
- Status: {two_strike_status}

**Loaded Bases:**
- ECE: {loaded_bases_ece}
- Confidence Gap: {loaded_bases_gap}
- Status: {loaded_bases_status}

## Feature Importance

| Feature | Importance | Type |
|---------|------------|------|
| {feature_1} | {importance_1} | {type_1} |
| {feature_2} | {importance_2} | {type_2} |
| ... | ... | ... |

## Bootstrap Uncertainty

| Metric | Mean | 5th Percentile | 95th Percentile |
|--------|------|----------------|-----------------|
| Log Loss | {log_loss_mean} | {log_loss_p5} | {log_loss_p95} |
| Brier Score | {brier_mean} | {brier_p5} | {brier_p95} |
| Accuracy | {acc_mean} | {acc_p5} | {acc_p95} |

## Comparison to Baseline

| Metric | Current Model | Baseline Model | Improvement |
|--------|---------------|----------------|-------------|
| Log Loss | {current_log_loss} | {baseline_log_loss} | {log_loss_improvement} |
| Brier Score | {current_brier} | {baseline_brier} | {brier_improvement} |
| Accuracy | {current_acc} | {baseline_acc} | {acc_improvement} |

## Issues and Concerns

{list_of_issues_or_concerns}

## Recommendation

**{recommendation (PROMOTE / HOLD / REJECT)}**

**Rationale:** {detailed_rationale}

## Next Steps

{list_of_next_steps}

## Appendix

### Calibration Plots
{reference_to_calibration_plots}

### Feature Distributions
{reference_to_feature_distributions}

### Error Analysis
{reference_to_error_analysis}
```

## Data Quality Validation Report Template

### Purpose
Document data quality check results for warehouse health monitoring.

### Template

```markdown
# Data Quality Validation Report

**Date:** {validation_date}
**Validated By:** {validator_name}
**Warehouse Version:** {warehouse_version}

## Executive Summary

{summary_of_data_quality_status}

## Overall Status

- **Total Checks:** {total_checks}
- **Passed:** {passed_checks}
- **Failed:** {failed_checks}
- **Overall Compliance:** {compliance_percentage}%

## Check Results

### Schema Validation

| Table | Status | Missing Columns | Notes |
|-------|--------|-----------------|-------|
| {table_1} | {status_1} | {missing_cols_1} | {notes_1} |
| {table_2} | {status_2} | {missing_cols_2} | {notes_2} |
| ... | ... | ... | ... |

### Null Rate Monitoring

| Table | Column | Null Rate | Threshold | Status |
|-------|--------|-----------|-----------|--------|
| {table_1} | {column_1} | {null_rate_1} | {threshold_1} | {status_1} |
| {table_2} | {column_2} | {null_rate_2} | {threshold_2} | {status_2} |
| ... | ... | ... | ... | ... |

### Value Range Validation

| Table | Column | Out of Range Count | Threshold | Status |
|-------|--------|-------------------|-----------|--------|
| {table_1} | {column_1} | {oor_count_1} | {threshold_1} | {status_1} |
| {table_2} | {column_2} | {oor_count_2} | {threshold_2} | {status_2} |
| ... | ... | ... | ... | ... |

### Referential Integrity

| Child Table | Child Column | Parent Table | Parent Column | Orphan Count | Status |
|-------------|--------------|--------------|---------------|--------------|--------|
| {child_1} | {child_col_1} | {parent_1} | {parent_col_1} | {orphan_1} | {status_1} |
| {child_2} | {child_col_2} | {parent_2} | {parent_col_2} | {orphan_2} | {status_2} |
| ... | ... | ... | ... | ... | ... |

### Temporal Consistency

| Table | Date Column | Season Column | Inconsistent Count | Status |
|-------|-------------|---------------|-------------------|--------|
| {table_1} | {date_col_1} | {season_col_1} | {inconsistent_1} | {status_1} |
| {table_2} | {date_col_2} | {season_col_2} | {inconsistent_2} | {status_2} |
| ... | ... | ... | ... | ... |

## Critical Issues

{list_of_critical_issues_requiring_immediate_attention}

## Warnings

{list_of_warnings_that_should_be_addressed}

## Recommendations

{list_of_recommendations_for_improvement}

## Trend Analysis

{comparison_with_previous_validations}

## Appendix

### Detailed Check Results
{reference_to_detailed_json_output}

### Historical Trends
{reference_to_trend_charts}
```

## Simulation Validation Report Template

### Purpose
Document simulation validation results to ensure baseball state transitions produce realistic outcomes.

### Template

```markdown
# Simulation Validation Report

**Date:** {validation_date}
**Validated By:** {validator_name}
**Simulation Version:** {simulation_version}

## Executive Summary

{summary_of_simulation_validation_results}

## State Transition Validation

### Base Transition Validation

| Start State | Event Type | End State | Historical Frequency | Simulated Frequency | Difference |
|-------------|------------|-----------|---------------------|---------------------|------------|
| {start_1} | {event_1} | {end_1} | {freq_1} | {sim_freq_1} | {diff_1} |
| {start_2} | {event_2} | {end_2} | {freq_2} | {sim_freq_2} | {diff_2} |
| ... | ... | ... | ... | ... | ... |

### Out Transition Validation

| Start Outs | Event Type | End Outs | Historical Rate | Simulated Rate | Status |
|------------|------------|----------|-----------------|----------------|--------|
| {outs_1} | {event_1} | {end_outs_1} | {rate_1} | {sim_rate_1} | {status_1} |
| {outs_2} | {event_2} | {end_outs_2} | {rate_2} | {sim_rate_2} | {status_2} |
| ... | ... | ... | ... | ... | ... |

### Score Transition Validation

| Event Type | Expected Runs | Simulated Runs | Difference | Status |
|------------|---------------|----------------|------------|--------|
| {event_1} | {exp_runs_1} | {sim_runs_1} | {diff_1} | {status_1} |
| {event_2} | {exp_runs_2} | {sim_runs_2} | {diff_2} | {status_2} |
| ... | ... | ... | ... | ... |

### Inning Transition Validation

| Start State | Event Type | End State | Historical Rate | Simulated Rate | Status |
|-------------|------------|-----------|-----------------|----------------|--------|
| {state_1} | {event_1} | {end_state_1} | {rate_1} | {sim_rate_1} | {status_1} |
| {state_2} | {event_2} | {end_state_2} | {rate_2} | {sim_rate_2} | {status_2} |
| ... | ... | ... | ... | ... | ... |

## Reproducibility Validation

- **Deterministic Transitions:** {pass/fail}
- **State Consistency:** {pass/fail}
- **Base State Validity:** {pass/fail}
- **Out Count Validity:** {pass/fail}

## Issues and Concerns

{list_of_simulation_issues}

## Recommendations

{recommendations_for_simulation_improvements}

## Appendix

### Detailed Transition Logs
{reference_to_transition_logs}

### Historical Comparison Plots
{reference_to_comparison_plots}
```

## Performance Benchmark Report Template

### Purpose
Document performance benchmark results for prediction serving and system optimization.

### Template

```markdown
# Performance Benchmark Report

**Date:** {benchmark_date}
**Benchmarked By:** {benchmark_runner}
**System Version:** {system_version}

## Executive Summary

{summary_of_performance_results}

## Prediction Serving Latency

### Historical Scorer

| Metric | Current | Target | Status |
|--------|---------|--------|--------|
| Cold Start Latency | {cold_hist} | {target_cold} | {status} |
| Warm Latency (P50) | {p50_hist} | {target_p50} | {status} |
| Warm Latency (P95) | {p95_hist} | {target_p95} | {status} |
| Warm Latency (P99) | {p99_hist} | {target_p99} | {status} |

### Live Scorer

| Metric | Current | Target | Status |
|--------|---------|--------|--------|
| Cold Start Latency | {cold_live} | {target_cold} | {status} |
| Warm Latency (P50) | {p50_live} | {target_p50} | {status} |
| Warm Latency (P95) | {p95_live} | {target_p95} | {status} |
| Warm Latency (P99) | {p99_live} | {target_p99} | {status} |

## Database Query Performance

### Feature Queries

| Query Type | Current | Target | Status |
|------------|---------|--------|--------|
| Single PA Feature Lookup | {single_pa} | {target_single} | {status} |
| Batch Feature Lookup (100) | {batch_100} | {target_batch} | {status} |
| Historical Aggregation | {hist_agg} | {target_agg} | {status} |

### Cache Performance

| Cache Type | Hit Rate | Target | Status |
|------------|----------|--------|--------|
| Model Cache | {model_cache} | {target_model} | {status} |
| Query Cache | {query_cache} | {target_query} | {status} |
| Prediction Cache | {pred_cache} | {target_pred} | {status} |

## System Metrics

| Metric | Current | Target | Status |
|--------|---------|--------|--------|
| CPU Utilization | {cpu} | {target_cpu} | {status} |
| Memory Usage | {memory} | {target_memory} | {status} |
| Connection Pool Utilization | {pool} | {target_pool} | {status} |

## Regression Analysis

{comparison_with_previous_benchmarks}

## Issues and Concerns

{list_of_performance_issues}

## Recommendations

{recommendations_for_performance_improvements}

## Appendix

### Detailed Benchmark Results
{reference_to_benchmark_logs}

### Performance Charts
{reference_to_performance_charts}
```

## Report Generation

### Automation

Validation reports can be generated using existing scripts:

```bash
# Model validation report
python3 scripts/analyze_pa_outcome_calibration.py --model-id {model_id} --output validation_report.md

# Data quality validation report
python3 scripts/validate_data_quality.py --output data_quality_report.json

# Performance benchmark report
python3 scripts/benchmark_prediction.py --output benchmark_report.json
```

### Report Storage

Store validation reports in `reports/validation/` with naming convention:
- `model_validation_{model_name}_{model_version}_{date}.md`
- `data_quality_{date}.md`
- `simulation_validation_{date}.md`
- `performance_benchmark_{date}.md`

### Report Review Process

1. Generate report using template
2. Review results against thresholds
3. Document issues and recommendations
4. Store report in version control
5. Update PROJECT_LOG.md with findings
6. Create GitHub issue for critical findings
