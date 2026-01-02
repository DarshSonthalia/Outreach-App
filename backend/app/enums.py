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
    BOOKING_INTENT = "BOOKING_INTENT"
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

