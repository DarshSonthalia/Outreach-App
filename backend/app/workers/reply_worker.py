"""
Reply worker - polls Gmail inbox for new replies.
Uses incremental sync via History API.
Runs every 2 minutes via Celery beat.

Fix Set A: Gmail History Cursor Reliability
Fix Set E: Bounce Heuristics with 2+ signals required
"""
import logging
from datetime import datetime

from app.celery_app import celery_app
from app.database import SessionLocal
from app.enums import MailboxStatus
from app.models import (
    Mailbox, Campaign, CampaignLead, Message, Event, Lead,
    CampaignStatus, CampaignLeadStatus, MessageDirection, 
    ReplyClassification, SuppressionReason
)
from app.services.gmail_service import GmailService
from app.services.classification_service import ClassificationService
from app.services.safety_service import SafetyService

logger = logging.getLogger(__name__)


@celery_app.task(name="app.workers.reply_worker.poll_all_mailboxes")
def poll_all_mailboxes():
    """
    Poll all active mailboxes for new replies.
    Uses incremental sync to minimize API usage.
    """
    db = SessionLocal()
    
    try:
        # Get all active mailboxes (not reauth_required)
        mailboxes = db.query(Mailbox).filter(
            Mailbox.is_active == True,
            Mailbox.status == MailboxStatus.ACTIVE,
            Mailbox.access_token_encrypted.isnot(None)
        ).all()
        
        logger.info(f"Polling {len(mailboxes)} mailboxes for replies")
        
        for mailbox in mailboxes:
            try:
                poll_single_mailbox(db, mailbox)
            except Exception as e:
                logger.error(f"Error polling mailbox {mailbox.email}: {e}")
                continue
        
        db.commit()
        
    except Exception as e:
        logger.error(f"Error in poll_all_mailboxes: {e}")
        db.rollback()
    finally:
        db.close()


def poll_single_mailbox(db, mailbox: Mailbox):
    """
    Fix A2: Poll a single mailbox using incremental sync.
    
    - Bootstrap: Sets history ID without scanning
    - Incremental: Only fetches new messages since last poll
    - Fix A3: Handles historyId too old by resetting cursor
    """
    logger.info(f"Polling mailbox {mailbox.email}, last_history_id: {mailbox.last_history_id}")
    
    # Get Gmail client with automatic token refresh
    service, mailbox = GmailService.get_gmail_client(mailbox, db)
    
    if not service:
        logger.warning(f"Could not get Gmail client for mailbox {mailbox.id} - may need reauth")
        return
    
    try:
        # Fix A2/A3: Poll inbox with proper history cursor handling
        new_messages, new_history_id = GmailService.poll_inbox_incremental(
            service,
            mailbox.last_history_id
        )
        
        # Update history ID and last polled time
        if new_history_id:
            mailbox.last_history_id = new_history_id
        mailbox.last_polled_at = datetime.utcnow()
        
        logger.info(f"Found {len(new_messages)} new messages for {mailbox.email}")
        
        # Process each new message
        for msg_data in new_messages:
            try:
                process_incoming_message(db, mailbox, msg_data)
            except Exception as e:
                logger.error(f"Error processing message {msg_data.get('id')}: {e}")
                continue
                
    except Exception as e:
        logger.error(f"Error polling mailbox {mailbox.email}: {e}")
        raise


def process_incoming_message(db, mailbox: Mailbox, msg_data: dict):
    """
    Process an incoming message - check if it's a reply to our campaign.
    
    Fix E1: Uses improved bounce detection requiring 2+ signals.
    """
    gmail_thread_id = msg_data.get("thread_id")
    gmail_message_id = msg_data.get("id")
    from_email = msg_data.get("from", "")
    subject = msg_data.get("subject", "")
    body = msg_data.get("body", "")
    
    # Extract just the email address from "Name <email@domain.com>" format
    import re
    email_match = re.search(r'[\w\.-]+@[\w\.-]+', from_email)
    sender_email = email_match.group(0).lower() if email_match else from_email.lower()
    
    # Check if this is a reply to one of our threads
    existing_outbound = db.query(Message).join(CampaignLead).join(Campaign).filter(
        Message.gmail_thread_id == gmail_thread_id,
        Message.direction == MessageDirection.OUTBOUND,
        Campaign.mailbox_id == mailbox.id
    ).first()
    
    if not existing_outbound:
        # Not a reply to our campaign
        return
    
    campaign_lead = existing_outbound.campaign_lead
    lead = campaign_lead.lead
    campaign = campaign_lead.campaign
    
    # Check if we already recorded this message
    existing_reply = db.query(Message).filter(
        Message.gmail_message_id == gmail_message_id
    ).first()
    
    if existing_reply:
        return
    
    logger.info(f"New reply detected from {sender_email} to campaign {campaign.id}")
    
    # Fix E1: Check if this is a bounce (heuristic with 2+ signals required)
    is_bounce, bounce_signal_count = ClassificationService.is_bounce_reply_strict(
        subject, body, from_email
    )
    
    if is_bounce:
        logger.warning(f"Detected potential bounce for {lead.email} ({bounce_signal_count} signals)")
        classification = ReplyClassification.UNKNOWN
        
        # Log as bounce event for safety tracking (labeled as heuristic)
        event = Event(
            entity_type="campaign_lead",
            entity_id=campaign_lead.id,
            action="bounce_detected_heuristic",
            details={
                "from": from_email,
                "subject": subject,
                "signal_count": bounce_signal_count,
            },
            explanation=f"[HEURISTIC] Possible bounce detected for {lead.email} ({bounce_signal_count} signals matched)"
        )
        db.add(event)
    else:
        # Classify the reply
        classification = ClassificationService.classify_reply(subject, body)
    
    # Record the reply (step_number = -1 for inbound)
    message = Message(
        campaign_lead_id=campaign_lead.id,
        direction=MessageDirection.INBOUND,
        step_number=-1,  # Inbound messages use -1
        gmail_message_id=gmail_message_id,
        gmail_thread_id=gmail_thread_id,
        subject=subject,
        body=body,
        classification=classification,
        received_at=datetime.utcnow()
    )
    db.add(message)
    
    # CRITICAL: Stop all future sends for this lead
    campaign_lead.status = CampaignLeadStatus.REPLIED
    campaign_lead.replied_at = datetime.utcnow()
    campaign_lead.next_action_at = None  # Cancel any scheduled sends
    
    # Handle based on classification
    if classification == ReplyClassification.UNSUBSCRIBE:
        # Add to permanent suppression list
        SafetyService.add_to_suppression(
            db,
            campaign.workspace_id,
            lead.email,
            SuppressionReason.UNSUBSCRIBE,
            f"Unsubscribed via reply to campaign {campaign.name}"
        )
        campaign_lead.status = CampaignLeadStatus.UNSUBSCRIBED
        
        logger.info(f"Lead {lead.email} unsubscribed and suppressed")
    
    # Log the reply event
    event = Event(
        entity_type="campaign_lead",
        entity_id=campaign_lead.id,
        action="reply_received",
        details={
            "from": sender_email,
            "subject": subject,
            "classification": classification.value if classification else None,
            "is_bounce": is_bounce
        },
        explanation=f"Reply received from {lead.email}. Classification: {classification.value if classification else 'unknown'}. All future sends stopped."
    )
    db.add(event)
    
    logger.info(f"Reply processed for {lead.email}, classification: {classification}")
