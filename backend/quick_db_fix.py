import os
from sqlalchemy import create_engine, text

# Hardcoded connection string from .env investigation
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://outreach:outreach_secure_2024@localhost:5432/outreach_db")

def fix_db():
    print("Starting quick DB fix...")
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        trans = conn.begin()
        try:
            # 1. Add columns to campaign_leads
            print("Updating campaign_leads...")
            res_cl = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='campaign_leads'")).fetchall()
            cols_cl = [r[0] for r in res_cl]
            
            # Create Types if not exist (Generic check)
            try:
                conn.execute(text("CREATE TYPE followupstate AS ENUM ('SCHEDULED', 'CANCELLED', 'COMPLETED')"))
            except:
                pass
            try:
                conn.execute(text("CREATE TYPE cancelreason AS ENUM ('REPLIED', 'NEGATIVE_REPLY', 'UNSUBSCRIBE', 'BOOKED', 'BOUNCE', 'SUPPRESSED', 'MANUAL', 'SAFETY')"))
            except:
                pass

            if 'followup_state' not in cols_cl:
                conn.execute(text("ALTER TABLE campaign_leads ADD COLUMN followup_state followupstate NOT NULL DEFAULT 'SCHEDULED'"))
            if 'cancelled_at' not in cols_cl:
                conn.execute(text("ALTER TABLE campaign_leads ADD COLUMN cancelled_at TIMESTAMP NULL"))
            if 'cancel_reason' not in cols_cl:
                conn.execute(text("ALTER TABLE campaign_leads ADD COLUMN cancel_reason cancelreason NULL"))
            if 'cancel_detail' not in cols_cl:
                conn.execute(text("ALTER TABLE campaign_leads ADD COLUMN cancel_detail TEXT NULL"))
            if 'current_step' not in cols_cl:
                conn.execute(text("ALTER TABLE campaign_leads ADD COLUMN current_step INTEGER NOT NULL DEFAULT 0"))
            if 'next_scheduled_at' not in cols_cl:
                conn.execute(text("ALTER TABLE campaign_leads ADD COLUMN next_scheduled_at TIMESTAMP NULL"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_campaign_leads_next_scheduled_at ON campaign_leads (next_scheduled_at)"))
            if 'schedule_json' not in cols_cl:
                conn.execute(text("ALTER TABLE campaign_leads ADD COLUMN schedule_json JSONB NULL")) # Use JSONB if possible

            # 2. Update messages
            print("Updating messages...")
            res_m = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='messages'")).fetchall()
            cols_m = [r[0] for r in res_m]

            try:
                conn.execute(text("CREATE TYPE draftstatus AS ENUM ('GENERATED', 'EDITED', 'SENT', 'DISCARDED', 'SAVED_TO_GMAIL_DRAFT')"))
            except:
                pass
                
            if 'planned_send_at' not in cols_m:
                 conn.execute(text("ALTER TABLE messages ADD COLUMN planned_send_at TIMESTAMP NULL"))
            if 'cancelled' not in cols_m:
                 conn.execute(text("ALTER TABLE messages ADD COLUMN cancelled BOOLEAN NOT NULL DEFAULT FALSE"))
            if 'cancel_reason' not in cols_m:
                 conn.execute(text("ALTER TABLE messages ADD COLUMN cancel_reason VARCHAR(255) NULL"))
            if 'is_draft' not in cols_m:
                 conn.execute(text("ALTER TABLE messages ADD COLUMN is_draft BOOLEAN NOT NULL DEFAULT FALSE"))
            if 'draft_status' not in cols_m:
                 conn.execute(text("ALTER TABLE messages ADD COLUMN draft_status draftstatus NULL"))

            # Update Constraint
            try:
                conn.execute(text("ALTER TABLE messages DROP CONSTRAINT uq_message_idempotency"))
                print("Dropped old constraint")
            except:
                pass
            try:
                conn.execute(text("ALTER TABLE messages ADD CONSTRAINT uq_message_idempotency UNIQUE (campaign_lead_id, step_number, direction, is_draft)"))
                print("Added new constraint")
            except Exception as e:
                print(f"Constraint add warning: {e}")

            # 3. Create reply_drafts
            print("Creating reply_drafts...")
            res_t = conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_name='reply_drafts'")).fetchall()
            if not res_t:
                conn.execute(text("""
                    CREATE TABLE reply_drafts (
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
                    )
                """))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_reply_drafts_gmail_thread_id ON reply_drafts (gmail_thread_id)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_reply_drafts_id ON reply_drafts (id)"))

            # Update ReplyClassification Enum
            try:
                conn.execute(text("ALTER TYPE replyclassification ADD VALUE IF NOT EXISTS 'INTERESTED'"))
                conn.execute(text("ALTER TYPE replyclassification ADD VALUE IF NOT EXISTS 'QUESTION'"))
                conn.execute(text("ALTER TYPE replyclassification ADD VALUE IF NOT EXISTS 'OUT_OF_OFFICE'"))
            except Exception as e:
                print(f"Enum update warning: {e}")

            trans.commit()
            print("DB Fix completed successfully!")
            
        except Exception as e:
            trans.rollback()
            print(f"DB Fix failed: {e}")
            raise

if __name__ == "__main__":
    fix_db()
