-- Manual Migration for Warm-up System
-- Run this in your PostgreSQL database (outreach_db)
-- Reason: Python environment is crashing on SQLAlchemy imports, preventing automatic migration.

-- 1. Update Workspaces Table
ALTER TABLE workspaces ADD COLUMN warmup_enabled BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE workspaces ADD COLUMN warmup_start_date TIMESTAMP NULL;

-- 2. Update Domains Table
ALTER TABLE domains ADD COLUMN warmup_day INTEGER NOT NULL DEFAULT 0;
ALTER TABLE domains ADD COLUMN warmup_completed BOOLEAN NOT NULL DEFAULT FALSE;

-- 3. Update Alembic Version
-- This ensures future migrations work correctly once the environment is fixed.
UPDATE alembic_version SET version_num = '005_add_warmup_fields';
