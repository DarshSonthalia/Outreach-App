BEGIN;

-- 1. Campaign Leads
DO $$ BEGIN
    CREATE TYPE followupstate AS ENUM ('SCHEDULED', 'CANCELLED', 'COMPLETED');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE cancelreason AS ENUM ('REPLIED', 'NEGATIVE_REPLY', 'UNSUBSCRIBE', 'BOOKED', 'BOUNCE', 'SUPPRESSED', 'MANUAL', 'SAFETY');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

ALTER TABLE campaign_leads ADD COLUMN IF NOT EXISTS followup_state followupstate NOT NULL DEFAULT 'SCHEDULED';
ALTER TABLE campaign_leads ADD COLUMN IF NOT EXISTS cancelled_at TIMESTAMP NULL;
ALTER TABLE campaign_leads ADD COLUMN IF NOT EXISTS cancel_reason cancelreason NULL;
ALTER TABLE campaign_leads ADD COLUMN IF NOT EXISTS cancel_detail TEXT NULL;
ALTER TABLE campaign_leads ADD COLUMN IF NOT EXISTS current_step INTEGER NOT NULL DEFAULT 0;
ALTER TABLE campaign_leads ADD COLUMN IF NOT EXISTS next_scheduled_at TIMESTAMP NULL;
ALTER TABLE campaign_leads ADD COLUMN IF NOT EXISTS schedule_json JSONB NULL;

CREATE INDEX IF NOT EXISTS ix_campaign_leads_next_scheduled_at ON campaign_leads (next_scheduled_at);

-- 2. Messages
DO $$ BEGIN
    CREATE TYPE draftstatus AS ENUM ('GENERATED', 'EDITED', 'SENT', 'DISCARDED', 'SAVED_TO_GMAIL_DRAFT');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

ALTER TABLE messages ADD COLUMN IF NOT EXISTS planned_send_at TIMESTAMP NULL;
ALTER TABLE messages ADD COLUMN IF NOT EXISTS cancelled BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE messages ADD COLUMN IF NOT EXISTS cancel_reason VARCHAR(255) NULL;
ALTER TABLE messages ADD COLUMN IF NOT EXISTS is_draft BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE messages ADD COLUMN IF NOT EXISTS draft_status draftstatus NULL;

-- Unique constraint update
ALTER TABLE messages DROP CONSTRAINT IF EXISTS uq_message_idempotency;
ALTER TABLE messages ADD CONSTRAINT uq_message_idempotency UNIQUE (campaign_lead_id, step_number, direction, is_draft);

-- 3. Reply Drafts
CREATE TABLE IF NOT EXISTS reply_drafts (
    id SERIAL PRIMARY KEY,
    workspace_id INTEGER NOT NULL REFERENCES workspaces(id),
    mailbox_id INTEGER NOT NULL REFERENCES mailboxes(id),
    gmail_thread_id VARCHAR(255) NOT NULL,
    gmail_message_id VARCHAR(255) NULL,
    subject TEXT NULL,
    body TEXT NULL,
    model VARCHAR(100) NOT NULL,
    prompt_version VARCHAR(100) NOT NULL,
    status draftstatus NOT NULL DEFAULT 'GENERATED',
    risk_flags JSONB NULL,
    classification VARCHAR(100) NULL,
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_reply_drafts_gmail_thread_id ON reply_drafts (gmail_thread_id);
CREATE INDEX IF NOT EXISTS ix_reply_drafts_id ON reply_drafts (id);

-- 4. Update ReplyClassification Enum
ALTER TYPE replyclassification ADD VALUE IF NOT EXISTS 'INTERESTED';
ALTER TYPE replyclassification ADD VALUE IF NOT EXISTS 'QUESTION';
ALTER TYPE replyclassification ADD VALUE IF NOT EXISTS 'OUT_OF_OFFICE';

-- 5. Update Alembic Version
UPDATE alembic_version SET version_num = '006_add_followup_and_drafts';

COMMIT;
