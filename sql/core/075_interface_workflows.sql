CREATE SCHEMA IF NOT EXISTS predictions;
CREATE SCHEMA IF NOT EXISTS chat;

CREATE TABLE IF NOT EXISTS predictions.simulation_runs (
    simulation_run_id bigserial PRIMARY KEY,
    run_name text,
    run_mode text NOT NULL,
    requested_at timestamptz NOT NULL DEFAULT now(),
    requested_by text,
    filters jsonb NOT NULL DEFAULT '{}'::jsonb,
    summary jsonb NOT NULL DEFAULT '{}'::jsonb,
    run_distribution jsonb NOT NULL DEFAULT '[]'::jsonb,
    sample_size integer,
    notes text
);

CREATE INDEX IF NOT EXISTS simulation_runs_requested_at_idx
ON predictions.simulation_runs (requested_at DESC);

CREATE INDEX IF NOT EXISTS simulation_runs_mode_idx
ON predictions.simulation_runs (run_mode, requested_at DESC);

CREATE INDEX IF NOT EXISTS simulation_runs_filters_gin_idx
ON predictions.simulation_runs USING gin (filters);

CREATE OR REPLACE VIEW predictions.recent_simulation_runs AS
SELECT
    simulation_run_id,
    requested_at,
    run_name,
    run_mode,
    filters,
    (summary ->> 'historical_half_innings')::integer AS historical_half_innings,
    (summary ->> 'expected_runs')::numeric AS expected_runs,
    (summary ->> 'run_probability')::numeric AS run_probability,
    (summary ->> 'all_left_handed_batters_hit_probability')::numeric AS all_left_handed_batters_hit_probability,
    sample_size,
    notes
FROM predictions.simulation_runs
ORDER BY requested_at DESC;

ALTER TABLE chat.query_logs
ADD COLUMN IF NOT EXISTS tools_used jsonb NOT NULL DEFAULT '[]'::jsonb,
ADD COLUMN IF NOT EXISTS result_row_count integer;

CREATE INDEX IF NOT EXISTS query_logs_asked_at_idx
ON chat.query_logs (asked_at DESC);

CREATE INDEX IF NOT EXISTS query_logs_intent_gin_idx
ON chat.query_logs USING gin (parsed_intent);
