import os
import json
import requests

# Read backend URL and API token from environment or default to localhost
BASE = os.environ.get('BACKEND_BASE', 'http://host.docker.internal:8000')
API_TOKEN = os.environ.get('BACKEND_API_TOKEN')

headers = {'Content-Type': 'application/json'}
if API_TOKEN:
    headers['Authorization'] = f'Bearer {API_TOKEN}'

payload = {
    'workspace_id': 1,
    'mailbox_id': 1,
    'name': 'smoke-test-campaign',
    'description': 'Smoke test campaign for customer_info persistence',
    'subject': 'Hello from smoke test',
    'body': 'This is a test body',
    'followup_enabled': False,
    'customer_info': {'company': 'ACME', 'industry': 'testing', 'notes': 'created-by-smoke'}
}

print('Creating campaign...')
resp = requests.post(f'{BASE}/api/campaigns', headers=headers, data=json.dumps(payload))
print('status', resp.status_code)
print(resp.text)

if resp.status_code == 200 or resp.status_code == 201:
    c = resp.json()
    cid = c.get('id')
    print('Fetching campaign', cid)
    r2 = requests.get(f'{BASE}/api/campaigns/{cid}', headers=headers)
    print('status', r2.status_code)
    print(r2.text)
else:
    print('Create failed')
