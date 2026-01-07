# Multiple Mailbox Support & Re-link Feature

## Overview

Implemented full support for:
1. ✅ **Add Multiple Mailboxes** – Users can connect multiple Gmail accounts to one workspace
2. ✅ **Re-link Mailbox** – Users can re-authenticate an inactive mailbox with one click
3. ✅ **Disconnect Mailbox** – Users can safely disconnect mailboxes (pauses associated campaigns)

---

## Changes Made

### Frontend Changes

#### 1. API Client Update (`frontend/src/lib/api.ts`)

Added `disconnect` method to mailboxes API:

```typescript
disconnect: (token: string, mailboxId: number) =>
    apiRequest<void>(`/api/mailboxes/${mailboxId}`, {
        method: 'DELETE',
        token,
    }),
```

#### 2. Dashboard Update (`frontend/src/app/dashboard/page.tsx`)

**New State Variables:**
```typescript
const [relinkingMailboxId, setRelinkingMailboxId] = useState<number | null>(null);
const [disconnectingMailboxId, setDisconnectingMailboxId] = useState<number | null>(null);
```

**New Handler Functions:**

1. **`handleRelinkMailbox()`** – Re-authenticate an inactive mailbox
   - Triggered by "🔄 Re-link" button (only shown if mailbox is inactive)
   - Gets OAuth URL and redirects to Google
   - On completion, tokens are updated and campaigns auto-resume

2. **`handleDisconnectMailbox()`** – Safely disconnect a mailbox
   - Triggered by "✕ Disconnect" button
   - Confirms user intent
   - Calls DELETE endpoint to mark mailbox as inactive
   - Pauses all campaigns using that mailbox (via backend logic)

3. **`handleAddMailbox()`** – Add a new mailbox to workspace
   - Triggered by "+ Add Mailbox" button
   - Gets OAuth URL and redirects to Google
   - On completion, new mailbox is added to workspace

**Updated Mailbox Display:**
- Shows all connected mailboxes in a list
- Each mailbox shows:
  - Email address
  - Connection date
  - Active/Inactive status badge
  - Re-link button (only if inactive)
  - Disconnect button
- Header button "+ Add Mailbox" for quick access
- Empty state with "Connect Gmail" button

---

### Backend (No Changes Needed)

✅ **Already Supported:**
- List multiple mailboxes: `GET /api/mailboxes/?workspace_id={id}`
- Disconnect mailbox: `DELETE /api/mailboxes/{mailbox_id}`
- Create mailbox via OAuth: `GET /api/mailboxes/oauth/callback`
- Auto-resume campaigns on re-auth: (implemented in previous token refresh fix)

---

## User Workflows

### Scenario 1: Add a New Mailbox

1. User clicks "+ Add Mailbox" button on dashboard
2. Redirected to Google OAuth
3. User authorizes Gmail access
4. New mailbox added to workspace
5. Appears in mailbox list immediately

### Scenario 2: Re-link an Inactive Mailbox

1. Mailbox shows "Inactive" status (red badge)
2. User clicks "🔄 Re-link" button
3. Redirected to Google OAuth
4. User authorizes Gmail access
5. Mailbox status updated to "Active"
6. All paused campaigns automatically resume (via auto-resume logic)

### Scenario 3: Disconnect a Mailbox

1. User clicks "✕ Disconnect" button on any mailbox
2. Confirmation dialog appears: "Are you sure? Campaigns will be paused."
3. User confirms
4. Mailbox marked as inactive
5. All campaigns using this mailbox are paused
6. Mailbox still visible but shows "Inactive" status
7. User can later re-link it or keep it disconnected

### Scenario 4: Use Multiple Mailboxes in One Workspace

1. User connects Gmail A (mailbox.email = alice@company.com)
2. Creates Campaign 1 with mailbox A
3. Clicks "+ Add Mailbox"
4. Connects Gmail B (mailbox.email = bob@company.com)
5. Creates Campaign 2 with mailbox B
6. Both campaigns run in parallel using different mailboxes
7. Dashboard shows both mailboxes with status indicators

---

## API Endpoints Used

### Get OAuth URL (for both new & re-link)
```
GET /api/mailboxes/oauth/url?workspace_id={workspace_id}
Authorization: Bearer {token}

Response:
{
  "auth_url": "https://accounts.google.com/o/oauth2/auth?..."
}
```

### List Mailboxes
```
GET /api/mailboxes/?workspace_id={workspace_id}
Authorization: Bearer {token}

Response:
[
  {
    "id": 1,
    "email": "user@gmail.com",
    "is_active": true,
    "status": "ACTIVE",
    "connected_at": "2026-01-07T10:30:00",
    ...
  }
]
```

### Disconnect Mailbox
```
DELETE /api/mailboxes/{mailbox_id}
Authorization: Bearer {token}

Response: 204 No Content
```

### OAuth Callback (Auto re-links or creates mailbox)
```
GET /api/mailboxes/oauth/callback?code={code}&state={workspace_id}

Behavior:
- If mailbox (workspace_id, email) exists → Updates tokens, sets is_active=true, auto-resumes campaigns
- If mailbox doesn't exist → Creates new mailbox, extracts domain, checks DNS
```

---

## Backend Integration Points

### Mailbox Router (`backend/app/routers/mailboxes.py`)

**OAuth Callback Logic:**
```python
if existing:
    # Update tokens
    existing.access_token_encrypted = access_encrypted
    existing.refresh_token_encrypted = refresh_encrypted
    existing.token_expiry = expiry
    existing.is_active = True
    existing.status = "ACTIVE"
    db.commit()
    mailbox = existing
    
    # Auto-resume campaigns that were paused due to auth issues
    _resume_paused_campaigns_for_mailbox(db, mailbox)
else:
    # Create new mailbox
    mailbox = Mailbox(...)
    db.add(mailbox)
    db.commit()
```

**Disconnect Endpoint:**
```python
@router.delete("/{mailbox_id}", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect_mailbox(mailbox_id: int, ...):
    mailbox.is_active = False
    db.commit()
    # Campaigns using this mailbox are paused via GmailService logic
```

---

## Frontend Structure

```
frontend/
├── src/
│   ├── lib/
│   │   └── api.ts                    ← Added disconnect() method
│   └── app/
│       └── dashboard/
│           └── page.tsx              ← Updated mailbox UI & handlers
```

---

## Testing Checklist

- [ ] **Add Single Mailbox** – Connect one Gmail account, verify in mailbox list
- [ ] **Add Multiple Mailboxes** – Connect 2+ Gmail accounts to same workspace
- [ ] **Re-link Mailbox** – Mark mailbox inactive, click re-link, complete OAuth
- [ ] **Auto-resume on Re-link** – Verify paused campaigns resume after re-link
- [ ] **Disconnect Mailbox** – Verify campaigns pause when mailbox is disconnected
- [ ] **Create Campaign** – Should be able to select any active mailbox for new campaigns
- [ ] **Campaign Persistence** – Verify campaigns continue with correct mailbox
- [ ] **Token Refresh** – Verify inactive mailbox can be re-linked without re-authenticating all campaigns

---

## Known Limitations & Future Enhancements

### Current Limitations:
- Disconnecting a mailbox pauses campaigns (doesn't delete them)
- No bulk mailbox operations (disconnect multiple at once)
- No mailbox sharing between workspaces

### Potential Enhancements:
- Add mailbox nickname/alias for easier identification
- Show which campaigns use each mailbox
- Ability to transfer campaigns between mailboxes
- Bulk mailbox operations
- Mailbox health status indicators (bounce rate, spam score, etc.)

---

## Backward Compatibility

✅ **Fully backward compatible**
- Existing single-mailbox setups continue to work
- No database schema changes
- No breaking API changes
- Existing campaigns unaffected

---

## Summary

**Before:**
- Only one mailbox per workspace
- No way to re-link inactive mailbox
- No way to disconnect mailboxes

**After:**
- Multiple mailboxes per workspace ✅
- One-click re-link for inactive mailboxes ✅
- Safe disconnect with campaign pause protection ✅
- Auto-resume campaigns on re-auth ✅
- Full multi-mailbox campaign management ✅

Users can now use multiple Gmail accounts in one workspace, re-authenticate when needed, and safely manage mailbox connections from the dashboard.
