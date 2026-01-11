
import psycopg2
import logging
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

def count_todays_emails():
    conn = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        logger.info("Counting emails sent today (UTC)...")
        
        cursor.execute("""
            SELECT COUNT(*) 
            FROM messages 
            WHERE sent_at >= CURRENT_DATE 
            AND direction = 'OUTBOUND'
        """)
        
        count = cursor.fetchone()[0]
        logger.info(f"\nTotal Outbound Emails Sent Today (UTC): {count}")
        
        if count > 5:
            logger.info("⚠️ ALERT: Count exceeds Day 1 limit of 5!")
        else:
            logger.info("✅ Count is within Day 1 limit.")

    except Exception as e:
        logger.error(f"Error: {e}")
    finally:
        if conn: conn.close()

if __name__ == "__main__":
    count_todays_emails()
