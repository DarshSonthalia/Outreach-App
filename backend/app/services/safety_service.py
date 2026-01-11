"""
Safety service - CRITICAL component for email sending protection.
All safety checks are MANDATORY before every send.
"""
import logging
from datetime import datetime, timedelta, date
from typing import Tuple, Optional, Dict, Any, List
from sqlalchemy.orm import Session

from app.config import safety_config
from app.models import (
    Mailbox, Domain, Campaign, CampaignLead, Message, Event,
    SuppressionEntry, RiskSnapshot, CampaignStatus, CampaignLeadStatus,
    MessageDirection, SuppressionReason
)

logger = logging.getLogger(__name__)


class SafetyDecision:
    """
    Result of a safety check with explanation.
    """
    def __init__(
        self,
        can_send: bool,
        reason: str,
        explanation: str,
        should_pause: bool = False,
        should_throttle: bool = False,
        delay_seconds: Optional[int] = None
    ):
        self.can_send = can_send
        self.reason = reason
        self.explanation = explanation
        self.should_pause = should_pause
        self.should_throttle = should_throttle
        self.delay_seconds = delay_seconds
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "can_send": self.can_send,
            "reason": self.reason,
            "explanation": self.explanation,
            "should_pause": self.should_pause,
            "should_throttle": self.should_throttle,
            "delay_seconds": self.delay_seconds
        }


class SafetyService:
    """
    Safety engine for email sending.
    All checks are MANDATORY before every send.
    
    Safety Rules:
    - Daily limits by mailbox age (10/15/20/25, hard cap 30)
    - Bounce heuristic threshold (2=throttle, 4=pause)
    - Suppression list check
    - Reply stops all future sends
    - Unsubscribe = permanent suppression
    """
    
    @staticmethod
    def get_mailbox_age_days(mailbox: Mailbox) -> int:
        """Get the age of a mailbox in days."""
        if not mailbox.connected_at:
            return 0
        delta = datetime.utcnow() - mailbox.connected_at
        return delta.days
    
    @staticmethod
    def get_daily_send_count(db: Session, mailbox_id: int, target_date: date = None) -> int:
        """Get the number of emails sent today from a mailbox."""
        target_date = target_date or datetime.utcnow().date()
        start_of_day = datetime.combine(target_date, datetime.min.time())
        end_of_day = datetime.combine(target_date, datetime.max.time())
        
        count = db.query(Message).join(CampaignLead).join(Campaign).filter(
            Campaign.mailbox_id == mailbox_id,
            Message.direction == MessageDirection.OUTBOUND,
            Message.sent_at >= start_of_day,
            Message.sent_at <= end_of_day
        ).count()
        
        return count
    
    @staticmethod
    def get_daily_limit(mailbox: Mailbox) -> int:
        """Get the daily send limit for a mailbox based on age."""
        age_days = SafetyService.get_mailbox_age_days(mailbox)
        limit = safety_config.get_daily_limit(age_days)
        return min(limit, safety_config.HARD_CAP)
    
    @staticmethod
    def check_daily_limit(db: Session, mailbox: Mailbox) -> SafetyDecision:
        """Check if daily send limit has been reached."""
        limit = SafetyService.get_daily_limit(mailbox)
        sent_today = SafetyService.get_daily_send_count(db, mailbox.id)
        remaining = limit - sent_today
        
        if remaining <= 0:
            # Calculate time until midnight
            now = datetime.utcnow()
            tomorrow = datetime.combine(now.date() + timedelta(days=1), datetime.min.time())
            delay_seconds = int((tomorrow - now).total_seconds())
            
            return SafetyDecision(
                can_send=False,
                reason="daily_limit_reached",
                explanation=f"Daily limit of {limit} emails reached. {sent_today} sent today. Will resume tomorrow.",
                delay_seconds=delay_seconds
            )
        
        return SafetyDecision(
            can_send=True,
            reason="daily_limit_ok",
            explanation=f"Daily limit check passed. {sent_today}/{limit} sent today, {remaining} remaining."
        )
    
    @staticmethod
    def get_bounce_count_24h(db: Session, domain_id: int) -> int:
        """
        Get heuristic bounce count in last 24 hours.
        Bounces are detected by DSN/mailer-daemon replies.
        """
        cutoff = datetime.utcnow() - timedelta(hours=24)
        
        # Count messages marked as bounced
        count = db.query(Message).join(CampaignLead).join(Campaign).join(Mailbox).join(Domain).filter(
            Domain.id == domain_id,
            Message.direction == MessageDirection.INBOUND,
            Message.created_at >= cutoff
        ).filter(
            # Heuristic: check for bounce patterns in subject
            # This is a simplified check - real implementation would be more sophisticated
            Message.subject.ilike('%delivery%failed%') |
            Message.subject.ilike('%undeliverable%') |
            Message.subject.ilike('%returned%') |
            Message.subject.ilike('%failure%notice%')
        ).count()
        
        return count
    
    @staticmethod
    def check_bounce_threshold(db: Session, domain: Domain) -> SafetyDecision:
        """
        Check bounce rate using heuristic detection.
        IMPORTANT: This is heuristic-based as Gmail API doesn't provide guaranteed bounce events.
        """
        bounce_count = SafetyService.get_bounce_count_24h(db, domain.id)
        
        if bounce_count >= safety_config.BOUNCE_PAUSE_THRESHOLD:
            return SafetyDecision(
                can_send=False,
                reason="bounce_threshold_pause",
                explanation=f"[HEURISTIC] {bounce_count} potential bounces detected in 24h. Campaign paused for safety. Please review your lead list quality.",
                should_pause=True
            )
        
        if bounce_count >= safety_config.BOUNCE_THROTTLE_THRESHOLD:
            return SafetyDecision(
                can_send=True,  # Still allow sends but with warning
                reason="bounce_threshold_throttle",
                explanation=f"[HEURISTIC] {bounce_count} potential bounces detected in 24h. Sending will continue with caution.",
                should_throttle=True
            )
        
        return SafetyDecision(
            can_send=True,
            reason="bounce_check_ok",
            explanation="Bounce check passed. No concerning patterns detected."
        )
    
    @staticmethod
    def check_suppression_list(db: Session, workspace_id: int, email: str) -> SafetyDecision:
        """Check if email is on the suppression list."""
        suppressed = db.query(SuppressionEntry).filter(
            SuppressionEntry.workspace_id == workspace_id,
            SuppressionEntry.email == email
        ).first()
        
        if suppressed:
            return SafetyDecision(
                can_send=False,
                reason="suppressed",
                explanation=f"Email is on suppression list. Reason: {suppressed.reason.value}. {suppressed.source_details or ''}"
            )
        
        return SafetyDecision(
            can_send=True,
            reason="not_suppressed",
            explanation="Email is not on suppression list."
        )
    
    @staticmethod
    def check_already_replied(db: Session, campaign_lead_id: int) -> SafetyDecision:
        """Check if lead has already replied to this campaign."""
        reply = db.query(Message).filter(
            Message.campaign_lead_id == campaign_lead_id,
            Message.direction == MessageDirection.INBOUND
        ).first()
        
        if reply:
            return SafetyDecision(
                can_send=False,
                reason="already_replied",
                explanation="Lead has already replied. All future sends stopped."
            )
        
        return SafetyDecision(
            can_send=True,
            reason="no_reply_yet",
            explanation="No reply received yet."
        )
    
    @staticmethod
    def run_all_safety_checks(
        db: Session,
        campaign: Campaign,
        campaign_lead: CampaignLead,
        lead_email: str
    ) -> SafetyDecision:
        """
        Run ALL safety checks before sending.
        Returns combined safety decision.
        
        Checks run in order:
        1. Suppression list
        2. Already replied
        3. Daily limit
        4. Bounce threshold
        """
        mailbox = campaign.mailbox
        domain = mailbox.domain
        workspace_id = campaign.workspace_id
        
        # Check 1: Suppression list
        suppression_check = SafetyService.check_suppression_list(db, workspace_id, lead_email)
        if not suppression_check.can_send:
            SafetyService.log_safety_decision(db, campaign, campaign_lead, suppression_check)
            return suppression_check
        
        # Check 2: Already replied
        reply_check = SafetyService.check_already_replied(db, campaign_lead.id)
        if not reply_check.can_send:
            SafetyService.log_safety_decision(db, campaign, campaign_lead, reply_check)
            return reply_check
        
        # Check 3: Daily limit
        limit_check = SafetyService.check_daily_limit(db, mailbox)
        if not limit_check.can_send:
            SafetyService.log_safety_decision(db, campaign, campaign_lead, limit_check)
            return limit_check
        
        # Check 4: Bounce threshold
        if domain:
            bounce_check = SafetyService.check_bounce_threshold(db, domain)
            if not bounce_check.can_send:
                SafetyService.log_safety_decision(db, campaign, campaign_lead, bounce_check)
                
                # Pause campaign if needed
                if bounce_check.should_pause:
                    SafetyService.pause_campaign(db, campaign, bounce_check.explanation)
                
                return bounce_check
        
        # All checks passed
        return SafetyDecision(
            can_send=True,
            reason="all_checks_passed",
            explanation="All safety checks passed. Email can be sent."
        )
    
    @staticmethod
    def log_safety_decision(
        db: Session,
        campaign: Campaign,
        campaign_lead: CampaignLead,
        decision: SafetyDecision
    ):
        """Log safety decision to events table."""
        event = Event(
            entity_type="campaign_lead",
            entity_id=campaign_lead.id,
            action="safety_check",
            details=decision.to_dict(),
            explanation=decision.explanation
        )
        db.add(event)
        db.commit()
    
    @staticmethod
    def pause_campaign(db: Session, campaign: Campaign, reason: str):
        """Pause a campaign due to safety concerns."""
        campaign.status = CampaignStatus.PAUSED
        campaign.pause_reason = reason
        
        event = Event(
            entity_type="campaign",
            entity_id=campaign.id,
            action="auto_paused",
            details={"reason": reason},
            explanation=f"Campaign automatically paused: {reason}"
        )
        db.add(event)
        db.commit()
        
        logger.warning(f"Campaign {campaign.id} auto-paused: {reason}")
    
    @staticmethod
    def add_to_suppression(
        db: Session,
        workspace_id: int,
        email: str,
        reason: SuppressionReason,
        source_details: str
    ):
        """Add email to suppression list."""
        # Check if already suppressed
        existing = db.query(SuppressionEntry).filter(
            SuppressionEntry.workspace_id == workspace_id,
            SuppressionEntry.email == email
        ).first()
        
        if not existing:
            entry = SuppressionEntry(
                workspace_id=workspace_id,
                email=email,
                reason=reason,
                source_details=source_details
            )
            db.add(entry)
            db.commit()
            
            logger.info(f"Added {email} to suppression list: {reason.value}")
    
    @staticmethod
    def get_safety_explanation_for_campaign(db: Session, campaign: Campaign) -> Dict[str, Any]:
        """Get human-readable safety explanation for a campaign."""
        mailbox = campaign.mailbox
        age_days = SafetyService.get_mailbox_age_days(mailbox)
        daily_limit = SafetyService.get_daily_limit(mailbox)
        sent_today = SafetyService.get_daily_send_count(db, mailbox.id)
        
        ramp_explanation = f"""
Your mailbox was connected {age_days} days ago.

**Daily Send Limits (Ramping Schedule):**
- Day 1: 10 emails/day
- Day 2: 15 emails/day
- Day 3: 20 emails/day
- Day 4+: 25 emails/day
- Hard cap: 30 emails/day (never exceeded)

**Current Status:**
- Your current limit: {daily_limit} emails/day
- Sent today: {sent_today}
- Remaining: {daily_limit - sent_today}

**Safety Rules:**
- If 2+ bounces detected in 24h: sending slows down
- If 4+ bounces detected in 24h: campaign pauses
- Any unsubscribe: email permanently blocked
- Any reply: future emails to that person stop

These limits protect your domain reputation.
"""
        
        return {
            "mailbox_age_days": age_days,
            "daily_limit": daily_limit,
            "sent_today": sent_today,
            "remaining_today": daily_limit - sent_today,
            "explanation": ramp_explanation.strip()
        }
