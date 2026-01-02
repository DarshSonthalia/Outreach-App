from app.database import SessionLocal
from app.models import Mailbox
from app.services.gmail_service import GmailService

def inspect_message_labels():
    db = SessionLocal()
    try:
        mailbox = db.query(Mailbox).filter(Mailbox.email == "sonthaliadarsh@gmail.com").first()
        service, _ = GmailService.get_gmail_client(mailbox, db)
        
        msg_id = "19b75c50742f56ab"
        msg = service.users().messages().get(userId='me', id=msg_id).execute()
        print(f"Message ID: {msg_id}")
        print(f"Thread ID: {msg.get('threadId')}")
        print(f"Labels: {msg.get('labelIds')}")
        
    finally:
        db.close()

if __name__ == "__main__":
    inspect_message_labels()
