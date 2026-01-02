import requests
import sys

BASE_URL = "http://localhost:8000/api"

def run_debug():
    # 1. Login
    print("Logging in...")
    login_resp = requests.post(f"{BASE_URL}/auth/login", json={
        "email": "test_final_bcrypt_fix@example.com",
        "password": "A"*100
    })
    
    if login_resp.status_code != 200:
        print(f"Login failed: {login_resp.text}")
        return

    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("Login success.")

    # 2. Get/Create Workspace
    print("Listing workspaces...")
    ws_resp = requests.get(f"{BASE_URL}/workspaces/", headers=headers)
    workspaces = ws_resp.json()
    
    if not workspaces:
        print("Creating workspace...")
        create_resp = requests.post(f"{BASE_URL}/workspaces/", headers=headers, json={"name": "Debug WS"})
        workspace_id = create_resp.json()["id"]
    else:
        workspace_id = workspaces[0]["id"]
    
    print(f"Using Workspace ID: {workspace_id}")

    # 3. Simulate Setup Update (The failing step)
    print("Sending PUT setup...")
    payload = {
        "what_you_sell": "AI Services",
        "target_industry": "SaaS",
        "target_role": "CTO",
        "target_region": "USA",
        "offer_type": "demo",
        "safety_preference": "Medium - Balanced (recommended)", # INVALID
        "has_leads": False,
        "meeting_days": None,
        "meeting_time_start": None,
        "meeting_time_end": None
    }
    
    setup_resp = requests.put(
        f"{BASE_URL}/workspaces/{workspace_id}/setup", 
        headers=headers, 
        json=payload
    )
    
    print(f"Setup Response Status: {setup_resp.status_code}")
    print(f"Setup Response Body: {setup_resp.text}")

if __name__ == "__main__":
    run_debug()
