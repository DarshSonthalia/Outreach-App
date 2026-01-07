# How to Get Your Workspace ID

## ⚠️ Important: Workspace ID is NOT from Google Cloud

The `workspace_id` is created in **your application's database** when you complete the setup wizard. It's not related to Google Cloud.

---

## Method 1: Via API (Easiest) ✅

### For Windows PowerShell Users

**Step 1: Login and Get Token**

```powershell
$loginBody = @{
    email = "your-email@example.com"
    password = "your-password"
} | ConvertTo-Json

$response = Invoke-RestMethod -Uri "http://localhost:8000/api/auth/login" `
    -Method POST `
    -ContentType "application/json" `
    -Body $loginBody

$token = $response.access_token
Write-Host "Token: $token"
```

**Step 2: Get Your Workspace ID**

```powershell
$headers = @{
    Authorization = "Bearer $token"
}

$workspaces = Invoke-RestMethod -Uri "http://localhost:8000/api/workspaces/" `
    -Method GET `
    -Headers $headers

$workspaceId = $workspaces[0].id
Write-Host "Workspace ID: $workspaceId"
```

### For Linux/Mac/Bash Users

**Step 1: Get Your Auth Token**

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "your-email@example.com", "password": "your-password"}'
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Step 2: List Your Workspaces**

```bash
curl -H "Authorization: Bearer YOUR_TOKEN_HERE" \
     http://localhost:8000/api/workspaces/
```

**Response:**
```json
[
  {
    "id": 1,                    ← This is your workspace_id
    "name": "My Workspace",
    "what_you_sell": "...",
    "target_industry": "...",
    ...
  }
]
```

**The `id` field is your `workspace_id`!**

---

## Method 2: From Frontend (If Already Logged In)

If you're already logged into the frontend:

1. Open browser DevTools (F12)
2. Go to **Console** tab
3. Run this JavaScript:

```javascript
const token = localStorage.getItem('token');
fetch('http://localhost:8000/api/workspaces/', {
  headers: { 'Authorization': `Bearer ${token}` }
})
.then(r => r.json())
.then(data => {
  console.log('Workspace ID:', data[0].id);
  console.log('All workspaces:', data);
});
```

---

## Method 3: From Database Directly

If you have database access:

```bash
# Connect to PostgreSQL
docker-compose exec db psql -U outreach -d outreach_db

# Then run:
SELECT id, name, user_id, created_at FROM workspaces;
```

**Example output:**
```
 id |     name      | user_id |      created_at
----+---------------+---------+---------------------
  1 | My Workspace  |       1 | 2026-01-03 10:00:00
```

The `id` column is your `workspace_id`.

---

## Method 4: Check Frontend Code

If you've already used the app, the workspace_id might be stored in:

1. **Browser LocalStorage** (check DevTools → Application → Local Storage)
2. **Frontend state** (check React DevTools)
3. **URL parameters** (if you've navigated to workspace-specific pages)

---

## Method 5: Create a New Workspace

If you don't have a workspace yet:

```bash
# 1. Login first (get token)
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "your-email@example.com", "password": "your-password"}'

# 2. Create workspace (use token from step 1)
curl -X POST http://localhost:8000/api/workspaces/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "My New Workspace"}'
```

**Response:**
```json
{
  "id": 2,                    ← This is your new workspace_id
  "name": "My New Workspace",
  ...
}
```

---

## Quick Test Script

Save this as `get_workspace_id.sh`:

```bash
#!/bin/bash

# Replace with your credentials
EMAIL="your-email@example.com"
PASSWORD="your-password"

# Login
echo "Logging in..."
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d "{\"email\": \"$EMAIL\", \"password\": \"$PASSWORD\"}" \
  | jq -r '.access_token')

if [ "$TOKEN" == "null" ] || [ -z "$TOKEN" ]; then
  echo "❌ Login failed!"
  exit 1
fi

echo "✅ Logged in successfully"
echo ""

# Get workspaces
echo "Fetching workspaces..."
curl -s -H "Authorization: Bearer $TOKEN" \
     http://localhost:8000/api/workspaces/ \
  | jq -r '.[] | "Workspace ID: \(.id) | Name: \(.name)"'

echo ""
echo "Use the Workspace ID above in your API calls!"
```

**Usage:**
```bash
chmod +x get_workspace_id.sh
./get_workspace_id.sh
```

---

## Example: Using Workspace ID

Once you have your `workspace_id`, use it like this:

```bash
# Get inbox replies
curl -H "Authorization: Bearer YOUR_TOKEN" \
     "http://localhost:8000/api/inbox/replies?workspace_id=1"

# Debug endpoint
curl -H "Authorization: Bearer YOUR_TOKEN" \
     "http://localhost:8000/api/inbox/debug/replies?workspace_id=1"
```

---

## Troubleshooting

### "Workspace not found" Error
- ✅ Verify you're using the correct workspace_id
- ✅ Check the workspace belongs to your user account
- ✅ Make sure you're logged in with the correct account

### No Workspaces Returned
- ✅ You might not have created a workspace yet
- ✅ Complete the setup wizard at `/wizard`
- ✅ Or create one via API (Method 5 above)

### Multiple Workspaces
- ✅ Most users have one workspace
- ✅ If you have multiple, use the one you want to test with
- ✅ The first one (`data[0].id`) is usually the default

---

## Summary

**Easiest Method**: Use Method 1 (API call)
1. Login → Get token
2. Call `/api/workspaces/` → Get workspace `id`
3. Use that `id` as `workspace_id` in other API calls

**Quick Command:**
```bash
# One-liner to get workspace ID (after login)
curl -H "Authorization: Bearer YOUR_TOKEN" \
     http://localhost:8000/api/workspaces/ | jq '.[0].id'
```

---

**Note**: Google Cloud credentials are used for Gmail OAuth, but the `workspace_id` is entirely separate and comes from your application's database.

