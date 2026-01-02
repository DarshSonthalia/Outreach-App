from app.database import SessionLocal
from app.models import Mailbox
from app.services.gmail_service import GmailService
from app.workers.reply_worker import process_incoming_message
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def resync_mailbox(email: str):
    db = SessionLocal()
    try:
        mailbox = db.query(Mailbox).filter(Mailbox.email == email).first()
        if not mailbox:
            print(f"Mailbox {email} not found")
            return
            
        service, _ = GmailService.get_gmail_client(mailbox, db)
        if not service:
            print("Failed to get Gmail service")
            return
            
        print(f"Starting resync for {email}...")
        
        # 1. Fetch recent messages (last 24 hours)
        # Gmail query: 'after:2025/12/30' (careful with date format)
        yesterday = (datetime.utcnow() - timedelta(days=1)).strftime('%Y/%m/%d')
        query = f"after:{yesterday}"
        
        results = service.users().messages().list(userId='me', q=query).execute()
        messages = results.get('messages', [])
        
        print(f"Found {len(messages)} messages in query: {query}")
        
        processed_count = 0
        for msg_summary in messages:
            msg_id = msg_summary['id']
            # Fetch full message
            msg = service.users().messages().get(userId='me', id=msg_id, format='full').execute()
            parsed_msg = GmailService._parse_message(msg)
            
            # Process it
            # Note: process_incoming_message handles deduplication internally (checking gmail_message_id)
            process_incoming_message(db, mailbox, parsed_msg)
            processed_count += 1
            
        db.commit()
        
        # 2. Update history ID to latest
        new_history_id = GmailService.get_mailbox_history_id(service)
        mailbox.last_history_id = new_history_id
        mailbox.last_polled_at = datetime.utcnow()
        db.commit()
        
        print(f"Resync complete. Processed {processed_count} messages. New History ID: {new_history_id}")
        
    finally:
        db.close()

if __name__ == "__main__":
    resync_mailbox("sonthaliadarsh@gmail.com")
