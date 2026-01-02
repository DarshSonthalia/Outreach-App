import requests
import json

BASE_URL = "http://localhost:8000"
EMAIL = "sonthaliadarsh@gmail.com"
PASSWORD = "darsh1234"

def test():
    print(f"Testing for {EMAIL}...")
    
    # Login
    login_res = requests.post(f"{BASE_URL}/api/auth/login", json={"email": EMAIL, "password": PASSWORD})
    if login_res.status_code != 200:
        print(f"Login failed: {login_res.text}")
        return
    
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # Get Workspace
    ws_res = requests.get(f"{BASE_URL}/api/workspaces/", headers=headers)
    workspaces = ws_res.json()
    print(f"Workspaces: {json.dumps(workspaces)}")
    
    if not workspaces:
        print("No workspaces found")
        return
        
    ws_id = workspaces[0]["id"]
    
    # Get Campaigns
    camp_res = requests.get(f"{BASE_URL}/api/campaigns/?workspace_id={ws_id}", headers=headers)
    campaigns = camp_res.json()
    print(f"\nCampaigns (Count: {len(campaigns)}):")
    print(json.dumps(campaigns, indent=2))
    
    # Get Dashboards
    print("\nDashboards:")
    for c in campaigns:
        dash_res = requests.get(f"{BASE_URL}/api/campaigns/{c['id']}/dashboard", headers=headers)
        if dash_res.status_code == 200:
            print(f"ID {c['id']} ({c['name']}): {json.dumps(dash_res.json())}")
        else:
            print(f"ID {c['id']} FAILED: {dash_res.status_code}")

if __name__ == "__main__":
    test()
