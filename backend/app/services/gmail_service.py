"""
Gmail service for OAuth, sending emails, and polling replies.
Implements incremental sync using history API.

Fix Set A: Gmail History Cursor Reliability
Fix Set B: OAuth Token Security + Refresh
"""
import base64
import logging
from datetime import datetime
from email.mime.text import MIMEText
from typing import Optional, Tuple, List, Dict, Any

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from sqlalchemy.orm import Session

from app.config import settings
from app.utils.security import encrypt_oauth_tokens, decrypt_oauth_tokens
from app.enums import MailboxStatus, CampaignStatus

logger = logging.getLogger(__name__)

# Gmail API scopes
GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
]


class GmailService:
    """
    Gmail API service for sending emails and polling replies.
    """
    
    @staticmethod
    def get_oauth_flow(redirect_uri: Optional[str] = None) -> Flow:
        """Create OAuth flow for Gmail authorization."""
        client_config = {
            "web": {
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [settings.google_redirect_uri]
            }
        }
        
        flow = Flow.from_client_config(
            client_config,
            scopes=GMAIL_SCOPES,
            redirect_uri=redirect_uri or settings.google_redirect_uri
        )
        
        return flow
    
    @staticmethod
    def get_authorization_url(state: Optional[str] = None) -> Tuple[str, str]:
        """
        Get the Google OAuth authorization URL.
        Returns (auth_url, state).
        
        Fix B3: access_type=offline, prompt=consent for refresh token
        """
        flow = GmailService.get_oauth_flow()
        auth_url, generated_state = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",  # Ensures we get refresh token
            state=state  # Fix B3: State for CSRF protection
        )
        return auth_url, generated_state
    
    @staticmethod
    def exchange_code_for_tokens(code: str) -> Tuple[bytes, bytes, datetime, str]:
        """
        Exchange authorization code for tokens.
        Returns (access_token_encrypted, refresh_token_encrypted, expiry, email).
        Tokens are encrypted for secure storage.
        """
        flow = GmailService.get_oauth_flow()
        flow.fetch_token(code=code)
        
        credentials = flow.credentials
        
        # Encrypt tokens for storage
        access_encrypted, refresh_encrypted = encrypt_oauth_tokens(
            credentials.token,
            credentials.refresh_token or ""
        )
        
        # Get user email
        service = build("gmail", "v1", credentials=credentials)
        profile = service.users().getProfile(userId="me").execute()
        email = profile.get("emailAddress", "")
        
        return access_encrypted, refresh_encrypted, credentials.expiry, email
    
    @staticmethod
    @staticmethod
    def get_credentials_from_encrypted(
        access_token_encrypted: bytes,
        refresh_token_encrypted: bytes,
        expiry: Optional[datetime]
    ) -> Credentials:
        """
        Get credentials from encrypted tokens.
        Refreshes if expired.
        
        Fix B2: Handle refresh errors gracefully
        """
        access_token, refresh_token = decrypt_oauth_tokens(
            access_token_encrypted,
            refresh_token_encrypted
        )
        
        if not access_token:
            raise ValueError("Failed to decrypt access token")
        
        credentials = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.google_client_id,
            client_secret=settings.google_client_secret,
            expiry=expiry
        )
        
        # Refresh if expired
        if credentials.expired and credentials.refresh_token:
            try:
                credentials.refresh(Request())
            except RefreshError as e:
                # Let caller handle refresh errors
                logger.warning(f"Token refresh failed: {e}")
                raise ValueError(f"Token refresh failed: {str(e)}")
            except Exception as e:
                logger.warning(f"Unexpected error during token refresh: {e}")
                raise ValueError(f"Token refresh error: {str(e)}")
        
        return credentials
    
    @staticmethod
    def get_gmail_client(mailbox, db: Session):
        """
        Fix B2: Get Gmail client with automatic token refresh and reauth handling.
        
        Returns (service, updated_mailbox) or (None, mailbox) if reauth required.
        
        If refresh token is missing or refresh fails:
        - Mark mailbox status = reauth_required
        - Pause all campaigns using that mailbox
        - Create event log entry
        """
        from app.models import Mailbox, Campaign, Event
        
        try:
            # Decrypt tokens
            access_token, refresh_token = decrypt_oauth_tokens(
                mailbox.access_token_encrypted,
                mailbox.refresh_token_encrypted
            )
            
            if not access_token:
                logger.error(f"Failed to decrypt tokens for mailbox {mailbox.id}")
                GmailService._mark_reauth_required(db, mailbox, "Token decryption failed")
                return None, mailbox
            
            # Check for missing refresh token
            if not refresh_token:
                logger.warning(f"Missing refresh token for mailbox {mailbox.id}")
                GmailService._mark_reauth_required(db, mailbox, "Missing refresh token")
                return None, mailbox
            
            credentials = Credentials(
                token=access_token,
                refresh_token=refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=settings.google_client_id,
                client_secret=settings.google_client_secret,
                expiry=mailbox.token_expiry
            )
            
            # Refresh if expired
            if credentials.expired:
                try:
                    logger.debug(f"Refreshing expired token for mailbox {mailbox.id}")
                    credentials.refresh(Request())
                    
                    # Save refreshed tokens
                    access_enc, refresh_enc = encrypt_oauth_tokens(
                        credentials.token,
                        credentials.refresh_token or refresh_token
                    )
                    mailbox.access_token_encrypted = access_enc
                    mailbox.refresh_token_encrypted = refresh_enc
                    mailbox.token_expiry = credentials.expiry
                    mailbox.status = MailboxStatus.ACTIVE
                    db.commit()
                    
                    logger.info(f"Successfully refreshed tokens for mailbox {mailbox.id}, token expires at {credentials.expiry}")
                    
                except RefreshError as e:
                    logger.error(f"Token refresh failed for mailbox {mailbox.id}: {str(e)}")
                    logger.error(f"Error type: {type(e).__name__}, Error code: {getattr(e, 'code', 'unknown')}")
                    GmailService._mark_reauth_required(db, mailbox, f"Token refresh failed: {str(e)}")
                    return None, mailbox
                except Exception as e:
                    logger.error(f"Unexpected error refreshing token for mailbox {mailbox.id}: {str(e)}")
                    GmailService._mark_reauth_required(db, mailbox, f"Token refresh error: {str(e)}")
                    return None, mailbox
            
            service = build("gmail", "v1", credentials=credentials)
            return service, mailbox
            
        except Exception as e:
            logger.error(f"Error getting Gmail client for mailbox {mailbox.id}: {e}")
            return None, mailbox
    
    @staticmethod
    def _mark_reauth_required(db: Session, mailbox, reason: str):
        """
        Fix B2: Mark mailbox as requiring reauth and pause campaigns.
        """
        from app.models import Mailbox, Campaign, Event
        
        mailbox.status = MailboxStatus.REAUTH_REQUIRED
        mailbox.is_active = False
        
        # Pause all campaigns using this mailbox
        campaigns = db.query(Campaign).filter(
            Campaign.mailbox_id == mailbox.id,
            Campaign.status.in_([CampaignStatus.RUNNING, CampaignStatus.THROTTLED])
        ).all()
        
        for campaign in campaigns:
            campaign.status = CampaignStatus.PAUSED
            campaign.pause_reason = f"Mailbox requires re-authentication: {reason}"
        
        # Log event
        event = Event(
            entity_type="mailbox",
            entity_id=mailbox.id,
            action="reauth_required",
            details={"reason": reason},
            explanation=f"Mailbox marked as requiring re-authentication: {reason}. All campaigns paused."
        )
        db.add(event)
        db.commit()
        
        logger.warning(f"Mailbox {mailbox.id} marked reauth_required: {reason}")
    
    @staticmethod
    def send_email(
        credentials: Credentials,
        to_email: str,
        subject: str,
        body: str,
        reply_to_thread_id: Optional[str] = None
    ) -> Tuple[str, str]:
        """
        Send an email via Gmail API.
        Returns (message_id, thread_id).
        
        IMPORTANT: This sends the email immediately, not as a draft.
        """
        service = build("gmail", "v1", credentials=credentials)
        
        # Create message
        message = MIMEText(body)
        message["to"] = to_email
        message["subject"] = subject
        
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        
        body_params: Dict[str, Any] = {"raw": raw_message}
        
        # Add thread ID for follow-ups
        if reply_to_thread_id:
            body_params["threadId"] = reply_to_thread_id
        
        try:
            sent_message = service.users().messages().send(
                userId="me",
                body=body_params
            ).execute()
            
            message_id = sent_message.get("id", "")
            thread_id = sent_message.get("threadId", "")
            
            logger.info(f"Email sent: message_id={message_id}, thread_id={thread_id}")
            
            return message_id, thread_id
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            raise
    
    @staticmethod
    def get_mailbox_history_id(service) -> Optional[str]:
        """
        Fix A2: Get current history ID from mailbox profile.
        Used for bootstrapping and resync.
        """
        try:
            profile = service.users().getProfile(userId="me").execute()
            return profile.get("historyId")
        except Exception as e:
            logger.error(f"Failed to get mailbox profile: {e}")
            return None
    
    @staticmethod
    def poll_inbox_incremental(
        service,
        last_history_id: Optional[str] = None
    ) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        """
        Fix A2: Poll inbox for new messages using incremental sync.
        Uses Gmail History API to avoid re-scanning entire inbox.
        
        Fix A3: Handles historyId too old by resetting cursor.
        
        Returns (new_messages, new_history_id).
        """
        new_messages = []
        new_history_id = last_history_id
        
        try:
            if last_history_id:
                try:
                    # Incremental sync using history
                    # Note: labelIds is not a valid parameter for history().list()
                    # History API automatically tracks messages added to inbox
                    history_response = service.users().history().list(
                        userId="me",
                        startHistoryId=last_history_id,
                        historyTypes=["messageAdded"]
                    ).execute()
                    
                    new_history_id = history_response.get("historyId", last_history_id)
                    
                    # Extract message IDs from history
                    history_list = history_response.get("history", [])
                    message_ids = set()
                    for history_item in history_list:
                        for msg in history_item.get("messagesAdded", []):
                            message_ids.add(msg["message"]["id"])
                    
                    # Fetch full message details
                    for msg_id in message_ids:
                        message = service.users().messages().get(
                            userId="me",
                            id=msg_id,
                            format="full"
                        ).execute()
                        
                        # Filter to only INBOX messages (exclude sent, drafts, etc.)
                        label_ids = message.get("labelIds", [])
                        if "INBOX" in label_ids:
                            parsed_msg = GmailService._parse_message(message)
                            new_messages.append(parsed_msg)
                        
                except HttpError as e:
                    # Fix A3: Handle historyId too old (404) or invalid
                    if e.resp.status in [404, 400]:
                        logger.warning(f"History ID expired or invalid, resetting cursor. Scanning recent messages to catch up.")
                        # Reset to current history ID
                        new_history_id = GmailService.get_mailbox_history_id(service)
                        
                        # Scan recent messages from inbox to catch any missed replies
                        # Get messages from last 7 days to catch recent replies
                        try:
                            from datetime import datetime, timedelta
                            after_date = int((datetime.utcnow() - timedelta(days=7)).timestamp() * 1000)
                            
                            messages_response = service.users().messages().list(
                                userId="me",
                                q="in:inbox",
                                maxResults=50
                            ).execute()
                            
                            message_ids = [msg["id"] for msg in messages_response.get("messages", [])]
                            
                            for msg_id in message_ids:
                                message = service.users().messages().get(
                                    userId="me",
                                    id=msg_id,
                                    format="full"
                                ).execute()
                                
                                # Only process if in INBOX and recent
                                label_ids = message.get("labelIds", [])
                                internal_date = int(message.get("internalDate", 0))
                                
                                if "INBOX" in label_ids and internal_date >= after_date:
                                    parsed_msg = GmailService._parse_message(message)
                                    new_messages.append(parsed_msg)
                            
                            logger.info(f"Scanned {len(new_messages)} recent messages after history reset")
                        except Exception as scan_error:
                            logger.error(f"Error scanning recent messages: {scan_error}")
                        
                        return new_messages, new_history_id
                    else:
                        raise
                    
            else:
                # Fix A2: Bootstrap - just get current history ID, do NOT scan inbox
                new_history_id = GmailService.get_mailbox_history_id(service)
                logger.info(f"Bootstrapped history ID: {new_history_id}")
                # Return empty - we'll start catching new messages from now
                    
        except Exception as e:
            logger.error(f"Failed to poll inbox: {e}")
            # On error, return empty list but preserve history ID
            
        return new_messages, new_history_id
    
    @staticmethod
    def _parse_message(message: Dict[str, Any]) -> Dict[str, Any]:
        """Parse a Gmail message into our format."""
        headers = message.get("payload", {}).get("headers", [])
        
        def get_header(name: str) -> str:
            for h in headers:
                if h["name"].lower() == name.lower():
                    return h["value"]
            return ""
        
        # Extract body
        body = ""
        payload = message.get("payload", {})
        
        if "body" in payload and payload["body"].get("data"):
            body = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="ignore")
        elif "parts" in payload:
            for part in payload["parts"]:
                if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
                    body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="ignore")
                    break
        
        return {
            "id": message.get("id", ""),
            "thread_id": message.get("threadId", ""),
            "from": get_header("From"),
            "to": get_header("To"),
            "subject": get_header("Subject"),
            "body": body,
            "internal_date": message.get("internalDate", ""),
        }
