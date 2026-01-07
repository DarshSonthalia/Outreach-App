# PowerShell API Commands

## ⚠️ Important: PowerShell Syntax

On Windows PowerShell, `curl` is an alias for `Invoke-WebRequest`, which uses different syntax. Use the commands below.

---

## Method 1: Using Invoke-RestMethod (Recommended) ✅

### Step 1: Login and Get Token

```powershell
$loginBody = @{
    email = "sonthaliadarsh@gmail.com"
    password = "Darsh4151"
} | ConvertTo-Json

$response = Invoke-RestMethod -Uri "http://localhost:8000/api/auth/login" `
    -Method POST `
    -ContentType "application/json" `
    -Body $loginBody

$token = $response.access_token
Write-Host "Token: $token"
```

### Step 2: Get Your Workspace ID

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

---

## Method 2: One-Liner Script

Save this as `get-workspace-id.ps1`:

```powershell
# Login
$loginBody = @{
    email = "sonthaliadarsh@gmail.com"
    password = "Darsh4151"
} | ConvertTo-Json

$response = Invoke-RestMethod -Uri "http://localhost:8000/api/auth/login" `
    -Method POST `
    -ContentType "application/json" `
    -Body $loginBody

$token = $response.access_token
Write-Host "✅ Logged in successfully" -ForegroundColor Green

# Get workspaces
$headers = @{
    Authorization = "Bearer $token"
}

$workspaces = Invoke-RestMethod -Uri "http://localhost:8000/api/workspaces/" `
    -Method GET `
    -Headers $headers

Write-Host "`n📋 Your Workspaces:" -ForegroundColor Cyan
foreach ($ws in $workspaces) {
    Write-Host "  Workspace ID: $($ws.id) | Name: $($ws.name)" -ForegroundColor Yellow
}

Write-Host "`n💡 Use the first Workspace ID in your API calls!" -ForegroundColor Green
```

**Run it:**
```powershell
.\get-workspace-id.ps1
```

---

## Method 3: Using curl.exe (If Installed)

If you have actual `curl.exe` installed (from Git Bash, WSL, or standalone):

```powershell
# Use curl.exe explicitly (not the alias)
curl.exe -X POST http://localhost:8000/api/auth/login `
  -H "Content-Type: application/json" `
  -d '{\"email\": \"sonthaliadarsh@gmail.com\", \"password\": \"Darsh4151\"}'
```

---

## Complete Test Commands (PowerShell)

### 1. Health Check

```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/health/db" -Method GET
```

### 2. Login

```powershell
$loginBody = @{
    email = "sonthaliadarsh@gmail.com"
    password = "Darsh4151"
} | ConvertTo-Json

$response = Invoke-RestMethod -Uri "http://localhost:8000/api/auth/login" `
    -Method POST `
    -ContentType "application/json" `
    -Body $loginBody

$token = $response.access_token
```

### 3. Get Workspace ID

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

### 4. Debug Endpoint

```powershell
$headers = @{
    Authorization = "Bearer $token"
}

Invoke-RestMethod -Uri "http://localhost:8000/api/inbox/debug/replies?workspace_id=$workspaceId" `
    -Method GET `
    -Headers $headers | ConvertTo-Json -Depth 10
```

### 5. Get Inbox Replies

```powershell
$headers = @{
    Authorization = "Bearer $token"
}

Invoke-RestMethod -Uri "http://localhost:8000/api/inbox/replies?workspace_id=$workspaceId" `
    -Method GET `
    -Headers $headers | ConvertTo-Json -Depth 10
```

---

## Complete Test Script

Save this as `test-api.ps1`:

```powershell
# Configuration
$email = "sonthaliadarsh@gmail.com"
$password = "Darsh4151"
$baseUrl = "http://localhost:8000"

Write-Host "🧪 Testing API Endpoints..." -ForegroundColor Cyan
Write-Host ""

# 1. Health Check
Write-Host "1️⃣ Testing Health Check..." -ForegroundColor Yellow
try {
    $health = Invoke-RestMethod -Uri "$baseUrl/api/health/db" -Method GET
    Write-Host "   ✅ Health: $($health.status) - $($health.database)" -ForegroundColor Green
} catch {
    Write-Host "   ❌ Health check failed: $_" -ForegroundColor Red
}
Write-Host ""

# 2. Login
Write-Host "2️⃣ Logging in..." -ForegroundColor Yellow
try {
    $loginBody = @{
        email = $email
        password = $password
    } | ConvertTo-Json

    $response = Invoke-RestMethod -Uri "$baseUrl/api/auth/login" `
        -Method POST `
        -ContentType "application/json" `
        -Body $loginBody

    $token = $response.access_token
    Write-Host "   ✅ Logged in successfully" -ForegroundColor Green
} catch {
    Write-Host "   ❌ Login failed: $_" -ForegroundColor Red
    exit 1
}
Write-Host ""

# 3. Get Workspace ID
Write-Host "3️⃣ Getting Workspace ID..." -ForegroundColor Yellow
try {
    $headers = @{
        Authorization = "Bearer $token"
    }

    $workspaces = Invoke-RestMethod -Uri "$baseUrl/api/workspaces/" `
        -Method GET `
        -Headers $headers

    if ($workspaces.Count -eq 0) {
        Write-Host "   ⚠️  No workspaces found. Create one first!" -ForegroundColor Yellow
        exit 1
    }

    $workspaceId = $workspaces[0].id
    Write-Host "   ✅ Workspace ID: $workspaceId" -ForegroundColor Green
} catch {
    Write-Host "   ❌ Failed to get workspaces: $_" -ForegroundColor Red
    exit 1
}
Write-Host ""

# 4. Debug Endpoint
Write-Host "4️⃣ Testing Debug Endpoint..." -ForegroundColor Yellow
try {
    $debug = Invoke-RestMethod -Uri "$baseUrl/api/inbox/debug/replies?workspace_id=$workspaceId" `
        -Method GET `
        -Headers $headers

    Write-Host "   ✅ Debug data retrieved:" -ForegroundColor Green
    Write-Host "      Total messages: $($debug.total_messages_in_db)" -ForegroundColor Cyan
    Write-Host "      Inbound messages: $($debug.total_inbound_messages)" -ForegroundColor Cyan
    Write-Host "      Workspace inbound: $($debug.workspace_inbound_messages)" -ForegroundColor Cyan
} catch {
    Write-Host "   ❌ Debug endpoint failed: $_" -ForegroundColor Red
}
Write-Host ""

# 5. Inbox Replies
Write-Host "5️⃣ Testing Inbox Replies..." -ForegroundColor Yellow
try {
    $replies = Invoke-RestMethod -Uri "$baseUrl/api/inbox/replies?workspace_id=$workspaceId" `
        -Method GET `
        -Headers $headers

    Write-Host "   ✅ Found $($replies.Count) replies" -ForegroundColor Green
    if ($replies.Count -gt 0) {
        Write-Host "   First reply:" -ForegroundColor Cyan
        $replies[0] | ConvertTo-Json -Depth 3
    }
} catch {
    Write-Host "   ❌ Inbox replies failed: $_" -ForegroundColor Red
}
Write-Host ""

Write-Host "✅ All tests completed!" -ForegroundColor Green
```

**Run it:**
```powershell
.\test-api.ps1
```

---

## Quick Reference

| Bash/Linux | PowerShell |
|------------|------------|
| `curl -X POST` | `Invoke-RestMethod -Method POST` |
| `-H "Header: value"` | `-Headers @{Header="value"}` |
| `-d '{"key":"value"}'` | `-Body (@{key="value"} \| ConvertTo-Json)` |
| `\` (line continuation) | `` ` `` (backtick) |

---

## Troubleshooting

### "Invoke-RestMethod: The underlying connection was closed"
- ✅ Check if backend is running: `docker-compose ps`
- ✅ Verify URL is correct: `http://localhost:8000`

### "401 Unauthorized"
- ✅ Token expired, login again
- ✅ Check token is being passed correctly

### "404 Not Found"
- ✅ Verify workspace_id is correct
- ✅ Check workspace belongs to your user

### "Cannot bind parameter 'Body'"
- ✅ Make sure to use `ConvertTo-Json` for JSON bodies
- ✅ Use `-ContentType "application/json"`

---

**Note**: All commands use `Invoke-RestMethod` which automatically parses JSON responses. Use `Invoke-WebRequest` if you need raw HTTP responses.


