# Test Plan for Health Check and Inbox Fixes

## Overview
This document outlines the test plan for verifying the fixes applied to:
1. Health check database endpoint (SQLAlchemy 2.0 compatibility)
2. Inbox replies endpoint (query and data retrieval)
3. Reply worker message storage

---

## Test Environment Setup

### Prerequisites
- Docker Compose services running
- Database initialized with migrations
- At least one user account created
- At least one workspace with a connected Gmail mailbox
- At least one campaign with sent emails

### Test Data Requirements
- **User Account**: Test user with email/password
- **Workspace**: Active workspace linked to test user
- **Mailbox**: Connected Gmail mailbox (OAuth completed)
- **Campaign**: At least one campaign with status RUNNING or COMPLETED
- **Leads**: At least 2-3 leads added to campaigns
- **Messages**: 
  - At least 2-3 outbound messages (sent emails)
  - At least 1-2 inbound messages (replies) - can be manually created for testing

---

## Test Cases

### 1. Health Check Endpoint Fix

#### Test Case 1.1: Database Health Check - Success
**Objective**: Verify the health check endpoint returns healthy status

**Steps**:
1. Ensure database is running and accessible
2. Make GET request to: `http://localhost:8000/api/health/db`
3. Verify response status code is 200
4. Verify response body contains:
   ```json
   {
     "status": "healthy",
     "database": "connected"
   }
   ```

**Expected Result**: ✅ Endpoint returns healthy status without SQL error

**Previous Error**: 
```json
{
  "status": "unhealthy",
  "database": "disconnected",
  "error": "Textual SQL expression 'SELECT 1' should be explicitly declared as text('SELECT 1')"
}
```

---

### 2. Inbox Replies Endpoint Fix

#### Test Case 2.1: List Replies - Empty State
**Objective**: Verify endpoint handles empty state correctly

**Steps**:
1. Login as test user and get auth token
2. Get workspace ID from user's workspaces
3. Make GET request to: `http://localhost:8000/api/inbox/replies?workspace_id={workspace_id}`
4. Include Authorization header: `Bearer {token}`
5. Verify response status code is 200
6. Verify response body is an empty array: `[]`

**Expected Result**: ✅ Returns empty array without errors

---

#### Test Case 2.2: List Replies - With Data
**Objective**: Verify endpoint returns replies when they exist

**Prerequisites**: 
- At least one inbound message exists in database
- Message is linked to a campaign in the workspace

**Steps**:
1. Login as test user and get auth token
2. Get workspace ID
3. Make GET request to: `http://localhost:8000/api/inbox/replies?workspace_id={workspace_id}`
4. Include Authorization header: `Bearer {token}`
5. Verify response status code is 200
6. Verify response body is an array
7. Verify each reply object contains:
   - `id` (number)
   - `lead_email` (string)
   - `lead_name` (string or null)
   - `campaign_name` (string)
   - `subject` (string or null)
   - `body` (string or null)
   - `classification` (string or null)
   - `received_at` (ISO datetime string or null)

**Expected Result**: ✅ Returns array of reply objects with all required fields

---

#### Test Case 2.3: List Replies - Filter by Campaign
**Objective**: Verify campaign filtering works

**Prerequisites**: 
- Multiple campaigns with replies

**Steps**:
1. Login and get auth token
2. Get workspace ID and a campaign ID that has replies
3. Make GET request: `http://localhost:8000/api/inbox/replies?workspace_id={workspace_id}&campaign_id={campaign_id}`
4. Verify response only contains replies for that campaign
5. Verify all returned replies have matching campaign

**Expected Result**: ✅ Returns only replies for specified campaign

---

#### Test Case 2.4: List Replies - Pagination
**Objective**: Verify skip/limit parameters work

**Steps**:
1. Login and get auth token
2. Get workspace ID
3. Make request with `skip=0&limit=10`
4. Verify response contains max 10 items
5. Make request with `skip=10&limit=10`
6. Verify response contains next 10 items (if available)

**Expected Result**: ✅ Pagination works correctly

---

#### Test Case 2.5: List Replies - Unauthorized Access
**Objective**: Verify workspace access control

**Steps**:
1. Login as User A and get token
2. Get workspace ID belonging to User B
3. Make GET request with User A's token to User B's workspace
4. Verify response status code is 404
5. Verify error message: "Workspace not found"

**Expected Result**: ✅ Access control prevents unauthorized access

---

### 3. Debug Endpoint

#### Test Case 3.1: Debug Replies Endpoint
**Objective**: Verify debug endpoint provides useful diagnostic information

**Steps**:
1. Login and get auth token
2. Get workspace ID
3. Make GET request: `http://localhost:8000/api/inbox/debug/replies?workspace_id={workspace_id}`
4. Verify response contains:
   - `workspace_id`
   - `total_messages_in_db`
   - `total_inbound_messages`
   - `total_outbound_messages`
   - `workspace_messages_total`
   - `workspace_inbound_messages`
   - `sample_messages` (array)
   - `campaigns_count`
   - `campaign_leads_count`

**Expected Result**: ✅ Returns detailed diagnostic information

---

### 4. Reply Worker Message Storage

#### Test Case 4.1: Reply Detection and Storage
**Objective**: Verify reply worker stores messages correctly

**Prerequisites**:
- Campaign with sent emails
- Gmail inbox with replies to campaign emails

**Steps**:
1. Ensure Celery worker is running
2. Wait for reply worker to poll (runs every 2 minutes)
3. Check Celery logs for reply detection
4. Query database directly:
   ```sql
   SELECT * FROM messages 
   WHERE direction = 'INBOUND' 
   ORDER BY received_at DESC 
   LIMIT 5;
   ```
5. Verify messages are stored with:
   - `direction = 'INBOUND'`
   - `campaign_lead_id` is set
   - `gmail_message_id` is set
   - `gmail_thread_id` matches outbound message
   - `classification` is set
   - `received_at` is set

**Expected Result**: ✅ Replies are detected and stored correctly

---

#### Test Case 4.2: Reply Classification
**Objective**: Verify replies are classified correctly

**Steps**:
1. Send test emails from campaign
2. Reply with different types:
   - Unsubscribe request ("unsubscribe", "remove me")
   - Booking intent ("schedule a call", "book a meeting")
   - Negative ("not interested", "no thanks")
   - Neutral (regular reply)
3. Wait for reply worker to process
4. Check message classifications in database
5. Verify classifications match expected types

**Expected Result**: ✅ Replies are classified correctly

---

#### Test Case 4.3: Campaign Lead Status Update
**Objective**: Verify campaign lead status updates on reply

**Steps**:
1. Create campaign with leads
2. Send initial email
3. Verify `campaign_leads.status = 'SENT'`
4. Receive reply
5. Wait for reply worker to process
6. Check database:
   ```sql
   SELECT status, replied_at, next_action_at 
   FROM campaign_leads 
   WHERE id = {campaign_lead_id};
   ```
7. Verify:
   - `status = 'REPLIED'`
   - `replied_at` is set
   - `next_action_at` is NULL

**Expected Result**: ✅ Campaign lead status updates correctly, future sends stopped

---

### 5. Frontend Inbox Page

#### Test Case 5.1: Inbox Page Loads
**Objective**: Verify inbox page displays correctly

**Steps**:
1. Login to frontend
2. Navigate to `/inbox`
3. Verify page loads without errors
4. Verify UI shows:
   - Header with navigation
   - Reply list sidebar (left)
   - Reply detail view (right)
   - "Replies (N)" count in sidebar

**Expected Result**: ✅ Page loads and displays UI correctly

---

#### Test Case 5.2: Inbox Shows Replies
**Objective**: Verify replies are displayed in UI

**Prerequisites**: At least one reply exists

**Steps**:
1. Navigate to `/inbox`
2. Verify reply list shows replies
3. Verify each reply shows:
   - Lead name/email
   - Subject
   - Campaign name
   - Classification badge
   - Received date
4. Click on a reply
5. Verify detail view shows:
   - Full subject
   - Lead email
   - Thread conversation
   - Reply input box

**Expected Result**: ✅ Replies are displayed correctly in UI

---

#### Test Case 5.3: Inbox Empty State
**Objective**: Verify empty state displays correctly

**Steps**:
1. Use workspace with no replies
2. Navigate to `/inbox`
3. Verify empty state message: "No replies yet"
4. Verify no errors in browser console

**Expected Result**: ✅ Empty state displays correctly

---

#### Test Case 5.4: Reply Classification in UI
**Objective**: Verify classification buttons work

**Prerequisites**: At least one reply exists

**Steps**:
1. Navigate to `/inbox`
2. Select a reply
3. Click on classification buttons (📅 Interested, 💬 Neutral, etc.)
4. Verify classification updates
5. Refresh page
6. Verify classification persists

**Expected Result**: ✅ Classification updates work correctly

---

#### Test Case 5.5: Send Reply from UI
**Objective**: Verify sending replies from inbox works

**Prerequisites**: At least one reply exists

**Steps**:
1. Navigate to `/inbox`
2. Select a reply
3. Type reply message in textarea
4. Click "🚀 Send Reply" button
5. Verify success message or UI update
6. Check Gmail inbox to verify email was sent
7. Verify thread view updates with new message

**Expected Result**: ✅ Replies can be sent from UI

---

## Manual Testing Checklist

### Quick Smoke Test
- [ ] Health check endpoint works: `GET /api/health/db`
- [ ] Inbox replies endpoint works: `GET /api/inbox/replies?workspace_id={id}`
- [ ] Frontend inbox page loads: `http://localhost:3000/inbox`
- [ ] Debug endpoint works: `GET /api/inbox/debug/replies?workspace_id={id}`

### Full Test Suite
- [ ] All Test Cases 1.x (Health Check)
- [ ] All Test Cases 2.x (Inbox Replies Endpoint)
- [ ] All Test Cases 3.x (Debug Endpoint)
- [ ] All Test Cases 4.x (Reply Worker)
- [ ] All Test Cases 5.x (Frontend Inbox)

---

## Automated Testing (Future)

### Unit Tests
```python
# backend/tests/test_health.py
def test_database_health_check():
    response = client.get("/api/health/db")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

# backend/tests/test_inbox.py
def test_list_replies_empty():
    response = client.get(f"/api/inbox/replies?workspace_id={workspace_id}")
    assert response.status_code == 200
    assert response.json() == []

def test_list_replies_with_data():
    # Create test data
    # ...
    response = client.get(f"/api/inbox/replies?workspace_id={workspace_id}")
    assert response.status_code == 200
    assert len(response.json()) > 0
```

### Integration Tests
- Test full reply flow: Send email → Receive reply → Store → Display
- Test classification pipeline
- Test campaign lead status updates

---

## Troubleshooting Guide

### Issue: Health check still fails
**Solution**: 
- Verify SQLAlchemy version: `pip show sqlalchemy`
- Ensure `text()` import is present
- Check database connection string

### Issue: Inbox shows no replies
**Debug Steps**:
1. Check debug endpoint: `GET /api/inbox/debug/replies?workspace_id={id}`
2. Verify messages exist in database:
   ```sql
   SELECT COUNT(*) FROM messages WHERE direction = 'INBOUND';
   ```
3. Verify workspace_id matches:
   ```sql
   SELECT m.* FROM messages m
   JOIN campaign_leads cl ON m.campaign_lead_id = cl.id
   JOIN campaigns c ON cl.campaign_id = c.id
   WHERE c.workspace_id = {workspace_id};
   ```
4. Check Celery worker logs for reply processing
5. Verify Gmail OAuth tokens are valid

### Issue: Replies not being detected
**Debug Steps**:
1. Check Celery worker is running: `docker-compose logs celery_worker`
2. Verify mailbox is active: `SELECT * FROM mailboxes WHERE is_active = true;`
3. Check last_polled_at timestamp
4. Manually trigger reply worker if needed
5. Check Gmail API quota/errors

---

## Test Data Creation Script

For testing purposes, you can create test replies manually:

```python
# backend/create_test_reply.py
from app.database import SessionLocal
from app.models import Message, CampaignLead, MessageDirection, ReplyClassification
from datetime import datetime

db = SessionLocal()

# Get a campaign_lead
campaign_lead = db.query(CampaignLead).first()

# Create test reply
reply = Message(
    campaign_lead_id=campaign_lead.id,
    direction=MessageDirection.INBOUND,
    step_number=-1,
    gmail_message_id="test_msg_123",
    gmail_thread_id=campaign_lead.campaign.mailbox.email,  # Use existing thread
    subject="Re: Test Campaign",
    body="This is a test reply message.",
    classification=ReplyClassification.NEUTRAL,
    received_at=datetime.utcnow()
)
db.add(reply)
db.commit()
```

---

## Success Criteria

✅ **All fixes verified working:**
- Health check endpoint returns healthy status
- Inbox replies endpoint returns data correctly
- Frontend inbox page displays replies
- Reply worker stores messages correctly
- No errors in logs
- All test cases pass

---

## Notes

- Test with real Gmail account for full integration testing
- Monitor Celery worker logs during testing
- Check database directly for data verification
- Use browser DevTools to check API calls and responses
- Test with multiple workspaces/users for access control

---

**Last Updated**: 2026-01-03  
**Test Plan Version**: 1.0




