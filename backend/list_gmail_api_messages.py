from app.database import SessionLocal
from app.models import Mailbox
from app.services.gmail_service import GmailService
import json

def list_recent_gmail_messages():
    db = SessionLocal()
    try:
        mailbox = db.query(Mailbox).filter(Mailbox.email == "sonthaliadarsh@gmail.com").first()
        if not mailbox:
            print("Mailbox not found")
            return
        
        service, _ = GmailService.get_gmail_client(mailbox, db)
        if not service:
            print("Failed to get Gmail service")
            return
        
        # List last 10 messages
        results = service.users().messages().list(userId='me', maxResults=10).execute()
        messages = results.get('messages', [])
        
        print(f"Found {len(messages)} recent messages.")
        for msg in messages:
            m = service.users().messages().get(userId='me', id=msg['id'], format='metadata', metadataHeaders=['Subject', 'From', 'Date']).execute()
            headers = m.get('payload', {}).get('headers', [])
            labels = m.get('labelIds', [])
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
            sender = next((h['value'] for h in headers if h['name'] == 'From'), 'No Sender')
            print(f"ID: {msg['id']}, ThreadID: {msg['threadId']}, Labels: {labels}, Subject: {subject}, From: {sender}")
            
    finally:
        db.close()

if __name__ == "__main__":
    list_recent_gmail_messages()
