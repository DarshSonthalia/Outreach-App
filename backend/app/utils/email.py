import re
from typing import Optional


_REPLY_PREFIX_RE = re.compile(r"^(re|fwd?):\s*", re.IGNORECASE)


def build_reply_subject(original_subject: Optional[str], fallback_subject: Optional[str] = None) -> str:
    subject = (original_subject or "").strip()
    if not subject and fallback_subject:
        subject = fallback_subject.strip()
    if not subject:
        return ""
    if _REPLY_PREFIX_RE.match(subject):
        return subject
    return f"Re: {subject}"
