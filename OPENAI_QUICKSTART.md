# OpenAI Integration - Quick Start Guide

## Setup

### 1. Get OpenAI API Key

1. Go to https://platform.openai.com/account/api-keys
2. Create a new API key
3. Copy it (looks like: `sk-proj-...`)

### 2. Add to Environment

Edit your `.env` file (or set environment variables):

```bash
OPENAI_API_KEY=sk-proj-YOUR_KEY_HERE
OPENAI_MODEL_DRAFT=gpt-4o-mini
OPENAI_MODEL_LINT=gpt-4o-mini
OPENAI_MODEL_CLASSIFY=gpt-4o-mini
OPENAI_TIMEOUT_SECONDS=30
OPENAI_MAX_RETRIES=3
```

### 3. Restart Backend

```bash
docker-compose restart backend
```

Verify it started:
```bash
docker logs outreach_backend | grep "Application startup complete"
```

---

## Testing the API

### Prerequisites

1. Get a valid JWT token:
   ```bash
   # Register user
   curl -X POST http://localhost:8000/api/auth/register \
     -H "Content-Type: application/json" \
     -d '{"email":"test@example.com","password":"password123"}'
   
   # Login
   curl -X POST http://localhost:8000/api/auth/login \
     -H "Content-Type: application/json" \
     -d '{"email":"test@example.com","password":"password123"}'
   
   # Copy the "access_token" from response
   ```

2. Create a workspace and campaign (or use existing IDs)

### Test 1: Generate Draft

```bash
JWT="YOUR_TOKEN_HERE"
CAMPAIGN_ID="1"  # Replace with real campaign ID

curl -X POST "http://localhost:8000/api/campaigns/$CAMPAIGN_ID/ai/draft" \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "tone": "friendly",
    "length": "medium",
    "include_followup": true
  }'
```

**Expected Response:**
```json
{
  "subject": "Quick question about [topic]",
  "body": "Hi {{first_name}},\n\n[personalized message]...",
  "followup_subject": "Following up",
  "followup_body": "Hi {{first_name}},\n\n[follow-up message]...",
  "personalization_vars_used": ["first_name", "company"],
  "risky_phrases_found": []
}
```

### Test 2: Lint Email

```bash
JWT="YOUR_TOKEN_HERE"
CAMPAIGN_ID="1"

curl -X POST "http://localhost:8000/api/campaigns/$CAMPAIGN_ID/ai/lint" \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "subject": "Quick question about lead scoring",
    "body": "Hi {{first_name}},\n\nI noticed your company recently...",
    "followup_subject": "Following up",
    "followup_body": "Just checking in."
  }'
```

**Expected Response (SAFE):**
```json
{
  "verdict": "SAFE",
  "risk_score": 15,
  "issues": []
}
```

**Expected Response (RISKY):**
```json
{
  "verdict": "RISKY",
  "risk_score": 65,
  "issues": [
    {
      "category": "SPAMMY_LANGUAGE",
      "severity": "HIGH",
      "explanation": "Contains spam-trigger word 'limited time'",
      "suggestion": "Remove 'limited time' and replace with specific deadline"
    }
  ]
}
```

### Test 3: Classify Reply

First, get a message ID from the inbox:

```bash
JWT="YOUR_TOKEN_HERE"
WORKSPACE_ID="1"

# Get replies
curl -X GET "http://localhost:8000/api/inbox/replies?workspace_id=$WORKSPACE_ID" \
  -H "Authorization: Bearer $JWT" | jq '.[] | select(.classification == "unknown") | .id' | head -1
```

Then classify one (use a message ID where classification == "unknown"):

```bash
JWT="YOUR_TOKEN_HERE"
MESSAGE_ID="123"  # Replace with real message ID

curl -X POST "http://localhost:8000/api/inbox/replies/$MESSAGE_ID/ai/classify" \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{}'
```

**Expected Response:**
```json
{
  "classification": "BOOKING_INTENT",
  "confidence": 0.92,
  "reason": "Recipient proposes specific meeting time"
}
```

---

## Rate Limiting

Each user gets **30 AI calls per hour**. After that:

```bash
curl -X POST "http://localhost:8000/api/campaigns/1/ai/draft" ...
```

**Response (429):**
```json
{
  "detail": "AI rate limit exceeded (30 calls per hour)"
}
```

**To reset:** Wait 1 hour or test with a different user account.

---

## Common Errors

### "OPENAI_API_KEY environment variable not configured"

**Fix:**
1. Set `OPENAI_API_KEY` in your `.env` file
2. Restart backend: `docker-compose restart backend`
3. Verify: `docker logs outreach_backend | grep "OpenAI"`

### "Campaign not found"

**Fix:**
- Use a real campaign ID
- Verify you own the campaign (check workspace)

### "AI service temporarily unavailable (503)"

**Possible causes:**
- OpenAI API is down (check https://status.openai.com/)
- Network timeout (increase `OPENAI_TIMEOUT_SECONDS`)
- Invalid API key (verify in https://platform.openai.com/)

### "Rate limit exceeded (429)"

**Fix:**
- Wait 1 hour for counter to reset
- Or use a different user account

### Timeout after 30 seconds

**Fix:**
- Increase `OPENAI_TIMEOUT_SECONDS` in `.env`
- Retry the request
- Check OpenAI status

---

## Monitoring

### Check logs for AI calls

```bash
# Filter for AI events
docker logs outreach_backend | grep "AI_DRAFT\|AI_LINT\|AI_REPLY"

# Follow logs in real-time
docker logs -f outreach_backend | grep "OpenAI"
```

### Check audit events

Query the database:

```sql
-- Find all AI-related events
SELECT * FROM events
WHERE action LIKE 'AI_%'
ORDER BY created_at DESC
LIMIT 10;

-- Count AI calls by user
SELECT user_id, COUNT(*) as count
FROM events
WHERE action LIKE 'AI_%'
GROUP BY user_id;
```

---

## Performance Tuning

### For faster responses

Use `gpt-4o-mini` (default, fastest, good quality):

```bash
OPENAI_MODEL_DRAFT=gpt-4o-mini
OPENAI_MODEL_LINT=gpt-4o-mini
OPENAI_MODEL_CLASSIFY=gpt-4o-mini
```

### For higher quality

Use `gpt-4` (slower, expensive, best quality):

```bash
OPENAI_MODEL_DRAFT=gpt-4
OPENAI_MODEL_LINT=gpt-4
OPENAI_MODEL_CLASSIFY=gpt-4o-mini  # Keep classify fast
```

### Increase timeout for slow networks

```bash
OPENAI_TIMEOUT_SECONDS=60  # Was 30
```

### Reduce retries for faster failure

```bash
OPENAI_MAX_RETRIES=1  # Was 3 (only retry once)
```

---

## Cost Estimation

**gpt-4o-mini pricing (as of Jan 2024):**
- Input: $0.15 per 1M tokens
- Output: $0.60 per 1M tokens

**Typical calls:**
- Draft generation: ~500 tokens total = ~$0.0004
- Email linting: ~400 tokens total = ~$0.0003
- Reply classification: ~200 tokens total = ~$0.0001

**For 30 calls/hour:**
- Draft (10 calls): ~$0.004
- Lint (10 calls): ~$0.003
- Classify (10 calls): ~$0.001
- **Total per hour: ~$0.008**

**Monthly estimate (30 calls/hour, 8 hours/day, 22 work days):**
- 30 × 8 × 22 = 5,280 calls
- ~$0.004 per call average = **~$20/month**

---

## Next Steps

1. ✅ Set up OPENAI_API_KEY
2. ✅ Restart backend
3. ✅ Test endpoints above
4. 📋 (Optional) Add UI buttons to frontend campaign wizard
5. 📋 (Optional) Monitor costs in OpenAI dashboard
6. 📋 (Optional) Adjust models based on quality/cost tradeoff

See [OPENAI_INTEGRATION.md](OPENAI_INTEGRATION.md) for complete API docs.
