from app.database import SessionLocal
from app.models import User, Workspace, Message, CampaignLead
from app.enums import MessageDirection

def diagnose():
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email=="sonthaliadarsh@gmail.com").first()
        if not user:
            print("User not found.")
            return
        
        print(f"User: {user.email} (ID: {user.id})")
        print(f"Workspaces: {[(w.id, w.name) for w in user.workspaces]}")
        
        for w in user.workspaces:
            inbound_count = db.query(Message).join(CampaignLead).filter(
                CampaignLead.campaign_id.in_([c.id for c in w.campaigns]),
                Message.direction == MessageDirection.INBOUND
            ).count()
            print(f"Workspace {w.id} ({w.name}) has {inbound_count} inbound messages.")
            
    finally:
        db.close()

if __name__ == "__main__":
    diagnose()
