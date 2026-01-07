## QUICK START: Test the Fixes NOW

### Step 1: Open Dashboard (30 seconds)
```
1. Open: http://localhost:3000
2. Login if needed
3. Click "Dashboard" tab
4. Scroll down to "Connected Mailboxes" section
```

**Expected to see**:
- List of mailboxes with email addresses
- Each mailbox has a status badge: [Active] or [Inactive]
- "[+ Add Mailbox]" button at the top of the section
- For inactive mailboxes: "[🔄 Re-link]" button
- For all mailboxes: "[✕ Disconnect]" button

---

### Step 2: Test Re-link Feature (2 minutes)
**If you have an inactive mailbox:**
```
1. Find the inactive mailbox (shows [Inactive] badge)
2. Click the "[🔄 Re-link]" button
3. You'll be redirected to Google login
4. Sign in with the Gmail account
5. Grant permissions to the app
6. You'll be redirected back to dashboard
7. Check if the mailbox is now [Active]
```

**Expected result**:
- Mailbox status changes from [Inactive] to [Active]
- Backend logs show: "Refreshed tokens" or similar
- Any campaigns that were paused due to auth now show as active again

---

### Step 3: Test Add Mailbox Feature (2 minutes)
```
1. Click "[+ Add Mailbox]" button
2. You'll be redirected to Google login
3. Sign in with a DIFFERENT Gmail account (important!)
4. Grant permissions
5. You'll be redirected back to dashboard
6. Look for the new mailbox in the list
```

**Expected result**:
- New mailbox appears in the list
- Status shows [Active]
- Email address matches the account you just linked

---

### Step 4: Test Disconnect Feature (1 minute)
```
1. Find any mailbox you don't need
2. Click the "[✕ Disconnect]" button
3. A dialog will ask: "Sure you want to disconnect {email}?"
4. Click "Yes" to confirm
```

**Expected result**:
- Mailbox status changes to [Inactive]
- Button is replaced with "[🔄 Re-link]"
- Can click "[🔄 Re-link]" at any time to activate again

---

### Step 5: Watch the Logs (Advanced)
**In a new terminal window, run**:
```bash
cd "c:\Users\carbo\outreach app antigravity"
docker-compose logs -f backend
```

**Watch for these messages when testing**:
- When clicking re-link: `"refreshed tokens"` or `"OAuth callback successful"`
- When campaign sending: `"Token refresh failed"` (if token bad)
- `"_mark_reauth_required"` (when auth needed)
- `"process_due_sends"` (periodic campaign processing)

---

### Step 6: Check Browser Console (If something breaks)
```
1. Press F12 to open DevTools
2. Click "Console" tab
3. Look for red error messages
4. Copy any errors and share them
```

**Should see**:
- No red errors
- Some DEBUG/INFO messages (normal)
- Occasional fetch logs (normal)

---

## Testing Token Refresh Failure (Advanced)

If you want to simulate a token expiration:

### Method 1: Manual Database Update
```bash
# Connect to postgres
docker-compose exec db psql -U postgres -d outreach_db

# Find your mailbox
SELECT id, email, is_active FROM mailboxes;

# Mark it as needing re-auth
UPDATE mailboxes SET is_active=false WHERE id=1;
UPDATE campaigns SET status='PAUSED', pause_reason='Mailbox requires re-authentication' WHERE mailbox_id=1;

# Then go to dashboard and re-link it
```

### Method 2: Wait for Natural Expiration
1. Link a mailbox
2. Wait for the refresh token to expire (if you have a test account)
3. Try to send a campaign
4. Campaign will pause with auth error
5. Click re-link to fix

---

## Troubleshooting: "Features Still Not Showing"

### Check 1: Frontend was built
```bash
# In terminal, check if .next folder exists
ls -la "c:\Users\carbo\outreach app antigravity\frontend\.next"
# Should show: public, server, static, data.json, etc.
```

### Check 2: Frontend container is using latest build
```bash
# Restart frontend container
docker-compose down frontend
docker-compose up -d frontend
# Wait 30 seconds
```

### Check 3: Browser cache
```
1. Press Ctrl+Shift+R in browser (hard refresh)
2. Or: Ctrl+Shift+Del (open clear cache dialog)
3. Select "Cookies and cached images and files"
4. Click "Clear data"
5. Refresh page
```

### Check 4: Check what frontend is actually serving
```bash
# Get the HTML from frontend
# It should contain JavaScript for handleAddMailbox
Invoke-WebRequest http://localhost:3000/dashboard | Select-String "handleAddMailbox"
```

### Check 5: Backend error handling
```bash
# Check if backend code changes are in place
findstr /C:"RefreshError" "c:\Users\carbo\outreach app antigravity\backend\app\services\gmail_service.py"
# Should output: from google.auth.exceptions import RefreshError
```

---

## Real-World Test Scenario

**Scenario**: "My token expired mid-campaign, what happens?"

### Current Behavior (FIXED):
1. Campaign is in `ACTIVE` state, sending emails
2. Celery worker tries to send to next recipient
3. Gmail API returns 401 (token expired)
4. Token refresh fails (token too old)
5. `campaign_worker.py` catches error and calls `_mark_reauth_required()`
6. Campaign pauses with message: "Mailbox requires re-authentication: Token refresh failed"
7. Mailbox status changes to [Inactive] on dashboard
8. User sees "[🔄 Re-link]" button
9. User clicks it, completes Google OAuth
10. Mailbox becomes [Active] again
11. Campaign automatically resumes sending to remaining recipients

### What Got Fixed:
- **Before**: Campaign would pause but no recovery mechanism
- **After**: User gets clear signal [Inactive] + [Re-link] button, campaign auto-resumes

---

## Expected Results Summary

| Feature | Expected Behavior |
|---------|------------------|
| **Add Mailbox** | Redirects to Google → User signs in → Returns to dashboard → New mailbox appears [Active] |
| **Re-link Mailbox** | Redirects to Google → User signs in → Returns to dashboard → Mailbox becomes [Active] → Paused campaigns resume |
| **Disconnect Mailbox** | Click button → Confirm dialog → Mailbox becomes [Inactive] → Can re-link later |
| **Token Refresh Failure** | Campaign pauses → Mailbox shows [Inactive] → User clicks [Re-link] → Campaign resumes |
| **Multiple Mailboxes** | Can have 5+ Gmail accounts in one workspace → All usable for campaigns |

---

## Contact Points / Things to Watch

### If token refresh still fails:
- Check backend logs for: `"Token refresh failed"` error message
- Check if encrypted token is valid: Is the token actually stored?
- Try manually re-linking the mailbox

### If buttons don't appear:
- Hard refresh browser: `Ctrl+Shift+R`
- Check frontend build: Look for `.next/static` folder
- Check browser console: Any JavaScript errors?

### If campaigns don't auto-resume:
- Check backend for: `"_mark_reauth_required"` message
- Check if mailbox became [Active] after re-link
- Look at campaign details: What's the `pause_reason`?

---

**You're all set! Go test it out.** 🚀

The code is in place, the frontend is built, the backend is running.

**Next**: Go to http://localhost:3000 → Dashboard → Click "[+ Add Mailbox]" → Enjoy!
