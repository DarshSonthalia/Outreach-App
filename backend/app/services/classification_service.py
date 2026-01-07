"""
Reply classification service - rule-based with LLM fallback for ambiguous cases.

Fix Set E: Bounce heuristics with 2+ signals requirement
"""
import re
from typing import Optional, Tuple
from app.enums import ReplyClassification


# Keyword patterns for classification
UNSUBSCRIBE_PATTERNS = [
    r'\bunsubscribe\b',
    r'\bremove\s+me\b',
    r'\bstop\s+(emailing|contacting)\b',
    r'\bopt\s*out\b',
    r'\btake\s+me\s+off\b',
    r'\bdo\s+not\s+contact\b',
    r'\bno\s+longer\s+interested\b',
]

NEGATIVE_PATTERNS = [
    r'\bnot\s+interested\b',
    r'\bno\s+thanks\b',
    r'\bplease\s+don\'?t\b',
    r'\bleave\s+me\s+alone\b',
    r'\bwrong\s+person\b',
    r'\bwrong\s+company\b',
    r'\bno\s+need\b',
    r'\bwe\'?re\s+not\s+(looking|buying)\b',
]

BOOKING_INTENT_PATTERNS = [
    # Direct scheduling requests
    r'\bschedule\s+a\s+(call|meeting|demo|sync)\b',
    r'\bbook\s+a\s+(call|meeting|demo|time|slot)\b',
    r'\blet\'?s\s+(chat|talk|meet|connect|discuss)\b',
    r'\bset\s+up\s+a\s+(call|meeting|time|demo)\b',
    r'\bwhat\s+times?\s+(work|are\s+good|do\s+you\s+have)\b',
    r'\bsend\s+me\s+(your\s+)?calendar\b',
    r'\bcalendly\b',
    r'\bfree\s+(this|next)\s+(week|day)\b',
    r'\bavailable\s+(this|next)\s+(week|day|time)\b',
    
    # Interest indicators
    r'\bwould\s+(love|like)\s+to\s+(learn|hear|discuss|know)\b',
    r'\bsounds?\s+(great|interesting|good)\b',
    r'\binterested\s+in\b',
    r'\bwant\s+to\s+(learn|know|discuss|explore)\b',
    r'\btell\s+me\s+more\b',
    r'\bmore\s+info(?:rmation)?\b',
    r'\bcan\s+we\s+(talk|discuss|connect)\b',
    r'\bwhen\s+can\s+(we|you)\s+(meet|talk|discuss)\b',
    r'\blet\'?s\s+(discuss|explore|talk)\b',
    r'\bthis\s+(sounds|looks)\s+(great|good|interesting)\b',
    
    # Positive engagement
    r'\bgreat\s+(idea|suggestion|thought)\b',
    r'\blooks\s+interesting\b',
    r'\bwould\s+work\s+for\s+(me|us)\b',
    r'\bhow\s+do\s+we\s+(get\s+started|move\s+forward|proceed)\b',
    r'\bwhat\'?s\s+the\s+next\s+step\b',
    r'\bsounds\s+perfect\b',
    r'\blet\'?s\s+move\s+forward\b',
    r'\bi\'?m\s+(interested|open|keen)\b',
    r'\bcatch\s+up\s+(soon|this\s+week)\b',
    r'\bfollow\s+up\b',
]

# Fix E1: Bounce detection with multiple signal categories
BOUNCE_SENDER_PATTERNS = [
    'mailer-daemon',
    'postmaster',
    'mail-delivery',
    'mailerdaemon',
    'noreply',
    'no-reply',
]

BOUNCE_SUBJECT_PATTERNS = [
    r'delivery\s+(failure|failed|status)',
    r'undeliverable',
    r'returned\s+mail',
    r'mail\s+delivery\s+failed',
    r'delivery\s+status\s+notification',
    r'failure\s+notice',
    r'undelivered\s+mail',
]

BOUNCE_BODY_PATTERNS = [
    r'could\s+not\s+be\s+delivered',
    r'permanent\s+failure',
    r'mailbox\s+(not\s+found|unavailable|full)',
    r'user\s+unknown',
    r'address\s+rejected',
    r'recipient\s+rejected',
    r'550\s+',  # SMTP error codes
    r'553\s+',
    r'554\s+',
]


class ClassificationService:
    """
    Rule-based reply classification.
    LLM fallback reserved for truly ambiguous cases.
    """
    
    @staticmethod
    def classify_reply(subject: str, body: str) -> ReplyClassification:
        """
        Classify a reply using rule-based pattern matching.
        
        Classification priority:
        1. Unsubscribe (immediate suppression)
        2. Booking intent (positive)
        3. Negative
        4. Neutral (default)
        """
        text = f"{subject} {body}".lower()
        
        # Check unsubscribe first (highest priority)
        for pattern in UNSUBSCRIBE_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return ReplyClassification.UNSUBSCRIBE
        
        # Check booking intent (positive signal)
        for pattern in BOOKING_INTENT_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return ReplyClassification.BOOKING_INTENT
        
        # Check negative patterns
        for pattern in NEGATIVE_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return ReplyClassification.NEGATIVE
        
        # Default to neutral
        return ReplyClassification.NEUTRAL
    
    @staticmethod
    def is_bounce_reply(subject: str, body: str, from_email: str) -> bool:
        """
        Legacy method - returns True if any bounce signal matches.
        Use is_bounce_reply_strict for 2+ signal requirement.
        """
        is_bounce, _ = ClassificationService.is_bounce_reply_strict(subject, body, from_email)
        return is_bounce
    
    @staticmethod
    def is_bounce_reply_strict(subject: str, body: str, from_email: str) -> Tuple[bool, int]:
        """
        Fix E1: Heuristic detection of bounce/DSN emails with 2+ signals required.
        
        Returns (is_bounce, signal_count) to reduce false positives.
        Only count as bounce if at least 2 different signal categories match.
        
        Signal categories:
        1. Sender address (mailer-daemon, postmaster)
        2. Subject patterns (delivery failure, undeliverable)
        3. Body patterns (could not be delivered, user unknown)
        """
        text = f"{subject} {body}".lower()
        from_lower = from_email.lower()
        
        signal_count = 0
        
        # Category 1: Check sender patterns
        sender_match = any(sender in from_lower for sender in BOUNCE_SENDER_PATTERNS)
        if sender_match:
            signal_count += 1
        
        # Category 2: Check subject patterns
        subject_lower = subject.lower()
        subject_match = any(
            re.search(pattern, subject_lower, re.IGNORECASE) 
            for pattern in BOUNCE_SUBJECT_PATTERNS
        )
        if subject_match:
            signal_count += 1
        
        # Category 3: Check body patterns
        body_match = any(
            re.search(pattern, text, re.IGNORECASE) 
            for pattern in BOUNCE_BODY_PATTERNS
        )
        if body_match:
            signal_count += 1
        
        # Fix E1: Require 2+ signals to flag as bounce
        is_bounce = signal_count >= 2
        
        return is_bounce, signal_count
    
    @staticmethod
    def get_classification_explanation(classification: ReplyClassification) -> str:
        """Get human-readable explanation for a classification."""
        explanations = {
            ReplyClassification.UNSUBSCRIBE: "The recipient has requested to be removed from your emails. They have been added to your suppression list and will not receive future emails.",
            ReplyClassification.NEGATIVE: "The recipient has expressed they are not interested. No further emails will be sent to them from this campaign.",
            ReplyClassification.NEUTRAL: "The reply doesn't clearly indicate interest or disinterest. You may want to review and respond manually.",
            ReplyClassification.BOOKING_INTENT: "The recipient has expressed interest in scheduling a meeting or call!",
            ReplyClassification.UNKNOWN: "The reply could not be automatically classified. Please review manually.",
        }
        return explanations.get(classification, "Unknown classification")

