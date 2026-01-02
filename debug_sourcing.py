import requests

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

    # 2. Get Workspace
    ws_resp = requests.get(f"{BASE_URL}/workspaces/", headers=headers)
    workspace_id = ws_resp.json()[0]["id"]
    print(f"Using Workspace ID: {workspace_id}")

    # 3. Simulate Sourcing (Frontend Style)
    print("Sending Source Request (JSON Body)...")
    
    # Frontend sends: body: { domains: ["example.com"] }
    data = {
        "domains": ["example.com"]
    }
    
    resp = requests.post(
        f"{BASE_URL}/leads/source?workspace_id={workspace_id}",
        headers=headers,
        json=data
    )
    
    print(f"Source Response Status: {resp.status_code}")
    print(f"Source Response Body: {resp.text}")

if __name__ == "__main__":
    run_debug()
