"""
Enums for the Email Outreach Platform.
Separated to avoid circular imports.
"""
import enum


class CampaignStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    THROTTLED = "THROTTLED"
    COMPLETED = "COMPLETED"


class CampaignLeadStatus(str, enum.Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"  # Fix D1: Atomic claiming
    SENT = "SENT"
    REPLIED = "REPLIED"
    BOUNCED = "BOUNCED"
    UNSUBSCRIBED = "UNSUBSCRIBED"
    COMPLETED = "COMPLETED"


class MessageDirection(str, enum.Enum):
    OUTBOUND = "OUTBOUND"
    INBOUND = "INBOUND"


class ReplyClassification(str, enum.Enum):
    UNSUBSCRIBE = "UNSUBSCRIBE"
    NEGATIVE = "NEGATIVE"
    NEUTRAL = "NEUTRAL"
    INTERESTED = "INTERESTED"
    BOOKING_INTENT = "BOOKING_INTENT"
    QUESTION = "QUESTION"
    OUT_OF_OFFICE = "OUT_OF_OFFICE"
    UNKNOWN = "UNKNOWN"


class SuppressionReason(str, enum.Enum):
    UNSUBSCRIBE = "UNSUBSCRIBE"
    BOUNCE = "BOUNCE"
    MANUAL = "MANUAL"
    ROLE_EMAIL = "ROLE_EMAIL"


class SafetyLevel(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class MailboxStatus(str, enum.Enum):
    """Fix B2: Mailbox connection status for OAuth handling."""
    ACTIVE = "ACTIVE"
    REAUTH_REQUIRED = "REAUTH_REQUIRED"
    DISCONNECTED = "DISCONNECTED"


class FollowupState(str, enum.Enum):
    SCHEDULED = "SCHEDULED"
    CANCELLED = "CANCELLED"
    COMPLETED = "COMPLETED"


class CancelReason(str, enum.Enum):
    REPLIED = "REPLIED"
    NEGATIVE_REPLY = "NEGATIVE_REPLY"
    UNSUBSCRIBE = "UNSUBSCRIBE"
    BOOKED = "BOOKED"
    BOUNCE = "BOUNCE"
    SUPPRESSED = "SUPPRESSED"
    MANUAL = "MANUAL"
    SAFETY = "SAFETY"


class DraftStatus(str, enum.Enum):
    GENERATED = "GENERATED"
    EDITED = "EDITED"
    SENT = "SENT"
    DISCARDED = "DISCARDED"
    SAVED_TO_GMAIL_DRAFT = "SAVED_TO_GMAIL_DRAFT"

