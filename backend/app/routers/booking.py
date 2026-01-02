"""
Booking router - Calendly webhook integration.

Fix Set C: Webhook Verification and Idempotency
"""
import hmac
import hashlib
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Request, Header
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import Optional
from datetime import datetime

from app.database import get_db
from app.config import settings
from app.models import (
    Campaign, CampaignLead, Lead, Event, BookingEvent,
    CampaignLeadStatus, ReplyClassification
)

router = APIRouter()
logger = logging.getLogger(__name__)


def verify_calendly_signature(body: bytes, signature: str, timestamp: str = None) -> bool:
    """
    Fix C1: Verify Calendly webhook signature.
    
    Calendly uses HMAC-SHA256 for signature verification.
    The signature header format is typically: t=<timestamp>,v1=<signature>
    """
    if not settings.calendly_webhook_secret:
        logger.warning("CALENDLY_WEBHOOK_SECRET not configured - skipping verification")
        return True
    
    if not signature:
        return False
    
    try:
        # Calendly signature format: v1,<signature> or just the signature
        if signature.startswith("v1,"):
            signature = signature[3:]
        
        # Handle format with timestamp: t=<timestamp>,v1=<signature>
        if ",v1=" in signature:
            parts = signature.split(",v1=")
            signature = parts[1] if len(parts) > 1 else signature
        
        expected_signature = hmac.new(
            settings.calendly_webhook_secret.encode(),
            body,
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(signature, expected_signature)
    except Exception as e:
        logger.error(f"Signature verification error: {e}")
        return False


def get_event_uuid(payload: dict) -> Optional[str]:
    """Extract unique event UUID from Calendly payload."""
    # Calendly sends a unique URI/UUID for each event
    event_data = payload.get("payload", {})
    
    # Try to get URI from invitee or event
    invitee_uri = event_data.get("invitee", {}).get("uri", "")
    event_uri = event_data.get("event", {}).get("uri", "")
    
    # Combine event type with URI for uniqueness
    event_type = payload.get("event", "")
    
    if invitee_uri:
        return f"{event_type}:{invitee_uri}"
    elif event_uri:
        return f"{event_type}:{event_uri}"
    
    return None


def compute_payload_hash(payload: dict) -> str:
    """Compute hash of payload for dedup verification."""
    import json
    payload_str = json.dumps(payload, sort_keys=True)
    return hashlib.sha256(payload_str.encode()).hexdigest()


@router.post("/calendly-webhook")
async def calendly_webhook(
    request: Request,
    db: Session = Depends(get_db),
    calendly_webhook_signature: Optional[str] = Header(None, alias="Calendly-Webhook-Signature")
):
    """
    Handle Calendly webhook events.
    
    Fix C1: Verifies webhook signature before processing.
    Fix C2: Implements idempotency using BookingEvent table.
    
    Triggered when a meeting is booked or canceled.
    """
    body = await request.body()
    
    # Fix C1: Verify webhook signature
    if settings.calendly_webhook_secret:
        if not calendly_webhook_signature:
            logger.warning("Calendly webhook received without signature")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing webhook signature"
            )
        
        if not verify_calendly_signature(body, calendly_webhook_signature):
            logger.warning("Calendly webhook signature verification failed")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid webhook signature"
            )
    
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload"
        )
    
    event_type = payload.get("event")
    event_data = payload.get("payload", {})
    
    logger.info(f"Received Calendly webhook: {event_type}")
    
    # Fix C2: Check idempotency - extract event UUID
    event_uuid = get_event_uuid(payload)
    if not event_uuid:
        logger.warning("Could not extract event UUID from Calendly payload")
        # Still process but log warning
        event_uuid = f"{event_type}:{datetime.utcnow().isoformat()}"
    
    # Check if we've already processed this event
    existing = db.query(BookingEvent).filter(
        BookingEvent.calendly_event_uuid == event_uuid
    ).first()
    
    if existing:
        logger.info(f"Duplicate webhook detected, ignoring: {event_uuid}")
        return {"status": "ok", "message": "duplicate event ignored"}
    
    # Get invitee info
    invitee = event_data.get("invitee", {})
    invitee_email = invitee.get("email", "").lower()
    event_info = event_data.get("event", {})
    start_time_str = event_info.get("start_time")
    
    # Parse start time
    event_start_time = None
    if start_time_str:
        try:
            event_start_time = datetime.fromisoformat(start_time_str.replace("Z", "+00:00"))
        except ValueError:
            pass
    
    # Determine workspace from lead
    workspace_id = None
    if invitee_email:
        lead = db.query(Lead).filter(Lead.email == invitee_email).first()
        if lead:
            workspace_id = lead.workspace_id
    
    # Create BookingEvent for idempotency (Fix C2)
    try:
        booking_event = BookingEvent(
            workspace_id=workspace_id or 1,  # Default to 1 if not found
            calendly_event_uuid=event_uuid,
            event_type=event_type,
            invitee_email=invitee_email,
            event_start_time=event_start_time,
            payload_hash=compute_payload_hash(payload)
        )
        db.add(booking_event)
        db.flush()  # Get any constraint errors early
    except IntegrityError:
        # Race condition - another request already processed this
        db.rollback()
        logger.info(f"Race condition detected for webhook: {event_uuid}")
        return {"status": "ok", "message": "duplicate event ignored"}
    
    # Handle invitee.created event (meeting booked)
    if event_type == "invitee.created":
        invitee_name = invitee.get("name", "")
        event_name = event_info.get("name", "Meeting")
        
        if invitee_email:
            lead = db.query(Lead).filter(Lead.email == invitee_email).first()
            
            if lead:
                campaign_lead = db.query(CampaignLead).filter(
                    CampaignLead.lead_id == lead.id
                ).first()
                
                if campaign_lead:
                    campaign_lead.status = CampaignLeadStatus.COMPLETED
                    campaign_lead.next_action_at = None
                    
                    audit_event = Event(
                        entity_type="campaign_lead",
                        entity_id=campaign_lead.id,
                        action="meeting_booked",
                        details={
                            "event_name": event_name,
                            "start_time": start_time_str,
                            "invitee_email": invitee_email,
                            "invitee_name": invitee_name,
                            "source": "calendly"
                        },
                        explanation=f"Meeting booked via Calendly: {event_name}"
                    )
                    db.add(audit_event)
                    logger.info(f"Meeting booked for lead {invitee_email}")
    
    # Handle invitee.canceled event
    elif event_type == "invitee.canceled":
        if invitee_email:
            lead = db.query(Lead).filter(Lead.email == invitee_email).first()
            
            if lead:
                campaign_lead = db.query(CampaignLead).filter(
                    CampaignLead.lead_id == lead.id
                ).first()
                
                if campaign_lead:
                    audit_event = Event(
                        entity_type="campaign_lead",
                        entity_id=campaign_lead.id,
                        action="meeting_canceled",
                        details={"invitee_email": invitee_email, "source": "calendly"},
                        explanation="Meeting canceled via Calendly"
                    )
                    db.add(audit_event)
                    logger.info(f"Meeting canceled for lead {invitee_email}")
    
    db.commit()
    return {"status": "ok"}


@router.get("/setup-info")
async def get_calendly_setup_info():
    """
    Get information for setting up Calendly webhook.
    """
    return {
        "webhook_url": f"{settings.backend_url}/api/booking/calendly-webhook",
        "events_to_subscribe": [
            "invitee.created",
            "invitee.canceled"
        ],
        "signature_header": "Calendly-Webhook-Signature",
        "instructions": """
To set up Calendly webhook integration:

1. Go to Calendly dashboard → Integrations → Webhooks
2. Click "Create Webhook Subscription"
3. Enter the webhook URL shown above
4. Select events: invitee.created, invitee.canceled
5. Copy the signing key and add to your .env as CALENDLY_WEBHOOK_SECRET
6. Click "Create Webhook"

When a meeting is booked, the system will:
- Mark the lead as completed
- Stop any scheduled follow-ups
- Log the booking event with details

Security:
- Webhook signature is verified using HMAC-SHA256
- Duplicate webhooks are idempotently handled
"""
    }
