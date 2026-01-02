from app.database import SessionLocal
from app.models import CampaignLead, Campaign, Lead, CampaignLeadStatus
from datetime import datetime

def check_next_send():
    db = next(SessionLocal())
    try:
        next_lead = db.query(CampaignLead, Campaign, Lead)\
            .join(Campaign, CampaignLead.campaign_id == Campaign.id)\
            .join(Lead, CampaignLead.lead_id == Lead.id)\
            .filter(CampaignLead.status == CampaignLeadStatus.PENDING)\
            .filter(CampaignLead.next_action_at != None)\
            .order_by(CampaignLead.next_action_at.asc())\
            .first()
        
        if next_lead:
            cl, c, l = next_lead
            print(f"NEXT_SEND_TIME: {cl.next_action_at}")
            print(f"CAMPAIGN: {c.name}")
            print(f"LEAD: {l.email}")
        else:
            print("NO_PENDING_SENDS")
    finally:
        db.close()

if __name__ == "__main__":
    check_next_send()
