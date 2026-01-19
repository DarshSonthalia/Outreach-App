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
from app.enums import FollowupState, CancelReason
from app.services.gmail_service import GmailService, RateLimitError
from app.services.safety_service import SafetyService
from app.services.followup_service import FollowupService
from app.services.warmup_service import WarmupService
from app.utils.email import build_reply_subject

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
    Uses new followup_state and next_scheduled_at fields.
    """
    db = SessionLocal()
    
    try:
        now = datetime.utcnow()
        
        # Select leads where followup_state is SCHEDULED and time is due
        # Use SKIP LOCKED to prevent race conditions
        due_sends = db.execute(
            text("""
                SELECT id FROM campaign_leads
                WHERE followup_state = :scheduled_state
                AND next_scheduled_at <= :now
                AND next_scheduled_at IS NOT NULL
                AND campaign_id IN (
                    SELECT id FROM campaigns WHERE status = :running_status
                )
                ORDER BY next_scheduled_at
                LIMIT 50
                FOR UPDATE SKIP LOCKED
            """),
            {
                "now": now,
                "scheduled_state": FollowupState.SCHEDULED.value,
                "running_status": CampaignStatus.RUNNING.value
            }
        ).fetchall()
        
        claimed_ids = [row[0] for row in due_sends]
        
        if not claimed_ids:
            return
        
        # We don't necessarily need to change state to IN_PROGRESS if we lock rows transactionally, 
        # but to keep visibility or retry logic we might. 
        # However, the prompt says "D1) Due selection must ONLY include: campaign_leads.followup_state='SCHEDULED'".
        # If we change it to 'IN_PROGRESS' (if that existed in FollowupState) it would work.
        # But FollowupState only has SCHEDULED, CANCELLED, COMPLETED.
        # So we relying on transaction lock to hold it separate? 
        # Or we can assume the worker processes immediately.
        # Wait, if we commit early, lock is lost?
        # The original code updated to IN_PROGRESS status. 
        # We should stick to 'status' field for locking/working indication IF we want to persist "working" state, 
        # OR we rely on `next_scheduled_at` being updated AFTER send.
        # If we don't update something, next poll will pick it up again if we release lock.
        # So we MUST process inside the lock or update a field.
        # Since 'status' (CampaignLeadStatus) still exists and has 'IN_PROGRESS', let's use it for worker visibility, 
        # while 'followup_state' controls the business logic.
        
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
                    db.commit() # Commit each lead individually
                except Exception as e:
                    db.rollback()
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
    Process a single send.
    """
    # Fix D2: Logic pre-send reload
    db.refresh(campaign_lead)
    
    if campaign_lead.followup_state != FollowupState.SCHEDULED:
        logger.info(f"Skipping send for lead {campaign_lead.id}: state is {campaign_lead.followup_state}")
        # Log event
        db.add(Event(
            entity_type="campaign_lead",
            entity_id=campaign_lead.id,
            action="SEND_BLOCKED_FOLLOWUPS_CANCELLED",
            details={"reason": str(campaign_lead.cancel_reason)},
            explanation="Send blocked because follow-ups are not scheduled."
        ))
        return

    campaign = campaign_lead.campaign
    lead = campaign_lead.lead
    mailbox = campaign.mailbox
    
    # Calculate step number from current_step
    step_number = campaign_lead.current_step
    
    # Validation: Ensure we haven't exceeded max followups
    # Step 0 is not a follow-up. 
    # Steps 1..N are followups. 
    # Max allowed step is N? 
    # If max_followups is 2. Steps are 0, 1, 2. (Total 3 emails).
    if step_number > campaign.max_followups:
        # Should be completed already
        campaign_lead.followup_state = FollowupState.COMPLETED
        campaign_lead.next_scheduled_at = None
        return

    logger.info(f"Processing send for campaign_lead {campaign_lead.id}, lead {lead.email}, step {step_number}")
    
    # Idempotency check in Message table
    existing_message = db.query(Message).filter(
        Message.campaign_lead_id == campaign_lead.id,
        Message.step_number == step_number,
        Message.direction == MessageDirection.OUTBOUND,
        Message.is_draft == False  # Check only sent messages
    ).first()
    
    if existing_message:
        logger.info(f"Message already exists for step {step_number}, skipping (idempotent)")
        advance_to_next_step(db, campaign_lead, campaign)
        return
    
    # Safety checks
    safety_decision = SafetyService.run_all_safety_checks(
        db, campaign, campaign_lead, lead.email
    )
    
    if not safety_decision.can_send:
        logger.warning(f"Safety check failed: {safety_decision.reason}")
        if safety_decision.reason in ["suppressed", "already_replied"]:
            reason = CancelReason.SUPPRESSED if safety_decision.reason == "suppressed" else CancelReason.REPLIED
            FollowupService.cancel_followups(
                db,
                campaign_lead.id,
                reason,
                safety_decision.explanation
            )
            campaign_lead.status = CampaignLeadStatus.PENDING
            return
        # Delay (reschedule)
        # We update next_scheduled_at but keep state SCHEDULED
        delay_sec = safety_decision.delay_seconds or 3600
        campaign_lead.next_scheduled_at = datetime.utcnow() + timedelta(seconds=delay_sec)
        campaign_lead.status = CampaignLeadStatus.PENDING # Release lock logic
        return

    # Get Gmail client
    service, mailbox = GmailService.get_gmail_client(mailbox, db)
    if not service:
        # Handle reauth or error
        campaign_lead.next_scheduled_at = datetime.utcnow() + timedelta(minutes=30)
        campaign_lead.status = CampaignLeadStatus.PENDING
        return
        
    try:
        credentials = GmailService.get_credentials_from_encrypted(
            mailbox.access_token_encrypted,
            mailbox.refresh_token_encrypted,
            mailbox.token_expiry
        )
    except Exception as e:
        logger.error(f"Credentials error: {e}")
        GmailService._mark_reauth_required(db, mailbox, str(e))
        return

    # Content generation
    followup_templates = getattr(campaign, "followup_templates", None)
    is_followup = step_number > 0
    subject = campaign.subject
    body = campaign.body
    
    if is_followup:
        # Try to find template in followup_templates
        template = None
        if followup_templates:
            for t in followup_templates:
                if t.get("step") == step_number:
                    template = t
                    break
        
        if template:
            subject = template.get("subject") or campaign.followup_subject or campaign.subject
            body = template.get("body") or campaign.followup_body or campaign.body
        else:
            # Fallback to legacy fields
            subject = campaign.followup_subject or campaign.subject
            body = campaign.followup_body or campaign.body
        
    # Personalization
    if lead.first_name:
        body = body.replace("{{first_name}}", lead.first_name)
        subject = subject.replace("{{first_name}}", lead.first_name)
    if lead.company:
        body = body.replace("{{company}}", lead.company)
        subject = subject.replace("{{company}}", lead.company)

    # Threading
    thread_id = None
    reply_message_id = None
    thread_subject = None
    if is_followup:
        base_message = db.query(Message).filter(
            Message.campaign_lead_id == campaign_lead.id,
            Message.direction == MessageDirection.OUTBOUND,
            Message.step_number == 0,
            Message.is_draft == False
        ).order_by(Message.sent_at.asc()).first()
        if base_message:
            thread_id = base_message.gmail_thread_id
            reply_message_id = base_message.gmail_message_id
            thread_subject = base_message.subject

        if not thread_id or not reply_message_id or not thread_subject:
            last_outbound = db.query(Message).filter(
                Message.campaign_lead_id == campaign_lead.id,
                Message.direction == MessageDirection.OUTBOUND,
                Message.is_draft == False
            ).order_by(Message.sent_at.desc()).first()
            if last_outbound:
                thread_id = thread_id or last_outbound.gmail_thread_id
                reply_message_id = reply_message_id or last_outbound.gmail_message_id
                thread_subject = thread_subject or last_outbound.subject

        subject = build_reply_subject(thread_subject, fallback_subject=subject)

    # Send
    try:
        message_id, gmail_thread_id = GmailService.send_email(
            credentials,
            lead.email,
            subject,
            body,
            reply_to_thread_id=thread_id,
            reply_to_message_id=reply_message_id
        )
        
        # Create Message
        msg = Message(
            campaign_lead_id=campaign_lead.id,
            direction=MessageDirection.OUTBOUND,
            step_number=step_number,
            gmail_message_id=message_id,
            gmail_thread_id=gmail_thread_id,
            subject=subject,
            body=body,
            sent_at=datetime.utcnow(),
            is_draft=False,
            planned_send_at=campaign_lead.next_scheduled_at # The time it was supposed to send
        )
        db.add(msg)
        
        # Log event
        db.add(Event(
            entity_type="campaign_lead",
            entity_id=campaign_lead.id,
            action="email_sent",
            details={
                 "step": step_number,
                 "message_id": message_id
            },
            explanation=f"Step {step_number} sent to {lead.email}"
        ))

        # Update Lead State after success
        campaign_lead.last_sent_at = datetime.utcnow()
        campaign_lead.retry_count = 0
        campaign_lead.current_step += 1
        
        # Update schedule_json
        if not campaign_lead.schedule_json:
            # First time initialization if missing (backfill)
            campaign_lead.schedule_json = []
            
            # Step 0
            body_full = campaign.body or ""
            campaign_lead.schedule_json.append({
                "step": 0,
                "planned_at": None,
                "subject": campaign.subject,
                "body": body_full,
                "body_preview": (body_full[:100] + "...") if body_full else "",
                "status": "SENT" if step_number > 0 else "PENDING"
            })
            
            # Follow-ups (reconstruct planned steps)
            for i in range(1, campaign.max_followups + 1):
                body_full = campaign.followup_body or ""
                body_prev = (body_full[:100] + "...") if body_full else "Follow-up email"
                if followup_templates and len(followup_templates) >= i:
                    tmpl = followup_templates[i-1]
                    body_full = tmpl.get("body", "") or body_full
                    body_prev = (body_full[:100] + "...") if body_full else "Follow-up email"
                
                campaign_lead.schedule_json.append({
                    "step": i,
                    "planned_at": (campaign_lead.next_scheduled_at.isoformat() if i == step_number else None),
                    "subject": f"Re: {campaign.subject}",
                    "body": body_full,
                    "body_preview": body_prev,
                    "status": "SENT" if step_number > i else "PLANNED"
                })

        # Update specific step
        new_schedule = []
        for item in campaign_lead.schedule_json:
            if item.get("step") == step_number:
                item["status"] = "SENT"
                item["message_id"] = message_id
                item["sent_at"] = datetime.utcnow().isoformat()
                item["subject"] = subject
            new_schedule.append(item)
        campaign_lead.schedule_json = new_schedule
        
        advance_to_next_step(db, campaign_lead, campaign)

    except RateLimitError as e:
        logger.warning(f"Rate limited by Gmail API: {e}")
        campaign_lead.next_scheduled_at = datetime.utcnow() + timedelta(minutes=10)
        campaign_lead.status = CampaignLeadStatus.PENDING
        db.add(Event(
            entity_type="campaign_lead",
            entity_id=campaign_lead.id,
            action="SEND_DELAYED_RATE_LIMIT",
            details={"error": str(e)},
            explanation="Gmail rate limit hit. Send delayed."
        ))
    except Exception as e:
        logger.error(f"Send failed: {e}")
        handle_send_failure(db, campaign_lead, str(e))


def advance_to_next_step(db: Session, campaign_lead: CampaignLead, campaign: Campaign):
    """
    Calculate next schedule time or complete.
    """
    next_step = campaign_lead.current_step
    
    if next_step <= campaign.max_followups and campaign.followup_enabled:
        # Calculate when
        # If we have a planned time in schedule_json for this step, use it?
        # Or recompute based on delay?
        # Prompt says: "increment current_step ... set next_scheduled_at = planned_at of next PENDING step"
        
        planned_time = None
        if campaign_lead.schedule_json:
             for item in campaign_lead.schedule_json:
                 if item.get("step") == next_step:
                     planned_time_str = item.get("planned_at")
                     if planned_time_str:
                         try:
                             planned_time = datetime.fromisoformat(planned_time_str)
                         except:
                             pass
                     break
        
        if not planned_time:
            # Fallback compute
            delay_days = campaign.followup_delay_days
            planned_time = datetime.utcnow() + timedelta(days=delay_days)
            
        campaign_lead.next_scheduled_at = planned_time
        campaign_lead.followup_state = FollowupState.SCHEDULED
        # Also release status lock
        campaign_lead.status = CampaignLeadStatus.PENDING 
    else:
        campaign_lead.followup_state = FollowupState.COMPLETED
        campaign_lead.next_scheduled_at = None
        campaign_lead.status = CampaignLeadStatus.COMPLETED


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
        campaign_lead.next_scheduled_at = None
        
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
        campaign_lead.next_scheduled_at = campaign_lead.next_retry_at
        logger.info(f"Retry scheduled in {delay} minutes")
