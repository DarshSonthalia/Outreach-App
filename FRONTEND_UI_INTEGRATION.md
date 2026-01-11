# Frontend UI Integration Checklist

This document outlines how to add AI buttons to the frontend UI. The API endpoints are ready; this guide shows where to add the buttons and how to handle responses.

## ✅ Completed

- [x] Backend API endpoints fully implemented
- [x] Frontend API client methods added to `lib/api.ts`
- [x] Rate limiting middleware
- [x] Structured output validation
- [x] Error handling
- [x] Audit logging

## 📋 Frontend UI Integration (Optional)

These are optional enhancements to add AI features to the user interface.

### Option 1: Campaign Creation (Recommended for MVP)

#### Location: `src/app/campaigns/new/page.tsx`

**Step 1: Add state for AI responses**

```typescript
const [draftLoading, setDraftLoading] = useState(false);
const [lintLoading, setLintLoading] = useState(false);
const [lintResult, setLintResult] = useState<any>(null);
```

**Step 2: Add handlers**

```typescript
const handleGenerateDraft = async () => {
  if (!token || !campaignId) return;
  setDraftLoading(true);
  try {
    const draft = await campaignsAI.generateDraft(
      token,
      campaignId,
      'friendly',
      'medium',
      true
    );
    // Auto-fill form fields
    setSubject(draft.subject);
    setBody(draft.body);
    if (draft.followup_subject) setFollowupSubject(draft.followup_subject);
    if (draft.followup_body) setFollowupBody(draft.followup_body);
    
    // Show risky phrases warning
    if (draft.risky_phrases_found?.length > 0) {
      alert(`Warning: Found risky phrases:\n${draft.risky_phrases_found.join(', ')}`);
    }
  } catch (err: any) {
    alert(`Failed to generate draft: ${err.message}`);
  }
  setDraftLoading(false);
};

const handleLintEmail = async () => {
  if (!token || !campaignId || !subject || !body) return;
  setLintLoading(true);
  try {
    const result = await campaignsAI.lintEmail(
      token,
      campaignId,
      subject,
      body,
      followupSubject,
      followupBody
    );
    setLintResult(result);
    
    // Show verdict
    if (result.verdict === 'RISKY') {
      const issuesSummary = result.issues
        .map(i => `${i.category}: ${i.explanation}`)
        .join('\n');
      alert(`⚠️ Email is RISKY (score: ${result.risk_score}/100)\n\nIssues:\n${issuesSummary}`);
    } else {
      alert(`✅ Email is SAFE (risk score: ${result.risk_score}/100)`);
    }
  } catch (err: any) {
    alert(`Failed to check email: ${err.message}`);
  }
  setLintLoading(false);
};
```

**Step 3: Add UI buttons in the form**

In Step 1 (subject/body entry), add:

```tsx
<button
  onClick={handleGenerateDraft}
  disabled={draftLoading || !campaignId}
  className="btn btn-outline btn-sm"
>
  {draftLoading ? '⏳ Generating...' : '✨ Generate Draft (AI)'}
</button>
```

In Step 3 (email content review), add:

```tsx
<button
  onClick={handleLintEmail}
  disabled={lintLoading || !subject || !body}
  className="btn btn-outline btn-sm"
>
  {lintLoading ? '⏳ Checking...' : '🔍 Check Risk (AI)'}
</button>

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
            <strong>{issue.category}</strong> ({issue.severity}): {issue.explanation}
            {issue.suggestion && <br/>}
            {issue.suggestion && <small>💡 {issue.suggestion}</small>}
          </li>
        ))}
      </ul>
    )}
  </div>
)}
```

### Option 2: Inbox Reply Classification

#### Location: `src/app/inbox/page.tsx`

**Step 1: Add state**

```typescript
const [classifyingId, setClassifyingId] = useState<number | null>(null);
```

**Step 2: Add handler**

```typescript
const handleAIClassify = async (messageId: number) => {
  if (!token) return;
  setClassifyingId(messageId);
  try {
    const result = await inboxAI.classify(token, messageId);
    // Update the message in the replies list
    setReplies(prev => prev.map(r => 
      r.id === messageId 
        ? { ...r, classification: result.classification }
        : r
    ));
    // Update the selected reply if it's open
    if (selectedReply?.id === messageId) {
      setSelectedReply({ ...selectedReply, classification: result.classification });
    }
    alert(`Classified as: ${result.classification} (confidence: ${(result.confidence * 100).toFixed(0)}%)`);
  } catch (err: any) {
    alert(`Failed to classify: ${err.message}`);
  }
  setClassifyingId(null);
};
```

**Step 3: Add button in reply list**

When classification is UNKNOWN, show button:

```tsx
{reply.classification === 'unknown' && (
  <button
    onClick={() => handleAIClassify(reply.id)}
    disabled={classifyingId === reply.id}
    className="btn btn-xs btn-ghost"
  >
    {classifyingId === reply.id ? '⏳' : '🤖 AI Classify'}
  </button>
)}
```

---

## Error Handling Best Practices

**For all AI calls:**

```typescript
try {
  const result = await campaignsAI.generateDraft(...);
  // Handle success
} catch (err: any) {
  const errorMsg = err?.message || 'AI service error';
  
  if (errorMsg.includes('rate limit')) {
    alert('You\'ve used all 30 AI calls this hour. Try again in 1 hour.');
  } else if (errorMsg.includes('temporarily unavailable')) {
    alert('OpenAI service is temporarily down. Please try again.');
  } else {
    alert(`Error: ${errorMsg}`);
  }
}
```

---

## User Experience Tips

1. **Show loading state** - Use spinner/disabled button while waiting
2. **Set expectations** - "Generating draft..." tells user what to expect
3. **Explain features** - "AI Draft uses your campaign settings to generate emails"
4. **Don't auto-save** - Let user review AI output before saving
5. **Show warnings** - Alert user to risky phrases found
6. **Explain rate limit** - "30 AI calls per hour per user"

---

## Testing

### Without OPENAI_API_KEY set

- API returns 503 Service Unavailable
- Frontend should show: "AI service temporarily unavailable"

### With OPENAI_API_KEY set

- Draft generation: 2-5 seconds
- Email linting: 1-3 seconds
- Reply classification: 1-2 seconds

### Rate limit test

```bash
# Make 31 requests rapidly
for i in {1..31}; do
  curl -X POST http://localhost:8000/api/campaigns/1/ai/draft \
    -H "Authorization: Bearer TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"tone":"friendly","length":"medium","include_followup":true}'
done
# Request 31 should get 429 error
```

---

## Security Considerations

1. ✅ All endpoints require JWT authentication
2. ✅ Workspace ownership verified server-side
3. ✅ Input truncation prevents token bloat
4. ✅ Rate limiting prevents abuse
5. ✅ No sensitive data logged
6. ✅ No per-lead dynamic rewriting

**Frontend should:**
- Validate user has valid token before calling
- Handle 401/403 errors (redirect to login)
- Handle 429 errors (show rate limit message)
- Never log API responses in production

---

## Performance Optimization

**Debounce rapid clicks:**

```typescript
const [generateTimeout, setGenerateTimeout] = useState<NodeJS.Timeout | null>(null);

const handleGenerateDraft = async () => {
  if (generateTimeout) clearTimeout(generateTimeout);
  
  setDraftLoading(true);
  try {
    // ... API call
  } finally {
    setGenerateTimeout(setTimeout(() => setDraftLoading(false), 1000));
  }
};
```

**Show skeleton loading:**

```tsx
{draftLoading && (
  <div className="space-y-2">
    <div className="skeleton h-10 w-full"></div>
    <div className="skeleton h-24 w-full"></div>
  </div>
)}
```

---

## Analytics (Optional)

Track which AI features users rely on:

```typescript
const handleGenerateDraft = async () => {
  // ... existing code ...
  
  // Track usage
  fetch('/api/analytics', {
    method: 'POST',
    body: JSON.stringify({ event: 'ai_draft_generated', campaignId })
  });
};
```

---

## Rollout Strategy

**Phase 1 (MVP):** Campaign draft generation only
**Phase 2:** Email risk linting
**Phase 3:** Reply classification in inbox
**Phase 4:** Advanced features (streaming, bulk ops, model selection)

---

## Troubleshooting

### AI button doesn't do anything

Check:
1. Is OPENAI_API_KEY set? (check docker logs)
2. Is user authenticated? (valid JWT?)
3. Check browser console for errors
4. Check server logs: `docker logs outreach_backend | grep Error`

### "Campaign not found"

- Make sure you're using the right campaign ID
- Verify campaign belongs to your workspace

### Response takes 30+ seconds

- OpenAI API is slow (check https://status.openai.com/)
- Increase OPENAI_TIMEOUT_SECONDS to 60

### Buttons are disabled

- Check if loading state is stuck
- Refresh page
- Check browser DevTools Network tab for failed requests

---

## Support

See full API docs in [OPENAI_INTEGRATION.md](OPENAI_INTEGRATION.md)
See quick start in [OPENAI_QUICKSTART.md](OPENAI_QUICKSTART.md)
