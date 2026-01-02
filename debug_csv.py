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

    # 3. Simulate CSV Map & Import
    print("Sending CSV Import...")
    
    # Create dummy CSV
    files = {
        'file': ('test.csv', 'email,first_name\ntest@example.com,Test', 'text/csv')
    }
    
    # Form data matching the new backend signature
    data = {
        'email': 'email',
        'first_name': 'first_name',
        # 'exclude_role_emails': 'false' 
        # Note: FastAPI Form(bool) expects 'true', 'false', 'on', 'off', '1', '0'
    }
    
    resp = requests.post(
        f"{BASE_URL}/leads/map-columns?workspace_id={workspace_id}",
        headers=headers,
        files=files,
        data=data
    )
    
    print(f"Import Response Status: {resp.status_code}")
    print(f"Import Response Body: {resp.text}")

if __name__ == "__main__":
    run_debug()
