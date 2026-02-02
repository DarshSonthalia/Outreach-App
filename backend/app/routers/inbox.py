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
    MessageDirection, SuppressionReason, Mailbox, BookingEvent,
    ReplyDraft, DraftStatus
)
from app.schemas import ReplyResponse, ClassifyRequest, SendReplyRequest
from app.utils.dependencies import get_current_user
from app.services.safety_service import SafetyService
from app.services.classification_service import ClassificationService
from app.services.gmail_service import GmailService
from app.utils.email import build_reply_subject
from datetime import datetime

router = APIRouter()
import logging
logger = logging.getLogger(__name__)
MAX_REPLY_DRAFTS_PER_THREAD = 2


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
        if cleaned:
            return cleaned
        # If the reply starts with quoted text, fall back to raw body
        return body.strip()
    
    return body.strip()


def _strip_html(body: str) -> str:
    import re
    text = re.sub(r"<(script|style)[^>]*>.*?</\\1>", " ", body, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\\s+", " ", text).strip()
    return text


def normalize_message_body(body: str, is_inbound: bool) -> str:
    raw = body or ""
    stripped = ""
    if "<" in raw and ">" in raw:
        stripped = _strip_html(raw)
    base = stripped or raw
    if is_inbound:
        cleaned = clean_message_body(base)
        if cleaned:
            return cleaned
    return base.strip()


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
        # Only show inbound replies in the inbox list.
        latest_msg = db.query(Message).filter(
            Message.campaign_lead_id == cl_id,
            Message.direction == MessageDirection.INBOUND
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
            cleaned_body = normalize_message_body(
                latest_msg.body or "",
                latest_msg.direction == MessageDirection.INBOUND
            )

            if not cleaned_body:
                fallback_msg = db.query(Message).filter(
                    Message.campaign_lead_id == cl_id,
                    Message.body.isnot(None),
                    Message.body != ""
                ).order_by(
                    Message.received_at.desc().nullslast(),
                    Message.sent_at.desc().nullslast(),
                    Message.id.desc()
                ).first()
                if fallback_msg:
                    cleaned_body = normalize_message_body(
                        fallback_msg.body or "",
                        fallback_msg.direction == MessageDirection.INBOUND
                    )
            
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
    
    campaign_lead = reply.campaign_lead
    lead = campaign_lead.lead
    campaign = campaign_lead.campaign
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
    
    campaign_lead = reply.campaign_lead
    lead = campaign_lead.lead
    campaign = campaign_lead.campaign
    
    # Get all messages in the same thread, sorted newest first
    thread_query = db.query(Message)
    if reply.gmail_thread_id:
        thread_query = thread_query.filter(Message.gmail_thread_id == reply.gmail_thread_id)
    else:
        thread_query = thread_query.filter(Message.campaign_lead_id == reply.campaign_lead_id)

    thread_messages = thread_query.order_by(
        Message.received_at.desc(),
        Message.sent_at.desc()
    ).all()

    if not thread_messages:
        thread_messages = db.query(Message).filter(
            Message.campaign_lead_id == reply.campaign_lead_id
        ).order_by(
            Message.received_at.desc(),
            Message.sent_at.desc()
        ).all()
    
    messages_data = []
    for msg in thread_messages:
        # Clean body for inbound messages only
        msg_body = normalize_message_body(
            msg.body or "",
            msg.direction == MessageDirection.INBOUND
        )
        
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
    ai_reply_generation_count = 0
    if reply.gmail_thread_id:
        ai_reply_generation_count = db.query(ReplyDraft).filter(
            ReplyDraft.workspace_id == campaign.workspace_id,
            ReplyDraft.gmail_thread_id == reply.gmail_thread_id
        ).count()
    
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
        "body": normalize_message_body(reply.body or "", True),
        "classification": reply.classification,
        "classification_explanation": explanation,
        "received_at": reply.received_at,
        "gmail_thread_id": reply.gmail_thread_id,
        "thread": messages_data,
        "campaign_lead": {
            "id": campaign_lead.id,
            "followup_state": campaign_lead.followup_state.value if campaign_lead.followup_state else None,
            "cancel_reason": campaign_lead.cancel_reason.value if campaign_lead.cancel_reason else None,
            "cancel_detail": campaign_lead.cancel_detail,
            "cancelled_at": campaign_lead.cancelled_at
        },
        "booking_confirmed": db.query(BookingEvent).filter(
            BookingEvent.invitee_email == lead.email,
            BookingEvent.event_type == "invitee.created"
        ).count() > 0,
        "ai_reply_generation_count": ai_reply_generation_count,
        "ai_reply_generation_limit": MAX_REPLY_DRAFTS_PER_THREAD,
        "ai_reply_remaining_generations": max(0, MAX_REPLY_DRAFTS_PER_THREAD - ai_reply_generation_count),
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


# ==========================================
# AI DRAFT ENDPOINTS
# ==========================================

from app.services.ai_service import AIService

@router.post("/threads/{gmail_thread_id}/ai-draft")
async def generate_ai_draft(
    gmail_thread_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate an AI draft reply for a specific thread.
    """
    # 1. Verification
    # Find the latest inbound message for this thread to reply to
    latest_msg = db.query(Message).join(CampaignLead).join(Campaign).join(Workspace).filter(
        Message.gmail_thread_id == gmail_thread_id,
        Workspace.user_id == current_user.id, # Ownership check
        Message.direction == MessageDirection.INBOUND
    ).order_by(Message.received_at.desc()).first()

    if not latest_msg:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No inbound message found for this thread"
        )

    # Limit AI reply drafts per thread to prevent repeated regenerations.
    existing_drafts = db.query(ReplyDraft).filter(
        ReplyDraft.workspace_id == latest_msg.campaign_lead.campaign.workspace_id,
        ReplyDraft.gmail_thread_id == gmail_thread_id
    ).count()
    if existing_drafts >= MAX_REPLY_DRAFTS_PER_THREAD:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"AI reply generation limit reached ({MAX_REPLY_DRAFTS_PER_THREAD})."
        )

    # 2. Context Gathering
    campaign_lead = latest_msg.campaign_lead
    campaign = campaign_lead.campaign
    lead = campaign_lead.lead
    
    # Get conversation history (sorted old -> new)
    history_msgs = db.query(Message).filter(
        Message.gmail_thread_id == gmail_thread_id
    ).order_by(Message.received_at, Message.sent_at).all()
    
    # Format history
    history_text = ""
    for msg in history_msgs:
        sender = "Lead" if msg.direction == MessageDirection.INBOUND else "Me"
        content = clean_message_body(msg.body) if msg.direction == MessageDirection.INBOUND else msg.body
        history_text += f"{sender}: {content}\n\n"
        
    campaign_body = campaign.body or ""
    campaign_context = f"Goal: {campaign.name}."
    if campaign_body:
        campaign_context = f"{campaign_context} Body sample: {campaign_body[:200]}..."

    context = {
        "lead_name": f"{lead.first_name} {lead.last_name}".strip(),
        "lead_company": lead.company,
        "lead_email": lead.email,
        "campaign_context": campaign_context,
        "conversation_history": history_text,
        "last_reply": latest_msg.body
    }
    
    # 3. Generate Draft via AI Service
    try:
        draft_json = AIService.generate_reply_draft(context)
    except Exception as e:
        logger.error(f"AI Generation failed: {e}")
        subject = latest_msg.subject or "Quick question"
        draft_json = {
            "classification": "NEUTRAL",
            "subject": f"Re: {subject}",
            "body": "Thanks for the note. Would you be open to a quick chat so I can better understand your needs?",
            "needs_human_review": True,
            "risk_flags": ["AI_GENERATION_FAILED"]
        }
        
    # 4. Save to DB (reply_drafts)
    new_draft = ReplyDraft(
        workspace_id=campaign.workspace_id,
        mailbox_id=campaign.mailbox_id,
        gmail_thread_id=gmail_thread_id,
        gmail_message_id=latest_msg.gmail_message_id, # Replying to this msg
        subject=draft_json.get("subject"),
        body=draft_json.get("body"),
        model="gpt-4o", # from config ideally
        prompt_version="v1",
        status=DraftStatus.GENERATED,
        risk_flags=draft_json.get("risk_flags"),
        classification=draft_json.get("classification")
    )
    db.add(new_draft)
    db.commit()
    db.refresh(new_draft)
    
    generation_count = existing_drafts + 1
    return {
        "id": new_draft.id,
        "workspace_id": new_draft.workspace_id,
        "mailbox_id": new_draft.mailbox_id,
        "gmail_thread_id": new_draft.gmail_thread_id,
        "gmail_message_id": new_draft.gmail_message_id,
        "subject": new_draft.subject,
        "body": new_draft.body,
        "model": new_draft.model,
        "prompt_version": new_draft.prompt_version,
        "status": new_draft.status.value if new_draft.status else None,
        "risk_flags": new_draft.risk_flags,
        "classification": new_draft.classification,
        "created_at": new_draft.created_at,
        "updated_at": new_draft.updated_at,
        "generation_count": generation_count,
        "generation_limit": MAX_REPLY_DRAFTS_PER_THREAD,
        "remaining_generations": max(0, MAX_REPLY_DRAFTS_PER_THREAD - generation_count),
    }


from fastapi import Body

@router.post("/drafts/{draft_id}/update")
async def update_draft(
    draft_id: int,
    body: str = Body(..., embed=True), # Expects {"body": "..."}
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update a draft's content (human edit).
    """
    draft = db.query(ReplyDraft).filter(ReplyDraft.id == draft_id).first()
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
        
    # Verify ownership via workspace -> user
    workspace = db.query(Workspace).filter(
        Workspace.id == draft.workspace_id, 
        Workspace.user_id == current_user.id
    ).first()
    
    if not workspace:
         raise HTTPException(status_code=403, detail="Not authorized")

    draft.body = body
    draft.status = DraftStatus.EDITED
    db.commit()
    db.refresh(draft)
    return draft


@router.post("/drafts/{draft_id}/send")
async def send_draft(
    draft_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Send a saved draft.
    """
    draft = db.query(ReplyDraft).filter(ReplyDraft.id == draft_id).first()
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")

    # Verify ownership
    workspace = db.query(Workspace).filter(
        Workspace.id == draft.workspace_id, 
        Workspace.user_id == current_user.id
    ).first()
    
    if not workspace:
         raise HTTPException(status_code=403, detail="Not authorized")
         
    if draft.status == DraftStatus.SENT:
        raise HTTPException(status_code=400, detail="Draft already sent")

    # Get Mailbox & Service
    mailbox = db.query(Mailbox).get(draft.mailbox_id)
    service, mailbox = GmailService.get_gmail_client(mailbox, db)
    
    if not service:
        raise HTTPException(status_code=401, detail="Mailbox auth failed")
        
    # Send
    # Fetch lead email to send to
    try:
        # Find original message to identify lead
        original_msg = db.query(Message).filter(Message.gmail_message_id == draft.gmail_message_id).first()
        if not original_msg:
            # Fallback to thread
            original_msg = db.query(Message).filter(Message.gmail_thread_id == draft.gmail_thread_id).first()
        
        if not original_msg or not original_msg.campaign_lead:
            raise ValueError("Could not find lead associated with this draft")
            
        lead_email = original_msg.campaign_lead.lead.email
        campaign_lead = original_msg.campaign_lead
        subject = build_reply_subject(original_msg.subject, fallback_subject=draft.subject)
        reply_to_thread_id = draft.gmail_thread_id or original_msg.gmail_thread_id
        reply_to_message_id = draft.gmail_message_id or original_msg.gmail_message_id
        
        credentials = GmailService.get_credentials_from_encrypted(
             mailbox.access_token_encrypted,
             mailbox.refresh_token_encrypted,
             mailbox.token_expiry
        )
        
        gmail_msg_id, gmail_thread_id = GmailService.send_email(
            credentials=credentials,
            to_email=lead_email,
            subject=subject,
            body=draft.body,
            reply_to_thread_id=reply_to_thread_id,
            reply_to_message_id=reply_to_message_id
        )
        
        from sqlalchemy import func
        min_step = db.query(func.min(Message.step_number)).filter(
            Message.campaign_lead_id == campaign_lead.id,
            Message.step_number < 0
        ).scalar()
        if min_step is None:
            next_step = -2
        else:
            next_step = min_step - 1

        # Record outbound
        new_msg = Message(
             campaign_lead_id=campaign_lead.id,
             direction=MessageDirection.OUTBOUND,
             step_number=next_step,
             gmail_message_id=gmail_msg_id,
             gmail_thread_id=gmail_thread_id,
             subject=subject,
             body=draft.body,
             sent_at=datetime.utcnow(),
             is_draft=False
        )
        db.add(new_msg)
        
        draft.status = DraftStatus.SENT
        db.commit()
        
        return {"status": "success", "message_id": gmail_msg_id}
        
    except Exception as e:
        logger.error(f"Send draft failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
