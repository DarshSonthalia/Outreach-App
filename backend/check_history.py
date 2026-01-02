from app.database import SessionLocal
from app.models import Mailbox
from app.services.gmail_service import GmailService
import json

def check_history():
    db = SessionLocal()
    try:
        mailbox = db.query(Mailbox).filter(Mailbox.email == "sonthaliadarsh@gmail.com").first()
        service, _ = GmailService.get_gmail_client(mailbox, db)
        
        last_id = "2843939"
        print(f"Checking history since: {last_id}")
        
        history_response = service.users().history().list(
            userId="me",
            startHistoryId=last_id,
            historyTypes=["messageAdded"]
        ).execute()
        
        histories = history_response.get("history", [])
        print(f"Found {len(histories)} history segments.")
        
        for h in histories:
            added = h.get("messagesAdded", [])
            for a in added:
                msg = a.get("message", {})
                print(f"History ID {h.get('id')}: Message Added {msg.get('id')} in Thread {msg.get('threadId')}")
        
    finally:
        db.close()

if __name__ == "__main__":
    check_history()
