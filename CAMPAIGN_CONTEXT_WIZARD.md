# Campaign Context Wizard - Implementation Summary

## Overview

A pre-campaign wizard has been added to collect context about each campaign **before** creation. This context is fed to the OpenAI API to generate personalized, high-converting email copy.

## User Flow

The campaign creation flow now has **5 steps** (previously 4):

```
Step 1: Campaign Context   ← NEW
Step 2: Campaign Setup
Step 3: Select Leads  
Step 4: Email Copy (AI-Generated)
Step 5: Launch
```

## Step 1: Campaign Context Wizard

### Fields Collected

| Field | Required | Description |
|-------|----------|-------------|
| **What do you sell?** | ✅ Yes | Description of your product/service and the value you provide |
| **Target Industry** | No | e.g., "SaaS", "FinTech", "Healthcare" |
| **Target Role** | ✅ Yes | e.g., "VP of Sales", "CTO", "Head of Marketing" |
| **Target Region** | No | e.g., "US", "Europe", "Global" |
| **Offer Type** | No | Dropdown: Consultation, Demo, Audit, Call, Trial, Resource |

### Pre-Population

The wizard automatically pre-fills values from the workspace's default settings if they exist:
- `workspace.what_you_sell`
- `workspace.target_industry`
- `workspace.target_role`
- `workspace.target_region`
- `workspace.offer_type`

Users can override these values for each campaign.

### Pro Tips Section

The wizard includes helpful tips:
- Be specific about your value proposition
- More context → better AI-generated emails
- You can refine the copy in later steps

## How Context is Used

### 1. Stored in Campaign

The context is stored in `campaign.customer_info` (JSON column) when the campaign is created:

```json
{
  "what_you_sell": "We help B2B SaaS companies reduce churn...",
  "target_industry": "SaaS",
  "target_role": "VP of Customer Success",
  "target_region": "US",
  "offer_type": "consultation"
}
```

### 2. Fed to OpenAI

The `campaigns_ai.py` endpoint uses this context to generate personalized drafts:

```python
draft = generate_campaign_draft(
    what_you_sell=campaign_info.get("what_you_sell"),
    target_industry=campaign_info.get("target_industry"),
    target_role=campaign_info.get("target_role"),
    offer_type=campaign_info.get("offer_type"),
    target_region=campaign_info.get("target_region"),
    tone="friendly",
    length="medium",
    include_followup=True,
)
```

### 3. AI Prompt Example

The LLM receives context like:

```
CONTEXT (do not invent details):
- What we sell: We help B2B SaaS companies reduce churn through predictive analytics
- Target industry: SaaS
- Target role: VP of Customer Success
- Offer type: consultation
- Target region: US

WRITING SETTINGS:
- Tone: friendly
- Length: medium
- Include follow-up: true
```

## UI Features

### Context Summary Card

In Step 2 (Setup), a summary card shows the campaign context:

```
📋 Campaign Context
Selling: We help B2B SaaS companies...
Target: VP of Customer Success in SaaS
Offer: consultation

← Edit context
```

### Regenerate Button

In Step 4 (Email Copy), users can click "🔄 Regenerate" to generate a new draft using the same context.

### Follow-up Content

The AI generates both:
- Initial email (subject + body)
- Follow-up email (subject + body)

Both are editable before launch.

## Files Modified

| File | Changes |
|------|---------|
| `frontend/src/app/campaigns/new/page.tsx` | Complete rewrite with new 5-step flow |

## Files Already Working (No Changes Needed)

| File | Purpose |
|------|---------|
| `backend/app/routers/campaigns.py` | Already stores `customer_info` in campaign |
| `backend/app/routers/campaigns_ai.py` | Already reads `customer_info` for AI drafts |
| `backend/app/services/llm_service.py` | Already generates drafts with context |
| `backend/app/schemas/schemas.py` | Already has `customer_info` in `CampaignCreate` |
| `backend/app/models/models.py` | Already has `customer_info` JSON column |

## Testing

### Quick Test

1. Navigate to `/campaigns/new`
2. Fill in the Campaign Context wizard (Step 1)
3. Proceed through Setup and Lead selection
4. Verify the AI-generated email mentions your context
5. Launch the campaign

### Verify Context Storage

Check the campaign's `customer_info` field in the database:

```sql
SELECT id, name, customer_info FROM campaigns ORDER BY created_at DESC LIMIT 1;
```

## Backward Compatibility

- All existing campaigns without `customer_info` continue to work
- The AI falls back to workspace defaults if `customer_info` is empty
- No database migrations required (column already exists)

---

**Date**: 2026-01-10  
**Status**: ✅ Implemented and tested
