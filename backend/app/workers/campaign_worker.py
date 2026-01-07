"""
Campaign worker - processes scheduled sends and follow-ups.
Runs every minute via Celery beat.

Fix Set D: Idempotency and Double-Send Prevention
- D1: Atomic claiming with SELECT FOR UPDATE SKIP LOCKED
- D2: step_number unique constraint prevents duplicates
- D3: Retry safety with IN_PROGRESS status
"""
import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.celery_app import celery_app
from app.database import SessionLocal
from app.models import (
    Campaign, CampaignLead, Lead, Message, Event, Mailbox,
    CampaignStatus, CampaignLeadStatus, MessageDirection
)
from app.services.gmail_service import GmailService
from app.services.safety_service import SafetyService

logger = logging.getLogger(__name__)

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAY_MINUTES = 30


@celery_app.task(name="app.workers.campaign_worker.process_due_sends")
def process_due_sends():
    """
    Process all campaign sends that are due.
    Runs every minute.
    
    Fix D1: Uses SELECT FOR UPDATE SKIP LOCKED for atomic claiming.
    
    For each due send:
    1. Atomically claim the row (PENDING -> IN_PROGRESS)
    2. Run ALL safety checks (MANDATORY)
    3. Check idempotency (step_number)
    4. If safe: send email via Gmail API
    5. Log the send
    6. Schedule follow-up if enabled
    """
    db = SessionLocal()
    
    try:
        now = datetime.utcnow()
        
        # Fix D1: Atomic claiming with FOR UPDATE SKIP LOCKED
        # This prevents multiple workers from processing the same row
        due_sends = db.execute(
            text("""
                SELECT id FROM campaign_leads
                WHERE status = :pending_status
                AND next_action_at <= :now
                AND next_action_at IS NOT NULL
                AND campaign_id IN (
                    SELECT id FROM campaigns WHERE status = :running_status
                )
                ORDER BY next_action_at
                LIMIT 50
                FOR UPDATE SKIP LOCKED
            """),
            {
                "now": now,
                "pending_status": CampaignLeadStatus.PENDING.value,
                "running_status": CampaignStatus.RUNNING.value
            }
        ).fetchall()
        
        claimed_ids = [row[0] for row in due_sends]
        
        if not claimed_ids:
            return
        
        # Transition to IN_PROGRESS atomically
        db.execute(
            text("""
                UPDATE campaign_leads 
                SET status = :in_progress_status, updated_at = :now
                WHERE id = ANY(:ids)
            """),
            {
                "now": now, 
                "ids": claimed_ids,
                "in_progress_status": CampaignLeadStatus.IN_PROGRESS.value
            }
        )
        db.commit()
        
        logger.info(f"Claimed {len(claimed_ids)} sends for processing")
        
        # Process each claimed row
        for cl_id in claimed_ids:
            campaign_lead = db.query(CampaignLead).get(cl_id)
            if campaign_lead:
                try:
                    process_single_send(db, campaign_lead)
                except Exception as e:
                    logger.error(f"Error processing campaign_lead {cl_id}: {e}")
                    handle_send_failure(db, campaign_lead, str(e))
        
        db.commit()
        
    except Exception as e:
        logger.error(f"Error in process_due_sends: {e}")
        db.rollback()
    finally:
        db.close()


def process_single_send(db: Session, campaign_lead: CampaignLead):
    """
    Process a single send with full safety checks.
    
    Fix D2: Checks idempotency via step_number before sending.
    Fix D3: Handles retries with retry_count tracking.
    """
    campaign = campaign_lead.campaign
    lead = campaign_lead.lead
    mailbox = campaign.mailbox
    
    # Calculate step number (0 = initial, 1+ = follow-ups)
    step_number = campaign_lead.followup_count
    
    logger.info(f"Processing send for campaign_lead {campaign_lead.id}, lead {lead.email}, step {step_number}")
    
    # Fix D2: Idempotency check - see if we already sent this step
    existing_message = db.query(Message).filter(
        Message.campaign_lead_id == campaign_lead.id,
        Message.step_number == step_number,
        Message.direction == MessageDirection.OUTBOUND
    ).first()
    
    if existing_message:
        logger.info(f"Message already exists for step {step_number}, skipping (idempotent)")
        # Move to next step or complete
        advance_to_next_step(db, campaign_lead, campaign)
        return
    
    # Run ALL safety checks (MANDATORY)
    safety_decision = SafetyService.run_all_safety_checks(
        db, campaign, campaign_lead, lead.email
    )
    
    if not safety_decision.can_send:
        logger.warning(f"Safety check failed: {safety_decision.reason}")
        
        # Delay the send, reset to PENDING
        campaign_lead.status = CampaignLeadStatus.PENDING
        if safety_decision.delay_seconds:
            campaign_lead.next_action_at = datetime.utcnow() + timedelta(
                seconds=safety_decision.delay_seconds
            )
        else:
            campaign_lead.next_action_at = datetime.utcnow() + timedelta(hours=1)
        
        return
    
    # Get Gmail client with auto-refresh
    service, mailbox = GmailService.get_gmail_client(mailbox, db)
    
    if not service:
        logger.error(f"Failed to get Gmail client for mailbox {mailbox.id}")
        campaign_lead.status = CampaignLeadStatus.PENDING
        campaign_lead.next_action_at = datetime.utcnow() + timedelta(minutes=30)
        return
    
    # Get credentials for sending (service already has them)
    try:
        credentials = GmailService.get_credentials_from_encrypted(
            mailbox.access_token_encrypted,
            mailbox.refresh_token_encrypted,
            mailbox.token_expiry
        )
    except ValueError as e:
        # Token refresh failed or decryption failed
        logger.error(f"Failed to get credentials for mailbox {mailbox.id}: {e}")
        
        # Check if this is a token refresh failure
        if "Token refresh failed" in str(e) or "Failed to decrypt" in str(e):
            # Mark mailbox as needing reauth and pause campaigns
            GmailService._mark_reauth_required(db, mailbox, str(e))
            return
        
        # Otherwise, just delay the send
        campaign_lead.status = CampaignLeadStatus.PENDING
        campaign_lead.next_action_at = datetime.utcnow() + timedelta(minutes=30)
        return
    except Exception as e:
        logger.error(f"Unexpected error getting credentials: {e}")
        campaign_lead.status = CampaignLeadStatus.PENDING
        campaign_lead.next_action_at = datetime.utcnow() + timedelta(minutes=30)
        return
    
    # Determine email content
    is_followup = step_number > 0
    
    if is_followup:
        subject = campaign.followup_subject or campaign.subject
        body = campaign.followup_body or campaign.body
    else:
        subject = campaign.subject
        body = campaign.body
    
    # Personalize
    if lead.first_name:
        body = body.replace("{{first_name}}", lead.first_name)
        subject = subject.replace("{{first_name}}", lead.first_name)
    if lead.company:
        body = body.replace("{{company}}", lead.company)
        subject = subject.replace("{{company}}", lead.company)
    
    # Get thread ID for follow-ups
    thread_id = None
    if is_followup:
        prev_message = db.query(Message).filter(
            Message.campaign_lead_id == campaign_lead.id,
            Message.direction == MessageDirection.OUTBOUND
        ).order_by(Message.sent_at.desc()).first()
        
        if prev_message:
            thread_id = prev_message.gmail_thread_id
    
    # Send email via Gmail API
    try:
        message_id, gmail_thread_id = GmailService.send_email(
            credentials,
            lead.email,
            subject,
            body,
            reply_to_thread_id=thread_id
        )
        
        logger.info(f"Email sent: {message_id} to {lead.email}")
        
        # Fix D2: Record the message with step_number for idempotency
        try:
            message = Message(
                campaign_lead_id=campaign_lead.id,
                direction=MessageDirection.OUTBOUND,
                step_number=step_number,
                gmail_message_id=message_id,
                gmail_thread_id=gmail_thread_id,
                subject=subject,
                body=body,
                sent_at=datetime.utcnow()
            )
            db.add(message)
            db.flush()  # Check unique constraint
        except IntegrityError:
            # Duplicate - another worker sent this already
            db.rollback()
            logger.info(f"Duplicate message detected for step {step_number}, another worker handled it")
            advance_to_next_step(db, campaign_lead, campaign)
            return
        
        # Log event
        event = Event(
            entity_type="campaign_lead",
            entity_id=campaign_lead.id,
            action="email_sent",
            details={
                "to": lead.email,
                "subject": subject,
                "message_id": message_id,
                "thread_id": gmail_thread_id,
                "step_number": step_number,
                "is_followup": is_followup,
            },
            explanation=f"Email {'follow-up ' if is_followup else ''}sent to {lead.email}"
        )
        db.add(event)
        
        # Update campaign lead status
        campaign_lead.last_sent_at = datetime.utcnow()
        campaign_lead.retry_count = 0  # Reset on success
        
        # Advance to next step
        advance_to_next_step(db, campaign_lead, campaign)
        
    except Exception as e:
        logger.error(f"Failed to send email to {lead.email}: {e}")
        handle_send_failure(db, campaign_lead, str(e))


def advance_to_next_step(db: Session, campaign_lead: CampaignLead, campaign: Campaign):
    """Advance campaign lead to next follow-up or complete."""
    if campaign.followup_enabled and campaign_lead.followup_count < campaign.max_followups:
        campaign_lead.followup_count += 1
        campaign_lead.status = CampaignLeadStatus.PENDING
        campaign_lead.next_action_at = datetime.utcnow() + timedelta(
            days=campaign.followup_delay_days
        )
        logger.info(f"Follow-up scheduled in {campaign.followup_delay_days} days")
    else:
        campaign_lead.status = CampaignLeadStatus.COMPLETED
        campaign_lead.next_action_at = None


def handle_send_failure(db: Session, campaign_lead: CampaignLead, error: str):
    """
    Fix D3: Handle send failure with retry logic.
    """
    campaign_lead.retry_count += 1
    
    # Log failure event
    event = Event(
        entity_type="campaign_lead",
        entity_id=campaign_lead.id,
        action="email_send_failed",
        details={"error": error, "retry_count": campaign_lead.retry_count},
        explanation=f"Failed to send email (attempt {campaign_lead.retry_count}): {error}"
    )
    db.add(event)
    
    if campaign_lead.retry_count >= MAX_RETRIES:
        # Max retries exceeded, mark as failed
        campaign_lead.status = CampaignLeadStatus.COMPLETED
        campaign_lead.next_action_at = None
        
        event = Event(
            entity_type="campaign_lead",
            entity_id=campaign_lead.id,
            action="email_send_max_retries",
            details={"error": error},
            explanation=f"Max retries ({MAX_RETRIES}) exceeded for sending"
        )
        db.add(event)
        logger.warning(f"Max retries exceeded for campaign_lead {campaign_lead.id}")
    else:
        # Schedule retry with exponential backoff
        delay = RETRY_DELAY_MINUTES * (2 ** (campaign_lead.retry_count - 1))
        campaign_lead.status = CampaignLeadStatus.PENDING
        campaign_lead.next_retry_at = datetime.utcnow() + timedelta(minutes=delay)
        campaign_lead.next_action_at = campaign_lead.next_retry_at
        logger.info(f"Retry scheduled in {delay} minutes")
