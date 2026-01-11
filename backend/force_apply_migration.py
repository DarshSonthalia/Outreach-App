import logging
import sqlalchemy as sa
from sqlalchemy.sql import text
from app.database import engine

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def force_apply():
    logger.info("Starting manual migration application...")
    
    with engine.connect() as conn:
        # 1. Update Workspaces table
        try:
            # Check if columns exist
            res = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='workspaces'")).fetchall()
            cols = [r[0] for r in res]
            
            if 'warmup_enabled' not in cols:
                logger.info("Adding warmup_enabled to workspaces...")
                conn.execute(text("ALTER TABLE workspaces ADD COLUMN warmup_enabled BOOLEAN NOT NULL DEFAULT FALSE"))
            
            if 'warmup_start_date' not in cols:
                logger.info("Adding warmup_start_date to workspaces...")
                conn.execute(text("ALTER TABLE workspaces ADD COLUMN warmup_start_date TIMESTAMP NULL"))
                
        except Exception as e:
            logger.error(f"Error updating workspaces: {e}")

        # 2. Update Domains table
        try:
            res = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='domains'")).fetchall()
            cols = [r[0] for r in res]
            
            if 'warmup_day' not in cols:
                logger.info("Adding warmup_day to domains...")
                conn.execute(text("ALTER TABLE domains ADD COLUMN warmup_day INTEGER NOT NULL DEFAULT 0"))
                
            if 'warmup_completed' not in cols:
                logger.info("Adding warmup_completed to domains...")
                conn.execute(text("ALTER TABLE domains ADD COLUMN warmup_completed BOOLEAN NOT NULL DEFAULT FALSE"))

        except Exception as e:
            logger.error(f"Error updating domains: {e}")

        # 3. Update Alembic Version to keep it in sync
        try:
            logger.info("Updating alembic_version table...")
            # Check if table exists
            conn.execute(text("UPDATE alembic_version SET version_num = '005_add_warmup_fields'"))
            conn.commit()
            logger.info("Successfully updated alembic_version to '005_add_warmup_fields'")
        except Exception as e:
            logger.error(f"Error updating alembic_version: {e}")
            conn.rollback()

    logger.info("Manual migration completed.")

if __name__ == "__main__":
    force_apply()
