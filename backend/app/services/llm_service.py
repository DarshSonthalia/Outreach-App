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

DRAFT_INSTRUCTIONS = """ROLE:
You are a safety-first B2B cold email copywriter for low-volume outreach.
Your job is to write an email that:
- does NOT look promotional
- does NOT read like a sales pitch
- does NOT introduce claims or offers
- does NOT ask for a meeting directly
- does NOT sound automated

HARD CONSTRAINTS (NON-NEGOTIABLE):
1) PERSONALIZATION
- You MUST use placeholders where appropriate: {{first_name}}, {{company}}, {{title}}.
- If unsure, omit a placeholder rather than inventing context.

2) SALES LANGUAGE (FORBIDDEN)
- NO "introduce our services"
- NO "offer", "audit", "review", "assessment"
- NO "schedule a call", "book a meeting"
- NO "we provide", "we help companies"
- NO pricing, urgency, or CTA pressure

3) TONE
- Human, Curious, Non-assumptive
- One person writing to another
- Reads like a genuine 1:1 message

4) CTA RULE
- The ONLY acceptable CTA is a QUESTION.
- The question must be easy to ignore (low friction).
- The email must feel complete if they don't reply.

5) LENGTH
- Max 120 words total.
- Short paragraphs.
- No bullet points.

GOAL:
To start a conversation by showing light awareness of their context and asking how they currently think about the problem. Making replying feel optional.

Output MUST follow the JSON schema strictly."""


def generate_campaign_draft(
    what_you_sell: str,
    target_industry: str,
    target_role: str,
    offer_type: str,
    target_region: str,
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
    # NOTE: SMOKE_TEST_MODE removed to ensure real AI generation is used with new safety prompt.
    
    input_text = f"""CONTEXT (do not invent details):
- What we sell: {what_you_sell}
- Target industry: {target_industry}
- Target role: {target_role}
- Offer type: {offer_type}
- Target region: {target_region}

WRITING SETTINGS:
- Tone: {tone}
- Length: {length}
- Include follow-up: {include_followup}

OUTPUT REQUIREMENTS:
- Provide a subject and an email body.
- If include_followup=true, also provide followup_subject and followup_body.
- The email MUST adhere to the safety guidelines in the system prompt.
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
def _smoke_test_draft() -> Dict[str, Any]:
    return {
        "subject": "Quick question about your {{company}} data",
        "body": "Hi {{first_name}},\n\nI help teams using analytics tools get clearer product insights without extra engineering. Would you be open to a short chat to see if there's a fit?\n\nBest,\nThe Team",
        "followup_subject": "Following up on my note",
        "followup_body": "Hey {{first_name}},\n\nJust checking in — did you see my note about analytics?\n\nThanks,",
        "personalization_vars_used": ["{{first_name}}", "{{company}}"],
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
