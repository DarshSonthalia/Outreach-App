"""
Inbox router - view and manage replies.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models import (
    User, Workspace, Campaign, CampaignLead, Message, Lead,
    MessageDirection, SuppressionReason, Mailbox
)
from app.schemas import ReplyResponse, ClassifyRequest, SendReplyRequest
from app.utils.dependencies import get_current_user
from app.services.safety_service import SafetyService
from app.services.classification_service import ClassificationService
from app.services.gmail_service import GmailService
from datetime import datetime

router = APIRouter()


@router.get("/replies", response_model=List[ReplyResponse])
async def list_replies(
    workspace_id: int,
    campaign_id: int = None,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all replies for a workspace, optionally filtered by campaign.
    """
    # Verify workspace belongs to user
    workspace = db.query(Workspace).filter(
        Workspace.id == workspace_id,
        Workspace.user_id == current_user.id
    ).first()
    
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )
    
    # Build query
    query = db.query(Message).join(CampaignLead).join(Campaign).filter(
        Campaign.workspace_id == workspace_id,
        Message.direction == MessageDirection.INBOUND
    )
    
    if campaign_id:
        query = query.filter(Campaign.id == campaign_id)
    
    replies = query.order_by(Message.received_at.desc()).offset(skip).limit(limit).all()
    
    # Build response with lead info
    result = []
    for reply in replies:
        lead = reply.campaign_lead.lead
        result.append(ReplyResponse(
            id=reply.id,
            lead_email=lead.email,
            lead_name=f"{lead.first_name or ''} {lead.last_name or ''}".strip() or None,
            subject=reply.subject,
            body=reply.body,
            classification=reply.classification,
            received_at=reply.received_at
        ))
    
    return result


@router.post("/replies/{reply_id}/classify", response_model=ReplyResponse)
async def classify_reply(
    reply_id: int,
    request: ClassifyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Manually classify a reply.
    """
    reply = db.query(Message).join(CampaignLead).join(Campaign).join(Workspace).filter(
        Message.id == reply_id,
        Workspace.user_id == current_user.id,
        Message.direction == MessageDirection.INBOUND
    ).first()
    
    if not reply:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reply not found"
        )
    
    reply.classification = request.classification
    
    # If classified as unsubscribe, add to suppression list
    from app.enums import ReplyClassification
    if request.classification == ReplyClassification.UNSUBSCRIBE:
        lead = reply.campaign_lead.lead
        SafetyService.add_to_suppression(
            db,
            reply.campaign_lead.campaign.workspace_id,
            lead.email,
            SuppressionReason.UNSUBSCRIBE,
            f"Manually classified as unsubscribe from reply {reply_id}"
        )
    
    db.commit()
    db.refresh(reply)
    
    lead = reply.campaign_lead.lead
    return ReplyResponse(
        id=reply.id,
        lead_email=lead.email,
        lead_name=f"{lead.first_name or ''} {lead.last_name or ''}".strip() or None,
        subject=reply.subject,
        body=reply.body,
        classification=reply.classification,
        received_at=reply.received_at
    )


@router.get("/replies/{reply_id}")
async def get_reply(
    reply_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get a single reply with full conversation thread.
    """
    reply = db.query(Message).join(CampaignLead).join(Campaign).join(Workspace).filter(
        Message.id == reply_id,
        Workspace.user_id == current_user.id,
        Message.direction == MessageDirection.INBOUND
    ).first()
    
    if not reply:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reply not found"
        )
    
    lead = reply.campaign_lead.lead
    campaign = reply.campaign_lead.campaign
    
    # Get all messages in the same thread
    thread_messages = db.query(Message).filter(
        Message.gmail_thread_id == reply.gmail_thread_id
    ).order_by(Message.received_at.asc(), Message.sent_at.asc()).all()
    
    messages_data = []
    for msg in thread_messages:
        messages_data.append({
            "id": msg.id,
            "direction": msg.direction,
            "subject": msg.subject,
            "body": msg.body,
            "received_at": msg.received_at,
            "sent_at": msg.sent_at,
            "classification": msg.classification,
        })

    # Get classification explanation
    explanation = ""
    if reply.classification:
        explanation = ClassificationService.get_classification_explanation(reply.classification)
    
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


@router.post("/replies/{reply_id}/send")
async def send_reply(
    reply_id: int,
    request: SendReplyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Send a reply to a lead from within the app.
    """
    
    # Find the inbound message
    reply = db.query(Message).join(CampaignLead).join(Campaign).join(Workspace).filter(
        Message.id == reply_id,
        Workspace.user_id == current_user.id,
        Message.direction == MessageDirection.INBOUND
    ).first()
    
    if not reply:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reply not found"
        )
    
    campaign_lead = reply.campaign_lead
    campaign = campaign_lead.campaign
    mailbox = db.query(Mailbox).get(campaign.mailbox_id)
    
    if not mailbox:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mailbox not found"
        )
    
    # Get Gmail client
    service, mailbox = GmailService.get_gmail_client(mailbox, db)
    if not service:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Gmail re-authentication required"
        )
    
    # Send the email
    try:
        # Get credentials
        credentials = GmailService.get_credentials_from_encrypted(
            mailbox.access_token_encrypted,
            mailbox.refresh_token_encrypted,
            mailbox.token_expiry
        )
        
        # In a real reply, we should preserve the subject and add "Re:" if missing
        original_subject = reply.subject or ""
        subject = original_subject if original_subject.lower().startswith("re:") else f"Re: {original_subject}"
        
        # Use our send_email service
        gmail_msg_id, gmail_thread_id = GmailService.send_email(
            credentials=credentials,
            to_email=campaign_lead.lead.email,
            subject=subject,
            body=request.body,
            reply_to_thread_id=reply.gmail_thread_id
        )
        
        # Record the manual outbound message
        new_msg = Message(
            campaign_lead_id=campaign_lead.id,
            direction=MessageDirection.OUTBOUND,
            step_number=-2,  # Manual follow-up
            gmail_message_id=gmail_msg_id,
            gmail_thread_id=gmail_thread_id,
            subject=subject,
            body=request.body,
            sent_at=datetime.utcnow()
        )
        db.add(new_msg)
        db.commit()
        
        return {"status": "success", "message_id": gmail_msg_id}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send reply: {str(e)}"
        )
