// Prediction API Types
// Based on response schema from predict_pa_outcome_distribution.py and predict_live_pa_outcome_distribution.py

export interface PredictRequest {
  game_id: string
  plate_appearance_id: number
  target_id?: string
  model_name?: string
  model_version?: string
  apply_calibration?: boolean
  calibration_report_name?: string
  // Live-specific fields
  live_game_pk?: number
  live_event_id?: number
}

export interface PredictionModelMetadata {
  model_name: string
  model_version: string
  artifact_uri: string
  feature_set: string
  is_active: boolean
  model_id?: number
}

export interface PredictionCalibrationMetadata {
  applied: boolean
  calibration_report_id?: number
  report_name?: string
  calibration_method?: string
  artifact_uri?: string
}

export interface PredictionStateSnapshot {
  inning?: number
  top_inning?: boolean
  outs?: number
  balls?: number
  strikes?: number
  runner_on_1b?: boolean
  runner_on_2b?: boolean
  runner_on_3b?: boolean
  home_score?: number
  away_score?: number
  is_bottom_inning?: number
  outs_before?: number
  start_bases?: number
  home_score_diff?: number
}

export interface LiveContext {
  live_game_pk?: number
  live_event_id?: number
  prediction_timestamp?: string
  persisted?: boolean
  prediction_id?: number
  run_id?: number
}

export interface DerivedProbabilities {
  p_hit: number
  p_extra_base_hit: number
  p_on_base_traditional: number
  p_reach_base_any: number
  p_ball_in_play: number
  expected_total_bases: number
}

export interface PredictResponse {
  target_id: string
  game_id: string
  plate_appearance_id: number
  actual_outcome_class?: string
  model: PredictionModelMetadata
  probability_sum: number
  class_probabilities: Record<string, number>
  derived_probabilities: DerivedProbabilities
  state_snapshot?: PredictionStateSnapshot
  missing_features?: string[]
  input_features?: Record<string, unknown>
  calibration?: PredictionCalibrationMetadata
  raw_class_probabilities?: Record<string, number>
  raw_derived_probabilities?: DerivedProbabilities
  // Live-specific fields
  live_context?: LiveContext
}

export interface PredictErrorResponse {
  error: string
  details?: string
  code?: string
}

// Legacy binary PA prediction response (for backward compatibility)
export interface LegacyPredictResponse {
  game_id: string
  plate_appearance_id: number
  predictions: Record<string, {
    probability: number
    model_name: string
    model_version: string
  }>
}
