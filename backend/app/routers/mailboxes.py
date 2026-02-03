"""
Mailbox router - Gmail OAuth connection.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models import User, Workspace, Mailbox, Domain
from app.schemas import MailboxResponse, OAuthUrlResponse
from app.utils.dependencies import get_current_user
from app.services.gmail_service import GmailService
from app.services.domain_service import DomainService
from app.enums import CampaignStatus, MailboxStatus
import logging
import traceback

logger = logging.getLogger(__name__)
router = APIRouter()


def _resume_paused_campaigns_for_mailbox(db: Session, mailbox: Mailbox):
    """
    Fix B2: Resume campaigns that were paused due to mailbox auth issues.
    
    When a mailbox is re-authenticated, find all campaigns that were paused
    due to "Mailbox requires re-authentication" and resume them.
    """
    from app.models import Campaign
    
    # Find campaigns paused due to auth issues
    paused_campaigns = db.query(Campaign).filter(
        Campaign.mailbox_id == mailbox.id,
        Campaign.status == CampaignStatus.PAUSED,
        Campaign.pause_reason.contains("Mailbox requires re-authentication")
    ).all()
    
    for campaign in paused_campaigns:
        campaign.status = CampaignStatus.RUNNING
        campaign.pause_reason = None
        
        # Re-schedule pending leads starting from now
        from datetime import datetime, timedelta
        from app.models import CampaignLead, CampaignLeadStatus
        
        now = datetime.utcnow()
        pending_leads = db.query(CampaignLead).filter(
            CampaignLead.campaign_id == campaign.id,
            CampaignLead.status == CampaignLeadStatus.PENDING
        ).all()
        
        from app.enums import FollowupState
        for i, cl in enumerate(pending_leads):
            cl.next_scheduled_at = now + timedelta(minutes=i * 2)
            cl.followup_state = FollowupState.SCHEDULED
    
    if paused_campaigns:
        db.commit()
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Resumed {len(paused_campaigns)} campaigns for mailbox {mailbox.id}")



@router.get("/oauth/url", response_model=OAuthUrlResponse)
async def get_oauth_url(
    workspace_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get Google OAuth authorization URL.
    """
    # Verify workspace belongs to user
    workspace = db.query(Workspace).filter(
        Workspace.id == workspace_id,
        Workspace.user_id == current_user.id
    ).first()
    
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )
    
    auth_url, state = GmailService.get_authorization_url(state=str(workspace_id))
    
    # In production, store state with workspace_id for verification
    # For simplicity, we'll pass workspace_id as state
    # auth_url = f"{auth_url}&state={workspace_id}"
    
    return OAuthUrlResponse(auth_url=auth_url)


@router.get("/oauth/callback")
async def oauth_callback(
    code: str = Query(...),
    state: str = Query(...),
    db: Session = Depends(get_db)
):
    """
    Handle OAuth callback from Google.
    Exchanges code for tokens and creates mailbox.
    """
    try:
        workspace_id = int(state)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid state parameter"
        )
    
    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not workspace:
        logger.error(f"OAuth Callback: Workspace {workspace_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )
    
    logger.info(f"OAuth Callback: Starting token exchange for workspace {workspace_id}")
    try:
        # Exchange code for tokens
        access_encrypted, refresh_encrypted, expiry, email = \
            GmailService.exchange_code_for_tokens(code)
        
        logger.info(f"OAuth Callback: Successfully exchanged code for {email}")
        
        # Check if mailbox already exists
        existing = db.query(Mailbox).filter(
            Mailbox.workspace_id == workspace_id,
            Mailbox.email == email
        ).first()
        
        if existing:
            # Update tokens
            existing.access_token_encrypted = access_encrypted
            existing.refresh_token_encrypted = refresh_encrypted
            existing.token_expiry = expiry
            existing.is_active = True
            existing.status = MailboxStatus.ACTIVE
            existing.error_reason = None
            db.commit()
            mailbox = existing
            
            # Fix B2: Resume campaigns that were paused due to auth issues
            _resume_paused_campaigns_for_mailbox(db, mailbox)
        else:
            # Create new mailbox
            mailbox = Mailbox(
                workspace_id=workspace_id,
                email=email,
                access_token_encrypted=access_encrypted,
                refresh_token_encrypted=refresh_encrypted,
                token_expiry=expiry,
                is_active=True
            )
            db.add(mailbox)
            db.commit()
            db.refresh(mailbox)
        
        # Extract domain and create domain record
        domain_name = email.split("@")[1] if "@" in email else ""
        if domain_name:
            existing_domain = db.query(Domain).filter(
                Domain.workspace_id == workspace_id,
                Domain.domain == domain_name
            ).first()
            
            if not existing_domain:
                # New domain - create it
                # Note: mailbox_id is set to the first mailbox that connected with this domain
                domain = Domain(
                    workspace_id=workspace_id,
                    mailbox_id=mailbox.id,
                    domain=domain_name
                )
                db.add(domain)
                
                # Run initial domain check
                spf_valid, spf_record = DomainService.check_spf(domain_name)
                dmarc_valid, dmarc_record = DomainService.check_dmarc(domain_name)
                
                domain.spf_valid = spf_valid
                domain.spf_record = spf_record
                domain.dmarc_valid = dmarc_valid
                domain.dmarc_record = dmarc_record
                
                db.commit()
            # If domain already exists, we don't modify it - multiple mailboxes can share the same domain
        
        # Redirect to frontend success page
        from app.config import settings
        
        # Robust path construction: Ensure /app is present exactly once
        base_url = settings.frontend_url.rstrip("/")
        if not base_url.endswith("/app"):
            base_url += "/app"
            
        success_url = f"{base_url}/dashboard?step=inbox-connected&email={email}"
        logger.info(f"OAuth Callback: Redirecting to success: {success_url}")
        return RedirectResponse(url=success_url)
        
    except Exception as e:
        logger.error(f"OAuth Callback Error: {str(e)}")
        logger.error(traceback.format_exc())
        
        from app.config import settings
        base_url = settings.frontend_url.rstrip("/")
        if not base_url.endswith("/app"):
            base_url += "/app"
            
        error_url = f"{base_url}/dashboard?step=inbox-error&error={str(e)}"
        logger.info(f"OAuth Callback: Redirecting to error: {error_url}")
        return RedirectResponse(url=error_url)


@router.get("/", response_model=List[MailboxResponse])
async def list_mailboxes(
    workspace_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all connected mailboxes for a workspace.
    """
    # Verify workspace belongs to user
    workspace = db.query(Workspace).filter(
        Workspace.id == workspace_id,
        Workspace.user_id == current_user.id
    ).first()
    
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )
    
    mailboxes = db.query(Mailbox).filter(
        Mailbox.workspace_id == workspace_id
    ).all()
    
    return mailboxes


@router.delete("/{mailbox_id}", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect_mailbox(
    mailbox_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Disconnect a mailbox (marks as inactive).
    """
    mailbox = db.query(Mailbox).join(Workspace).filter(
        Mailbox.id == mailbox_id,
        Workspace.user_id == current_user.id
    ).first()
    
    if not mailbox:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mailbox not found"
        )
    
    mailbox.is_active = False
    db.commit()
