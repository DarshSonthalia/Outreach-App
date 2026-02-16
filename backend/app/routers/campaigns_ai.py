"""
Campaign AI endpoints - draft generation and risk linting.
"""
import logging
import os
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, Campaign, Workspace, Event
from app.utils.dependencies import get_current_user
from app.services.llm_service import (
    generate_campaign_draft,
    lint_email,
    LLMError,
    _smoke_test_draft,
)
from app.utils.rate_limit import check_rate_limit

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/campaigns", tags=["campaigns_ai"])
MAX_CAMPAIGN_DRAFT_GENERATIONS = 2


# =====================================================================
# SCHEMAS
# =====================================================================

class DraftRequest(BaseModel):
    tone: str = "friendly"  # calm | direct | friendly
    length: str = "medium"  # short | medium
    include_followup: bool = True


class DraftResponse(BaseModel):
    subject: str
    body: str
    followup_subject: Optional[str] = None
    followup_body: Optional[str] = None
    personalization_vars_used: list[str]
    risky_phrases_found: list[str]
    generation_count: int = 0
    generation_limit: int = MAX_CAMPAIGN_DRAFT_GENERATIONS
    remaining_generations: int = MAX_CAMPAIGN_DRAFT_GENERATIONS


class DraftUsageResponse(BaseModel):
    generation_count: int
    generation_limit: int
    remaining_generations: int


class LintRequest(BaseModel):
    subject: str
    body: str
    followup_subject: Optional[str] = None
    followup_body: Optional[str] = None


class LintIssue(BaseModel):
    category: str  # SPAMMY_LANGUAGE | OVERCLAIMS | etc
    severity: str  # LOW | MEDIUM | HIGH
    explanation: str
    suggestion: str


class LintResponse(BaseModel):
    verdict: str  # SAFE | RISKY
    risk_score: int  # 0-100
    issues: list[LintIssue]


# =====================================================================
# ENDPOINTS
# =====================================================================

@router.post("/{campaign_id}/ai/draft", response_model=DraftResponse)
async def ai_generate_draft(
    campaign_id: int,
    request: DraftRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Generate campaign draft (subject + body) using OpenAI.
    
    Uses campaign wizard context (what_you_sell, target_industry, etc).
    
    Rate limit: 30 calls per hour per user.
    
    Returns: DraftResponse with subject, body, and optional follow-up fields.
    """
    # Check rate limit
    allowed, remaining = check_rate_limit(current_user.id)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="AI rate limit exceeded (30 calls per hour)",
        )
    
    # Verify campaign ownership
    campaign = db.query(Campaign).join(Workspace).filter(
        Campaign.id == campaign_id,
        Workspace.user_id == current_user.id,
    ).first()
    
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found",
        )

    # Hard cap per campaign to prevent repeated regenerate loops.
    campaign_draft_count = db.query(Event).filter(
        Event.entity_type == "campaign",
        Event.entity_id == campaign_id,
        Event.action.in_(["AI_DRAFT_GENERATED", "AI_DRAFT_FALLBACK"]),
    ).count()
    if campaign_draft_count >= MAX_CAMPAIGN_DRAFT_GENERATIONS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"AI email generation limit reached ({MAX_CAMPAIGN_DRAFT_GENERATIONS}).",
        )
    
    # Get workspace context
    workspace = campaign.workspace

    # Extract wizard answers (support older schema where fields are top-level)
    wizard_answers = getattr(workspace, "wizard_answers", None) or {}
    what_you_sell = wizard_answers.get("what_you_sell") or getattr(workspace, "what_you_sell", "your product/service")
    target_industry = wizard_answers.get("target_industry") or getattr(workspace, "target_industry", "general")
    target_role = wizard_answers.get("target_role") or getattr(workspace, "target_role", "decision maker")
    offer_type = wizard_answers.get("offer_type") or getattr(workspace, "offer_type", "consultation")
    target_region = wizard_answers.get("target_region") or getattr(workspace, "target_region", "global")
    founder_name = wizard_answers.get("founder_name") or getattr(workspace, "founder_name", None)

    pain_points = None
    value_prop = None
    social_proof = None
    cta_preference = None
    personalization_notes = None
    additional_context = None

    # Campaign-specific `customer_info` on the campaign record overrides workspace wizard answers.
    # Fall back to Event-based storage if the campaign column is empty (back-compat).
    try:
        if getattr(campaign, 'customer_info', None) and isinstance(campaign.customer_info, dict):
            campaign_info = campaign.customer_info
        else:
            ci_event = (
                db.query(Event)
                .filter(Event.entity_type == "campaign", Event.entity_id == campaign_id, Event.action == "CAMPAIGN_CUSTOMER_INFO")
                .order_by(Event.timestamp.desc())
                .first()
            )
            campaign_info = ci_event.details if ci_event and isinstance(ci_event.details, dict) else None

        if campaign_info:
            # Only override known fields to avoid unexpected prompt injection
            what_you_sell = campaign_info.get("what_you_sell") or what_you_sell
            target_industry = campaign_info.get("target_industry") or target_industry
            target_role = campaign_info.get("target_role") or target_role
            offer_type = campaign_info.get("offer_type") or offer_type
            target_region = campaign_info.get("target_region") or target_region
            pain_points = campaign_info.get("pain_points") or pain_points
            value_prop = campaign_info.get("value_prop") or value_prop
            social_proof = campaign_info.get("social_proof") or social_proof
            cta_preference = campaign_info.get("cta_preference") or cta_preference
            personalization_notes = campaign_info.get("personalization_notes") or personalization_notes
            additional_context = campaign_info.get("additional_context") or additional_context
            founder_name = campaign_info.get("founder_name") or founder_name
        
        # Final cleanup for founder_name to avoid empty string issues
        if founder_name and isinstance(founder_name, str) and not founder_name.strip():
            founder_name = None
    except Exception:
        pass
    
    logger.info(
        f"Generating draft for campaign {campaign_id}, "
        f"user {current_user.id}, tone={request.tone}, length={request.length}"
    )
    # For local debugging, emit a preview of the prompt that will be sent to the LLM
    try:
        input_preview = f"""CONTEXT (do not invent details):
- What we sell: {what_you_sell}
- Sender Name: {founder_name or 'n/a'}
- Target industry: {target_industry}
- Target role: {target_role}
- Offer type: {offer_type}
- Target region: {target_region}
 - Pain points: {pain_points or 'n/a'}
 - Value prop: {value_prop or 'n/a'}
 - Social proof: {social_proof or 'n/a'}
 - CTA preference: {cta_preference or 'n/a'}
 - Personalization notes: {personalization_notes or 'n/a'}
 - Additional context: {additional_context or 'n/a'}

WRITING SETTINGS:
- Tone: {request.tone}
- Length: {request.length}
- Include follow-up: {request.include_followup}

OUTPUT REQUIREMENTS:
- Provide a subject and an email body.
"""
        if os.getenv("DEBUG_AI_PROMPT") == "1":
            logger.info(f"AI_PROMPT_PREVIEW for campaign {campaign_id}: {input_preview}")
    except Exception:
        pass
    
    try:
        # Call LLM service
        draft = generate_campaign_draft(
            what_you_sell=what_you_sell,
            target_industry=target_industry,
            target_role=target_role,
            offer_type=offer_type,
            target_region=target_region,
            founder_name=founder_name,
            pain_points=pain_points,
            value_prop=value_prop,
            social_proof=social_proof,
            cta_preference=cta_preference,
            personalization_notes=personalization_notes,
            additional_context=additional_context,
            tone=request.tone,
            length=request.length,
            include_followup=request.include_followup,
        )

        # Log audit event
        event = Event(
            entity_type="campaign",
            entity_id=campaign_id,
            action="AI_DRAFT_GENERATED",
            details={
                "model": os.getenv("OPENAI_MODEL_DRAFT", "unknown"),
                "tone": request.tone,
                "length": request.length,
                "risky_phrases": draft.get("risky_phrases_found", []),
            },
            explanation=f"AI-generated draft for campaign {campaign.name}",
        )
        db.add(event)
        db.commit()

        logger.info(f"Draft generated successfully for campaign {campaign_id}")

        # Return response (do NOT store in campaign automatically)
        return DraftResponse(
            subject=draft.get("subject", ""),
            body=draft.get("body", ""),
            followup_subject=draft.get("followup_subject"),
            followup_body=draft.get("followup_body"),
            personalization_vars_used=draft.get("personalization_vars_used", []),
            risky_phrases_found=draft.get("risky_phrases_found", []),
            generation_count=campaign_draft_count + 1,
            generation_limit=MAX_CAMPAIGN_DRAFT_GENERATIONS,
            remaining_generations=max(0, MAX_CAMPAIGN_DRAFT_GENERATIONS - (campaign_draft_count + 1)),
        )

    except LLMError as e:
        logger.error(f"LLM error generating draft: {e}")
        # If OpenAI key is not configured, return a safe canned draft so the
        # campaign creation flow doesn't fail for local/dev environments.
        if not os.getenv("OPENAI_API_KEY"):
            logger.info("OPENAI_API_KEY missing — returning canned draft fallback")
            fallback = _smoke_test_draft(founder_name=founder_name)
            event = Event(
                entity_type="campaign",
                entity_id=campaign_id,
                action="AI_DRAFT_FALLBACK",
                details={"reason": "OPENAI_API_KEY_MISSING"},
                explanation=f"Returned canned draft for campaign {campaign.name} because OpenAI key is missing",
            )
            db.add(event)
            db.commit()

            return DraftResponse(
                subject=fallback.get("subject", ""),
                body=fallback.get("body", ""),
                followup_subject=fallback.get("followup_subject"),
                followup_body=fallback.get("followup_body"),
                personalization_vars_used=fallback.get("personalization_vars_used", []),
                risky_phrases_found=fallback.get("risky_phrases_found", []),
                generation_count=campaign_draft_count + 1,
                generation_limit=MAX_CAMPAIGN_DRAFT_GENERATIONS,
                remaining_generations=max(0, MAX_CAMPAIGN_DRAFT_GENERATIONS - (campaign_draft_count + 1)),
            )

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service temporarily unavailable. Please try again.",
        )
    except Exception as e:
        logger.error(f"Unexpected error in draft generation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error generating draft. Please try again.",
        )


@router.get("/{campaign_id}/ai/draft-usage", response_model=DraftUsageResponse)
async def ai_draft_usage(
    campaign_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    campaign = db.query(Campaign).join(Workspace).filter(
        Campaign.id == campaign_id,
        Workspace.user_id == current_user.id,
    ).first()
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found",
        )

    generation_count = db.query(Event).filter(
        Event.entity_type == "campaign",
        Event.entity_id == campaign_id,
        Event.action.in_(["AI_DRAFT_GENERATED", "AI_DRAFT_FALLBACK"]),
    ).count()

    return DraftUsageResponse(
        generation_count=generation_count,
        generation_limit=MAX_CAMPAIGN_DRAFT_GENERATIONS,
        remaining_generations=max(0, MAX_CAMPAIGN_DRAFT_GENERATIONS - generation_count),
    )


@router.post("/{campaign_id}/ai/lint", response_model=LintResponse)
async def ai_lint_email(
    campaign_id: int,
    request: LintRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Check email for deliverability and compliance risk.
    
    Returns: LintResponse with verdict (SAFE/RISKY), risk_score, and issues.
    
    Rate limit: 30 calls per hour per user.
    """
    # Check rate limit
    allowed, remaining = check_rate_limit(current_user.id)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="AI rate limit exceeded (30 calls per hour)",
        )
    
    # Verify campaign ownership
    campaign = db.query(Campaign).join(Workspace).filter(
        Campaign.id == campaign_id,
        Workspace.user_id == current_user.id,
    ).first()
    
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found",
        )
    
    logger.info(f"Linting email for campaign {campaign_id}, user {current_user.id}")
    
    try:
        # Call LLM service
        lint_result = lint_email(
            subject=request.subject,
            body=request.body,
            followup_subject=request.followup_subject,
            followup_body=request.followup_body,
        )
        
        # Log audit event
        event = Event(
            entity_type="campaign",
            entity_id=campaign_id,
            action="AI_LINT_RUN",
            details={
                "model": "gpt-4o-mini",
                "verdict": lint_result.get("verdict"),
                "risk_score": lint_result.get("risk_score"),
                "issue_count": len(lint_result.get("issues", [])),
            },
            explanation=f"Email risk lint for campaign {campaign.name}",
        )
        db.add(event)
        db.commit()
        
        logger.info(
            f"Lint completed for campaign {campaign_id}, "
            f"verdict={lint_result.get('verdict')}, score={lint_result.get('risk_score')}"
        )
        
        # Build response
        issues = []
        for issue in lint_result.get("issues", []):
            issues.append(LintIssue(**issue))
        
        return LintResponse(
            verdict=lint_result.get("verdict", "UNKNOWN"),
            risk_score=lint_result.get("risk_score", 50),
            issues=issues,
        )
        
    except LLMError as e:
        logger.error(f"LLM error linting email: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service temporarily unavailable. Please try again.",
        )
    except Exception as e:
        logger.error(f"Unexpected error in email linting: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error checking email. Please try again.",
        )
