import asyncio
import json
from app.database import SessionLocal
from app.models import User
from app.models.models import Campaign, Event
from app.routers.campaigns_ai import ai_generate_draft, DraftRequest


db = SessionLocal()
user = db.query(User).filter(User.id==5).first()
if not user:
    raise SystemExit('Test user not found')
# Create campaign
c = Campaign(workspace_id=7, mailbox_id=6, name='smoke-customer-info')
db.add(c)
db.commit()
db.refresh(c)
print('CAMPAIGN_ID:'+str(c.id))
# Add campaign customer_info event
ci = {
    'what_you_sell': 'A lightweight analytics add-on',
    'target_industry': 'SaaS',
    'target_role': 'Head of Sales',
    'offer_type': 'free trial',
    'target_region': 'EMEA'
}
e = Event(entity_type='campaign', entity_id=c.id, action='CAMPAIGN_CUSTOMER_INFO', details=ci, explanation='Smoke test customer info')
db.add(e)
db.commit()
req = DraftRequest()
res = asyncio.run(ai_generate_draft(c.id, req, current_user=user, db=db))
print('DRAFT:', json.dumps(res.dict()))
