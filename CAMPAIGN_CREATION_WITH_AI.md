# Campaign Creation Flow with OpenAI Integration

This document shows exactly how the OpenAI API integrates into the campaign creation process when selecting leads to start a new campaign.

---

## 📋 Campaign Creation Steps

```
Step 1: Setup             Step 2: Select Leads      Step 3: Email Copy        Step 4: Launch
├─ Campaign name          ├─ Import CSV/Source      ├─ Write subject line     ├─ Safety review
├─ Select mailbox         ├─ Select leads           ├─ Write body             ├─ Preview all
├─ Continue               ├─ Continue               ├─ Set follow-up          ├─ Launch
                                                     ├─ [AI GENERATE DRAFT] ← AI HERE
                                                     ├─ [AI CHECK RISK] ← AI HERE
                                                     └─ Continue
```

---

## 🤖 OpenAI Integration Points

The OpenAI API is used in **Step 3: Email Copy** to help draft emails and check compliance.

### Point 1: Generate Draft (Optional AI Enhancement)

**When:** User clicks "✨ Generate Draft (AI)" button
**Why:** User doesn't know what to write, wants AI assistance

**Flow:**
```
User clicks "Generate Draft"
    ↓
Frontend: handleGenerateDraft()
    ↓
API Call: POST /api/campaigns/{campaignId}/ai/draft
    ↓
Backend: llm_service.generate_campaign_draft()
    ↓
OpenAI API: gpt-4.1 (draft model)
    ↓
Returns: {subject, body, followup_subject, followup_body, risky_phrases_found}
    ↓
Auto-fills form: setSubject(), setBody()
    ↓
Shows warnings if risky phrases detected
```

---

### Point 2: Check Email Risk (Optional Safety Check)

**When:** User clicks "🔍 Check Risk (AI)" button  
**Why:** User wants to verify email won't trigger spam filters

**Flow:**
```
User clicks "Check Risk"
    ↓
Frontend: handleLintEmail()
    ↓
API Call: POST /api/campaigns/{campaignId}/ai/lint
    ↓
Backend: llm_service.lint_email()
    ↓
OpenAI API: gpt-5-mini (lint model)
    ↓
Returns: {verdict: SAFE|RISKY, risk_score: 0-100, issues: [...]}
    ↓
Shows alert: "✅ SAFE (risk score: 15/100)" or "⚠️ RISKY (score: 75/100)"
    ↓
Lists specific issues (spam trigger words, etc.)
```

---

## 🔄 Full Flow Diagram

```
CAMPAIGN CREATION FLOW WITH OPENAI

Step 1: Setup Campaign
┌─────────────────────┐
│ Campaign Name       │  → "Q1 Outreach"
│ Select Mailbox      │  → "john@company.com"
│ [Continue]          │
└─────────────────────┘
        ↓

Step 2: Select Leads
┌─────────────────────┐
│ Leads List          │
│ ☑ john@acme.com    │
│ ☑ jane@stripe.com  │
│ ☑ bob@google.com   │
│ [Continue]          │
└─────────────────────┘
        ↓

Step 3: Email Copy ←─ OPENAI INTEGRATION HAPPENS HERE
┌────────────────────────────────────────────────┐
│ Subject: Quick question, {{first_name}}         │
│ Body: Hi {{first_name}}, I noticed...          │
│                                                │
│ [✨ Generate Draft (AI)] ─┐                   │
│                          │  Optional: Let OpenAI
│ [🔍 Check Risk (AI)] ←───┤  write initial draft
│                          │  and check compliance
│ Enable follow-up: ☑                           │
│ Days between: 3                                │
│                                                │
│ [Back] [Preview & Launch]                     │
└────────────────────────────────────────────────┘
        ↓

Step 4: Launch
┌──────────────────────────────────────┐
│ Safety Review                        │
│ ✓ Domain verified                   │
│ ✓ Mailbox active                    │
│ ✓ Email passes safety checks        │
│                                     │
│ [Back] [🚀 Launch Campaign]         │
└──────────────────────────────────────┘
```

---

## 💻 Frontend Implementation

### Step 3: Email Copy Page

**File:** [src/app/campaigns/new/page.tsx](src/app/campaigns/new/page.tsx#L462)

Current UI (without AI buttons):
```tsx
{step === 3 && (
    <div className="card">
        <h2>Email Content</h2>
        
        <input
            type="text"
            placeholder="Quick question, {{first_name}}"
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
        />
        
        <textarea
            placeholder="Hi {{first_name}}, I noticed {{company}} is..."
            value={body}
            onChange={(e) => setBody(e.target.value)}
            rows={8}
        />
        
        <button onClick={handleSetEmails}>Preview & Launch</button>
    </div>
)}
```

---

## 🚀 How to Add AI Buttons (Optional Implementation)

To activate AI features, add these handlers and UI:

### Add State Variables
```typescript
const [draftLoading, setDraftLoading] = useState(false);
const [lintLoading, setLintLoading] = useState(false);
const [lintResult, setLintResult] = useState<any>(null);
```

### Add Generate Draft Handler
```typescript
const handleGenerateDraft = async () => {
    if (!token || !campaignId) return;
    setDraftLoading(true);
    try {
        const draft = await campaignsAI.generateDraft(
            token,
            campaignId,
            'friendly',      // tone
            'medium',        // length
            true             // include_followup
        );
        
        // Auto-fill form with generated content
        setSubject(draft.subject);
        setBody(draft.body);
        
        // Warn user if risky phrases found
        if (draft.risky_phrases_found?.length > 0) {
            alert(`Warning: Found risky phrases:\n${draft.risky_phrases_found.join(', ')}`);
        }
    } catch (err: any) {
        alert(`Failed to generate draft: ${err.message}`);
    }
    setDraftLoading(false);
};
```

### Add Email Lint Handler
```typescript
const handleLintEmail = async () => {
    if (!token || !campaignId || !subject || !body) return;
    setLintLoading(true);
    try {
        const result = await campaignsAI.lintEmail(
            token,
            campaignId,
            subject,
            body
        );
        setLintResult(result);
        
        if (result.verdict === 'RISKY') {
            const issues = result.issues
                .map(i => `${i.category}: ${i.explanation}`)
                .join('\n');
            alert(`⚠️ Email is RISKY (score: ${result.risk_score}/100)\n\n${issues}`);
        } else {
            alert(`✅ Email is SAFE (risk score: ${result.risk_score}/100)`);
        }
    } catch (err: any) {
        alert(`Failed to check email: ${err.message}`);
    }
    setLintLoading(false);
};
```

### Add UI Buttons to Step 3
```tsx
<div style={{ marginBottom: '20px' }}>
    <label>Subject Line</label>
    <input
        type="text"
        className="input"
        value={subject}
        onChange={(e) => setSubject(e.target.value)}
        placeholder="Quick question, {{first_name}}"
    />
    <button
        onClick={handleGenerateDraft}
        disabled={draftLoading || !campaignId}
        className="btn btn-outline btn-sm"
        style={{ marginTop: '8px' }}
    >
        {draftLoading ? '⏳ Generating...' : '✨ Generate Draft (AI)'}
    </button>
</div>

<div style={{ marginBottom: '20px' }}>
    <label>Email Body</label>
    <textarea
        className="input"
        value={body}
        onChange={(e) => setBody(e.target.value)}
        placeholder="Hi {{first_name}}, I noticed {{company}} is..."
        rows={8}
    />
</div>

{lintResult && (
    <div className={`alert ${lintResult.verdict === 'SAFE' ? 'alert-success' : 'alert-warning'}`}>
        <span>
            {lintResult.verdict === 'SAFE' ? '✅ SAFE' : '⚠️ RISKY'} 
            (Risk Score: {lintResult.risk_score}/100)
        </span>
        {lintResult.issues.length > 0 && (
            <ul style={{ marginTop: '8px' }}>
                {lintResult.issues.map((issue: any, idx: number) => (
                    <li key={idx}>
                        <strong>{issue.category}</strong> ({issue.severity}):<br/>
                        {issue.explanation}
                        {issue.suggestion && <br/>}
                        {issue.suggestion && <small>💡 {issue.suggestion}</small>}
                    </li>
                ))}
            </ul>
        )}
    </div>
)}

<button
    onClick={handleLintEmail}
    disabled={lintLoading || !subject || !body}
    className="btn btn-outline btn-sm"
    style={{ marginBottom: '20px' }}
>
    {lintLoading ? '⏳ Checking...' : '🔍 Check Risk (AI)'}
</button>
```

---

## 🔗 API Endpoints

### 1. Generate Draft

**Request:**
```http
POST /api/campaigns/123/ai/draft
Authorization: Bearer <JWT_TOKEN>
Content-Type: application/json

{
    "tone": "friendly",
    "length": "medium",
    "include_followup": true
}
```

**Response:**
```json
{
    "subject": "Quick question about {{company}}",
    "body": "Hi {{first_name}},\n\nI noticed {{company}} is in the {{industry}} space...",
    "followup_subject": "Quick follow-up",
    "followup_body": "Hi {{first_name}},\n\nJust checking in...",
    "personalization_vars_used": ["first_name", "company", "industry"],
    "risky_phrases_found": []
}
```

---

### 2. Lint Email

**Request:**
```http
POST /api/campaigns/123/ai/lint
Authorization: Bearer <JWT_TOKEN>
Content-Type: application/json

{
    "subject": "Quick question about {{company}}",
    "body": "Hi {{first_name}}, I noticed {{company}} is...",
    "followup_subject": "Quick follow-up",
    "followup_body": "Hi {{first_name}}, Just checking in..."
}
```

**Response:**
```json
{
    "verdict": "SAFE",
    "risk_score": 15,
    "issues": [
        {
            "category": "PERSONALIZATION",
            "severity": "INFO",
            "explanation": "Uses 2 personalization variables",
            "suggestion": "Consider adding more variables for better engagement"
        }
    ]
}
```

**Response if RISKY:**
```json
{
    "verdict": "RISKY",
    "risk_score": 72,
    "issues": [
        {
            "category": "SPAM_TRIGGER",
            "severity": "HIGH",
            "explanation": "Contains word 'FREE' which triggers spam filters",
            "suggestion": "Replace 'FREE' with 'complimentary' or 'at no cost'"
        },
        {
            "category": "PERSONALIZATION",
            "severity": "MEDIUM",
            "explanation": "No personalization variables - treats all leads the same",
            "suggestion": "Add {{first_name}}, {{company}}, {{title}} for better engagement"
        }
    ]
}
```

---

## 📊 Backend Processing

### llm_service.generate_campaign_draft()

**File:** [backend/app/services/llm_service.py](backend/app/services/llm_service.py)

```python
@staticmethod
async def generate_campaign_draft(
    workspace_wizard: dict,  # what_you_sell, target_industry, target_role, etc.
    tone: str,              # "friendly", "professional", "aggressive"
    length: str,            # "short", "medium", "long"
    include_followup: bool
) -> dict:
    """
    Generate email draft using OpenAI.
    Uses campaign context to personalize the draft.
    """
    
    prompt = f"""
    You are a sales email expert. Generate a professional outreach email.
    
    Context:
    - What we sell: {workspace_wizard['what_you_sell']}
    - Target industry: {workspace_wizard['target_industry']}
    - Target role: {workspace_wizard['target_role']}
    - Offer type: {workspace_wizard['offer_type']}
    
    Requirements:
    - Tone: {tone}
    - Length: {length}
    - Use personalization variables: {{{{first_name}}}}, {{{{company}}}}, {{{{title}}}}
    - Avoid spam trigger words
    - Include call-to-action
    {f'- Include follow-up email' if include_followup else ''}
    
    Return JSON with: subject, body, followup_subject, followup_body, personalization_vars_used, risky_phrases_found
    """
    
    response = await LLMService._call_responses_api(
        model=OPENAI_MODEL_DRAFT,  # gpt-4.1
        prompt=prompt,
        schema=DRAFT_SCHEMA,
        temperature=0.3  # Creative but consistent
    )
    
    return response
```

**Key points:**
- Uses workspace wizard context (what_you_sell, target_industry, etc.)
- Temperature: 0.3 (some creativity, but deterministic)
- Model: gpt-4.1 (best quality for writing)
- Max tokens: 400
- Structured output enforces JSON schema

---

### llm_service.lint_email()

```python
@staticmethod
async def lint_email(
    subject: str,
    body: str,
    followup_subject: str = None,
    followup_body: str = None
) -> dict:
    """
    Check email for compliance and deliverability issues.
    """
    
    prompt = f"""
    Analyze this email for compliance and deliverability issues.
    
    Subject: {subject[:3000]}
    Body: {body[:3000]}
    
    Check for:
    1. Spam trigger words (FREE, URGENT, ACT NOW, etc.)
    2. Personalization quality
    3. CTA clarity
    4. Length appropriateness
    5. Compliance (GDPR, CAN-SPAM)
    
    Return JSON with: verdict (SAFE|RISKY), risk_score (0-100), issues array
    """
    
    response = await LLMService._call_responses_api(
        model=OPENAI_MODEL_LINT,  # gpt-5-mini
        prompt=prompt,
        schema=LINT_SCHEMA,
        temperature=0.0  # Deterministic - same input = same output
    )
    
    return response
```

**Key points:**
- Temperature: 0.0 (completely deterministic)
- Model: gpt-5-mini (fast, cheap, deterministic)
- Max tokens: 300
- No token limit on input (but capped at 3000 chars to avoid bloat)

---

## 🔀 Campaign Creation Data Flow

```
User selects leads → Campaign created with status "DRAFT"
        ↓
User enters email copy (manually or via AI)
        ↓
User clicks "Preview & Launch"
        ↓
Backend calls campaigns.setEmails()
        ↓
Database saves: {subject, body, followup_enabled, followup_delay_days}
        ↓
Backend generates preview (1 lead personalized example)
        ↓
User sees: "Ready to Launch"
        ↓
User clicks "🚀 Launch Campaign"
        ↓
Backend validates:
  - Domain configured
  - Mailbox active
  - Email has subject + body
        ↓
Backend starts campaign_worker (Celery)
        ↓
Worker fetches all leads for this campaign
        ↓
For each lead:
  - Render email with personalization variables
  - Build Gmail draft via Gmail API
  - Queue for sending (or send immediately)
        ↓
Campaign status = "LAUNCHED"
```

---

## 🎯 Key Differences: AI vs Manual

| Aspect | Manual | AI-Generated |
|--------|--------|-------------|
| **Time** | 5-10 min | 2-5 sec |
| **Quality** | Depends on user | Consistent, researched |
| **Personalization** | User must remember variables | AI suggests variables |
| **Compliance** | User must check | AI flags issues |
| **Cost** | Free | $0.001-0.01 per generation |
| **Rate Limit** | None | 30/hour per user |
| **Auto-save** | Manual | No - must review first |

---

## 🔒 Security & Safety

### Rate Limiting
```python
# 30 calls/hour per user
RATE_LIMIT_CALLS = 30
RATE_LIMIT_WINDOW_SECONDS = 3600

# If exceeded: HTTP 429 Too Many Requests
```

### Input Validation
```python
# Subject + body truncated to prevent token bloat
subject = subject[:500]
body = body[:3000]

# Only uses workspace wizard context (no lead data in prompt)
# No PII sent to OpenAI
```

### Audit Logging
```python
# Every AI call logged
AuditEvent(
    action="AI_DRAFT_GENERATED",
    user_id=user.id,
    workspace_id=workspace_id,
    campaign_id=campaign_id,
    metadata={"tone": tone, "length": length}
)
```

---

## 📈 Example Workflow

### Scenario: User wants to write a campaign to CTOs in fintech

**Step 1: Create Campaign**
```
Name: "Fintech CTO Outreach Q1"
Mailbox: "john@company.com"
Leads: [john@stripe.com, jane@affirm.com, bob@checkout.com]
```

**Step 2: Click "Generate Draft"**
```
OpenAI generates:

Subject: "Quick question about {{company}}'s data infrastructure"

Body: "Hi {{first_name}},

I've been following {{company}}'s innovation in {{industry}}.
With the rise of real-time payment systems, I imagine you're dealing
with scaling challenges around data consistency and latency.

We built a solution that helps fintech companies like {{company}}
reduce payment processing latency by 40%. Would be worth 15 minutes?

Best,
John"

Risky phrases: []
```

**Step 3: Click "Check Risk"**
```
OpenAI responds:

Verdict: SAFE
Risk score: 22/100

Issues:
- INFO: Uses 3 personalization variables (good)
- INFO: Mentions specific metric (40% improvement) - adds credibility
```

**Step 4: Review & Adjust**
```
User is happy with the draft, makes 1 small edit:
"with scaling challenges" → "with scaling challenges around payments"
```

**Step 5: Launch**
```
3 emails sent to:
- john@stripe.com → "Quick question about Stripe's data infrastructure"
- jane@affirm.com → "Quick question about Affirm's data infrastructure"  
- bob@checkout.com → "Quick question about Checkout's data infrastructure"

(Personalization variables filled in for each lead)
```

---

## 🚨 Error Handling

### OpenAI API Down
```
HTTP 503 Service Unavailable
Message: "OpenAI service temporarily unavailable. Please try again."
```

### Rate Limit Exceeded
```
HTTP 429 Too Many Requests
Message: "You've used all 30 AI calls this hour. Try again in 1 hour."
```

### Invalid Campaign
```
HTTP 404 Not Found
Message: "Campaign not found or does not belong to your workspace"
```

### Missing OPENAI_API_KEY
```
HTTP 503 Service Unavailable
Message: "AI features not available. Contact support."
```

---

## 📝 Summary

**OpenAI integration in campaign creation:**

1. **Optional feature** - Users can draft emails manually OR use AI
2. **Two endpoints:**
   - Generate Draft: Writes email based on campaign context
   - Lint Email: Checks for spam/compliance issues
3. **Rate limited:** 30 calls/hour per user
4. **Not auto-saved:** User must review generated content
5. **Personalization-aware:** Works with {{variables}}
6. **Safe:** No PII sent to OpenAI, all requests logged
7. **Cost:** ~$0.001-0.01 per call (very cheap)

The AI is a **helper**, not a replacement. Users always have final control over email content before launching.
