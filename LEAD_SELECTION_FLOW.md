# Lead Selection Flow - Complete Analysis

This document traces exactly what happens when a user selects a lead in the inbox, from the UI click through the database queries and API calls.

## 🎯 User Actions Flow

### When User Selects a Lead in Inbox

```
User clicks on a reply in the inbox list
    ↓
onClick handler: handleSelectReply(reply)
    ↓
Updates UI state: setSelectedReply(reply)
    ↓
Calls API: inbox.getReply(token, reply.id)
    ↓
Backend processes: GET /api/inbox/replies/{reply_id}
    ↓
Returns full thread + reply details
    ↓
Updates UI with thread messages: setThread(fullReply.thread)
```

---

## 📱 Frontend Code Flow

### Step 1: Initial Inbox Load

**File**: [src/app/inbox/page.tsx](src/app/inbox/page.tsx#L42)

```typescript
useEffect(() => {
    const init = async () => {
        const storedToken = localStorage.getItem('token');
        setToken(storedToken);
        
        // Get workspace ID
        const userWorkspaces = await workspaces.list(storedToken);
        const wsId = userWorkspaces[0].id;
        setWorkspaceId(wsId);
        
        // Get all replies for this workspace
        const replyList = await inbox.replies(storedToken, wsId);
        setReplies(replyList);
        
        // Auto-select first reply
        if (replyList.length > 0) {
            handleSelectReply(replyList[0], storedToken);
        }
    };
    init();
}, [router]);
```

**What happens:**
1. Load JWT token from localStorage
2. Fetch workspaces - get user's first workspace ID
3. Call `inbox.replies(token, workspaceId)` - gets all replies
4. Auto-select first reply

---

### Step 2: API Call - List Replies

**File**: [src/lib/api.ts](src/lib/api.ts#L221)

```typescript
export const inbox = {
    replies: (token: string, workspaceId: number, campaignId?: number) => {
        let url = `/api/inbox/replies?workspace_id=${workspaceId}`;
        if (campaignId) url += `&campaign_id=${campaignId}`;
        return apiRequest<any[]>(url, { token });
    },
    // ... other methods
};
```

**Request made:**
```
GET /api/inbox/replies?workspace_id=1
Headers: Authorization: Bearer <JWT_TOKEN>
```

---

### Step 3: Backend Processes - List Replies Endpoint

**File**: [backend/app/routers/inbox.py](backend/app/routers/inbox.py#L46)

```python
@router.get("/replies", response_model=List[ReplyResponse])
async def list_replies(
    workspace_id: int,
    campaign_id: int = None,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
```

**Processing steps:**

#### 3a. Verify Workspace Ownership
```python
workspace = db.query(Workspace).filter(
    Workspace.id == workspace_id,
    Workspace.user_id == current_user.id
).first()

if not workspace:
    raise HTTPException(404, "Workspace not found")
```

Security check: Ensure the workspace belongs to the authenticated user.

#### 3b. Get All Campaign Leads
```python
campaign_leads_query = db.query(CampaignLead.id).join(
    Campaign, CampaignLead.campaign_id == Campaign.id
).filter(
    Campaign.workspace_id == workspace_id
)

campaign_lead_ids = [cl[0] for cl in campaign_leads_query.all()]
```

Gets all `campaign_lead` records linked to campaigns in this workspace.

**Database query:**
```sql
SELECT campaign_lead.id 
FROM campaign_lead
JOIN campaign ON campaign_lead.campaign_id = campaign.id
WHERE campaign.workspace_id = 1
```

#### 3c. Get Latest Message Per Conversation
```python
for cl_id in campaign_lead_ids:
    latest_msg = db.query(Message).filter(
        Message.campaign_lead_id == cl_id
    ).order_by(
        Message.received_at.desc().nullslast(),
        Message.sent_at.desc().nullslast(),
        Message.id.desc()
    ).first()
```

For each campaign_lead, fetch the LATEST message in that conversation.

**Database query per campaign_lead:**
```sql
SELECT * FROM message
WHERE campaign_lead_id = 123
ORDER BY received_at DESC, sent_at DESC, id DESC
LIMIT 1
```

#### 3d. Build Response Objects
```python
result.append(ReplyResponse(
    id=latest_msg.id,
    lead_email=lead.email,
    lead_name=f"{lead.first_name or ''} {lead.last_name or ''}".strip(),
    campaign_name=campaign.name,
    subject=latest_msg.subject,
    body=clean_message_body(latest_msg.body),  # Remove quoted text
    classification=latest_msg.classification,
    received_at=latest_msg.received_at or latest_msg.sent_at,
    direction=latest_msg.direction.value
))
```

For each message, get associated lead and campaign data.

#### 3e. Sort & Paginate
```python
result.sort(key=lambda x: x.received_at or '', reverse=True)
paginated_result = result[skip:skip+limit]
return paginated_result
```

Sort by timestamp (newest first), then apply pagination.

**Response returned to frontend:**
```json
[
    {
        "id": 456,
        "lead_email": "john@acme.com",
        "lead_name": "John Smith",
        "campaign_name": "Q1 Outreach",
        "subject": "RE: Check out our service",
        "body": "Thanks for reaching out...",
        "classification": "booking_intent",
        "received_at": "2025-01-10T14:32:00Z",
        "direction": "inbound"
    },
    // ... more replies
]
```

---

### Step 4: Frontend Receives Reply List

**File**: [src/app/inbox/page.tsx](src/app/inbox/page.tsx#L70)

```typescript
const replyList = await inbox.replies(storedToken, wsId);
setReplies(replyList);

// Auto-select first reply if exists
if (replyList.length > 0) {
    handleSelectReply(replyList[0], storedToken);
}
```

The UI now renders the reply list on the left sidebar. Each reply shows:
- Lead name/email
- Subject line
- Classification badge (if classified)
- Campaign name
- Timestamp

---

### Step 5: User Clicks on a Reply

**File**: [src/app/inbox/page.tsx](src/app/inbox/page.tsx#L253)

```typescript
replies.map((reply) => (
    <div
        key={reply.id}
        onClick={() => handleSelectReply(reply)}  // <-- USER CLICKS HERE
        style={{
            background: selectedReply?.id === reply.id ? 'var(--bg-card)' : 'transparent',
        }}
    >
        {/* Render reply preview */}
    </div>
))
```

---

### Step 6: handleSelectReply Function

**File**: [src/app/inbox/page.tsx](src/app/inbox/page.tsx#L97)

```typescript
const handleSelectReply = async (reply: any) => {
    // 1. Update state to highlight selected reply
    setSelectedReply(reply);
    
    if (!token) return;

    try {
        // 2. Fetch the full thread for this reply
        const fullReply = await inbox.getReply(token, reply.id);
        
        // 3. Update thread state with all messages
        setThread(fullReply.thread || []);
        
        // 4. Reset reply input
        setReplyBody('');
    } catch (err) {
        console.error('Error fetching thread:', err);
        setThread([]);
    }
};
```

**Steps:**
1. Highlight the selected reply in the list UI
2. Call backend to get full conversation thread
3. Display all messages in thread view
4. Clear reply input box

---

### Step 7: API Call - Get Full Reply Thread

**File**: [src/lib/api.ts](src/lib/api.ts#L231)

```typescript
getReply: (token: string, replyId: number) =>
    apiRequest<any>(`/api/inbox/replies/${replyId}`, { token }),
```

**Request made:**
```
GET /api/inbox/replies/456
Headers: Authorization: Bearer <JWT_TOKEN>
```

---

### Step 8: Backend Processes - Get Reply Endpoint

**File**: [backend/app/routers/inbox.py](backend/app/routers/inbox.py#L198)

```python
@router.get("/replies/{reply_id}")
async def get_reply(
    reply_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
```

**Processing steps:**

#### 8a. Fetch the Reply Message
```python
reply = db.query(Message).join(CampaignLead).join(Campaign).join(Workspace).filter(
    Message.id == reply_id,
    Workspace.user_id == current_user.id,
    Message.direction == MessageDirection.INBOUND  # Must be inbound
).first()

if not reply:
    raise HTTPException(404, "Reply not found")
```

**Database query:**
```sql
SELECT message.* FROM message
JOIN campaign_lead ON message.campaign_lead_id = campaign_lead.id
JOIN campaign ON campaign_lead.campaign_id = campaign.id
JOIN workspace ON campaign.workspace_id = workspace.id
WHERE message.id = 456
  AND workspace.user_id = 1
  AND message.direction = 'INBOUND'
```

Security checks:
- Message exists
- Message is inbound (from lead, not our outbound email)
- Workspace belongs to user

#### 8b. Get Lead & Campaign Data
```python
lead = reply.campaign_lead.lead
campaign = reply.campaign_lead.campaign
```

Access related lead and campaign info through relationships.

#### 8c. Fetch Full Conversation Thread
```python
thread_messages = db.query(Message).filter(
    Message.gmail_thread_id == reply.gmail_thread_id
).order_by(
    Message.received_at.desc(), 
    Message.sent_at.desc()
).all()
```

Get ALL messages with the same Gmail thread ID (both inbound and outbound).

**Database query:**
```sql
SELECT * FROM message
WHERE gmail_thread_id = 'thread-abc123'
ORDER BY received_at DESC, sent_at DESC
```

#### 8d. Build Thread Data
```python
messages_data = []
for msg in thread_messages:
    if msg.direction == MessageDirection.INBOUND:
        msg_body = clean_message_body(msg.body)  # Remove quoted text
    else:
        msg_body = msg.body
    
    messages_data.append({
        "id": msg.id,
        "direction": msg.direction.value,
        "subject": msg.subject,
        "body": msg_body,
        "received_at": msg.received_at,
        "sent_at": msg.sent_at,
        "classification": msg.classification.value if msg.classification else None,
    })
```

For each message in thread, extract relevant fields.

#### 8e. Get Classification Explanation
```python
explanation = ""
if reply.classification:
    explanation = ClassificationService.get_classification_explanation(reply.classification)
```

Get human-readable explanation of why the reply was classified this way.

#### 8f. Return Full Response
```python
return {
    "id": reply.id,
    "lead": {
        "id": lead.id,
        "email": lead.email,
        "first_name": lead.first_name,
        "last_name": lead.last_name,
        "company": lead.company,
    },
    "campaign": {
        "id": campaign.id,
        "name": campaign.name,
    },
    "subject": reply.subject,
    "body": reply.body,
    "classification": reply.classification,
    "classification_explanation": explanation,
    "received_at": reply.received_at,
    "gmail_thread_id": reply.gmail_thread_id,
    "thread": messages_data
}
```

**Response example:**
```json
{
    "id": 456,
    "lead": {
        "id": 123,
        "email": "john@acme.com",
        "first_name": "John",
        "last_name": "Smith",
        "company": "ACME Corp"
    },
    "campaign": {
        "id": 1,
        "name": "Q1 Outreach"
    },
    "subject": "RE: Check out our service",
    "body": "Thanks for reaching out! Here's the pricing info...",
    "classification": "booking_intent",
    "classification_explanation": "Lead is interested and asked about next steps",
    "received_at": "2025-01-10T14:32:00Z",
    "gmail_thread_id": "thread-abc123",
    "thread": [
        {
            "id": 789,
            "direction": "inbound",
            "subject": "RE: Check out our service",
            "body": "Thanks for reaching out! Here's the pricing info...",
            "received_at": "2025-01-10T14:32:00Z",
            "sent_at": null,
            "classification": "booking_intent"
        },
        {
            "id": 788,
            "direction": "outbound",
            "subject": "Check out our service",
            "body": "Hi John, I thought you'd be interested in...",
            "received_at": null,
            "sent_at": "2025-01-10T10:15:00Z",
            "classification": null
        },
        {
            "id": 787,
            "direction": "inbound",
            "subject": "RE: Check out our service",
            "body": "Can you send me the pricing?",
            "received_at": "2025-01-10T09:45:00Z",
            "sent_at": null,
            "classification": null
        }
    ]
}
```

---

### Step 9: Frontend Updates UI with Thread

**File**: [src/app/inbox/page.tsx](src/app/inbox/page.tsx#L300)

```typescript
// Update right panel with selected reply details
<h2 style={{ fontSize: '20px' }}>
    {selectedReply.subject || '(no subject)'}
</h2>
<div style={{ color: 'var(--text-secondary)' }}>
    With: {selectedReply.lead_email}
</div>

// Render thread messages
{thread.map((msg: any) => (
    <div
        key={msg.id}
        style={{
            alignSelf: msg.direction === 'outbound' ? 'flex-end' : 'flex-start',
        }}
    >
        <div style={{ color: 'var(--text-muted)' }}>
            {msg.direction === 'outbound' ? 'You' : selectedReply.lead_name} 
            • {new Date(msg.sent_at || msg.received_at).toLocaleString()}
        </div>
        <div style={{
            background: msg.direction === 'outbound' ? 'var(--bg-tertiary)' : 'var(--bg-card)',
            padding: '16px',
            borderRadius: '12px',
            border: '1px solid var(--border-color)',
        }}>
            {msg.body}
        </div>
    </div>
))}
```

**UI now shows:**
- Lead name and email
- Subject line
- Full conversation thread with:
  - Outbound messages (our emails) - right-aligned, darker background
  - Inbound messages (lead's replies) - left-aligned, lighter background
  - Timestamps for each message
  - Clean message bodies (no quoted text)

---

## 🗄️ Database Tables Involved

### 1. **Workspace** (Security boundary)
```
├─ user_id: Links to User
└─ id: 1
```

### 2. **Campaign** (Email campaign)
```
├─ workspace_id: 1
├─ name: "Q1 Outreach"
├─ mailbox_id: Sender mailbox
├─ status: "LAUNCHED"
└─ id: 1
```

### 3. **CampaignLead** (Lead + Campaign association)
```
├─ campaign_id: 1
├─ lead_id: 123
├─ status: "ACTIVE" 
├─ created_at: timestamp
└─ id: 456
```

### 4. **Lead** (Lead contact info)
```
├─ workspace_id: 1
├─ email: "john@acme.com"
├─ first_name: "John"
├─ last_name: "Smith"
├─ company: "ACME Corp"
├─ title: "Manager"
└─ id: 123
```

### 5. **Message** (Email message)
```
├─ campaign_lead_id: 456 (associates with conversation)
├─ gmail_thread_id: "thread-abc123"
├─ direction: INBOUND or OUTBOUND
├─ subject: "RE: Check out our service"
├─ body: "Full email content"
├─ classification: BOOKING_INTENT (for inbound only)
├─ received_at: timestamp (inbound only)
├─ sent_at: timestamp (outbound only)
└─ id: 789
```

---

## 🔄 Query Sequence Summary

### Initial List Load (Step 3)
```
SELECT campaign_lead.id 
FROM campaign_lead
JOIN campaign ON campaign_lead.campaign_id = campaign.id
WHERE campaign.workspace_id = 1

For each campaign_lead:
  SELECT * FROM message 
  WHERE campaign_lead_id = ? 
  ORDER BY received_at DESC, sent_at DESC, id DESC 
  LIMIT 1
  
  SELECT * FROM lead WHERE id = ?
  SELECT * FROM campaign WHERE id = ?
```

**Result:** List of latest messages from each conversation, sorted by recency.

### Detail Load (Step 8)
```
SELECT message.* FROM message
JOIN campaign_lead ON message.campaign_lead_id = campaign_lead.id
JOIN campaign ON campaign_lead.campaign_id = campaign.id
JOIN workspace ON campaign.workspace_id = workspace.id
WHERE message.id = 456
  AND workspace.user_id = 1
  AND message.direction = 'INBOUND'

SELECT * FROM lead WHERE id = ?
SELECT * FROM campaign WHERE id = ?

SELECT * FROM message 
WHERE gmail_thread_id = 'thread-abc123' 
ORDER BY received_at DESC, sent_at DESC
```

**Result:** Full conversation thread with all related data.

---

## 🔐 Security Checks

1. **JWT Authentication**
   - Every request requires valid JWT token
   - Extracted via `get_current_user` dependency

2. **Workspace Ownership**
   - Verify `Workspace.user_id == current_user.id`
   - Prevents users from accessing other workspaces' data

3. **Campaign Membership**
   - Reply must belong to campaign in user's workspace
   - Verified through join: `Campaign.workspace_id == workspace_id`

4. **Message Direction Check**
   - `get_reply` only returns INBOUND messages
   - Prevents accessing arbitrary outbound messages

---

## 📊 Performance Characteristics

### Initial Load
- **Time complexity:** O(n) where n = number of campaign_leads
- **Database queries:** 1 + (n × 3) queries
  - 1 query for campaign_lead IDs
  - n queries for latest message per campaign_lead
  - n queries for lead data
  - n queries for campaign data
- **Optimization:** Could use single query with GROUP BY, but current approach more flexible

### Detail Load
- **Time complexity:** O(m) where m = messages in thread
- **Database queries:** 4 + m
  - 1 query for reply message
  - 1 query for lead
  - 1 query for campaign
  - 1 query for full thread (all messages)
  - m iterations to clean/format messages (in Python, not SQL)

### Pagination
- Slice done in Python after fetching all results
- Could be optimized with SQL OFFSET/LIMIT

---

## 🎨 UI State Changes

When user selects a reply:

```
Before:
├─ replies: [reply1, reply2, reply3, ...]
├─ selectedReply: null
├─ thread: []
└─ replyBody: ""

After:
├─ replies: [reply1, reply2, reply3, ...] (unchanged)
├─ selectedReply: {id, lead_email, subject, ...}
├─ thread: [{id, direction, body, timestamp}, ...]
└─ replyBody: "" (reset)
```

---

## 🔄 User Actions After Selection

Once a reply is selected, user can:

### 1. Classify Reply
```typescript
onClick={() => handleClassify(selectedReply.id, 'booking_intent')}
  ↓
POST /api/inbox/replies/{reply_id}/classify
  ↓
Backend updates Message.classification
  ↓
Update replies list & UI
```

### 2. Send Reply
```typescript
onClick={() => handleSendReply()}
  ↓
POST /api/inbox/replies/{reply_id}/send
  ↓
Backend calls Gmail API to send email
  ↓
Saves sent message to database
  ↓
Re-fetch thread to show new message
```

### 3. AI Classify (if unknown)
```typescript
onClick={() => inboxAI.classify(token, selectedReply.id)}
  ↓
POST /api/inbox/replies/{reply_id}/ai/classify
  ↓
Backend calls OpenAI GPT with message context
  ↓
Returns classification with confidence score
  ↓
Update message classification in database
```

---

## 📝 Key Data Transformations

### 1. clean_message_body()
Removes quoted/previous message content from email bodies:
```
Input:
  Thanks for reaching out! Here's the pricing...
  
  On Jan 10 at 10:15, john@acme.com wrote:
  > Check out our service...
  > It's amazing!

Output:
  Thanks for reaching out! Here's the pricing...
```

### 2. Direction Enum to String
```python
# Database: MessageDirection.INBOUND (enum)
# API Response: "inbound" (string)
message.direction.value  # Converts enum to string value
```

### 3. Classification Explanation
```python
# Database: ReplyClassification.BOOKING_INTENT
# API Response: "Lead is interested and asked about next steps"
ClassificationService.get_classification_explanation(classification)
```

---

## 🎯 Summary

**When user selects a lead:**

1. Frontend calls `inbox.getReply(token, reply_id)`
2. Backend verifies workspace ownership via JWT + workspace join
3. Backend fetches the reply message with security checks
4. Backend fetches all messages in the same Gmail thread
5. Backend cleans message bodies, converts enums to strings
6. Backend returns full thread with lead/campaign context
7. Frontend updates UI to show:
   - Selected reply highlighted in list
   - Thread messages in chat-like interface
   - Outbound messages right-aligned, inbound left-aligned
   - Classification and timestamp for each message
   - Reply input box ready to send

**Total database operations:** ~4 queries + message formatting
**Security layers:** JWT auth + workspace verification + direction check
**Performance:** Real-time, no background jobs needed
