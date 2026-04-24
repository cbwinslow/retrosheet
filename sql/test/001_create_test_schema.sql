/*
File: sql/test/001_create_test_schema.sql
Purpose: Create isolated test schema for E2E validation
Author: Agent Cascade
Date: 2026-04-24
Called By: scripts/test/e2e_test_runner.sh

This creates a test schema in the existing PostgreSQL database.
No Docker, no cloud - completely free local testing.
*/

-- Drop and recreate test schema
DROP SCHEMA IF EXISTS test CASCADE;
CREATE SCHEMA test;

-- Grant permissions
GRANT ALL ON SCHEMA test TO current_user;

-- Create test tracking table
CREATE TABLE test.runs (
    run_id SERIAL PRIMARY KEY,
    test_name VARCHAR(255) NOT NULL,
    started_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    status VARCHAR(20) DEFAULT 'running',
    error_message TEXT,
    row_counts JSONB
);

COMMENT ON TABLE test.runs IS 'Tracks E2E test execution and results';
COMMENT ON COLUMN test.runs.run_id IS 'Unique test run identifier';
COMMENT ON COLUMN test.runs.test_name IS 'Name of the test being run';
COMMENT ON COLUMN test.runs.status IS 'Test status: running, completed, failed';
COMMENT ON COLUMN test.runs.row_counts IS 'JSONB of table row counts for validation';
