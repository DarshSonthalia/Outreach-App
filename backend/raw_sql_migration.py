
import os
import logging
import sqlalchemy as sa
from sqlalchemy.sql import text

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_database_url():
    # Try to read .env from parent directory
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env')
    db_url = "postgresql://outreach:outreach_dev@localhost:5432/outreach_db" # Default
    
    if os.path.exists(env_path):
        try:
            with open(env_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('DATABASE_URL='):
                        db_url = line.split('=', 1)[1].strip().strip('"').strip("'")
                        logger.info(f"Found DATABASE_URL in .env: {db_url}")
                        break
        except Exception as e:
            logger.warning(f"Could not read .env: {e}")
            
    return db_url

def raw_apply():
    logger.info("Starting RAW SQL migration application (No Pydantic)...")
    
    db_url = get_database_url()
    engine = sa.create_engine(db_url)
    
    with engine.connect() as conn:
        # 1. Update Workspaces table
        try:
            # Check if columns exist
            res = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='workspaces'")).fetchall()
            cols = [r[0] for r in res]
            
            if 'warmup_enabled' not in cols:
                logger.info("Adding warmup_enabled to workspaces...")
                conn.execute(text("ALTER TABLE workspaces ADD COLUMN warmup_enabled BOOLEAN NOT NULL DEFAULT FALSE"))
                conn.commit()
            
            if 'warmup_start_date' not in cols:
                logger.info("Adding warmup_start_date to workspaces...")
                conn.execute(text("ALTER TABLE workspaces ADD COLUMN warmup_start_date TIMESTAMP NULL"))
                conn.commit()
                
        except Exception as e:
            logger.error(f"Error updating workspaces: {e}")
            conn.rollback()

        # 2. Update Domains table
        try:
            res = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='domains'")).fetchall()
            cols = [r[0] for r in res]
            
            if 'warmup_day' not in cols:
                logger.info("Adding warmup_day to domains...")
                conn.execute(text("ALTER TABLE domains ADD COLUMN warmup_day INTEGER NOT NULL DEFAULT 0"))
                conn.commit()
                
            if 'warmup_completed' not in cols:
                logger.info("Adding warmup_completed to domains...")
                conn.execute(text("ALTER TABLE domains ADD COLUMN warmup_completed BOOLEAN NOT NULL DEFAULT FALSE"))
                conn.commit()

        except Exception as e:
            logger.error(f"Error updating domains: {e}")
            conn.rollback()

        # 3. Update Alembic Version to keep it in sync
        try:
            logger.info("Updating alembic_version table...")
            # Check current version
            current_ver = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
            logger.info(f"Current alembic version: {current_ver}")
            
            if current_ver != '005_add_warmup_fields':
                conn.execute(text("UPDATE alembic_version SET version_num = '005_add_warmup_fields'"))
                conn.commit()
                logger.info("Successfully updated alembic_version to '005_add_warmup_fields'")
            else:
                logger.info("Alembic version already up to date.")
                
        except Exception as e:
            logger.error(f"Error updating alembic_version: {e}")
            conn.rollback()

    logger.info("Raw SQL migration completed.")

if __name__ == "__main__":
    raw_apply()
