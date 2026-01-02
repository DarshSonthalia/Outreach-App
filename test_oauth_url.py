import requests
import json

BASE_URL = "http://localhost:8000"
EMAIL = "sonthaliadarsh@gmail.com"
PASSWORD = "darsh1234"

def test_oauth_url():
    # Login
    login_res = requests.post(f"{BASE_URL}/api/auth/login", json={"email": EMAIL, "password": PASSWORD})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # Get Workspace
    ws_res = requests.get(f"{BASE_URL}/api/workspaces/", headers=headers)
    workspace_id = ws_res.json()[0]["id"]
    print(f"Testing with Workspace ID: {workspace_id}")
    
    # Test getOAuthUrl
    url_res = requests.get(f"{BASE_URL}/api/mailboxes/oauth/url?workspace_id={workspace_id}", headers=headers)
    
    print(f"Status Code: {url_res.status_code}")
    print(f"Response: {json.dumps(url_res.json(), indent=2)}")

if __name__ == "__main__":
    test_oauth_url()
