
import psycopg2
import logging
import sys

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

def check_campaign_issues():
    conn = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        logger.info("Checking campaign_leads for issues...")
        
        # Check for failed or retrying leads
        cursor.execute("""
            SELECT cl.id, c.name, l.email, cl.status, cl.retry_count, cl.last_sent_at
            FROM campaign_leads cl
            JOIN campaigns c ON cl.campaign_id = c.id
            JOIN leads l ON cl.lead_id = l.id
            WHERE cl.status IN ('failed', 'completed') 
            AND cl.retry_count > 0
            ORDER BY cl.updated_at DESC
            LIMIT 10
        """)
        
        issues = cursor.fetchall()
        
        if issues:
            logger.info("\n=== FAILED/RETRYING LEADS ===")
            for row in issues:
                logger.info(f"ID: {row[0]} | Campaign: {row[1]} | To: {row[2]}")
                logger.info(f"Status: {row[3]} | Retries: {row[4]}")
                logger.info("-" * 30)
        else:
            logger.info("\nNo failed leads with retries found.")
            
        # Check for stuck PENDING items with past next_action_at
        cursor.execute("""
            SELECT COUNT(*) 
            FROM campaign_leads 
            WHERE status = 'pending' 
            AND next_action_at < NOW() - INTERVAL '10 minutes'
        """)
        stuck_count = cursor.fetchone()[0]
        
        if stuck_count > 0:
            logger.info(f"\n⚠️ WARNING: {stuck_count} leads are PENDING but overdue by >10 mins.")
            logger.info("This suggests the worker might be stuck or crashing.")
        else:
             logger.info("\nNo stuck pending leads found.")

    except Exception as e:
        logger.error(f"Error: {e}")
    finally:
        if conn: conn.close()

if __name__ == "__main__":
    check_campaign_issues()
