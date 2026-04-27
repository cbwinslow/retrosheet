-- File: sql/features/004_alter_base_features_types.sql
-- Purpose: Fix column length issues in base_features table for pitch data
-- Author: Agent Cascade
-- Date: 2026-04-24

-- Fix column length issues in base_features table
-- Run this before populating base_features from locations

-- Extend varchar columns that are too short
ALTER TABLE features_pitch.base_features
ALTER COLUMN of_fielding_alignment TYPE varchar(50);

-- Verify the change
SELECT
    column_name,
    data_type,
    character_maximum_length
FROM information_schema.columns
WHERE
    table_schema = 'features_pitch'
    AND table_name = 'base_features'
    AND column_name IN ('of_fielding_alignment', 'if_fielding_alignment', 'quality_flag');
