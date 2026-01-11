from fastapi.testclient import TestClient
from app.main import app
import json

client = TestClient(app)

payload = {
    'workspace_id': 1,
    'mailbox_id': 1,
    'name': 'tc-smoke-ui-campaign',
    'subject': 'TC smoke subject',
    'body': 'TC smoke body',
    'followup_enabled': False,
    'customer_info': {'company': 'ACME-TC', 'note': 'testclient'}
}

resp = client.post('/api/campaigns', json=payload)
print('status', resp.status_code)
print(resp.text)

if resp.status_code in (200,201):
    cid = resp.json().get('id')
    getr = client.get(f'/api/campaigns/{cid}')
    print('get status', getr.status_code)
    print(getr.text)
else:
    print('create failed')
