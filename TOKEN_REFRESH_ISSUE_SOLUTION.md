# Token Refresh Issue - Fix Summary

## Quick Answer

**Problem:** Campaigns get paused with "Mailbox requires re-authentication: Token refresh failed" and won't resume.

**Solution:** Three-part fix implemented:

1. **Auto-resume on re-auth** – Campaigns automatically resume when user re-authenticates
2. **Manual resume endpoint** – Users can call `POST /api/campaigns/{campaign_id}/resume` to manually resume
3. **Better error logging** – Token refresh failures now logged with more detail for debugging

---

## What Was Changed

### File 1: `backend/app/routers/mailboxes.py`

**Added function to auto-resume campaigns after OAuth:**
```python
def _resume_paused_campaigns_for_mailbox(db: Session, mailbox: Mailbox):
    """Find all campaigns paused due to auth issues and resume them."""
    paused_campaigns = db.query(Campaign).filter(
        Campaign.mailbox_id == mailbox.id,
        Campaign.status == CampaignStatus.PAUSED,
        Campaign.pause_reason.contains("Mailbox requires re-authentication")
    ).all()
    
    for campaign in paused_campaigns:
        campaign.status = CampaignStatus.RUNNING
        campaign.pause_reason = None
        # Reschedule pending leads...
```

**Modified OAuth callback to call this function:**
```python
if existing:
    # Update tokens
    existing.access_token_encrypted = access_encrypted
    existing.refresh_token_encrypted = refresh_encrypted
    existing.token_expiry = expiry
    existing.is_active = True
    existing.status = "ACTIVE"  # NEW
    db.commit()
    mailbox = existing
    
    # NEW: Resume campaigns that were paused due to auth issues
    _resume_paused_campaigns_for_mailbox(db, mailbox)
```

---

### File 2: `backend/app/routers/campaigns.py`

**Added new endpoint to manually resume campaigns:**

```python
@router.post("/{campaign_id}/resume", response_model=CampaignResponse)
async def resume_campaign_if_auth_fixed(
    campaign_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Resume a campaign that was paused due to mailbox re-authentication.
    
    Checks:
    1. Campaign exists and belongs to user
    2. Campaign is paused due to auth issue
    3. Mailbox is now active
    """
    # ... validation logic ...
    
    campaign.status = CampaignStatus.RUNNING
    campaign.pause_reason = None
    
    # Reschedule pending leads
    for i, cl in enumerate(pending_leads):
        cl.next_action_at = now + timedelta(minutes=i * 2)
    
    db.commit()
    return campaign
```

---

### File 3: `backend/app/services/gmail_service.py`

**Enhanced token refresh error handling:**

```python
# Refresh if expired
if credentials.expired:
    try:
        logger.debug(f"Refreshing expired token for mailbox {mailbox.id}")
        credentials.refresh(Request())
        
        # Save refreshed tokens
        access_enc, refresh_enc = encrypt_oauth_tokens(
            credentials.token,
            credentials.refresh_token or refresh_token
        )
        mailbox.access_token_encrypted = access_enc
        mailbox.refresh_token_encrypted = refresh_enc
        mailbox.token_expiry = credentials.expiry
        mailbox.status = MailboxStatus.ACTIVE  # NEW
        db.commit()
        
        logger.info(f"Successfully refreshed tokens for mailbox {mailbox.id}")
        
    except RefreshError as e:
        # IMPROVED: More detailed error logging
        logger.error(f"Token refresh failed for mailbox {mailbox.id}: {str(e)}")
        logger.error(f"Error type: {type(e).__name__}, Error code: {getattr(e, 'code', 'unknown')}")
        GmailService._mark_reauth_required(db, mailbox, f"Token refresh failed: {str(e)}")
        return None, mailbox
    except Exception as e:
        logger.error(f"Unexpected error refreshing token: {str(e)}")
        GmailService._mark_reauth_required(db, mailbox, f"Token refresh error: {str(e)}")
        return None, mailbox
```

---

### Files Created

1. **`check_campaign_status.py`** – Diagnostic script to identify stuck campaigns
   - Usage: `python check_campaign_status.py`
   - Shows which campaigns are paused due to auth issues
   - Displays related events and mailbox status

2. **`TOKEN_REFRESH_FIX.md`** – Comprehensive documentation
   - Problem description
   - Root cause analysis
   - Solution details
   - Testing instructions
   - Backward compatibility notes

3. **`TOKEN_REFRESH_API_REFERENCE.py`** – Quick API reference
   - Copy-paste curl commands
   - Database queries for debugging
   - Complete recovery workflow

---

## How It Works

### Scenario A: Automatic Resume (Happy Path)

1. Campaign running → token expires → refresh fails → campaigns paused ❌
2. User visits `/api/mailboxes/oauth/url?workspace_id=X`
3. User completes Google OAuth login
4. OAuth callback fires:
   - Mailbox tokens updated ✅
   - `_resume_paused_campaigns_for_mailbox()` called automatically
   - All paused campaigns resume → sends rescheduled ✅

### Scenario B: Manual Resume (Fallback)

If auto-resume somehow doesn't work:

1. Campaign stuck in PAUSED status
2. User already re-authenticated (tokens updated)
3. User calls: `POST /api/campaigns/{campaign_id}/resume`
4. Endpoint validates mailbox is active, then resumes campaign ✅

---

## Testing the Fix

### Check status:
```bash
python check_campaign_status.py
```

### Manual resume (if needed):
```bash
curl -X POST http://localhost:8000/api/campaigns/1/resume \
  -H "Authorization: Bearer <token>"
```

### View campaign details:
```bash
curl http://localhost:8000/api/campaigns/1/dashboard \
  -H "Authorization: Bearer <token>"
```

---

## Why This Fix Works

| Problem | Before | After |
|---------|--------|-------|
| Token refresh fails | ❌ Campaign paused forever | ✅ Auto-resumes on re-auth |
| User re-authenticates | ❌ Campaigns still paused | ✅ Campaigns resume automatically |
| No manual option | ❌ No way to recover | ✅ `POST /resume` endpoint |
| Poor diagnostics | ❌ Limited error info | ✅ Detailed logging + script |

---

## Zero Breaking Changes

✅ No database migrations needed
✅ No API breaking changes
✅ Fully backward compatible
✅ Existing campaigns unaffected
✅ Works with existing mailboxes

---

## Next Steps

1. Test the fix in your environment:
   - Run `python check_campaign_status.py` to see current state
   - Trigger a token refresh failure (manually expire a token)
   - Verify auto-resume works after re-auth

2. Update frontend (optional):
   - Show "Reconnect Gmail" button when campaigns are paused
   - Call `/api/campaigns/{id}/resume` after re-auth completes

3. Monitor:
   - Watch logs for "Token refresh failed" messages
   - Track "Refreshed tokens successfully" to confirm recovery
   - Use `check_campaign_status.py` periodically to monitor for stuck campaigns
