import requests
import time

BASE_URL = "http://localhost:8000/api"

def run_debug():
    # 1. Login
    print("Logging in...")
    try:
        login_resp = requests.post(f"{BASE_URL}/auth/login", json={
            "email": "test_final_bcrypt_fix@example.com",
            "password": "A"*100
        })
    except requests.exceptions.ConnectionError:
        print("Backend not ready yet...")
        return

    if login_resp.status_code != 200:
        print(f"Login failed: {login_resp.text}")
        return

    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("Login success.")

    # 2. Get Workspace
    ws_resp = requests.get(f"{BASE_URL}/workspaces/", headers=headers)
    workspace_id = ws_resp.json()[0]["id"]
    print(f"Using Workspace ID: {workspace_id}")

    # 3. Get Mailbox
    mb_resp = requests.get(f"{BASE_URL}/mailboxes/?workspace_id={workspace_id}", headers=headers)
    mailboxes = mb_resp.json()
    if not mailboxes:
        print("No mailboxes found. Cannot test campaign.")
        return
    mailbox_id = mailboxes[0]["id"]
    print(f"Using Mailbox ID: {mailbox_id}")

    # 4. Create a Dummy Lead (if not exists)
    # Just list leads and pick one, or create one
    leads_resp = requests.get(f"{BASE_URL}/leads/?workspace_id={workspace_id}&limit=1", headers=headers)
    leads = leads_resp.json()
    if leads:
        lead_id = leads[0]["id"]
        print(f"Using existing Lead ID: {lead_id}")
    else:
        # Create one (implicitly via map columns simulation? or ensure one exists)
        # Assuming DB has leads from previous tests.
        print("No leads found. Please run debug_csv.py first.")
        return

    # 5. Create Campaign
    print("Creating Campaign...")
    data = {
        "name": f"Debug Campaign {time.time()}",
        "mailbox_id": mailbox_id,
        "lead_ids": [lead_id]
    }
    
    resp = requests.post(f"{BASE_URL}/campaigns/?workspace_id={workspace_id}", headers=headers, json=data)
    
    print(f"Create Campaign Status: {resp.status_code}")
    print(f"Create Campaign Body: {resp.text}")

if __name__ == "__main__":
    run_debug()
