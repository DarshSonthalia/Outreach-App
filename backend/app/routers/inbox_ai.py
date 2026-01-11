"""
Inbox AI endpoints - reply classification fallback.
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, Message, Campaign, Workspace, Event, MessageDirection
from app.utils.dependencies import get_current_user
from app.services.llm_service import classify_reply, LLMError
from app.utils.rate_limit import check_rate_limit

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/inbox", tags=["inbox_ai"])


# =====================================================================
# SCHEMAS
# =====================================================================

class ClassifyRequest(BaseModel):
    """Request to classify a reply using AI."""
    pass  # Just uses the message data


class ClassifyResponse(BaseModel):
    """AI classification response."""
    classification: str  # enum value
    confidence: float  # 0.0-1.0
    reason: str


# =====================================================================
# ENDPOINTS
# =====================================================================

@router.post("/replies/{message_id}/ai/classify", response_model=ClassifyResponse)
async def ai_classify_reply(
    message_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Classify inbound reply using AI (fallback for UNKNOWN).
    
    Only works on INBOUND messages (actual replies).
    
    Rate limit: 30 calls per hour per user.
    
    Returns: ClassifyResponse with classification enum, confidence, and reason.
    """
    # Check rate limit
    allowed, remaining = check_rate_limit(current_user.id)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="AI rate limit exceeded (30 calls per hour)",
        )
    
    # Verify message ownership and is inbound
    message = db.query(Message).join(
        Message.campaign_lead
    ).join(
        Campaign, Message.campaign_lead.campaign_id == Campaign.id
    ).join(
        Workspace, Campaign.workspace_id == Workspace.id
    ).filter(
        Message.id == message_id,
        Workspace.user_id == current_user.id,
        Message.direction == MessageDirection.INBOUND,
    ).first()
    
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found or is not an inbound reply",
        )
    
    logger.info(f"AI classifying message {message_id}, user {current_user.id}")
    
    try:
        # Call LLM service
        result = classify_reply(
            subject=message.subject or "",
            body=message.body or "",
        )
        
        # Log audit event
        campaign = message.campaign_lead.campaign
        event = Event(
            entity_type="message",
            entity_id=message_id,
            action="AI_REPLY_CLASSIFIED",
            details={
                "model": "gpt-4o-mini",
                "classification": result.get("classification"),
                "confidence": result.get("confidence"),
            },
            explanation=f"AI classified reply for campaign {campaign.name}",
        )
        db.add(event)
        db.commit()
        
        logger.info(
            f"AI classification complete: {result.get('classification')} "
            f"(confidence {result.get('confidence')})"
        )
        
        return ClassifyResponse(
            classification=result.get("classification", "UNKNOWN"),
            confidence=result.get("confidence", 0.0),
            reason=result.get("reason", ""),
        )
        
    except LLMError as e:
        logger.error(f"LLM error classifying reply: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service temporarily unavailable. Please try again.",
        )
    except Exception as e:
        logger.error(f"Unexpected error in reply classification: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error classifying reply. Please try again.",
        )
