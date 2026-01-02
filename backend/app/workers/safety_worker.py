"""
Safety worker - periodic risk assessment and auto-pause.
Runs every 5 minutes via Celery beat.
"""
import logging
from datetime import datetime, date, timedelta

from app.celery_app import celery_app
from app.database import SessionLocal
from app.config import safety_config
from app.models import (
    Domain, RiskSnapshot, Campaign, CampaignLead, Message, Event,
    CampaignStatus, MessageDirection
)
from app.services.safety_service import SafetyService

logger = logging.getLogger(__name__)


@celery_app.task(name="app.workers.safety_worker.update_risk_snapshots")
def update_risk_snapshots():
    """
    Update daily risk snapshots for all domains.
    Checks bounce rates and triggers auto-pause if thresholds exceeded.
    """
    db = SessionLocal()
    
    try:
        today = date.today()
        
        # Get all domains with active campaigns
        domains = db.query(Domain).filter(
            Domain.id.in_(
                db.query(Campaign.mailbox_id).join(
                    Domain, Campaign.mailbox_id == Domain.mailbox_id
                ).filter(
                    Campaign.status.in_([CampaignStatus.RUNNING, CampaignStatus.THROTTLED])
                )
            )
        ).all()
        
        logger.info(f"Updating risk snapshots for {len(domains)} domains")
        
        for domain in domains:
            try:
                update_domain_risk(db, domain, today)
            except Exception as e:
                logger.error(f"Error updating risk for domain {domain.domain}: {e}")
                continue
        
        db.commit()
        
    except Exception as e:
        logger.error(f"Error in update_risk_snapshots: {e}")
        db.rollback()
    finally:
        db.close()


def update_domain_risk(db, domain: Domain, target_date: date):
    """
    Update risk snapshot for a single domain.
    """
    # Get or create snapshot for today
    snapshot = db.query(RiskSnapshot).filter(
        RiskSnapshot.domain_id == domain.id,
        RiskSnapshot.date == target_date
    ).first()
    
    if not snapshot:
        snapshot = RiskSnapshot(
            domain_id=domain.id,
            date=target_date
        )
        db.add(snapshot)
    
    # Calculate stats for the day
    start_of_day = datetime.combine(target_date, datetime.min.time())
    end_of_day = datetime.combine(target_date, datetime.max.time())
    
    # Count sent emails
    sent_count = db.query(Message).join(CampaignLead).join(Campaign).filter(
        Campaign.mailbox_id == domain.mailbox_id,
        Message.direction == MessageDirection.OUTBOUND,
        Message.sent_at >= start_of_day,
        Message.sent_at <= end_of_day
    ).count()
    
    # Count replies
    reply_count = db.query(Message).join(CampaignLead).join(Campaign).filter(
        Campaign.mailbox_id == domain.mailbox_id,
        Message.direction == MessageDirection.INBOUND,
        Message.received_at >= start_of_day,
        Message.received_at <= end_of_day
    ).count()
    
    # Count unsubscribes
    from app.enums import ReplyClassification
    unsub_count = db.query(Message).join(CampaignLead).join(Campaign).filter(
        Campaign.mailbox_id == domain.mailbox_id,
        Message.direction == MessageDirection.INBOUND,
        Message.classification == ReplyClassification.UNSUBSCRIBE,
        Message.received_at >= start_of_day,
        Message.received_at <= end_of_day
    ).count()
    
    # Count heuristic bounces (from events)
    bounce_count = db.query(Event).filter(
        Event.action == "bounce_detected_heuristic",
        Event.timestamp >= start_of_day,
        Event.timestamp <= end_of_day
    ).count()
    
    # Update snapshot
    snapshot.sent_count = sent_count
    snapshot.reply_count = reply_count
    snapshot.unsubscribe_count = unsub_count
    snapshot.bounce_count = bounce_count
    
    # Check thresholds and update status
    cutoff_24h = datetime.utcnow() - timedelta(hours=24)
    bounce_24h = db.query(Event).filter(
        Event.action == "bounce_detected_heuristic",
        Event.timestamp >= cutoff_24h
    ).count()
    
    if bounce_24h >= safety_config.BOUNCE_PAUSE_THRESHOLD:
        # Pause all campaigns for this domain
        snapshot.is_paused = True
        snapshot.pause_reason = f"[HEURISTIC] {bounce_24h} potential bounces detected in 24 hours"
        
        campaigns = db.query(Campaign).filter(
            Campaign.mailbox_id == domain.mailbox_id,
            Campaign.status == CampaignStatus.RUNNING
        ).all()
        
        for campaign in campaigns:
            SafetyService.pause_campaign(db, campaign, snapshot.pause_reason)
        
        logger.warning(f"Domain {domain.domain} campaigns paused: {snapshot.pause_reason}")
        
    elif bounce_24h >= safety_config.BOUNCE_THROTTLE_THRESHOLD:
        snapshot.is_throttled = True
        snapshot.pause_reason = f"[HEURISTIC] {bounce_24h} potential bounces detected - sending throttled"
        
        # Update campaigns to throttled status
        campaigns = db.query(Campaign).filter(
            Campaign.mailbox_id == domain.mailbox_id,
            Campaign.status == CampaignStatus.RUNNING
        ).all()
        
        for campaign in campaigns:
            campaign.status = CampaignStatus.THROTTLED
            
        logger.info(f"Domain {domain.domain} throttled: {snapshot.pause_reason}")
        
    else:
        snapshot.is_paused = False
        snapshot.is_throttled = False
        snapshot.pause_reason = None
    
    logger.info(f"Risk snapshot updated for {domain.domain}: sent={sent_count}, replies={reply_count}, bounces={bounce_count}")
