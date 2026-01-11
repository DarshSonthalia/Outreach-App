import asyncio, json
from app.database import SessionLocal
from app.models.models import Campaign, Event
from app.models import User
from app.routers.campaigns_ai import ai_generate_draft, DraftRequest

db = SessionLocal()
# create campaign
c = Campaign(workspace_id=7, mailbox_id=6, name='smoke-customer-info-2')
db.add(c)
db.commit()
db.refresh(c)
ci = {'what_you_sell':'Custom analytics for ACME','target_industry':'Manufacturing','target_role':'CTO','offer_type':'audit','target_region':'US'}
e = Event(entity_type='campaign', entity_id=c.id, action='CAMPAIGN_CUSTOMER_INFO', details=ci, explanation='preview')
db.add(e)
db.commit()
# build preview
ws = db.query(Campaign).filter(Campaign.id==c.id).first().workspace
wizard_answers = getattr(ws,'wizard_answers',None) or {}
what_you_sell = wizard_answers.get('what_you_sell') or getattr(ws,'what_you_sell','your product/service')
what_you_sell = ci.get('what_you_sell') or what_you_sell
target_industry = ci.get('target_industry') or wizard_answers.get('target_industry') or getattr(ws,'target_industry','general')
target_role = ci.get('target_role') or wizard_answers.get('target_role') or getattr(ws,'target_role','decision maker')
offer_type = ci.get('offer_type') or wizard_answers.get('offer_type') or getattr(ws,'offer_type','consultation')
target_region = ci.get('target_region') or wizard_answers.get('target_region') or getattr(ws,'target_region','global')
input_preview = f"CONTEXT:\n- What we sell: {what_you_sell}\n- Target industry: {target_industry}\n- Target role: {target_role}\n- Offer type: {offer_type}\n- Target region: {target_region}\n"
print('PROMPT_PREVIEW:')
print(input_preview)
# call ai_generate_draft
user = db.query(User).filter(User.id==5).first()
req = DraftRequest()
res = asyncio.run(ai_generate_draft(c.id, req, current_user=user, db=db))
print('DRAFT:', json.dumps(res.dict()))
