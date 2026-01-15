import logging
import sqlalchemy as sa
from sqlalchemy.sql import text
from app.database import engine

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def force_apply():
    logger.info("Starting manual migration application (006)...")
    
    with engine.connect() as conn:
        trans = conn.begin()
        try:
            # 1. Update CampaignLeads table
            logger.info("Checking campaign_leads columns...")
            res_cl = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='campaign_leads'")).fetchall()
            cols_cl = [r[0] for r in res_cl]
            
            # Enums might need creation
            try:
                conn.execute(text("CREATE TYPE followupstate AS ENUM ('SCHEDULED', 'CANCELLED', 'COMPLETED')"))
            except Exception:
                logger.info("Enum followupstate likely exists or error ignored.")

            try:
                conn.execute(text("CREATE TYPE cancelreason AS ENUM ('REPLIED', 'NEGATIVE_REPLY', 'UNSUBSCRIBE', 'BOOKED', 'BOUNCE', 'SUPPRESSED', 'MANUAL', 'SAFETY')"))
            except Exception:
                logger.info("Enum cancelreason likely exists or error ignored.")
            
            if 'followup_state' not in cols_cl:
                logger.info("Adding followup_state...")
                conn.execute(text("ALTER TABLE campaign_leads ADD COLUMN followup_state followupstate NOT NULL DEFAULT 'SCHEDULED'"))

            if 'cancelled_at' not in cols_cl:
                logger.info("Adding cancelled_at...")
                conn.execute(text("ALTER TABLE campaign_leads ADD COLUMN cancelled_at TIMESTAMP NULL"))
                
            if 'cancel_reason' not in cols_cl:
                logger.info("Adding cancel_reason...")
                conn.execute(text("ALTER TABLE campaign_leads ADD COLUMN cancel_reason cancelreason NULL"))
                
            if 'cancel_detail' not in cols_cl:
                logger.info("Adding cancel_detail...")
                conn.execute(text("ALTER TABLE campaign_leads ADD COLUMN cancel_detail TEXT NULL"))
                
            if 'current_step' not in cols_cl:
                logger.info("Adding current_step...")
                conn.execute(text("ALTER TABLE campaign_leads ADD COLUMN current_step INTEGER NOT NULL DEFAULT 0"))
                
            if 'next_scheduled_at' not in cols_cl:
                logger.info("Adding next_scheduled_at...")
                conn.execute(text("ALTER TABLE campaign_leads ADD COLUMN next_scheduled_at TIMESTAMP NULL"))
                conn.execute(text("CREATE INDEX ix_campaign_leads_next_scheduled_at ON campaign_leads (next_scheduled_at)"))

            if 'schedule_json' not in cols_cl:
                logger.info("Adding schedule_json...")
                conn.execute(text("ALTER TABLE campaign_leads ADD COLUMN schedule_json JSON NULL"))

            # 2. Update Messages table
            logger.info("Checking messages columns...")
            res_m = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='messages'")).fetchall()
            cols_m = [r[0] for r in res_m]
            
            try:
                conn.execute(text("CREATE TYPE draftstatus AS ENUM ('GENERATED', 'EDITED', 'SENT', 'DISCARDED', 'SAVED_TO_GMAIL_DRAFT')"))
            except Exception:
                logger.info("Enum draftstatus likely exists.")

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

            # Update unique constraint
            # Check if constraint exists, hard to do portably in raw SQL across versions but we assume standard naming 'uq_message_idempotency'
            try:
                conn.execute(text("ALTER TABLE messages DROP CONSTRAINT uq_message_idempotency"))
                logger.info("Dropped old unique constraint.")
            except Exception as e:
                logger.info(f"Constraint drop failed (maybe didn't exist): {e}")
                
            try:
                # Add new constraint with is_draft
                conn.execute(text("ALTER TABLE messages ADD CONSTRAINT uq_message_idempotency UNIQUE (campaign_lead_id, step_number, direction, is_draft)"))
                logger.info("Created new unique constraint.")
            except Exception as e:
                 logger.info(f"Constraint creation failed: {e}")
            
            # 3. Create reply_drafts
            logger.info("Checking reply_drafts table...")
            res_t = conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_name='reply_drafts'")).fetchall()
            if not res_t:
                logger.info("Creating reply_drafts table...")
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
                        risk_flags JSON NULL,
                        classification VARCHAR(100) NULL,
                        created_at TIMESTAMP DEFAULT now(),
                        updated_at TIMESTAMP DEFAULT now()
                    )
                """))
                conn.execute(text("CREATE INDEX ix_reply_drafts_gmail_thread_id ON reply_drafts (gmail_thread_id)"))
                conn.execute(text("CREATE INDEX ix_reply_drafts_id ON reply_drafts (id)"))

            # Update enum values for ReplyClassification in DB if needed?
            # Enums are static in Postgres. If I added 'INTERESTED', etc. to python code, I need to add them to DB enum type 'replyclassification'.
            # ALTER TYPE replyclassification ADD VALUE 'INTERESTED';
            try:
                conn.execute(text("ALTER TYPE replyclassification ADD VALUE IF NOT EXISTS 'INTERESTED'"))
                conn.execute(text("ALTER TYPE replyclassification ADD VALUE IF NOT EXISTS 'QUESTION'"))
                conn.execute(text("ALTER TYPE replyclassification ADD VALUE IF NOT EXISTS 'OUT_OF_OFFICE'"))
            except Exception as e:
                logger.info(f"Updating replyclassification enum failed: {e}")
            
            # 4. Update Alembic Version
            logger.info("Updating alembic_version table...")
            conn.execute(text("UPDATE alembic_version SET version_num = '006_add_followup_and_drafts'"))
            
            trans.commit()
            logger.info("Manual migration 006 completed successfully.")
            
        except Exception as e:
            trans.rollback()
            logger.error(f"Migration failed: {e}")
            raise e

if __name__ == "__main__":
    force_apply()
