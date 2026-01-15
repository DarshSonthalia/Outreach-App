"""
Booking router - Calendly webhook integration.
"""
import hmac
import hashlib
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Request, Header
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.database import get_db
from app.config import settings
from app.models import (
    Campaign, CampaignLead, Lead, Event, BookingEvent, Message, MessageDirection
)
from app.services.followup_service import FollowupService
from app.enums import CancelReason, CampaignStatus

router = APIRouter()
logger = logging.getLogger(__name__)


def verify_calendly_signature(body: bytes, signature: str, secret: str) -> bool:
    """
    Verify Calendly webhook signature (HMAC-SHA256).
    Signature header format is typically: t=<timestamp>,v1=<signature>
    """
    if not signature:
        return False

    try:
        if ",v1=" in signature:
            parts = signature.split(",v1=")
            signature = parts[1] if len(parts) > 1 else signature
        elif signature.startswith("v1,"):
            signature = signature[3:]

        expected_signature = hmac.new(
            secret.encode(),
            body,
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(signature, expected_signature)
    except Exception as e:
        logger.error(f"Signature verification error: {e}")
        return False


def get_event_uuid(payload: dict) -> Optional[str]:
    """Extract unique event UUID from Calendly payload."""
    event_data = payload.get("payload", {})

    event_uuid = event_data.get("event", {}).get("uuid")
    invitee_uuid = event_data.get("invitee", {}).get("uuid")

    if event_uuid:
        return event_uuid
    if invitee_uuid:
        return invitee_uuid

    invitee_uri = event_data.get("invitee", {}).get("uri", "")
    event_uri = event_data.get("event", {}).get("uri", "")
    event_type = payload.get("event", "")

    if invitee_uri:
        return f"{event_type}:{invitee_uri}"
    if event_uri:
        return f"{event_type}:{event_uri}"

    return None


@router.post("/calendly-webhook")
async def calendly_webhook(
    request: Request,
    db: Session = Depends(get_db),
    calendly_webhook_signature: Optional[str] = Header(None, alias="Calendly-Webhook-Signature")
):
    """
    Handle Calendly webhook events.
    """
    body = await request.body()

    if not settings.calendly_webhook_secret:
        logger.warning("CALENDLY_WEBHOOK_SECRET not configured - rejecting webhook")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Webhook signing secret not configured"
        )

    if not calendly_webhook_signature:
        logger.warning("Calendly webhook received without signature")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing webhook signature"
        )

    if not verify_calendly_signature(body, calendly_webhook_signature, settings.calendly_webhook_secret):
        logger.warning("Calendly webhook signature verification failed")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
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

    event_uuid = get_event_uuid(payload)
    if not event_uuid:
        logger.warning("Could not extract event UUID from Calendly payload")
        event_uuid = f"{event_type}:{datetime.utcnow().isoformat()}"

    existing = db.query(BookingEvent).filter(
        BookingEvent.calendly_event_uuid == event_uuid
    ).first()

    if existing:
        logger.info(f"Duplicate webhook detected, ignoring: {event_uuid}")
        return {"status": "ok", "message": "duplicate event ignored"}

    invitee_email = event_data.get("invitee", {}).get("email", "").lower()
    lead = None
    workspace_id = None
    mailbox_id = None
    campaign_lead_ids = []

    if invitee_email:
        lead = db.query(Lead).filter(Lead.email == invitee_email).first()
        if lead:
            workspace_id = lead.workspace_id

    if event_type == "invitee.created" and lead:
        recent_context = db.query(Message).join(CampaignLead).filter(
            CampaignLead.lead_id == lead.id,
            Message.direction == MessageDirection.OUTBOUND
        ).order_by(Message.sent_at.desc().nullslast()).first()

        if recent_context:
            campaign_lead_ids = [recent_context.campaign_lead_id]
            mailbox_id = recent_context.campaign_lead.campaign.mailbox_id
        else:
            campaign_leads = db.query(CampaignLead).join(Campaign).filter(
                CampaignLead.lead_id == lead.id,
                Campaign.status.in_([CampaignStatus.RUNNING, CampaignStatus.THROTTLED, CampaignStatus.PAUSED])
            ).all()
            campaign_lead_ids = [cl.id for cl in campaign_leads]
            if campaign_leads:
                mailbox_id = campaign_leads[0].campaign.mailbox_id

    try:
        booking_event = BookingEvent(
            workspace_id=workspace_id,
            mailbox_id=mailbox_id,
            calendly_event_uuid=event_uuid,
            event_type=event_type,
            invitee_email=invitee_email,
            payload=payload
        )
        db.add(booking_event)
        db.flush()
    except IntegrityError:
        db.rollback()
        logger.info(f"Race condition detected for webhook: {event_uuid}")
        return {"status": "ok", "message": "duplicate event ignored"}

    if event_type == "invitee.created" and invitee_email and lead:
        for cl_id in campaign_lead_ids:
            FollowupService.cancel_followups(
                db,
                cl_id,
                CancelReason.BOOKED,
                f"Calendly booking confirmed: {event_uuid}"
            )

        db.add(Event(
            entity_type="lead",
            entity_id=lead.id if lead else 0,
            action="BOOKING_CONFIRMED",
            details={
                "uuid": event_uuid,
                "invitee_email": invitee_email,
                "campaign_lead_ids": campaign_lead_ids
            },
            explanation="Calendly booking confirmed"
        ))

    if event_type == "invitee.canceled" and invitee_email:
        db.add(Event(
            entity_type="lead",
            entity_id=lead.id if lead else 0,
            action="BOOKING_CANCELED",
            details={"uuid": event_uuid, "invitee_email": invitee_email},
            explanation="Calendly booking canceled"
        ))

    db.commit()
    return {"status": "ok"}


@router.get("/setup-info")
async def get_calendly_setup_info():
    """
    Get information for setting up Calendly webhook.
    """
    return {
        "webhook_url": f"{settings.app_public_base_url}/api/booking/calendly-webhook",
        "required_events": ["invitee.created", "invitee.canceled"],
        "signature_header_name": "Calendly-Webhook-Signature",
        "notes": ["Enable signing secret", "Use HTTPS only"]
    }
