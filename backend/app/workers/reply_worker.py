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
    Mailbox, Campaign, CampaignLead, Message, Event, Lead, Workspace,
    CampaignStatus, CampaignLeadStatus, MessageDirection, 
    ReplyClassification, SuppressionReason
)
from app.services.gmail_service import GmailService
from app.services.classification_service import ClassificationService
from app.services.safety_service import SafetyService
from app.services.followup_service import FollowupService
from app.enums import FollowupState, CancelReason

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
                db.commit()  # Commit after each mailbox to ensure data is saved
            except Exception as e:
                logger.error(f"Error polling mailbox {mailbox.email}: {e}")
                db.rollback()  # Rollback on error
                continue
        
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
                db.rollback()  # Rollback transaction on error to recover session state
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
    # IMPORTANT: Search across ALL campaigns in the mailbox's workspace
    # (not just campaigns tied to this specific mailbox)
    # This ensures replies are detected regardless of which mailbox sent the original email
    existing_outbound = db.query(Message).join(CampaignLead).join(Campaign).join(Workspace).filter(
        Message.gmail_thread_id == gmail_thread_id,
        Message.direction == MessageDirection.OUTBOUND,
        Workspace.id == mailbox.workspace_id
    ).first()
    
    if not existing_outbound:
        # Not a reply to our campaign
        return
    
    campaign_lead = existing_outbound.campaign_lead
    lead = campaign_lead.lead
    campaign = campaign_lead.campaign
    
    # Check if we already recorded THIS EXACT message (by Gmail message ID)
    # This prevents duplicate processing of the same email
    existing_reply = db.query(Message).filter(
        Message.gmail_message_id == gmail_message_id
    ).first()
    
    if existing_reply:
        logger.info(f"Message {gmail_message_id} already processed, skipping")
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
    
    # Calculate next step_number for inbound messages
    # Inbound messages use negative step numbers (-1, -2, -3, etc.) for ordering
    max_inbound_step = db.query(Message).filter(
        Message.campaign_lead_id == campaign_lead.id,
        Message.direction == MessageDirection.INBOUND
    ).count()
    next_step_number = -(max_inbound_step + 1)  # -1 for first reply, -2 for second, etc.
    
    # Record the reply with incrementing step_number to allow multiple replies
    message = Message(
        campaign_lead_id=campaign_lead.id,
        direction=MessageDirection.INBOUND,
        step_number=next_step_number,  # Allows multiple replies per campaign_lead
        gmail_message_id=gmail_message_id,
        gmail_thread_id=gmail_thread_id,
        subject=subject,
        body=body,
        classification=classification,
        received_at=datetime.utcnow(),
        is_draft=False  # Inbound is never a draft
    )
    db.add(message)
    db.flush() # Persist to get ID
    
    # Handle Bounce logic
    if is_bounce:
        FollowupService.cancel_followups(
            db, 
            campaign_lead.id, 
            CancelReason.BOUNCE, 
            f"Heuristic bounce detected ({bounce_signal_count} signals)"
        )
    else:
        # Apply Inbound Signal (Auto-cancel if needed)
        # Check for OOO? existing classifier might return 'OUT_OF_OFFICE' if implemented?
        # Prompt: "Determine out-of-office (if supported)"
        # ClassificationService currently supports: UNSUBSCRIBE, NEGATIVE, NEUTRAL, BOOKING_INTENT, OUT_OF_OFFICE (if added).
        # We assume ClassificationService returns valid enum.
        
        is_ooo = (classification == ReplyClassification.OUT_OF_OFFICE)
        FollowupService.apply_inbound_signal(db, message, is_out_of_office=is_ooo)
    
    # Additional Actions (Suppression)
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
    else:
        # Just mark status as REPLIED (legacy status field update)
        campaign_lead.status = CampaignLeadStatus.REPLIED
        campaign_lead.replied_at = datetime.utcnow()
    
    logger.info(f"Reply processed for {lead.email}, classification: {classification}")
