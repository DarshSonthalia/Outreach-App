#!/usr/bin/env python3
"""
Visual Guide: New Mailbox Management UI on Dashboard

This file describes the updated mailbox section layout and interactions.
"""

print("""
╔════════════════════════════════════════════════════════════════════════════╗
║                      MAILBOX MANAGEMENT SECTION                            ║
║                          (Dashboard Page)                                   ║
╚════════════════════════════════════════════════════════════════════════════╝

┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│  Connected Mailboxes                               [+ Add Mailbox] button    │
│  ═════════════════════════════════════════════════════════════════════════   │
│                                                                              │
│  For each mailbox:                                                           │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │ 📬  alice@company.com                  [Active]  [🔄 Re-link] [✕ Disc] │  │
│  │     Connected Jan 7, 2026                                               │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │ 📬  bob@company.com                   [Inactive] [🔄 Re-link] [✕ Disc] │  │
│  │     Connected Jan 6, 2026                                               │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │ 📬  charlie@different.com              [Active]              [✕ Disc]  │  │
│  │     Connected Jan 5, 2026                                               │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

═══════════════════════════════════════════════════════════════════════════════

BUTTON VISIBILITY RULES:
═════════════════════

✅ Active Mailbox (mailbox.is_active = true):
   └─ Shows: [✕ Disconnect] button only
   └─ Re-link button: HIDDEN (not needed)

❌ Inactive Mailbox (mailbox.is_active = false):
   └─ Shows: [🔄 Re-link] button + [✕ Disconnect] button
   └─ Re-link allows user to re-authenticate without creating new mailbox

═══════════════════════════════════════════════════════════════════════════════

INTERACTION FLOWS:
══════════════════

Flow 1: ADD A NEW MAILBOX
─────────────────────────
User clicks "+ Add Mailbox"
           ↓
Get OAuth URL from backend
           ↓
Redirect to Google login
           ↓
User grants permissions
           ↓
Callback creates/updates mailbox
           ↓
Mailbox appears in list as [Active]

Flow 2: RE-LINK INACTIVE MAILBOX
────────────────────────────────
User sees [Inactive] badge
           ↓
User clicks [🔄 Re-link]
           ↓
Get OAuth URL from backend
           ↓
Redirect to Google login
           ↓
User grants permissions
           ↓
Callback updates existing mailbox
           ↓
Mailbox status: [Active]
           ↓
Paused campaigns auto-resume

Flow 3: DISCONNECT A MAILBOX
──────────────────────────────
User clicks [✕ Disconnect]
           ↓
Confirmation dialog:
  "Are you sure you want to disconnect alice@company.com?
   Any campaigns using this mailbox will be paused."
           ↓
User confirms
           ↓
Mailbox marked inactive (is_active = false)
           ↓
All campaigns using this mailbox paused
           ↓
Mailbox shows [Inactive] badge
           ↓
User can re-link later if needed

Flow 4: USE MULTIPLE MAILBOXES
───────────────────────────────
Connect mailbox A (alice@company.com)
           ↓
Create Campaign 1 → Select mailbox A for sends
           ↓
Click "+ Add Mailbox"
           ↓
Connect mailbox B (bob@company.com)
           ↓
Create Campaign 2 → Select mailbox B for sends
           ↓
Both campaigns run in parallel using different mailboxes
           ↓
Dashboard shows both mailboxes + both campaigns

═══════════════════════════════════════════════════════════════════════════════

MAILBOX CARD DETAILS:
════════════════════

Left side:
  📬 Icon (mailbox emoji)

Center:
  Email address (bold)
  Connection date (gray, smaller)

Right side (flex-end):
  [Active] or [Inactive] badge
    - Active = green background + white text
    - Inactive = red background + white text

Buttons (rightmost):
  If Inactive:
    [🔄 Re-link] ← blue button, left-aligned
  Always:
    [✕ Disconnect] ← red button

Button states:
  Normal: background=rgba(33,150,243,0.1), color=#2196f3 (blue)
  Disabled: opacity=0.6, cursor=not-allowed
  Hover: could add scale/shadow effect

═══════════════════════════════════════════════════════════════════════════════

EMPTY STATE (No Mailboxes):
═══════════════════════════

┌─────────────────────────────────────────┐
│                                          │
│   Connected Mailboxes      [+ Add Mailbox]
│                                          │
│   ┌─────────────────────────────────┐   │
│   │                                  │   │
│   │   No mailboxes connected         │   │
│   │                                  │   │
│   │   [Connect Gmail] button         │   │
│   │                                  │   │
│   └─────────────────────────────────┘   │
│                                          │
└─────────────────────────────────────────┘

═══════════════════════════════════════════════════════════════════════════════

RESPONSIVE BEHAVIOR:
════════════════════

Desktop (> 1024px):
  └─ Full layout with all buttons visible

Tablet (768px - 1024px):
  └─ Button text may abbreviate: "Re-link" → "Relink", etc.
  └─ Spacing may adjust but all elements visible

Mobile (< 768px):
  └─ Buttons stack vertically
  └─ Icon + email take full width
  └─ Status badge + buttons below
  └─ Consider: tooltip on hover for "Disconnect" warning

═══════════════════════════════════════════════════════════════════════════════

EXAMPLE: MULTI-MAILBOX CAMPAIGN CREATION
══════════════════════════════════════════

In "Create Campaign" page, when selecting mailbox:

┌─────────────────────────────────────────┐
│ Select Sending Mailbox:                  │
│                                          │
│ ○ alice@company.com      [Active]        │
│ ● bob@company.com        [Active]        │
│ ○ charlie@different.com  [Inactive]      │
│                                          │
│ (Disabled options shown in gray)         │
└─────────────────────────────────────────┘

Only ACTIVE mailboxes can be selected for campaigns.

═══════════════════════════════════════════════════════════════════════════════

BACKEND CHANGES NEEDED:
═══════════════════════

Campaign creation page needs to:
1. Fetch mailboxes: GET /api/mailboxes/?workspace_id={id}
2. Filter for is_active=true
3. Show in dropdown/radio selection
4. Save selected mailbox_id to campaign.mailbox_id

This is already implemented - just needs to be used in campaigns/new page.

═══════════════════════════════════════════════════════════════════════════════
""")
