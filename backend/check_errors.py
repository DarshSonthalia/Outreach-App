
import psycopg2
import logging
import sys
from datetime import datetime, timedelta

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

def check_recent_errors():
    conn = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Look for recent events in the last hour
        logger.info("checking recent events (last 1 hour)...")
        
        # Check for WARMUP_LIMIT_REACHED
        cursor.execute("""
            SELECT entity_type, entity_id, action, details, explanation, timestamp 
            FROM events 
            WHERE timestamp > NOW() - INTERVAL '5 minutes'
            AND action = 'WARMUP_LIMIT_REACHED'
            ORDER BY timestamp DESC
            LIMIT 5
        """)
        warmup_events = cursor.fetchall()
        
        if warmup_events:
            logger.info("\n=== WARMUP LIMIT EVENTS ===")
            for row in warmup_events:
                logger.info(f"[{row[5]}] {row[2]}: {row[4]}")
        else:
            logger.info("\nNo recent warm-up limit events found.")

        # Check for other errors
        cursor.execute("""
            SELECT entity_type, entity_id, action, details, explanation, timestamp 
            FROM events 
            WHERE timestamp > NOW() - INTERVAL '1 hour'
            AND (action ILIKE '%error%' OR action ILIKE '%fail%' OR action ILIKE '%reauth%')
            ORDER BY timestamp DESC
            LIMIT 10
        """)
        error_events = cursor.fetchall()
        
        if error_events:
            logger.info("\n=== RECENT ERRORS/FAILURES ===")
            for row in error_events:
                logger.info(f"[{row[5]}] Action: {row[2]}")
                logger.info(f"Details: {row[3]}")
                logger.info(f"Explanation: {row[4]}")
                logger.info("-" * 30)
        else:
            logger.info("\nNo other recent errors found.")

    except Exception as e:
        logger.error(f"Error: {e}")
    finally:
        if conn: conn.close()

if __name__ == "__main__":
    check_recent_errors()
