import requests
import json

BASE_URL = "http://localhost:8000"
EMAIL = "sonthaliadarsh@gmail.com"
PASSWORD = "darsh1234"

def test_wizard_setup():
    # Login
    login_res = requests.post(f"{BASE_URL}/api/auth/login", json={"email": EMAIL, "password": PASSWORD})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # Get Workspace
    ws_res = requests.get(f"{BASE_URL}/api/workspaces/", headers=headers)
    workspace_id = ws_res.json()[0]["id"]
    print(f"Testing with Workspace ID: {workspace_id}")
    
    # Simulated Payload from Wizard correctly capitalized as per my fix
    payload = {
        "what_you_sell": "Advanced AI coding assistants",
        "target_industry": "Software Engineering",
        "target_role": "CTO",
        "target_region": "Global",
        "offer_type": "demo",
        "safety_preference": "HIGH", # Capitalized
        "has_leads": False,
        "connect_gmail": "Connect Gmail" # Extra field from Wizard state
    }
    
    print(f"Sending payload: {json.dumps(payload, indent=2)}")
    
    setup_res = requests.put(f"{BASE_URL}/api/workspaces/{workspace_id}/setup", json=payload, headers=headers)
    
    print(f"Status Code: {setup_res.status_code}")
    print(f"Response: {json.dumps(setup_res.json(), indent=2)}")

if __name__ == "__main__":
    test_wizard_setup()
