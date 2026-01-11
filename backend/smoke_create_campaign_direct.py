from app.database import SessionLocal
from app.models.models import Campaign
from datetime import datetime

session = SessionLocal()
try:
    c = Campaign(
        workspace_id=1,
        mailbox_id=1,
        name='smoke-test-campaign-db',
        subject='Hello DB smoke',
        body='This is a test body inserted directly',
        followup_enabled=False,
        customer_info={'company': 'ACME', 'industry': 'testing', 'notes': 'created-by-smoke-db'},
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    session.add(c)
    session.commit()
    session.refresh(c)
    print('Created campaign id=', c.id)
    print('customer_info=', c.customer_info)

    # fetch back
    fetched = session.query(Campaign).filter_by(id=c.id).first()
    print('Fetched customer_info=', fetched.customer_info)
finally:
    session.close()
