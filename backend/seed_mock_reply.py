from app.database import SessionLocal
from app.models import (
    Mailbox, Campaign, CampaignLead, Message, Lead,
    MessageDirection, ReplyClassification
)
from datetime import datetime, timedelta

def seed_mock_reply():
    db = SessionLocal()
    try:
        # Find an existing campaign lead in Workspace 1
        campaign_lead = db.query(CampaignLead).join(Campaign).filter(
            Campaign.workspace_id == 1
        ).first()
        if not campaign_lead:
            # Create a mock campaign lead if missing
            print("No campaign lead found in Workspace 1. Please ensure a campaign is created.")
            return
        
        # 1. Create an outbound message if not exists
        outbound = db.query(Message).filter(
            Message.campaign_lead_id == campaign_lead.id,
            Message.direction == MessageDirection.OUTBOUND
        ).first()
        
        if not outbound:
            outbound = Message(
                campaign_lead_id=campaign_lead.id,
                direction=MessageDirection.OUTBOUND,
                step_number=0,
                gmail_message_id="mock_outbound_123",
                gmail_thread_id="mock_thread_456",
                subject="Initial Outreach",
                body="Hello! Are you interested in our product?",
                sent_at=datetime.utcnow() - timedelta(days=1)
            )
            db.add(outbound)
            db.flush()
        
        thread_id = outbound.gmail_thread_id or "mock_thread_456"
        
        # 2. Add an inbound reply
        reply = Message(
            campaign_lead_id=campaign_lead.id,
            direction=MessageDirection.INBOUND,
            step_number=-1,
            gmail_message_id="mock_inbound_789",
            gmail_thread_id=thread_id,
            subject="Re: Initial Outreach",
            body="Yes, I am interested! Let's talk.",
            classification=ReplyClassification.BOOKING_INTENT,
            received_at=datetime.utcnow()
        )
        db.add(reply)
        db.commit()
        print(f"Mock reply created in thread {thread_id} for lead {campaign_lead.lead.email}")
        
    finally:
        db.close()

if __name__ == "__main__":
    seed_mock_reply()
