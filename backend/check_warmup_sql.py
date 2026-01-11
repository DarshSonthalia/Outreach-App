
import psycopg2
import logging
import sys
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

DB_CONFIG = {
    "dbname": "outreach_db",
    "user": "outreach",
    "password": "outreach_secure_2024",
    "host": "localhost",
    "port": "5432"
}

def check_live_status():
    conn = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Get latest workspace
        logger.info("Querying latest workspace...")
        cursor.execute("""
            SELECT id, name, created_at, warmup_enabled, warmup_start_date 
            FROM workspaces 
            ORDER BY created_at DESC 
            LIMIT 1
        """)
        row = cursor.fetchone()
        
        if not row:
            logger.info("❌ No workspaces found")
            return

        ws_id, name, created, enabled, start_date = row
        logger.info(f"=== Latest Workspace: '{name}' ===")
        logger.info(f"ID: {ws_id}")
        logger.info(f"Created: {created}")
        logger.info(f"Warmup Enabled: {enabled}")
        logger.info(f"Start Date: {start_date}")
        
        if enabled: 
             logger.info("✅ PASS: Warmup Enabled is TRUE")
        else:
             logger.info("❌ FAIL: Warmup Enabled is FALSE")

        # Check domains
        logger.info("\nChecking domains...")
        # Join on string match since there's no FK
        cursor.execute("""
            SELECT d.domain, d.warmup_day, d.warmup_completed
            FROM domains d
            JOIN mailboxes m ON d.domain = substring(m.email from position('@' in m.email)+1)
            WHERE m.workspace_id = %s
        """, (ws_id,))
        
        domains = cursor.fetchall()
        if not domains:
            logger.info("❌ No domains found for this workspace.")
        
        for d_domain, day, complete in domains:
            logger.info(f"\n--- Domain: {d_domain} ---")
            logger.info(f"Warmup Day: {day}")
            logger.info(f"Completed: {complete}")
            
            # Simple calc check
            if start_date:
                # Naive day diff
                diff = (datetime.utcnow() - start_date).days + 1
                logger.info(f"(Calculated Day roughly: {diff})")
                
    except Exception as e:
        logger.error(f"Error: {e}")
    finally:
        if conn: conn.close()

if __name__ == "__main__":
    check_live_status()
