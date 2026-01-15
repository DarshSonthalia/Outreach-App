from datetime import datetime, timedelta
from sqlalchemy import or_, and_
from sqlalchemy.orm import Session
from app.models.models import CampaignLead, Message, Event, ReplyClassification
from app.enums import FollowupState, CancelReason, MessageDirection
from app.config import settings

class FollowupService:
    @staticmethod
    def cancel_followups(
        db: Session,
        campaign_lead_id: int,
        reason: CancelReason | str,
        detail: str,
        source_event: Event = None
    ):
        """
        Idempotent cancellation of follow-ups.
        """
        lead = db.query(CampaignLead).filter(CampaignLead.id == campaign_lead_id).with_for_update().first()
        if not lead:
            return

        # Idempotency check
        if lead.followup_state in [FollowupState.CANCELLED, FollowupState.COMPLETED]:
            return

        # Update Lead State
        lead.followup_state = FollowupState.CANCELLED
        lead.cancelled_at = datetime.utcnow()
        lead.cancel_reason = reason
        lead.cancel_detail = detail
        lead.next_scheduled_at = None

        # Update schedule_json if exists
        if lead.schedule_json:
            updated_schedule = []
            for item in lead.schedule_json:
                if item.get("status") == "PENDING":
                    item["status"] = "CANCELLED"
                updated_schedule.append(item)
            lead.schedule_json = updated_schedule

        # Cancel any PENDING outbound messages (if any exist in queue, though we usually generate JIT)
        # But if we pre-generated draft or queued messages, cancel them.
        pending_msgs = db.query(Message).filter(
            Message.campaign_lead_id == campaign_lead_id,
            Message.direction == MessageDirection.OUTBOUND,
            Message.sent_at.is_(None),
            Message.cancelled.is_(False)
        ).all()
        
        for msg in pending_msgs:
            msg.cancelled = True
            msg.cancel_reason = str(reason)

        # Log Event
        source_event_id = source_event.id if source_event else None
        db.add(Event(
            entity_type="campaign_lead",
            entity_id=campaign_lead_id,
            action="FOLLOWUPS_CANCELLED",
            details={
                "reason": str(reason),
                "detail": detail,
                "source_event_id": source_event_id
            },
            explanation=f"Follow-ups cancelled due to {reason}"
        ))
        
        db.commit()

    @staticmethod
    def should_stop_followups(
        classification: ReplyClassification,
        is_out_of_office: bool = False
    ) -> bool:
        """
        Determine if follow-ups should be stopped based on reply classification.
        """
        # Rules:
        # - UNSUBSCRIBE => stop
        # - NEGATIVE => stop
        # - BOOKING_INTENT => stop
        # - REPLIED (Any inbound reply) => stop, UNLESS is_out_of_office
        
        if classification == ReplyClassification.UNSUBSCRIBE:
            return True
        if classification == ReplyClassification.NEGATIVE:
            return True
        if classification == ReplyClassification.BOOKING_INTENT:
            return True
        
        # OOO check: If OOO, do NOT stop (unless also classified as Unsubscribe/Negative which is rare)
        if is_out_of_office:
            return False
            
        # Any other reply (NEUTRAL, QUESTION, INTERESTED, UNKNOWN) should stop follow-ups
        # The prompt says: "Any inbound reply => stop (REPLIED) EXCEPT if is_out_of_office=True"
        return True

    @staticmethod
    def apply_inbound_signal(
        db: Session,
        inbound_message: Message,
        is_out_of_office: bool = False
    ):
        """
        Apply logic when an inbound reply is received.
        """
        if not inbound_message.campaign_lead_id:
            return

        should_stop = FollowupService.should_stop_followups(
            inbound_message.classification,
            is_out_of_office
        )

        if should_stop:
            reason = CancelReason.REPLIED
            if inbound_message.classification == ReplyClassification.UNSUBSCRIBE:
                reason = CancelReason.UNSUBSCRIBE
            elif inbound_message.classification == ReplyClassification.NEGATIVE:
                reason = CancelReason.NEGATIVE_REPLY
            elif inbound_message.classification == ReplyClassification.BOOKING_INTENT:
                reason = CancelReason.BOOKED
            
            detail = f"Received reply classified as {inbound_message.classification}"
            
            FollowupService.cancel_followups(
                db,
                inbound_message.campaign_lead_id,
                reason,
                detail
            )
            
            # Log specific REPLY_RECEIVED event with stop flag
            db.add(Event(
                entity_type="lead",
                entity_id=inbound_message.campaign_lead.lead_id if inbound_message.campaign_lead else 0, # Best effort
                action="REPLY_RECEIVED",
                details={
                    "classification": str(inbound_message.classification),
                    "stopped_followups": True,
                    "message_id": inbound_message.id
                },
                explanation=f"Reply received ({inbound_message.classification}), follow-ups stopped."
            ))
            db.commit()
        else:
             db.add(Event(
                entity_type="lead",
                entity_id=inbound_message.campaign_lead.lead_id if inbound_message.campaign_lead else 0,
                action="REPLY_RECEIVED",
                details={
                    "classification": str(inbound_message.classification),
                    "stopped_followups": False,
                    "is_out_of_office": True
                },
                explanation=f"Reply received ({inbound_message.classification}), is OOO. Follow-ups continue."
            ))
             db.commit()
