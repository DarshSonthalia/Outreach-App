"""
LLM Service - Centralized OpenAI Responses API wrapper.

STRICT RULES:
- Single source of truth for all GPT calls
- Structured outputs (JSON schema) ONLY
- Deterministic temperature per task
- No sensitive PII logging
- Retry with exponential backoff
- Timeout enforcement
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, Optional

from openai import OpenAI, APIError, APITimeoutError, RateLimitError
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

logger = logging.getLogger(__name__)

# =====================================================================
# CONFIG
# =====================================================================

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_TIMEOUT_SECONDS = int(os.getenv("OPENAI_TIMEOUT_SECONDS", "30"))
OPENAI_MAX_RETRIES = int(os.getenv("OPENAI_MAX_RETRIES", "3"))
OPENAI_MODEL_DRAFT = os.getenv("OPENAI_MODEL_DRAFT", "gpt-4o-mini")
OPENAI_MODEL_LINT = os.getenv("OPENAI_MODEL_LINT", "gpt-4o-mini")
OPENAI_MODEL_CLASSIFY = os.getenv("OPENAI_MODEL_CLASSIFY", "gpt-4o-mini")

# Initialize client only if API key is available
if OPENAI_API_KEY:
    client = OpenAI(api_key=OPENAI_API_KEY, timeout=OPENAI_TIMEOUT_SECONDS)
else:
    client = None  # Will fail gracefully on use


class LLMError(Exception):
    """Raised when LLM service encounters an error."""
    pass


# =====================================================================
# CORE RETRY LOGIC
# =====================================================================

@retry(
    reraise=True,
    stop=stop_after_attempt(OPENAI_MAX_RETRIES),
    wait=wait_exponential(multiplier=1, min=1, max=12),
    retry=retry_if_exception_type((APIError, APITimeoutError, RateLimitError)),
)
def _call_responses_api(
    model: str,
    instructions: str,
    input_text: str,
    json_schema: Dict[str, Any],
    temperature: float,
    max_output_tokens: int,
) -> Dict[str, Any]:
    """
    Low-level call to OpenAI Responses API with Structured Outputs.
    DO NOT log request/response bodies due to sensitivity.
    """
    if not client:
        raise LLMError(
            "OpenAI API key not configured. Set OPENAI_API_KEY environment variable."
        )
    
    try:
        logger.info(f"Calling OpenAI {model} for AI task (temp={temperature})")
        
        resp = client.responses.create(
            model=model,
            instructions=instructions,
            input=input_text,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            text={
                "format": {
                    "type": "json_schema",
                    "name": "structured_output",
                    "schema": json_schema,
                    "strict": True,
                }
            },
        )
        
        # Extract text output
        output_text = resp.output_text
        if not output_text:
            raise LLMError("Empty output_text from OpenAI API")
        
        # Parse JSON (Structured Outputs guarantees valid JSON)
        result = json.loads(output_text)
        logger.info(f"OpenAI {model} call succeeded")
        return result
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse OpenAI JSON output: {e}")
        raise LLMError(f"Invalid JSON from OpenAI: {e}") from e
    except (APIError, APITimeoutError, RateLimitError) as e:
        logger.warning(f"OpenAI API error (will retry): {type(e).__name__}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error calling OpenAI: {type(e).__name__}: {e}")
        raise LLMError(str(e)) from e


# =====================================================================
# DRAFT GENERATION
# =====================================================================

DRAFT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "subject": {
            "type": "string",
            "minLength": 1,
            "maxLength": 80,
        },
        "body": {
            "type": "string",
            "minLength": 20,
            "maxLength": 1200,
        },
        "followup_subject": {
            "type": "string",
            "maxLength": 80,
        },
        "followup_body": {
            "type": "string",
            "maxLength": 1200,
        },
        "personalization_vars_used": {
            "type": "array",
            "items": {"type": "string"},
            "maxItems": 10,
        },
        "risky_phrases_found": {
            "type": "array",
            "items": {"type": "string"},
            "maxItems": 10,
        },
    },
    "required": ["subject", "body", "personalization_vars_used", "risky_phrases_found", "followup_subject", "followup_body"],
}

DRAFT_INSTRUCTIONS = """You write safe, human-sounding B2B cold emails for low-volume outreach.
Hard rules:
- No hype, no buzzwords, no exaggerated claims.
- No fake personalization. Do not guess facts about the recipient or company.
- No pressure language, no urgency, no "quick call", no meeting requests.
- Keep it short and plain. Prefer 60–120 words for the body.
- The FIRST email must be inquisitive and light-touch: lead with a question and aim for a foot-in-the-door reply.
- CRITICAL: DO NOT use any placeholders or variables like {{first_name}}, {{company}}, {{title}}, [Your Name], or [Sender Name].
- Write the email as a ready-to-send message. If you don't know a name or company, write in a way that doesn't require it (e.g., "Hi there" or "to your team").
- SIGNATURE RULES:
    1. Look at the "Sender Name" in CONTEXT.
    2. If Sender Name is provided (and not "N/A"), you MUST use it as the signature (e.g., "Best,\n[Sender Name]").
    3. If Sender Name is "N/A" or missing, use "The Team".
    4. NEVER use [Your Name] or other placeholders.
    5. Personalization is ONLY allowed for the signature; do not hallucinate recipient names.
Output MUST follow the JSON schema strictly. """


def generate_campaign_draft(
    what_you_sell: str,
    target_industry: str,
    target_role: str,
    offer_type: str,
    target_region: str,
    founder_name: Optional[str] = None,
    pain_points: Optional[str] = None,
    value_prop: Optional[str] = None,
    social_proof: Optional[str] = None,
    cta_preference: Optional[str] = None,
    personalization_notes: Optional[str] = None,
    additional_context: Optional[str] = None,
    tone: str = "friendly",
    length: str = "medium",
    include_followup: bool = True,
) -> Dict[str, Any]:
    """
    Generate campaign draft (subject + body).
    
    Args:
        what_you_sell: Description of product/service
        target_industry: Industry (e.g., "SaaS", "Manufacturing")
        target_role: Job title (e.g., "VP Sales")
        offer_type: Offer (e.g., "consultation", "demo")
        target_region: Geography (e.g., "US West Coast")
        tone: "calm" | "direct" | "friendly"
        length: "short" | "medium"
        include_followup: Whether to generate follow-up
        
    Returns:
        Dict with subject, body, followup_subject, followup_body, etc.
        
    Raises:
        LLMError on timeout, API error, or invalid output
    """
    if os.getenv("SMOKE_TEST_MODE") == "1":
        logger.info("SMOKE_TEST_MODE enabled - returning canned draft (no OpenAI call)")
        return _smoke_test_draft(founder_name=founder_name)
    extra_lines = []
    if pain_points:
        extra_lines.append(f"- Pain points: {pain_points}")
    if value_prop:
        extra_lines.append(f"- Value prop: {value_prop}")
    if social_proof:
        extra_lines.append(f"- Social proof: {social_proof}")
    if cta_preference:
        extra_lines.append(f"- CTA preference: {cta_preference}")
    if personalization_notes:
        extra_lines.append(f"- Personalization notes: {personalization_notes}")
    if additional_context:
        extra_lines.append(f"- Additional context: {additional_context}")

    extra_context = "\n".join(extra_lines)
    if extra_context:
        extra_context = "\n" + extra_context

    input_text = f"""CONTEXT (do not invent details):
- Sender Name: {founder_name or 'N/A'}
- What we sell: {what_you_sell}
- Target industry: {target_industry}
- Target role: {target_role}
- Offer type: {offer_type}
- Target region: {target_region}
{extra_context}

WRITING SETTINGS:
- Tone: {tone}
- Length: {length}
- Include follow-up: {include_followup}

OUTPUT REQUIREMENTS:
- Provide a subject and an email body.
- If include_followup=true, also provide followup_subject and followup_body.
- Avoid spammy words (free, guarantee, act now, limited time, click here).
- Output must follow the JSON schema strictly."""

    return _call_responses_api(
        model=OPENAI_MODEL_DRAFT,
        instructions=DRAFT_INSTRUCTIONS,
        input_text=input_text,
        json_schema=DRAFT_SCHEMA,
        temperature=0.3,
        max_output_tokens=400,
    )


# Smoke-test helper: when set, avoid real OpenAI calls and return a deterministic draft
def _smoke_test_draft(founder_name: Optional[str] = None) -> Dict[str, Any]:
    signature = founder_name if founder_name and founder_name != 'N/A' else "The Team"
    return {
        "subject": "Quick question about your team's data",
        "body": f"Hi there,\n\nI help teams get clearer product insights without extra engineering. Would you be open to a short chat to see if there's a fit?\n\nBest,\n{signature}",
        "followup_subject": "Following up on my note",
        "followup_body": f"Hi,\n\nJust checking in — did you see my note about analytics?\n\nThanks,\n{signature}",
        "personalization_vars_used": [],
        "risky_phrases_found": [],
    }



# =====================================================================
# EMAIL RISK LINTING
# =====================================================================

LINT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "verdict": {
            "type": "string",
            "enum": ["SAFE", "RISKY"],
        },
        "risk_score": {
            "type": "integer",
            "minimum": 0,
            "maximum": 100,
        },
        "issues": {
            "type": "array",
            "maxItems": 12,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "category": {
                        "type": "string",
                        "enum": [
                            "SPAMMY_LANGUAGE",
                            "OVERCLAIMS",
                            "CREEPY_PERSONALIZATION",
                            "TOO_LONG",
                            "TOO_MANY_LINKS",
                            "TOO_MANY_VARIABLES",
                            "AGGRESSIVE_CTA",
                        ],
                    },
                    "severity": {
                        "type": "string",
                        "enum": ["LOW", "MEDIUM", "HIGH"],
                    },
                    "explanation": {
                        "type": "string",
                        "maxLength": 300,
                    },
                    "suggestion": {
                        "type": "string",
                        "maxLength": 200,
                    },
                },
                "required": ["category", "severity", "explanation", "suggestion"],
            },
        },
    },
    "required": ["verdict", "risk_score", "issues"],
}

LINT_INSTRUCTIONS = """You are a deliverability and compliance reviewer for cold outreach emails.
Your job is to flag risk, not to rewrite the email.
Rules:
- Be conservative.
- Flag spam-trigger phrasing, aggressive CTAs, exaggerated claims, or creepy personalization references.
- Prefer short, plain language.
Output MUST follow the JSON schema strictly."""


def lint_email(
    subject: str,
    body: str,
    followup_subject: Optional[str] = None,
    followup_body: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Check email for deliverability and compliance risk.
    
    Args:
        subject: Email subject line
        body: Email body (truncated to 3000 chars)
        followup_subject: Optional follow-up subject
        followup_body: Optional follow-up body
        
    Returns:
        Dict with verdict ("SAFE"/"RISKY"), risk_score (0-100), and issues list.
        
    Raises:
        LLMError on timeout, API error, or invalid output
    """
    # Truncate to avoid huge inputs
    body_trunc = body[:3000] if body else ""
    followup_body_trunc = followup_body[:3000] if followup_body else ""
    
    email_text = f"SUBJECT: {subject}\n\nBODY:\n{body_trunc}"
    if followup_subject:
        email_text += f"\n\nFOLLOW-UP SUBJECT: {followup_subject}"
    if followup_body_trunc:
        email_text += f"\n\nFOLLOW-UP BODY:\n{followup_body_trunc}"
    
    return _call_responses_api(
        model=OPENAI_MODEL_LINT,
        instructions=LINT_INSTRUCTIONS,
        input_text=email_text,
        json_schema=LINT_SCHEMA,
        temperature=0.0,  # Deterministic
        max_output_tokens=300,
    )


# =====================================================================
# REPLY CLASSIFICATION
# =====================================================================

CLASSIFY_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "classification": {
            "type": "string",
            "enum": [
                "UNSUBSCRIBE",
                "NEGATIVE",
                "NEUTRAL",
                "BOOKING_INTENT",
                "POSITIVE_INTEREST",
                "OUT_OF_OFFICE",
                "UNKNOWN",
            ],
        },
        "confidence": {
            "type": "number",
            "minimum": 0.0,
            "maximum": 1.0,
        },
        "reason": {
            "type": "string",
            "maxLength": 200,
        },
    },
    "required": ["classification", "confidence", "reason"],
}

CLASSIFY_INSTRUCTIONS = """Classify the inbound reply for a cold outreach campaign.
Rules:
- Use ONLY the text provided.
- If unclear, return UNKNOWN with low confidence.
- If the message asks to stop emailing, classify as UNSUBSCRIBE.
- If hostile or says not interested, classify NEGATIVE.
- If proposes time/meeting/booking, classify BOOKING_INTENT.
- If positive/interested but no meeting request yet, classify POSITIVE_INTEREST.
- If "out of office" message, classify OUT_OF_OFFICE.
Output MUST follow the JSON schema strictly."""


def classify_reply(subject: str, body: str) -> Dict[str, Any]:
    """
    Classify inbound reply (fallback for UNKNOWN rules-based classification).
    
    Args:
        subject: Reply subject
        body: Reply body (truncated to 2000 chars)
        
    Returns:
        Dict with classification enum, confidence (0.0-1.0), and reason.
        
    Raises:
        LLMError on timeout, API error, or invalid output
    """
    body_trunc = body[:2000] if body else ""
    
    email_text = f"SUBJECT: {subject}\n\nBODY:\n{body_trunc}"
    
    return _call_responses_api(
        model=OPENAI_MODEL_CLASSIFY,
        instructions=CLASSIFY_INSTRUCTIONS,
        input_text=email_text,
        json_schema=CLASSIFY_SCHEMA,
        temperature=0.0,  # Deterministic
        max_output_tokens=120,
    )
