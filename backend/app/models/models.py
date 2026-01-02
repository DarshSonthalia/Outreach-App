"""
SQLAlchemy models for the Email Outreach Platform.
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, 
    ForeignKey, Date, JSON, Enum as SQLEnum, LargeBinary, UniqueConstraint
)
from sqlalchemy.orm import relationship
from app.database import Base
from app.enums import (
    CampaignStatus,
    CampaignLeadStatus,
    MessageDirection,
    ReplyClassification,
    SuppressionReason,
    SafetyLevel,
    MailboxStatus,
)


# ===========================================
# MODELS
# ===========================================

class User(Base):
    """User account for authentication."""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    workspaces = relationship("Workspace", back_populates="user")


class Workspace(Base):
    """User workspace with setup configuration."""
    __tablename__ = "workspaces"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=False)
    
    # Wizard answers stored as JSON
    what_you_sell = Column(Text, nullable=True)
    target_industry = Column(String(255), nullable=True)
    target_role = Column(String(255), nullable=True)
    target_region = Column(String(255), nullable=True)
    offer_type = Column(String(100), nullable=True)  # demo / audit / call
    safety_preference = Column(SQLEnum(SafetyLevel), default=SafetyLevel.MEDIUM)
    meeting_days = Column(JSON, nullable=True)  # ["monday", "tuesday", ...]
    meeting_time_start = Column(String(10), nullable=True)  # "09:00"
    meeting_time_end = Column(String(10), nullable=True)  # "17:00"
    has_leads = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="workspaces")
    mailboxes = relationship("Mailbox", back_populates="workspace")
    domains = relationship("Domain", back_populates="workspace")
    leads = relationship("Lead", back_populates="workspace")
    campaigns = relationship("Campaign", back_populates="workspace")
    suppression_list = relationship("SuppressionEntry", back_populates="workspace")


class Mailbox(Base):
    """Connected Gmail mailbox with OAuth tokens."""
    __tablename__ = "mailboxes"
    
    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False)
    email = Column(String(255), nullable=False, index=True)
    
    # OAuth tokens (encrypted at rest)
    access_token_encrypted = Column(LargeBinary, nullable=True)
    refresh_token_encrypted = Column(LargeBinary, nullable=True)
    token_expiry = Column(DateTime, nullable=True)
    
    # Fix A1: Gmail sync cursor for incremental polling
    last_history_id = Column(String(100), nullable=True)
    gmail_watch_expiration = Column(DateTime, nullable=True)
    last_polled_at = Column(DateTime, nullable=True)
    
    # Fix B2: Mailbox status for OAuth handling
    status = Column(SQLEnum(MailboxStatus), default=MailboxStatus.ACTIVE)
    
    # Legacy field (kept for compatibility)
    is_active = Column(Boolean, default=True)
    connected_at = Column(DateTime, default=datetime.utcnow)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    workspace = relationship("Workspace", back_populates="mailboxes")
    domain = relationship("Domain", back_populates="mailbox", uselist=False)
    campaigns = relationship("Campaign", back_populates="mailbox")


class Domain(Base):
    """Email domain with health checks."""
    __tablename__ = "domains"
    
    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False)
    mailbox_id = Column(Integer, ForeignKey("mailboxes.id"), nullable=True)
    domain = Column(String(255), nullable=False, index=True)
    
    # DNS checks
    spf_valid = Column(Boolean, nullable=True)
    spf_record = Column(Text, nullable=True)
    dmarc_valid = Column(Boolean, nullable=True)
    dmarc_record = Column(Text, nullable=True)
    
    last_checked_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    workspace = relationship("Workspace", back_populates="domains")
    mailbox = relationship("Mailbox", back_populates="domain")
    risk_snapshots = relationship("RiskSnapshot", back_populates="domain")


class Lead(Base):
    """Individual lead/contact."""
    __tablename__ = "leads"
    
    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False)
    
    email = Column(String(255), nullable=False, index=True)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    company = Column(String(255), nullable=True)
    title = Column(String(255), nullable=True)
    
    # Source tracking
    source = Column(String(50), nullable=True)  # "csv" or "web_sourcing"
    source_url = Column(Text, nullable=True)  # For web-sourced leads
    
    # Validation flags
    is_valid_email = Column(Boolean, default=True)
    is_role_email = Column(Boolean, default=False)  # info@, support@, etc.
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    workspace = relationship("Workspace", back_populates="leads")
    campaign_leads = relationship("CampaignLead", back_populates="lead")


class Campaign(Base):
    """Email campaign configuration."""
    __tablename__ = "campaigns"
    
    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False)
    mailbox_id = Column(Integer, ForeignKey("mailboxes.id"), nullable=False)
    
    name = Column(String(255), nullable=False)
    status = Column(SQLEnum(CampaignStatus), default=CampaignStatus.DRAFT)
    pause_reason = Column(Text, nullable=True)
    
    # Email content
    subject = Column(String(500), nullable=True)
    body = Column(Text, nullable=True)
    
    # Follow-up configuration
    followup_enabled = Column(Boolean, default=True)
    followup_delay_days = Column(Integer, default=3)
    followup_subject = Column(String(500), nullable=True)
    followup_body = Column(Text, nullable=True)
    max_followups = Column(Integer, default=2)
    
    # Safety (read-only, enforced by system)
    safety_level = Column(SQLEnum(SafetyLevel), default=SafetyLevel.MEDIUM)
    
    launched_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    workspace = relationship("Workspace", back_populates="campaigns")
    mailbox = relationship("Mailbox", back_populates="campaigns")
    campaign_leads = relationship("CampaignLead", back_populates="campaign")


class CampaignLead(Base):
    """Link between campaign and lead with send state."""
    __tablename__ = "campaign_leads"
    
    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=False)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False)
    
    status = Column(SQLEnum(CampaignLeadStatus), default=CampaignLeadStatus.PENDING)
    
    # Scheduling
    next_action_at = Column(DateTime, nullable=True, index=True)
    followup_count = Column(Integer, default=0)
    
    # Fix D3: Retry safety
    retry_count = Column(Integer, default=0)
    next_retry_at = Column(DateTime, nullable=True)
    
    # Tracking
    last_sent_at = Column(DateTime, nullable=True)
    replied_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    campaign = relationship("Campaign", back_populates="campaign_leads")
    lead = relationship("Lead", back_populates="campaign_leads")
    messages = relationship("Message", back_populates="campaign_lead")


class Message(Base):
    """Email message log (sent and received)."""
    __tablename__ = "messages"
    
    # Fix D2: Unique constraint for idempotency
    __table_args__ = (
        UniqueConstraint('campaign_lead_id', 'step_number', 'direction', name='uq_message_idempotency'),
    )
    
    id = Column(Integer, primary_key=True, index=True)
    campaign_lead_id = Column(Integer, ForeignKey("campaign_leads.id"), nullable=False)
    
    direction = Column(SQLEnum(MessageDirection), nullable=False)
    
    # Fix D2: Step number for idempotency (0 = initial, 1+ = follow-ups)
    step_number = Column(Integer, default=0, nullable=False)
    
    # Gmail identifiers
    gmail_message_id = Column(String(255), nullable=True, index=True)
    gmail_thread_id = Column(String(255), nullable=True, index=True)
    
    # Content
    subject = Column(String(500), nullable=True)
    body = Column(Text, nullable=True)
    
    # For inbound messages
    classification = Column(SQLEnum(ReplyClassification), nullable=True)
    
    sent_at = Column(DateTime, nullable=True)
    received_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    campaign_lead = relationship("CampaignLead", back_populates="messages")


class Event(Base):
    """Audit log for all actions."""
    __tablename__ = "events"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # What entity was affected
    entity_type = Column(String(50), nullable=False)  # campaign, lead, mailbox, etc.
    entity_id = Column(Integer, nullable=False)
    
    # What happened
    action = Column(String(100), nullable=False)
    details = Column(JSON, nullable=True)
    
    # Explanation for user (especially safety decisions)
    explanation = Column(Text, nullable=True)
    
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)


class SuppressionEntry(Base):
    """Suppression list - permanently blocked emails."""
    __tablename__ = "suppression_list"
    
    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False)
    
    email = Column(String(255), nullable=False, index=True)
    reason = Column(SQLEnum(SuppressionReason), nullable=False)
    source_details = Column(Text, nullable=True)  # e.g., "Unsubscribed from campaign X"
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    workspace = relationship("Workspace", back_populates="suppression_list")


class RiskSnapshot(Base):
    """Daily risk metrics per domain for safety monitoring."""
    __tablename__ = "risk_snapshots"
    
    id = Column(Integer, primary_key=True, index=True)
    domain_id = Column(Integer, ForeignKey("domains.id"), nullable=False)
    
    date = Column(Date, nullable=False, index=True)
    
    # Counts
    sent_count = Column(Integer, default=0)
    bounce_count = Column(Integer, default=0)  # Heuristic detection
    reply_count = Column(Integer, default=0)
    unsubscribe_count = Column(Integer, default=0)
    
    # Safety status
    is_throttled = Column(Boolean, default=False)
    is_paused = Column(Boolean, default=False)
    pause_reason = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    domain = relationship("Domain", back_populates="risk_snapshots")


class BookingEvent(Base):
    """
    Fix C2: Calendly webhook idempotency.
    Stores processed webhook events to prevent duplicate handling.
    """
    __tablename__ = "booking_events"
    
    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False)
    
    # Unique identifier from Calendly
    calendly_event_uuid = Column(String(255), unique=True, nullable=False, index=True)
    
    # Event details
    event_type = Column(String(100), nullable=False)  # invitee.created, invitee.canceled
    invitee_email = Column(String(255), nullable=True)
    event_start_time = Column(DateTime, nullable=True)
    
    # Payload hash for verification
    payload_hash = Column(String(64), nullable=True)
    
    # Tracking
    processed_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
