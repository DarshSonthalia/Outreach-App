# Fix: Token Refresh Failure - Campaign Resume Solution

## Problem Summary

When a mailbox's OAuth token expires and refresh fails, campaigns are automatically paused with:
```
Mailbox requires re-authentication: Token refresh failed
```

**The issue:** Once paused, campaigns remain paused indefinitely, even after the user successfully re-authenticates. There was no mechanism to resume them.

---

## Root Cause

1. **Token expires** during a campaign send → Gmail API call fails
2. **Campaign worker catches RefreshError** → calls `GmailService._mark_reauth_required()`
3. **All campaigns on that mailbox are paused** with `pause_reason = "Mailbox requires re-authentication: Token refresh failed"`
4. **User re-authenticates via OAuth** (visits `/api/mailboxes/oauth/callback`)
5. **Mailbox tokens are updated** and `is_active` set to `True`
6. **BUT:** Paused campaigns are NOT automatically resumed → user sees them stuck in PAUSED state forever

---

## Solution Implemented

### 1. **Auto-Resume in OAuth Callback** (`backend/app/routers/mailboxes.py`)

When user re-authenticates, the OAuth callback now:
- Updates the mailbox tokens
- Sets `mailbox.status = "ACTIVE"` (new field for clarity)
- **Calls `_resume_paused_campaigns_for_mailbox()`** which:
  - Finds all campaigns paused due to "re-authentication" issues
  - Sets their status back to `RUNNING`
  - Clears the `pause_reason`
  - Reschedules pending leads to send immediately (starting now)

**Code location:** [backend/app/routers/mailboxes.py](backend/app/routers/mailboxes.py#L22-L48)

```python
def _resume_paused_campaigns_for_mailbox(db: Session, mailbox: Mailbox):
    """Resume campaigns paused due to auth issues when mailbox is re-authenticated."""
    paused_campaigns = db.query(Campaign).filter(
        Campaign.mailbox_id == mailbox.id,
        Campaign.status == CampaignStatus.PAUSED,
        Campaign.pause_reason.contains("Mailbox requires re-authentication")
    ).all()
    
    for campaign in paused_campaigns:
        campaign.status = CampaignStatus.RUNNING
        campaign.pause_reason = None
        # ... reschedule pending leads
```

### 2. **Manual Resume Endpoint** (`backend/app/routers/campaigns.py`)

Added new endpoint for users to manually resume campaigns:

```
POST /api/campaigns/{campaign_id}/resume
```

**Endpoint logic:**
- Verifies campaign is paused due to auth issue (checks pause_reason)
- Verifies mailbox is now active (`is_active = True`)
- If both pass: resumes campaign with rescheduled sends
- Returns helpful error if conditions not met

**Code location:** [backend/app/routers/campaigns.py](backend/app/routers/campaigns.py#L331-L401)

### 3. **Improved Token Refresh Error Logging** (`backend/app/services/gmail_service.py`)

Enhanced error handling to help diagnose token issues:
- Logs error type and code
- Captures exception message in pause_reason for user visibility
- Sets `mailbox.status = MailboxStatus.ACTIVE` when refresh succeeds

**Key changes:**
```python
except RefreshError as e:
    logger.error(f"Token refresh failed for mailbox {mailbox.id}: {str(e)}")
    logger.error(f"Error type: {type(e).__name__}, Error code: {getattr(e, 'code', 'unknown')}")
    GmailService._mark_reauth_required(db, mailbox, f"Token refresh failed: {str(e)}")
    return None, mailbox
```

---

## How It Works (User Flow)

### Scenario 1: Auto-Resume (Automatic)

1. User's campaign is running ✅
2. Token expires, refresh fails → campaigns auto-pause ❌
3. User visits `/api/mailboxes/oauth/url?workspace_id=X` to re-authenticate
4. Completes Google OAuth login
5. Callback fires → tokens updated → **campaigns auto-resume** ✅

### Scenario 2: Manual Resume (Fallback)

If auto-resume fails for any reason:

1. User sees campaign paused with reason: "Mailbox requires re-authentication: Token refresh failed"
2. User re-authenticates (same as above)
3. User calls: `POST /api/campaigns/{campaign_id}/resume`
4. Campaign resumes if mailbox is active ✅

---

## Testing the Fix

### Check current campaign status:

```bash
python check_campaign_status.py
```

This script shows:
- Which campaigns are paused due to auth issues
- Which mailboxes need re-authentication
- Recent events for debugging

### Manually resume a campaign (if needed):

```bash
curl -X POST http://localhost:8000/api/campaigns/1/resume \
  -H "Authorization: Bearer <access_token>"
```

**Response (success):**
```json
{
  "campaign_id": 1,
  "status": "RUNNING",
  "pause_reason": null
}
```

**Response (error):**
```json
{
  "detail": "Campaign is RUNNING, not paused"
}
```

---

## Changes Made

### Files Modified:
1. **[backend/app/routers/mailboxes.py](backend/app/routers/mailboxes.py)**
   - Added `_resume_paused_campaigns_for_mailbox()` helper
   - Modified OAuth callback to call the helper
   - Added import for `CampaignStatus`

2. **[backend/app/routers/campaigns.py](backend/app/routers/campaigns.py)**
   - Added `POST /api/campaigns/{campaign_id}/resume` endpoint
   - Validates pause reason and mailbox status before resuming

3. **[backend/app/services/gmail_service.py](backend/app/services/gmail_service.py)**
   - Enhanced token refresh error handling with better logging
   - Set `mailbox.status = MailboxStatus.ACTIVE` on successful refresh
   - Improved error messages for debugging

### Files Created:
1. **[check_campaign_status.py](check_campaign_status.py)** (diagnostic script)
   - Shows all campaigns and their pause reasons
   - Identifies which are stuck due to auth issues
   - Displays related events for debugging

---

## What NOT to Do

❌ **Don't** manually mark the mailbox as active in the database—use the OAuth flow
❌ **Don't** manually update `campaign.status` without checking mailbox state
❌ **Don't** assume campaigns will resume without clicking the OAuth link again

---

## Backward Compatibility

✅ **Fully backward compatible**
- Existing campaigns continue to work
- Existing mailboxes unaffected
- Database schema unchanged (no migrations needed)
- New fields/endpoints are optional

---

## Summary

**Before:** Token refresh failure = permanent pause
**After:** Token refresh failure → auto-resume on re-auth OR manual resume endpoint

The fix ensures that temporary token issues don't permanently break campaigns. Users can recover with a simple re-authentication step.
