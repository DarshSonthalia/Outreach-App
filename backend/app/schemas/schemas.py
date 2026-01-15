"""
Pydantic schemas for API request/response validation.
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
from typing import Any, Dict
from app.enums import (
    SafetyLevel, CampaignStatus, ReplyClassification, 
    FollowupState, CancelReason, DraftStatus
)


# ===========================================
# AUTH SCHEMAS
# ===========================================

class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    email: str
    created_at: datetime

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ===========================================
# WORKSPACE SCHEMAS
# ===========================================

class WorkspaceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)


class WorkspaceSetup(BaseModel):
    """Wizard answers for workspace setup."""
    what_you_sell: Optional[str] = None
    target_industry: Optional[str] = None
    target_role: Optional[str] = None
    target_region: Optional[str] = None
    offer_type: Optional[str] = None  # demo / audit / call
    safety_preference: SafetyLevel = SafetyLevel.MEDIUM
    meeting_days: Optional[List[str]] = None
    meeting_time_start: Optional[str] = None
    meeting_time_end: Optional[str] = None
    has_leads: bool = False


class WorkspaceResponse(BaseModel):
    id: int
    name: str
    what_you_sell: Optional[str]
    target_industry: Optional[str]
    target_role: Optional[str]
    target_region: Optional[str]
    offer_type: Optional[str]
    safety_preference: SafetyLevel
    has_leads: bool
    warmup_enabled: bool = False
    warmup_start_date: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ===========================================
# MAILBOX SCHEMAS
# ===========================================

class MailboxResponse(BaseModel):
    id: int
    email: str
    is_active: bool
    connected_at: datetime

    class Config:
        from_attributes = True


class OAuthUrlResponse(BaseModel):
    auth_url: str


# ===========================================
# DOMAIN SCHEMAS
# ===========================================

class DomainCheckRequest(BaseModel):
    domain: str


class DomainResponse(BaseModel):
    id: int
    domain: str
    spf_valid: Optional[bool]
    spf_record: Optional[str]
    dmarc_valid: Optional[bool]
    dmarc_record: Optional[str]
    warmup_day: int
    warmup_completed: bool
    last_checked_at: Optional[datetime]

    class Config:
        from_attributes = True


# ===========================================
# LEAD SCHEMAS
# ===========================================

class LeadCreate(BaseModel):
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    company: Optional[str] = None
    title: Optional[str] = None


class LeadResponse(BaseModel):
    id: int
    email: str
    first_name: Optional[str]
    last_name: Optional[str]
    company: Optional[str]
    title: Optional[str]
    source: Optional[str]
    is_valid_email: bool
    is_role_email: bool
    created_at: datetime

    class Config:
        from_attributes = True


class CSVColumnMapping(BaseModel):
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    company: Optional[str] = None
    title: Optional[str] = None


class CSVUploadResponse(BaseModel):
    total_rows: int
    valid_leads: int
    invalid_emails: int
    role_emails: int
    columns: List[str]


class WebSourceRequest(BaseModel):
    industry: Optional[str] = None
    region: Optional[str] = None
    domains: Optional[List[str]] = None


class WebSourceResponse(BaseModel):
    leads_found: int
    domains_searched: int
    leads: List[LeadResponse]


# ===========================================
# CAMPAIGN SCHEMAS
# ===========================================

class CampaignCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    mailbox_id: int
    lead_ids: List[int]
    # Optional per-campaign customer info to override workspace wizard answers
    customer_info: Optional[dict] = None


class CampaignEmailContent(BaseModel):
    subject: str = Field(..., max_length=500)
    body: str
    followup_enabled: bool = True
    followup_delay_days: int = Field(default=3, ge=1, le=14)
    followup_subject: Optional[str] = None
    followup_body: Optional[str] = None
    max_followups: int = Field(default=2, ge=0, le=5)
    followup_templates: Optional[List[Dict[str, Any]]] = None


class CampaignResponse(BaseModel):
    id: int
    name: str
    status: CampaignStatus
    pause_reason: Optional[str]
    subject: Optional[str]
    body: Optional[str]
    followup_templates: Optional[List[Dict[str, Any]]] = None
    safety_level: SafetyLevel
    launched_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class CampaignDashboard(BaseModel):
    campaign_id: int
    name: str
    status: CampaignStatus
    pause_reason: Optional[str]
    
    # Stats
    emails_sent_today: int
    total_emails_sent: int
    replies_count: int
    meetings_booked: int
    
    # Safety
    daily_limit: int
    remaining_today: int


class CampaignPreview(BaseModel):
    """Preview before launch."""
    total_leads: int
    estimated_days_to_complete: int
    daily_send_limit: int
    safety_explanation: str
    sample_emails: List[dict]


class CampaignScheduleItem(BaseModel):
    lead_email: str
    lead_name: str
    followup_state: FollowupState
    current_step: int
    next_scheduled_at: Optional[datetime]
    cancelled_at: Optional[datetime]
    cancel_reason: Optional[CancelReason]
    schedule_json: Optional[Any] = None # JSON for timeline


class CampaignScheduleResponse(BaseModel):
    campaign_name: str
    campaign_id: int
    followup_templates: Optional[List[dict]] = None
    items: List[CampaignScheduleItem]


# ===========================================
# INBOX SCHEMAS
# ===========================================

class ReplyResponse(BaseModel):
    id: int
    lead_email: str
    lead_name: Optional[str]
    campaign_name: Optional[str]
    subject: Optional[str]
    body: Optional[str]
    classification: Optional[ReplyClassification]
    received_at: Optional[datetime]
    direction: Optional[str]  # "INBOUND" or "OUTBOUND" for frontend styling

    class Config:
        from_attributes = True


class ClassifyRequest(BaseModel):
    classification: ReplyClassification


class SendReplyRequest(BaseModel):
    body: str


# ===========================================
# BOOKING SCHEMAS
# ===========================================

class CalendlyWebhookPayload(BaseModel):
    """Calendly webhook event payload."""
    event: str
    payload: dict
