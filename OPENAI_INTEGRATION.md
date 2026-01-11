# OpenAI GPT Integration - API Documentation

## Overview

The Email Outreach Platform integrates OpenAI's Responses API with Structured Outputs for:

1. **Campaign Draft Generation** - AI-generated subject lines and email bodies
2. **Email Risk Linting** - Deliverability and compliance checking
3. **Reply Classification** - AI fallback for message classification (when rules-based returns UNKNOWN)

All outputs are **structured JSON** (no free-form text), **deterministic** where needed (temperature 0.0 for classification), and **safety-first** (no per-lead dynamic rewriting at send time).

---

## Rate Limiting

All AI endpoints enforce a **30 calls per hour per user** limit (HTTP 429 if exceeded).

---

## Campaign Draft Generation

### Endpoint

```
POST /api/campaigns/{campaign_id}/ai/draft
```

### Authentication

Requires valid JWT token in `Authorization: Bearer <token>` header.

### Request Body

```json
{
  "tone": "friendly",
  "length": "medium",
  "include_followup": true
}
```

**Fields:**
- `tone` (string): "calm" | "direct" | "friendly"
- `length` (string): "short" | "medium"
- `include_followup` (boolean): Whether to generate follow-up subject/body

### Response (200 OK)

```json
{
  "subject": "Quick question about lead scoring at Acme Corp",
  "body": "Hi {{first_name}},\n\nI've been following Acme's recent expansion into the West Coast. Your team is likely evaluating new ways to prioritize leads.\n\nWe work with {{company}} to reduce time-to-conversion by 35%...",
  "followup_subject": "Following up on lead scoring",
  "followup_body": "Hi {{first_name}},\n\nJust checking in on my last message. Would love to chat briefly.",
  "personalization_vars_used": ["first_name", "company"],
  "risky_phrases_found": []
}
```

**Response Fields:**
- `subject` (string, 1–80 chars): Email subject line
- `body` (string, 20–1200 chars): Email body
- `followup_subject` (string, optional, max 80): Follow-up subject if requested
- `followup_body` (string, optional, max 1200): Follow-up body if requested
- `personalization_vars_used` (array of strings): Variables like `{{first_name}}`, `{{company}}`
- `risky_phrases_found` (array of strings): Any risky phrasing detected (usually empty)

### Error Responses

- **404 Not Found**: Campaign does not exist or user lacks access
- **429 Too Many Requests**: Rate limit exceeded (30/hour)
- **503 Service Unavailable**: OpenAI service error (transient)
- **500 Internal Server Error**: Unexpected error

### Example cURL

```bash
curl -X POST http://localhost:8000/api/campaigns/42/ai/draft \
  -H "Authorization: Bearer <JWT_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "tone": "friendly",
    "length": "medium",
    "include_followup": true
  }'
```

### Notes

- Draft is **NOT automatically saved** to the campaign. User must review and explicitly save.
- Uses workspace's wizard context (what_you_sell, target_industry, target_role, etc.)
- Temperature: 0.3 (slightly creative but consistent)
- Model: gpt-4o-mini (configurable via OPENAI_MODEL_DRAFT)

---

## Email Risk Linting

### Endpoint

```
POST /api/campaigns/{campaign_id}/ai/lint
```

### Authentication

Requires valid JWT token.

### Request Body

```json
{
  "subject": "Quick question about lead scoring at Acme Corp",
  "body": "Hi {{first_name}},\n\nI've been following Acme's recent expansion...",
  "followup_subject": "Following up on lead scoring",
  "followup_body": "Hi {{first_name}},\n\nJust checking in on my last message."
}
```

**Fields:**
- `subject` (string): Email subject line
- `body` (string): Email body (truncated to 3000 chars internally)
- `followup_subject` (string, optional): Follow-up subject
- `followup_body` (string, optional): Follow-up body (truncated to 3000 chars)

### Response (200 OK)

```json
{
  "verdict": "SAFE",
  "risk_score": 15,
  "issues": [
    {
      "category": "TOO_MANY_VARIABLES",
      "severity": "LOW",
      "explanation": "Using more than 3 personalization variables may reduce deliverability.",
      "suggestion": "Consider limiting to {{first_name}} and {{company}} only."
    }
  ]
}
```

**Response Fields:**
- `verdict` (string): "SAFE" or "RISKY"
- `risk_score` (integer): 0–100 (higher = more risky)
- `issues` (array of objects): Detected problems with category, severity, explanation, suggestion

**Issue Categories:**
- `SPAMMY_LANGUAGE`: Spam-trigger words (free, guarantee, act now, etc.)
- `OVERCLAIMS`: Exaggerated claims without evidence
- `CREEPY_PERSONALIZATION`: Inappropriate personal references
- `TOO_LONG`: Email body exceeds recommended length
- `TOO_MANY_LINKS`: More links than safe for cold email
- `TOO_MANY_VARIABLES`: Too many placeholders
- `AGGRESSIVE_CTA`: High-pressure calls-to-action

**Severity Levels:**
- `LOW`: Recommendation for improvement
- `MEDIUM`: Notable risk
- `HIGH`: Significant deliverability or compliance risk

### Error Responses

- **404 Not Found**: Campaign not found or user lacks access
- **429 Too Many Requests**: Rate limit exceeded
- **503 Service Unavailable**: OpenAI service error
- **500 Internal Server Error**: Unexpected error

### Example cURL

```bash
curl -X POST http://localhost:8000/api/campaigns/42/ai/lint \
  -H "Authorization: Bearer <JWT_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "subject": "Quick question about lead scoring",
    "body": "Hi {{first_name}}, ...",
    "followup_subject": "Following up",
    "followup_body": "Just checking in..."
  }'
```

### Notes

- **Deterministic**: Same input always returns same verdict (temperature 0.0)
- **NO rewriting**: Only flags issues; does not rewrite email
- **Suggestions are optional guidance**, not mandates
- Model: gpt-4o-mini (configurable via OPENAI_MODEL_LINT)

---

## Reply Classification (AI Fallback)

### Endpoint

```
POST /api/inbox/replies/{message_id}/ai/classify
```

### Authentication

Requires valid JWT token.

### Request Body

```json
{}
```

(No body; classification is performed on the existing message in the database)

### Response (200 OK)

```json
{
  "classification": "BOOKING_INTENT",
  "confidence": 0.92,
  "reason": "Recipient proposes specific meeting time."
}
```

**Response Fields:**
- `classification` (string): One of UNSUBSCRIBE | NEGATIVE | NEUTRAL | BOOKING_INTENT | POSITIVE_INTEREST | OUT_OF_OFFICE | UNKNOWN
- `confidence` (float): 0.0–1.0 (higher = more confident)
- `reason` (string): Brief explanation of classification

### Error Responses

- **404 Not Found**: Message not found, is not inbound, or user lacks access
- **429 Too Many Requests**: Rate limit exceeded
- **503 Service Unavailable**: OpenAI service error
- **500 Internal Server Error**: Unexpected error

### Example cURL

```bash
curl -X POST http://localhost:8000/api/inbox/replies/123/ai/classify \
  -H "Authorization: Bearer <JWT_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{}'
```

### Notes

- **Fallback only**: Only called when rule-based classification returns UNKNOWN
- **Deterministic**: Temperature 0.0 for consistent results
- **Input truncation**: Body limited to 2000 chars
- **Does not auto-save**: Frontend must explicitly update the message classification
- Model: gpt-4o-mini (configurable via OPENAI_MODEL_CLASSIFY)

---

## Environment Variables

Required in `.env`:

```
OPENAI_API_KEY=sk-proj-...
OPENAI_MODEL_DRAFT=gpt-4o-mini
OPENAI_MODEL_LINT=gpt-4o-mini
OPENAI_MODEL_CLASSIFY=gpt-4o-mini
OPENAI_TIMEOUT_SECONDS=30
OPENAI_MAX_RETRIES=3
```

---

## Logging & Auditing

All AI calls are logged as **Event** records with action:
- `AI_DRAFT_GENERATED`
- `AI_LINT_RUN`
- `AI_REPLY_CLASSIFIED`

**Audit details include:**
- Model used
- Token usage (if available)
- Verdict/classification result
- NOT the full prompt or response (privacy)

Logs do **NOT contain**:
- OpenAI request bodies
- OpenAI response bodies
- API keys
- Sensitive recipient data

---

## Guardrails

1. **No per-lead dynamic rewriting**: GPT never generates a unique email per lead at send time
2. **Structured outputs only**: All responses are strict JSON schemas
3. **Rate limiting**: 30 calls/hour per user
4. **Timeout enforcement**: 30 seconds (configurable)
5. **Retry policy**: Up to 3 retries with exponential backoff on 429/5xx errors
6. **Input truncation**: Bodies capped at 3000/2000 chars to control costs
7. **No background worker GPT calls**: campaign_worker never calls GPT
8. **Auth checks**: All endpoints require JWT and workspace ownership verification

---

## Setup Instructions

1. **Install dependencies:**
   ```bash
   pip install openai tenacity
   ```

2. **Set environment variables:**
   ```bash
   export OPENAI_API_KEY="sk-proj-..."
   export OPENAI_MODEL_DRAFT="gpt-4o-mini"
   export OPENAI_MODEL_LINT="gpt-4o-mini"
   export OPENAI_MODEL_CLASSIFY="gpt-4o-mini"
   ```

3. **Restart backend:**
   ```bash
   docker-compose restart backend
   ```

4. **Test endpoints** (see cURL examples above)

---

## Troubleshooting

**"Missing OPENAI_API_KEY"**
- Ensure `OPENAI_API_KEY` is set in `.env` or environment

**Rate limit exceeded (429)**
- User has made >30 AI calls in the past hour
- In-memory counter resets each hour

**503 Service Unavailable**
- OpenAI API is experiencing issues
- Retry after a few seconds
- Check OpenAI status: https://status.openai.com/

**Timeout (30s)**
- OpenAI took too long to respond
- Automatically retried up to 3 times
- If persistent, check network and OpenAI status

---

## References

- [OpenAI Responses API](https://platform.openai.com/docs/guides/responses-api)
- [OpenAI Structured Outputs](https://platform.openai.com/docs/guides/structured-outputs)
- [Tenacity (Retries)](https://tenacity.readthedocs.io/)
