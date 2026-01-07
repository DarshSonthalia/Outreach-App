#!/usr/bin/env python3
"""
Quick reference: API commands for token refresh issue recovery
"""

# ==============================================================================
# 1. CHECK CURRENT STATUS (Run diagnostic)
# ==============================================================================

"""
Command: python check_campaign_status.py

Shows:
- How many campaigns are paused due to auth issues
- Which mailboxes need re-authentication
- Campaign details and pause reasons
"""

# ==============================================================================
# 2. USER RE-AUTHENTICATES (Automatic fix)
# ==============================================================================

"""
Step 1: Get OAuth URL
  GET /api/mailboxes/oauth/url?workspace_id=<workspace_id>
  
  Response:
  {
    "auth_url": "https://accounts.google.com/o/oauth2/auth?..."
  }

Step 2: Visit the OAuth URL in browser
  - User logs in with Google
  - User grants permissions
  - Redirected to callback
  
Step 3: Auto-resume triggers
  - Mailbox tokens updated
  - Status = ACTIVE
  - All paused campaigns auto-resume
  - Sends rescheduled to start immediately
"""

# ==============================================================================
# 3. MANUALLY RESUME A CAMPAIGN (If auto-resume didn't work)
# ==============================================================================

"""
Command: 
  POST /api/campaigns/{campaign_id}/resume
  
  Headers:
    Authorization: Bearer <access_token>

Example with curl:
  curl -X POST http://localhost:8000/api/campaigns/5/resume \
    -H "Authorization: Bearer eyJhbGc..." \
    -H "Content-Type: application/json"

Response (success):
  {
    "campaign_id": 5,
    "name": "Test Campaign",
    "status": "RUNNING",
    "pause_reason": null,
    ...
  }

Response (error - campaign not paused):
  {
    "detail": "Campaign is RUNNING, not paused"
  }

Response (error - mailbox not active):
  {
    "detail": "Mailbox is still inactive. Please re-authenticate first."
  }
"""

# ==============================================================================
# 4. DEBUG: View campaign details
# ==============================================================================

"""
Command:
  GET /api/campaigns/{campaign_id}/dashboard
  
  Headers:
    Authorization: Bearer <access_token>

Shows:
  - Campaign status
  - Pause reason (if any)
  - Emails sent today
  - Total emails sent
  - Reply count
  - Meetings booked
  - Daily send limit
  - Remaining sends for today
"""

# ==============================================================================
# 5. POSTGRES: Check database directly (if needed)
# ==============================================================================

"""
Connect to database:
  psql -U outreach_user -d outreach_db -h localhost

View paused campaigns:
  SELECT id, name, status, pause_reason, mailbox_id 
  FROM campaigns 
  WHERE status = 'PAUSED' 
  AND pause_reason ILIKE '%re-authentication%';

View mailbox status:
  SELECT id, email, is_active, status, token_expiry 
  FROM mailboxes;

Manually resume campaign (NOT RECOMMENDED):
  UPDATE campaigns 
  SET status = 'RUNNING', pause_reason = NULL
  WHERE id = <campaign_id>;
  
  UPDATE campaign_leads 
  SET next_action_at = NOW() 
  WHERE campaign_id = <campaign_id> 
  AND status = 'PENDING';
"""

# ==============================================================================
# 6. LOGS: Monitor token refresh issues
# ==============================================================================

"""
Watch logs in real-time:
  docker-compose logs -f outreach_backend | grep -i "token\|refresh"

Look for:
  - "Token refresh failed" → indicates the problem
  - "Refreshed tokens" → indicates successful recovery
  - "reauth_required" → mailbox marked for re-auth
"""

# ==============================================================================
# 7. COMMON ERROR MESSAGES & SOLUTIONS
# ==============================================================================

"""
Error: "Mailbox requires re-authentication: Token refresh failed"
Solution: User re-authenticates via OAuth URL

Error: "Campaign is RUNNING, not paused"
Solution: Campaign doesn't need resuming—it's already running

Error: "Mailbox is still inactive. Please re-authenticate first."
Solution: Must complete OAuth flow before resuming campaigns

Error: "Campaign not found"
Solution: Check campaign_id exists and belongs to user's workspace
"""

# ==============================================================================
# 8. WORKFLOW: Complete recovery steps
# ==============================================================================

"""
Step-by-step recovery for end users:

1. Notice campaign paused with: "Mailbox requires re-authentication"

2. Click "Reconnect Gmail" or:
   a. GET /api/mailboxes/oauth/url?workspace_id=<your_workspace>
   b. Copy the auth_url
   c. Paste in browser
   d. Complete Google login

3. You'll be redirected to success page
   (Campaigns auto-resume here)

4. If still paused, click "Resume Campaign":
   POST /api/campaigns/{campaign_id}/resume

5. Campaign resumes and sends continue

6. View progress in dashboard:
   GET /api/campaigns/{campaign_id}/dashboard
"""

# ==============================================================================
# 9. MONITORING: Automated health checks (optional)
# ==============================================================================

"""
Suggested cron job to detect issues:
  
  # Every 5 minutes, check for campaigns stuck in re-auth
  */5 * * * * python /app/check_campaign_status.py 2>&1 | \
    grep "Paused (auth issues):" | \
    grep -v "0)" && \
    curl -X POST https://your-slack-webhook \
      -d '{"text": "WARNING: Campaigns stuck due to auth issues"}'
"""

print(__doc__)
