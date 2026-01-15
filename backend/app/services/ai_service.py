import json
import logging
from typing import Dict, Any, List, Optional
from openai import OpenAI
from app.config import settings

# Configure logging
logger = logging.getLogger(__name__)

class AIService:
    _client = None

    @classmethod
    def get_client(cls):
        if cls._client is None:
            if settings.openai_api_key:
                cls._client = OpenAI(api_key=settings.openai_api_key)
            else:
                logger.warning("OPENAI_API_KEY not set. AI features will fail.")
        return cls._client

    @staticmethod
    def generate_reply_draft(context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a reply draft using OpenAI.
        
        Context should include:
        - thread_messages: List of message usage (sender, body, etc.)
        - lead: {first_name, company, role, etc.}
        - campaign: {what_you_sell, offer_type, calendly_link_allowed}
        """
        client = AIService.get_client()
        if not client:
            raise ValueError("OpenAI API key missing")

        model = settings.openai_model_reply_draft or "gpt-4o"
        
        system_prompt = """
You are an expert SDR (Sales Development Representative) assistant.
Your goal is to draft a reply to an email thread.

STRICT RULES:
1. Write as a human. Short, professional but conversational. 80-140 words max.
9. Classification MUST be one of: UNSUBSCRIBE, NEGATIVE, NEUTRAL, INTERESTED, BOOKING_INTENT, QUESTION, OUT_OF_OFFICE, UNKNOWN.

INPUT CONTEXT:
You will receive the thread history, lead info, and campaign details.

OUTPUT FORMAT:
You must output a valid JSON object with the following schema:
{
  "classification": "string", 
  "subject": "string",
  "body": "string",
  "needs_human_review": boolean,
  "risk_flags": ["string"]
}
"""
        
        user_content = json.dumps(context, indent=2)

        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ],
                response_format={"type": "json_object"},
                temperature=0.7,
                max_tokens=500
            )
            
            content = response.choices[0].message.content
            if not content:
                raise ValueError("Empty response from OpenAI")
                
            data = json.loads(content)
            
            # Basic validation
            required_keys = ["classification", "subject", "body", "needs_human_review", "risk_flags"]
            for key in required_keys:
                if key not in data:
                    data[key] = None # or raise error
                    
            # Enforce constraints post-generation (safety net)
            classification = data.get("classification")
            body = data.get("body", "")
            
            if classification == "UNSUBSCRIBE":
                # Ensure no questions or links
                if "?" in body:
                    data["risk_flags"].append("Unsubscribe draft contains question")
                if "http" in body:
                    data["risk_flags"].append("Unsubscribe draft contains link")
                    
            return data

        except Exception as e:
            logger.error(f"Error generating AI draft: {e}")
            raise e
    @staticmethod
    def generate_followup_sequence(context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate a 3-step follow-up sequence based on initial email and campaign metadata.
        
        Context should include:
        - campaign_offer: {selling, target_role, value_prop}
        - initial_email_body: str
        """
        client = AIService.get_client()
        if not client:
            raise ValueError("OpenAI API key missing")

        model = settings.openai_model_reply_draft or "gpt-4o"
        
        system_prompt = """
You are an elite Sales Development Copywriter. 
Your goal is to generate a high-converting 3-step follow-up sequence based on an initial "foot in the door" email.

STRATEGIC CONTEXT:
1. The Initial Email (Step 0) was a "foot in the door" — low friction, high curiosity.
2. Follow-ups must pivot toward addressing specific lead problems and positioning our offer as the bridge to their desired goal.

STRICT RULES:
1. VOICE: Short (60-100 words), professional, conversational. NO corporate jargon.
2. STEP 1 (The Bump - 2 days): Soft nudge. Reference the first email. Low friction.
3. STEP 2 (The Solution - 5 days): Identify a core problem the lead likely faces. Position the campaign's offer as the solution. Focus on high value.
4. STEP 3 (The Breakup - 9 days): Professional close-out. Acknowledge they might be busy. Leave the door open but stop the automation.
5. FORMATTING: Use {{first_name}} and {{company}} as placeholders.
6. NO generic "Hope you are doing well" or "Just checking in" openings. Be direct and valuable.

OUTPUT FORMAT:
You must output a valid JSON array of objects:
[
  {
    "step": 1,
    "delay_days": 2,
    "subject": "string",
    "body": "string"
  },
  {
    "step": 2,
    "delay_days": 5,
    "subject": "string",
    "body": "string"
  },
  {
    "step": 3,
    "delay_days": 9,
    "subject": "string",
    "body": "string"
  }
]
"""
        
        user_content = json.dumps(context, indent=2)

        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ],
                temperature=0.8,
                max_tokens=1000
            )
            
            content = response.choices[0].message.content
            if not content:
                raise ValueError("Empty response from OpenAI")
                
            # Content might have markdown backticks
            if "```json" in content:
                content = content.replace("```json", "").replace("```", "").strip()
            elif "```" in content:
                content = content.replace("```", "").strip()
            
            data = json.loads(content)
            return data

        except Exception as e:
            logger.error(f"Error generating AI follow-ups: {e}")
            raise e
