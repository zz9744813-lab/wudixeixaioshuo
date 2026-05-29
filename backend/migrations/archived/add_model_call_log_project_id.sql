-- Migration: Add project_id to model_call_logs
-- Run this SQL if your existing database doesn't have the project_id column

ALTER TABLE model_call_logs ADD COLUMN project_id INTEGER REFERENCES projects(id);
CREATE INDEX IF NOT EXISTS ix_model_call_logs_project_id ON model_call_logs(project_id);
