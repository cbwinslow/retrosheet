-- File: sql/mlb/150_model_registry.sql
-- Purpose: Central registry for ML model artifacts and versions
-- Author: Agent Cascade
-- Date: 2026-04-24
CREATE TABLE IF NOT EXISTS models.model_registry (
    model_id SERIAL PRIMARY KEY,
    model_name TEXT NOT NULL,
    model_version TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    description TEXT,
    artifact_path TEXT,
    metrics_json JSONB,
    CONSTRAINT uq_model_name_version UNIQUE (model_name, model_version)
);

-- Indexes for fast lookup by active status and name.
CREATE INDEX IF NOT EXISTS idx_model_registry_active ON models.model_registry (is_active) WHERE is_active;
CREATE INDEX IF NOT EXISTS idx_model_registry_name ON models.model_registry (model_name);

-- Trigger to auto‑update the `updated_at` timestamp on row modification.
CREATE OR REPLACE FUNCTION models.update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at := NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_model_registry_timestamp
BEFORE UPDATE ON models.model_registry
FOR EACH ROW EXECUTE FUNCTION models.update_timestamp();

COMMENT ON TABLE models.model_registry IS 'Central registry for ML model artifacts, versions, and metadata.';

