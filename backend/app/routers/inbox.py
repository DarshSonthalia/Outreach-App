"""
Inbox router - view and manage replies.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import re

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
import logging
logger = logging.getLogger(__name__)


def clean_message_body(body: str) -> str:
    """
    Remove quoted/previous message content from email bodies.
    Strips everything from "On <date> at <time>, <email> wrote:" onwards.
    """
    if not body:
        return body
    
    # Match the quoted message pattern: "On <date> at <time>, <email> wrote:"
    # This is the standard Gmail/Outlook format for quoted messages
    pattern = r'On\s+.+?at\s+.+?,\s+<?.+?@.+?\.com>?\s+wrote:'
    
    # Find the first occurrence of the quoted message pattern
    match = re.search(pattern, body, re.IGNORECASE | re.DOTALL)
    
    if match:
        # Return only the part before the quoted message
        cleaned = body[:match.start()].strip()
        return cleaned
    
    return body.strip()


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
    
    logger.info(f"Fetching replies for workspace {workspace_id}, user {current_user.id}")
    
    # Get all campaign_lead IDs for this workspace
    campaign_leads_query = db.query(CampaignLead.id).join(
        Campaign, CampaignLead.campaign_id == Campaign.id
    ).filter(
        Campaign.workspace_id == workspace_id
    )
    
    if campaign_id:
        campaign_leads_query = campaign_leads_query.filter(Campaign.id == campaign_id)
        logger.info(f"Filtering by campaign_id: {campaign_id}")
    
    campaign_lead_ids = [cl[0] for cl in campaign_leads_query.all()]
    logger.info(f"Found {len(campaign_lead_ids)} campaign_leads in workspace")
    
    if not campaign_lead_ids:
        logger.info("No campaign leads found, returning empty list")
        return []
    
    # For each campaign_lead, get the LATEST message (by received_at or sent_at)
    # This shows one item per conversation
    result = []
    for cl_id in campaign_lead_ids:
        # Get the latest message for this conversation
        # Try received_at first (for inbound), then sent_at (for outbound)
        latest_msg = db.query(Message).filter(
            Message.campaign_lead_id == cl_id
        ).order_by(
            Message.received_at.desc().nullslast(),
            Message.sent_at.desc().nullslast(),
            Message.id.desc()
        ).first()
        
        if not latest_msg:
            continue
        
        try:
            campaign_lead = db.query(CampaignLead).get(cl_id)
            if not campaign_lead:
                continue
                
            lead = campaign_lead.lead
            campaign = campaign_lead.campaign
            
            # Only clean body for inbound messages (replies)
            if latest_msg.direction == MessageDirection.INBOUND:
                cleaned_body = clean_message_body(latest_msg.body)
            else:
                cleaned_body = latest_msg.body
            
            result.append(ReplyResponse(
                id=latest_msg.id,
                lead_email=lead.email,
                lead_name=f"{lead.first_name or ''} {lead.last_name or ''}".strip() or None,
                campaign_name=campaign.name,
                subject=latest_msg.subject,
                body=cleaned_body,
                classification=latest_msg.classification,
                received_at=latest_msg.received_at or latest_msg.sent_at,
                direction=latest_msg.direction.value
            ))
        except Exception as e:
            logger.error(f"Error building response for campaign_lead {cl_id}: {e}")
            continue
    
    # Sort by timestamp descending (newest first)
    result.sort(key=lambda x: x.received_at or '', reverse=True)
    
    # Apply pagination
    total_count = len(result)
    logger.info(f"Found {total_count} total conversations")
    
    paginated_result = result[skip:skip+limit]
    logger.info(f"Returning {len(paginated_result)} conversation threads (skip={skip}, limit={limit})")
    
    return paginated_result


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
    campaign = reply.campaign_lead.campaign
    return ReplyResponse(
        id=reply.id,
        lead_email=lead.email,
        lead_name=f"{lead.first_name or ''} {lead.last_name or ''}".strip() or None,
        campaign_name=campaign.name,
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
    
    # Get all messages in the same thread, sorted newest first
    thread_messages = db.query(Message).filter(
        Message.gmail_thread_id == reply.gmail_thread_id
    ).order_by(Message.received_at.desc(), Message.sent_at.desc()).all()
    
    messages_data = []
    for msg in thread_messages:
        # Clean body for inbound messages only
        if msg.direction == MessageDirection.INBOUND:
            msg_body = clean_message_body(msg.body)
        else:
            msg_body = msg.body
        
        messages_data.append({
            "id": msg.id,
            "direction": msg.direction.value,  # Convert Enum to string
            "subject": msg.subject,
            "body": msg_body,
            "received_at": msg.received_at,
            "sent_at": msg.sent_at,
            "classification": msg.classification.value if msg.classification else None,  # Convert Enum to string
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
            reply_to_thread_id=reply.gmail_thread_id,
            reply_to_message_id=reply.gmail_message_id  # <--- Fix: Pass API ID for header fetching
        )
        
        # Calculate unique negative step number for manual replies
        # Find the lowest existing negative step number for this lead
        from sqlalchemy import func
        min_step = db.query(func.min(Message.step_number)).filter(
            Message.campaign_lead_id == campaign_lead.id,
            Message.step_number < 0
        ).scalar()
        
        # Start at -2, then go to -3, -4, etc.
        if min_step is None:
            next_step = -2
        else:
            next_step = min_step - 1
            
        # Record the manual outbound message
        new_msg = Message(
            campaign_lead_id=campaign_lead.id,
            direction=MessageDirection.OUTBOUND,
            step_number=next_step,  # Dynamic negative step number
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


@router.get("/debug/replies")
async def debug_replies(
    workspace_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Debug endpoint to check reply data in database.
    Returns detailed information about messages and relationships.
    """
    # Verify workspace
    workspace = db.query(Workspace).filter(
        Workspace.id == workspace_id,
        Workspace.user_id == current_user.id
    ).first()
    
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )
    
    # Count all messages
    total_messages = db.query(Message).count()
    inbound_messages = db.query(Message).filter(
        Message.direction == MessageDirection.INBOUND
    ).count()
    outbound_messages = db.query(Message).filter(
        Message.direction == MessageDirection.OUTBOUND
    ).count()
    
    # Count messages for this workspace
    workspace_messages = db.query(Message).join(
        CampaignLead, Message.campaign_lead_id == CampaignLead.id
    ).join(
        Campaign, CampaignLead.campaign_id == Campaign.id
    ).filter(
        Campaign.workspace_id == workspace_id
    ).count()
    
    workspace_inbound = db.query(Message).join(
        CampaignLead, Message.campaign_lead_id == CampaignLead.id
    ).join(
        Campaign, CampaignLead.campaign_id == Campaign.id
    ).filter(
        Campaign.workspace_id == workspace_id,
        Message.direction == MessageDirection.INBOUND
    ).count()
    
    # Get sample messages
    sample_messages = db.query(Message).join(
        CampaignLead, Message.campaign_lead_id == CampaignLead.id
    ).join(
        Campaign, CampaignLead.campaign_id == Campaign.id
    ).filter(
        Campaign.workspace_id == workspace_id,
        Message.direction == MessageDirection.INBOUND
    ).limit(5).all()
    
    sample_data = []
    for msg in sample_messages:
        try:
            sample_data.append({
                "message_id": msg.id,
                "campaign_lead_id": msg.campaign_lead_id,
                "subject": msg.subject,
                "received_at": str(msg.received_at) if msg.received_at else None,
                "classification": msg.classification.value if msg.classification else None,
                "has_campaign_lead": msg.campaign_lead is not None,
                "has_lead": msg.campaign_lead.lead is not None if msg.campaign_lead else False,
                "has_campaign": msg.campaign_lead.campaign is not None if msg.campaign_lead else False,
            })
        except Exception as e:
            sample_data.append({
                "message_id": msg.id,
                "error": str(e)
            })
    
    return {
        "workspace_id": workspace_id,
        "total_messages_in_db": total_messages,
        "total_inbound_messages": inbound_messages,
        "total_outbound_messages": outbound_messages,
        "workspace_messages_total": workspace_messages,
        "workspace_inbound_messages": workspace_inbound,
        "sample_messages": sample_data,
        "campaigns_count": db.query(Campaign).filter(Campaign.workspace_id == workspace_id).count(),
        "campaign_leads_count": db.query(CampaignLead).join(Campaign).filter(
            Campaign.workspace_id == workspace_id
        ).count(),
    }
