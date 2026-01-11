
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

def inspect_schema():
    conn = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        logger.info("Columns in 'mailboxes' table:")
        cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name='mailboxes'")
        cols = cursor.fetchall()
        for c in cols:
            logger.info(f"- {c[0]}")

    except Exception as e:
        logger.error(f"Error: {e}")
    finally:
        if conn: conn.close()

if __name__ == "__main__":
    inspect_schema()
