import asyncio
import json
from app.database import SessionLocal
from app.models import User
from app.routers.campaigns_ai import ai_generate_draft, DraftRequest


db = SessionLocal()
user = db.query(User).filter(User.id==5).first()
if not user:
    raise SystemExit('Test user not found')
req = DraftRequest()
result = asyncio.run(ai_generate_draft(29, req, current_user=user, db=db))
print('DRAFT_FROM_AI_ENDPOINT:'+json.dumps(result.dict()))
