#!/usr/bin/env python3
"""
QUICK REFERENCE: Multiple Mailbox & Re-link Feature
=====================================================

For developers and end users
"""

print("""
╔══════════════════════════════════════════════════════════════════════════╗
║                                                                          ║
║                   MAILBOX MANAGEMENT - QUICK REFERENCE                  ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════╝

📍 LOCATION ON DASHBOARD
═════════════════════════
Dashboard → Bottom Section → "Connected Mailboxes"

🎯 WHAT'S NEW
═════════════
1. [+ Add Mailbox] button in header        → Connect more Gmail accounts
2. [🔄 Re-link] button on inactive boxes   → Re-authenticate without recreating
3. [✕ Disconnect] button on all boxes     → Safely remove mailbox
4. Status badge [Active] or [Inactive]     → Shows current state

🚀 USER ACTIONS
═══════════════

ACTION 1: ADD A NEW MAILBOX
──────────────────────────
Click: "+ Add Mailbox" button
  ↓
Google OAuth login
  ↓
Grant permissions
  ↓
New mailbox appears as [Active]

ACTION 2: RE-LINK INACTIVE MAILBOX
──────────────────────────────────
See mailbox with [Inactive] badge
  ↓
Click: "🔄 Re-link" button
  ↓
Google OAuth login (same account)
  ↓
Mailbox becomes [Active]
  ↓
Paused campaigns auto-resume

ACTION 3: DISCONNECT A MAILBOX
──────────────────────────────
Click: "✕ Disconnect" button on any mailbox
  ↓
Confirm: "Are you sure?"
  ↓
Mailbox marked [Inactive]
  ↓
All campaigns using it are paused
  ↓
Can re-link later if needed

ACTION 4: USE IN CAMPAIGNS
─────────────────────────
Create new campaign
  ↓
Select mailbox: Only [Active] mailboxes shown
  ↓
Campaign sends using selected mailbox

📋 MAILBOX STATES
═════════════════

[Active] (GREEN BADGE)
├─ Token is valid
├─ Can send emails
├─ Can be selected for new campaigns
└─ Shows: [✕ Disconnect] button only

[Inactive] (RED BADGE)
├─ Token expired or refresh failed
├─ Cannot send emails
├─ Cannot be selected for new campaigns
├─ All campaigns paused
└─ Shows: [🔄 Re-link] + [✕ Disconnect] buttons

🔄 TOKEN REFRESH FLOW
═════════════════════

Normal Send:
  Campaign worker
    ↓
  Check token expiry
    ↓
  If expired: Auto-refresh via Gmail API
    ↓
  Success? Send email
    ↓
  Failure? Mark mailbox [Inactive] & pause campaigns

User Re-links:
  Click [🔄 Re-link]
    ↓
  Complete Google OAuth
    ↓
  New tokens stored
    ↓
  Mailbox → [Active]
    ↓
  Paused campaigns → [Running] (auto-resume)

📊 MULTIPLE MAILBOX EXAMPLE
═══════════════════════════

Workspace: "My Company"
├─ Mailbox 1: alice@company.com    [Active]
│  └─ Campaign A (sends 100/day)
│  └─ Campaign B (sends 50/day)
│
├─ Mailbox 2: bob@company.com      [Active]
│  └─ Campaign C (sends 75/day)
│
└─ Mailbox 3: charlie@old.com      [Inactive]
   └─ Campaign D (paused)

Total: 3 campaigns running in parallel, using 2 mailboxes

🛠️ BACKEND ENDPOINTS
════════════════════

GET /api/mailboxes/oauth/url?workspace_id={id}
  → Returns: { "auth_url": "https://..." }
  → Used for: Adding new mailbox OR re-linking existing

GET /api/mailboxes/?workspace_id={id}
  → Returns: [ { id, email, is_active, status, ... } ]
  → Used for: Listing all mailboxes

DELETE /api/mailboxes/{mailbox_id}
  → Returns: 204 No Content
  → Used for: Disconnecting mailbox

GET /api/mailboxes/oauth/callback?code={code}&state={workspace_id}
  → Handles: OAuth completion from Google
  → Creates: New mailbox OR updates existing
  → Auto-resumes: Paused campaigns

💡 BEST PRACTICES
═════════════════

1. Keep Gmail account passwords secure in Google Account settings
2. Use different Gmail accounts for different purposes if needed
3. Re-link before token expires (Gmail will notify if issues occur)
4. Disconnect unused mailboxes to keep things clean
5. Check mailbox status before launching campaigns

⚠️ THINGS TO REMEMBER
══════════════════════

✓ Re-linking doesn't create a new mailbox - it updates existing
✓ Disconnecting pauses campaigns but doesn't delete them
✓ All campaigns with paused mailbox can be resumed by re-linking
✓ Only [Active] mailboxes can be selected for new campaigns
✓ Multiple campaigns can run simultaneously using different mailboxes
✓ Each mailbox has its own email sending limit (as per safety config)

🔒 SECURITY NOTES
═════════════════

✓ OAuth tokens encrypted at rest
✓ Refresh tokens stored securely
✓ Re-link uses same OAuth flow as initial setup
✓ Disconnect is soft (can recover by re-linking)
✓ All operations require user authentication

📞 SUPPORT/TROUBLESHOOTING
════════════════════════════

Issue: Re-link button not showing
  → Check if mailbox status is [Inactive]
  → Refresh page

Issue: Campaign won't start
  → Check if selected mailbox is [Active]
  → If [Inactive], click Re-link

Issue: "Mailbox requires re-authentication"
  → Token expired, click [🔄 Re-link]
  → Campaigns will auto-resume after re-auth

Issue: Added mailbox but not in dropdown
  → Refresh page to see it
  → Check if mailbox is [Active]
  → Only [Active] mailboxes appear in campaign selection

Issue: Want to use different Gmail
  → Disconnect old mailbox (campaigns pause)
  → Add new mailbox (re-auth with different account)
  → Create new campaigns with new mailbox

═══════════════════════════════════════════════════════════════════════════════

KEYBOARD SHORTCUTS (Future Enhancement)
════════════════════════════════════════
[Not yet implemented, but could add:]
- 'A' → Add mailbox (focus button)
- 'R' → Re-link (first inactive mailbox)
- 'D' → Disconnect (focus first mailbox)

═══════════════════════════════════════════════════════════════════════════════

RELATED DOCUMENTATION
══════════════════════
- MAILBOX_FEATURES.md       → Full feature documentation
- MAILBOX_UI_GUIDE.py       → Visual UI guide
- TOKEN_REFRESH_FIX.md      → How token refresh & auto-resume work
- IMPLEMENTATION_SUMMARY.md → Code changes & testing guide

═══════════════════════════════════════════════════════════════════════════════

VERSION HISTORY
════════════════
2026-01-07  v1.0  Initial implementation
            ✓ Multiple mailboxes per workspace
            ✓ Re-link inactive mailboxes
            ✓ Disconnect with confirmation
            ✓ Auto-resume on re-auth
            ✓ Multi-mailbox campaign support

═══════════════════════════════════════════════════════════════════════════════
""")
