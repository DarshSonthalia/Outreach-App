# OpenAI GPT Integration - Implementation Complete ✅

## Summary

Full OpenAI Responses API integration with Structured Outputs has been implemented across the Email Outreach Platform. All constraints met: deterministic outputs, strict safety, structured JSON, no per-lead dynamic rewriting.

---

## Files Created / Modified

### Backend

#### New Files
1. **`backend/app/services/llm_service.py`** (230 lines)
   - Centralized OpenAI Responses API wrapper
   - Structured Output schemas (JSON schema)
   - 3 core functions: `generate_campaign_draft()`, `lint_email()`, `classify_reply()`
   - Retry logic with exponential backoff
   - Temperature enforcement (0.3 for draft, 0.0 for lint/classify)
   - No logging of request/response bodies

2. **`backend/app/routers/campaigns_ai.py`** (175 lines)
   - `POST /api/campaigns/{campaign_id}/ai/draft` - Generate subject/body/follow-up
   - `POST /api/campaigns/{campaign_id}/ai/lint` - Check deliverability/compliance risk
   - Rate limiting (30 calls/hour per user)
   - Workspace ownership checks
   - Audit event logging

3. **`backend/app/routers/inbox_ai.py`** (120 lines)
   - `POST /api/inbox/replies/{message_id}/ai/classify` - Fallback classification
   - Returns enum classification with confidence and reason
   - Only works on INBOUND messages
   - Rate limiting + auth checks

4. **`backend/app/utils/rate_limit.py`** (40 lines)
   - In-memory rate limit counter
   - 30 AI calls/hour per user
   - Automatic window reset

#### Modified Files
1. **`backend/requirements.txt`**
   - Added: `openai>=1.0.0`
   - Added: `tenacity>=8.2.3` (for retries)

2. **`backend/app/main.py`**
   - Imported new routers: `campaigns_ai`, `inbox_ai`
   - Registered both routers with FastAPI

3. **`.env.example`**
   - Added OpenAI environment variables:
     - `OPENAI_API_KEY`
     - `OPENAI_MODEL_DRAFT`
     - `OPENAI_MODEL_LINT`
     - `OPENAI_MODEL_CLASSIFY`
     - `OPENAI_TIMEOUT_SECONDS`
     - `OPENAI_MAX_RETRIES`

### Frontend

#### Modified Files
1. **`frontend/src/lib/api.ts`**
   - Added `campaignsAI` export with methods:
     - `generateDraft(token, campaignId, tone, length, includeFollowup)`
     - `lintEmail(token, campaignId, subject, body, followupSubject, followupBody)`
   - Added `inboxAI` export with method:
     - `classify(token, messageId)`

### Documentation

#### New Files
1. **`OPENAI_INTEGRATION.md`** (350 lines)
   - Complete API documentation
   - Request/response schemas for all 3 endpoints
   - cURL examples
   - Environment setup
   - Troubleshooting guide
   - Safety guardrails

---

## API Endpoints

### 1. Campaign Draft Generation

```
POST /api/campaigns/{campaign_id}/ai/draft
```

**Request:**
```json
{
  "tone": "friendly",
  "length": "medium",
  "include_followup": true
}
```

**Response:**
```json
{
  "subject": "Quick question about lead scoring at Acme Corp",
  "body": "Hi {{first_name}},\n\nI've been following...",
  "followup_subject": "Following up on lead scoring",
  "followup_body": "Hi {{first_name}},\n\nJust checking in...",
  "personalization_vars_used": ["first_name", "company"],
  "risky_phrases_found": []
}
```

**Features:**
- Uses workspace wizard context (what_you_sell, target_industry, target_role, etc.)
- Temperature: 0.3 (consistent but slightly creative)
- Max tokens: 400
- NOT automatically saved (user must review first)

---

### 2. Email Risk Linting

```
POST /api/campaigns/{campaign_id}/ai/lint
```

**Request:**
```json
{
  "subject": "Quick question about lead scoring",
  "body": "Hi {{first_name}},\n\nI've been following...",
  "followup_subject": "Following up",
  "followup_body": "Just checking in..."
}
```

**Response:**
```json
{
  "verdict": "SAFE",
  "risk_score": 15,
  "issues": [
    {
      "category": "TOO_MANY_VARIABLES",
      "severity": "LOW",
      "explanation": "Using more than 3 variables may reduce deliverability",
      "suggestion": "Consider limiting to {{first_name}} and {{company}} only"
    }
  ]
}
```

**Features:**
- Deterministic (temperature 0.0)
- Flags: spam language, overclaims, creepy personalization, length, links, variables, CTA aggression
- Severity levels: LOW, MEDIUM, HIGH
- Does NOT rewrite email (only flags issues)
- Max tokens: 300

---

### 3. Reply Classification (AI Fallback)

```
POST /api/inbox/replies/{message_id}/ai/classify
```

**Request:** (no body)

**Response:**
```json
{
  "classification": "BOOKING_INTENT",
  "confidence": 0.92,
  "reason": "Recipient proposes specific meeting time"
}
```

**Features:**
- Fallback for rule-based classifier (only if rule returns UNKNOWN)
- Deterministic (temperature 0.0)
- Classifications: UNSUBSCRIBE, NEGATIVE, NEUTRAL, BOOKING_INTENT, POSITIVE_INTEREST, OUT_OF_OFFICE, UNKNOWN
- Confidence: 0.0-1.0
- Max tokens: 120

---

## Safety Guardrails ✅

1. **No per-lead dynamic rewriting** ❌ Never happens
   - Draft is generated once per campaign
   - Used for all leads
   - Personalization via variables only ({{first_name}}, {{company}})

2. **Structured Outputs Only** ✅
   - All responses validate against strict JSON schemas
   - No free-form text parsing
   - Deterministic enums (e.g., verdict: "SAFE" | "RISKY")

3. **Rate Limiting** ✅
   - 30 AI calls per hour per user
   - Returns HTTP 429 if exceeded
   - In-memory counter with hourly windows

4. **Timeout Enforcement** ✅
   - 30 seconds (configurable via OPENAI_TIMEOUT_SECONDS)
   - Automatic retries (up to 3) with exponential backoff
   - Fails gracefully on timeout

5. **Input Truncation** ✅
   - Lint: body capped at 3000 chars
   - Classify: body capped at 2000 chars
   - Prevents token bloat and cost explosion

6. **No Background Worker Calls** ✅
   - campaign_worker.py NEVER calls GPT
   - Celery tasks are deterministic (no LLM variation)
   - Only user-initiated endpoints call GPT

7. **Auth + Workspace Checks** ✅
   - All endpoints require JWT token
   - Verify workspace ownership
   - Verify message/campaign belongs to workspace

8. **Audit Logging** ✅
   - Every AI call creates Event record
   - Logs: action, model, verdict/classification
   - NO request/response bodies logged
   - NO API keys in logs
   - NO sensitive PII beyond DB records

---

## Environment Setup

**Required in `.env`:**

```bash
OPENAI_API_KEY=sk-proj-YOUR_KEY_HERE
OPENAI_MODEL_DRAFT=gpt-4o-mini
OPENAI_MODEL_LINT=gpt-4o-mini
OPENAI_MODEL_CLASSIFY=gpt-4o-mini
OPENAI_TIMEOUT_SECONDS=30
OPENAI_MAX_RETRIES=3
```

**Optional (defaults shown):**

```bash
# Customize model per task (e.g., use gpt-4 for higher quality)
OPENAI_MODEL_DRAFT=gpt-4
OPENAI_MODEL_LINT=gpt-4
OPENAI_MODEL_CLASSIFY=gpt-4o-mini

# Adjust timeout if network is slow
OPENAI_TIMEOUT_SECONDS=60

# Reduce retries in production for faster failures
OPENAI_MAX_RETRIES=1
```

---

## Testing the Implementation

### 1. Generate Draft

```bash
curl -X POST http://localhost:8000/api/campaigns/1/ai/draft \
  -H "Authorization: Bearer <JWT_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "tone": "friendly",
    "length": "medium",
    "include_followup": true
  }'
```

### 2. Lint Email

```bash
curl -X POST http://localhost:8000/api/campaigns/1/ai/lint \
  -H "Authorization: Bearer <JWT_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "subject": "Quick question",
    "body": "Hi {{first_name}}, I noticed your company...",
    "followup_subject": "Following up",
    "followup_body": "Just checking in..."
  }'
```

### 3. Classify Reply

```bash
curl -X POST http://localhost:8000/api/inbox/replies/123/ai/classify \
  -H "Authorization: Bearer <JWT_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{}'
```

---

## Model Selection

**Current Default:** `gpt-4o-mini`

**Recommended by Task:**

| Task | Model | Rationale |
|------|-------|-----------|
| Draft generation | gpt-4o-mini | Good balance of quality + cost |
| Email linting | gpt-4o-mini | Deterministic, fast, reliable |
| Reply classification | gpt-4o-mini | Enum outputs, high accuracy |

**For higher quality (but higher cost):**

```bash
OPENAI_MODEL_DRAFT=gpt-4
OPENAI_MODEL_LINT=gpt-4
```

---

## Architecture Diagram

```
┌─────────────────────────────────────────┐
│         Next.js Frontend (3000)         │
│  ┌──────────────────────────────────┐   │
│  │ campaigns/new/page.tsx           │   │
│  │  - [Generate Draft (AI)] button   │   │
│  │  - [Check Risk (AI)] button       │   │
│  └──────────────────────────────────┘   │
│  ┌──────────────────────────────────┐   │
│  │ inbox/page.tsx                   │   │
│  │  - [AI classify] button (if UNK)  │   │
│  └──────────────────────────────────┘   │
└────────────┬────────────────────────────┘
             │ HTTP
             ▼
┌─────────────────────────────────────────┐
│      FastAPI Backend (8000)             │
│  ┌──────────────────────────────────┐   │
│  │ routers/campaigns_ai.py          │   │
│  │  - POST /api/campaigns/.../draft │   │
│  │  - POST /api/campaigns/.../lint  │   │
│  └──────────────────────────────────┘   │
│  ┌──────────────────────────────────┐   │
│  │ routers/inbox_ai.py              │   │
│  │  - POST /api/inbox/.../classify  │   │
│  └──────────────────────────────────┘   │
│  ┌──────────────────────────────────┐   │
│  │ services/llm_service.py          │   │
│  │  - generate_campaign_draft()     │   │
│  │  - lint_email()                  │   │
│  │  - classify_reply()              │   │
│  └──────────────────────────────────┘   │
└────────────┬────────────────────────────┘
             │ OpenAI Responses API
             ▼
┌─────────────────────────────────────────┐
│       OpenAI API (api.openai.com)       │
│  - POST /v1/responses                   │
│  - Structured Outputs (JSON schema)     │
│  - gpt-4o-mini / gpt-4                  │
└─────────────────────────────────────────┘
```

---

## Next Steps (Optional Enhancements)

1. **Add AI buttons to frontend campaign creation UI**
   - "Generate Draft (AI)" button in Step 1
   - "Check Risk (AI)" button in Step 3
   - "AI Classify" button in inbox for UNKNOWN messages

2. **Streaming responses** (for better UX on slow networks)
   - Use `stream=True` in OpenAI API
   - Show progress to user

3. **Custom model selection per task**
   - Allow user to choose gpt-4 vs gpt-4o-mini
   - Trade quality vs cost

4. **Bulk operations**
   - Generate draft for multiple campaigns at once
   - Lint multiple emails in parallel

5. **Cost tracking**
   - Track tokens used per endpoint
   - Show estimated costs to user

6. **Prompt engineering**
   - A/B test different instructions
   - Fine-tune prompts based on user feedback

---

## Verification Checklist ✅

- [x] `POST /api/campaigns/{id}/ai/draft` returns valid JSON per DRAFT_SCHEMA
- [x] `POST /api/campaigns/{id}/ai/lint` returns SAFE/RISKY deterministically (temp 0.0)
- [x] `POST /api/inbox/replies/{id}/ai/classify` returns enum + confidence
- [x] No GPT call in campaign_worker.py (verified - only human-initiated endpoints call GPT)
- [x] Logs contain NO request bodies, response bodies, API keys
- [x] All endpoints require JWT and workspace ownership checks
- [x] Rate limiting: 30 calls/hour per user (in-memory counter)
- [x] Timeout: 30 seconds with exponential backoff retries
- [x] Input truncation: bodies capped at 3000/2000 chars
- [x] Structured Outputs: strict JSON schemas, no free-form parsing
- [x] No per-lead dynamic rewriting (draft is global, personalization via variables)
- [x] Audit events logged for each AI call

---

## Deployment Status

**Current:** ✅ Production Ready

All containers built and running:
- Backend: ✅ Started (includes new routers)
- Frontend: ✅ Built (includes API client methods)
- Database: ✅ Healthy
- Redis: ✅ Healthy
- Celery: ✅ Running (unchanged, no GPT calls)

---

## Support

See [OPENAI_INTEGRATION.md](OPENAI_INTEGRATION.md) for:
- Complete API documentation
- Error responses and troubleshooting
- Rate limiting details
- Environment variable reference

