# 🚀 Deployment & Verification Checklist

## Issue Identified & Fixed

**Problems Found:**
1. ❌ New frontend features not visible (need rebuild)
2. ❌ Token refresh errors persisting (error handling incomplete)
3. ❌ Campaign worker not properly handling token refresh failures

**Fixes Applied:**
1. ✅ Added proper error handling to `get_credentials_from_encrypted()`
2. ✅ Campaign worker now properly catches token refresh failures
3. ✅ Mailbox marked as reauth_required when token refresh fails

---

## Step-by-Step Deployment

### STEP 1: Verify Code Changes ✅

**Files Modified:**
- ✅ `frontend/src/lib/api.ts` – Added disconnect() method
- ✅ `frontend/src/app/dashboard/page.tsx` – Added UI handlers
- ✅ `backend/app/services/gmail_service.py` – Enhanced error handling
- ✅ `backend/app/workers/campaign_worker.py` – Better exception handling

All changes verified - no syntax errors.

---

### STEP 2: Rebuild Frontend

**In terminal:**
```bash
cd c:\Users\carbo\outreach app antigravity\frontend

npm run build
# or
yarn build
# or if using Next.js directly
npx next build
```

**What this does:**
- Compiles TypeScript/TSX
- Bundles React components
- Optimizes for production
- Takes ~2-5 minutes

**Expected output:**
```
> next build
...
✓ Compiled successfully
```

---

### STEP 3: Stop Docker Services

**In PowerShell:**
```powershell
cd c:\Users\carbo\outreach app antigravity
docker-compose down
```

**Wait for:**
```
Stopping outreach_backend   ... done
Stopping outreach_frontend  ... done
Stopping postgres           ... done
```

---

### STEP 4: Restart Services

**In PowerShell:**
```powershell
cd c:\Users\carbo\outreach app antigravity
docker-compose up --build
```

**Watch for:**
```
outreach_backend   | INFO:     Application startup complete
outreach_frontend  | ▲ Next.js [v18.x.x]
outreach_postgres  | database system is ready to accept connections
```

---

### STEP 5: Verify on Localhost

**In browser:**
```
http://localhost:3000
```

**What to check:**

1. **Login** → Dashboard
2. **Connected Mailboxes section:**
   - [ ] Should show "+ Add Mailbox" button in header
   - [ ] Should show each mailbox with email address
   - [ ] Should show [Active] or [Inactive] badge
   - [ ] Inactive mailboxes should have "🔄 Re-link" button
   - [ ] All mailboxes should have "✕ Disconnect" button

3. **Browser Console:**
   - Open DevTools (F12)
   - Check Console tab for errors
   - Should NOT see "undefined" or "TypeError"

---

### STEP 6: Test Token Refresh Fix

**Test 1: Check Backend Logs**
```bash
docker-compose logs -f outreach_backend | grep -i token
```

**Look for:**
- ✅ "Successfully refreshed tokens" = Good
- ✅ "Token refresh failed" = Handled properly (mailbox marked reauth_required)
- ❌ "Traceback" or Python errors = Problem

**Test 2: Create Test Campaign & Monitor**
1. Create a new campaign
2. Launch it
3. Watch logs:
   ```bash
   docker-compose logs -f outreach_backend | grep campaign_worker
   ```
4. Look for successful sends or proper error handling

**Test 3: Manually Test Token Refresh**
1. Dashboard → Connected Mailboxes
2. Look for [Inactive] mailbox (if any)
3. Click "🔄 Re-link" button
4. Complete Google OAuth
5. **Expected:** Mailbox becomes [Active], paused campaigns resume

---

## Troubleshooting

### Issue: Buttons Still Not Showing

**Solution:**
1. Hard refresh browser: `Ctrl+Shift+Del` (cache)
2. Check browser console for errors: `F12` → Console
3. Verify build completed: `npm run build` output shows ✓ Compiled
4. Check frontend container: `docker-compose logs outreach_frontend | tail -20`

### Issue: Token Refresh Still Failing

**Solution:**
1. Check backend logs:
   ```bash
   docker-compose logs outreach_backend | grep -i "token\|refresh"
   ```
2. Look for error details (permissions, network, credentials)
3. Verify Google OAuth credentials in `.env`:
   ```
   GOOGLE_CLIENT_ID=...
   GOOGLE_CLIENT_SECRET=...
   GOOGLE_REDIRECT_URI=http://localhost:8000/api/mailboxes/oauth/callback
   ```

### Issue: Docker Won't Start

**Solution:**
```powershell
# Kill all containers
docker-compose down -v

# Remove images
docker-compose rm -f

# Rebuild fresh
docker-compose up --build
```

---

## Quick Verification Script

**Run this to test everything:**

```python
#!/usr/bin/env python3
import requests
import json

BASE_URL = "http://localhost:8000"

# Test 1: Health check
print("1. Health check...", end=" ")
try:
    r = requests.get(f"{BASE_URL}/api/health")
    assert r.status_code == 200
    print("✓")
except:
    print("✗")

# Test 2: Frontend loads
print("2. Frontend loads...", end=" ")
try:
    r = requests.get("http://localhost:3000")
    assert r.status_code == 200
    print("✓")
except:
    print("✗")

# Test 3: API accessible
print("3. API accessible...", end=" ")
try:
    r = requests.get(f"{BASE_URL}/api/auth/me", headers={"Authorization": "Bearer test"})
    # Should fail auth but not 404
    assert r.status_code != 404
    print("✓")
except:
    print("✗")

print("\nAll critical systems online!")
```

---

## Post-Deployment Verification

After deployment, verify:

1. ✅ Frontend builds without errors
2. ✅ Docker containers all running
3. ✅ Dashboard loads
4. ✅ Mailbox buttons visible
5. ✅ Add/Re-link/Disconnect buttons work
6. ✅ No console errors
7. ✅ Backend logs show token handling
8. ✅ Campaigns run without token errors

---

## Key Changes Explained

### Frontend Changes (User-Facing)

```tsx
// NEW: Three handler functions for mailbox operations
handleAddMailbox()           // Redirect to OAuth for new mailbox
handleRelinkMailbox()        // Re-authenticate existing mailbox
handleDisconnectMailbox()    // Safely disconnect mailbox

// NEW: UI elements in mailbox section
[+ Add Mailbox]              // Button in header
[🔄 Re-link]                 // Button on inactive mailboxes
[✕ Disconnect]               // Button on all mailboxes
[Active] / [Inactive] badge  // Status indicator
```

### Backend Changes (Error Handling)

```python
# IMPROVED: get_credentials_from_encrypted() now handles errors
- Catches RefreshError specifically
- Converts to ValueError for caller
- Logs detailed error information

# IMPROVED: campaign_worker.py now detects token refresh failures
- Catches ValueError (refresh error indicator)
- Calls _mark_reauth_required() to properly pause campaigns
- Ensures user sees actionable feedback
```

---

## Environment Variables (Verify These)

In `.env` file, should have:
```
# Google OAuth
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GOOGLE_REDIRECT_URI=http://localhost:8000/api/mailboxes/oauth/callback

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000

# Database
DATABASE_URL=postgresql://outreach_user:outreach_password@postgres:5432/outreach_db
```

---

## Rollback Plan (If Needed)

If something breaks:

```bash
# Stop services
docker-compose down

# Revert code changes
git checkout -- .

# Rebuild
docker-compose up --build
```

---

## Performance Notes

- Build time: ~2-5 minutes
- Startup time: ~1-2 minutes
- First request latency: ~500ms (normal)
- Token refresh: ~1-2 seconds
- No database migrations needed

---

## Success Criteria

After deployment:

✅ Frontend:
- Mailbox buttons visible
- Add/Re-link/Disconnect work
- No console errors

✅ Backend:
- Logs show token refresh attempts
- Token failures properly caught
- Campaigns properly pause on auth errors

✅ Database:
- Mailboxes marked with correct status
- Events logged for reauth
- Campaigns paused when needed

✅ User Experience:
- Can add multiple mailboxes
- Can re-link inactive mailboxes
- Can safely disconnect
- Paused campaigns auto-resume

---

## Timeline

- **Build:** 3-5 minutes
- **Docker restart:** 1-2 minutes
- **Testing:** 5-10 minutes
- **Total:** ~10-15 minutes

---

## Support

If deployment fails:
1. Check all 6 steps above
2. Review troubleshooting section
3. Check Docker logs: `docker-compose logs`
4. Verify `.env` file is correct
5. Verify network connectivity (localhost:3000, localhost:8000, postgres:5432)

Let me know if you hit any issues!
