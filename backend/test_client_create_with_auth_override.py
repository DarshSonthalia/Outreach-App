from fastapi.testclient import TestClient
from app.main import app
from app.utils.dependencies import get_current_user
from app.database import SessionLocal
from app.models import User, Workspace, Mailbox
from types import SimpleNamespace

# Prepare DB objects
session = SessionLocal()
try:
    user = session.query(User).filter(User.email == 'tc@example.com').first()
    if not user:
        user = User(email='tc@example.com', password_hash='x')
        session.add(user)
        session.commit()
        session.refresh(user)

    workspace = session.query(Workspace).filter(Workspace.user_id == user.id).first()
    if not workspace:
        workspace = Workspace(user_id=user.id, name='TC Workspace')
        session.add(workspace)
        session.commit()
        session.refresh(workspace)

    mailbox = session.query(Mailbox).filter(Mailbox.workspace_id == workspace.id).first()
    if not mailbox:
        mailbox = Mailbox(workspace_id=workspace.id, email='noreply@example.com', is_active=True)
        session.add(mailbox)
        session.commit()
        session.refresh(mailbox)

    user_id = user.id
    workspace_id = workspace.id
    mailbox_id = mailbox.id
finally:
    session.close()

# override dependency: return simple object with .id to avoid detached instances
def _fake_current_user():
    return SimpleNamespace(id=user_id)

app.dependency_overrides[get_current_user] = _fake_current_user

client = TestClient(app)

payload = {
    'name': 'tc-smoke-ui-campaign',
    'mailbox_id': mailbox_id,
    'lead_ids': [],
    'customer_info': {'company': 'ACME-TC', 'note': 'testclient'}
}

resp = client.post(f'/api/campaigns?workspace_id={workspace_id}', json=payload)
print('status', resp.status_code)
print(resp.text)

if resp.status_code in (200,201):
    cid = resp.json().get('id')
    getr = client.get(f'/api/campaigns/{cid}')
    print('get status', getr.status_code)
    print(getr.text)
