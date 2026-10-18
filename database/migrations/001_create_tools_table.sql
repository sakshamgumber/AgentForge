-- Migration: 001_create_tools_table.sql
-- Description: Create tools table to track tool executions, attempts, operations, statuses, and errors in PostgreSQL.

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Enum for tool status
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'tool_status_enum') THEN
        CREATE TYPE tool_status_enum AS ENUM (
            'SUCCESS',
            'FAILURE',
            'TIMEOUT',
            'PERMISSION_DENIED',
            'PENDING',
            'RUNNING'
        );
    END IF;
END$$;

-- Table: tools
CREATE TABLE IF NOT EXISTS tools (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tool_name VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'PENDING',
    error TEXT,
    attempt_id VARCHAR(100) NOT NULL,
    operation_id VARCHAR(100) NOT NULL,
    parameters JSONB DEFAULT '{}'::jsonb,
    result JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_tools_tool_name ON tools (tool_name);
CREATE INDEX IF NOT EXISTS idx_tools_status ON tools (status);
CREATE INDEX IF NOT EXISTS idx_tools_attempt_id ON tools (attempt_id);
CREATE INDEX IF NOT EXISTS idx_tools_operation_id ON tools (operation_id);
CREATE INDEX IF NOT EXISTS idx_tools_created_at ON tools (created_at DESC);

-- Trigger to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_tools_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_update_tools_timestamp ON tools;
CREATE TRIGGER trg_update_tools_timestamp
    BEFORE UPDATE ON tools
    FOR EACH ROW
    EXECUTE FUNCTION update_tools_timestamp();
