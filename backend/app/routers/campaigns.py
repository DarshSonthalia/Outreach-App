"""
Campaign router - create, configure, launch, and monitor campaigns.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timedelta

from app.database import get_db
from app.models import (
    User, Workspace, Mailbox, Lead, Campaign, CampaignLead, Domain, Event, BookingEvent,
    CampaignStatus, CampaignLeadStatus, Message, MessageDirection,
    ReplyClassification
)
from app.schemas import (
    CampaignCreate, CampaignEmailContent, CampaignResponse,
    CampaignDashboard, CampaignPreview
)
from app.utils.dependencies import get_current_user
from app.services.safety_service import SafetyService
from app.enums import FollowupState

router = APIRouter()


@router.post("/", response_model=CampaignResponse, status_code=status.HTTP_201_CREATED)
async def create_campaign(
    campaign_data: CampaignCreate,
    workspace_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new campaign with selected leads.
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
    
    # Verify mailbox belongs to workspace
    mailbox = db.query(Mailbox).filter(
        Mailbox.id == campaign_data.mailbox_id,
        Mailbox.workspace_id == workspace_id,
        Mailbox.is_active == True
    ).first()
    
    if not mailbox:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mailbox not found or inactive"
        )
    
    # Create campaign
    campaign = Campaign(
        workspace_id=workspace_id,
        mailbox_id=campaign_data.mailbox_id,
        name=campaign_data.name,
        status=CampaignStatus.DRAFT,
        safety_level=workspace.safety_preference,
        customer_info=campaign_data.customer_info if getattr(campaign_data, 'customer_info', None) else None,
    )
    db.add(campaign)
    db.commit()

    # Backwards-compat: also persist as an Event for existing tooling (optional)
    if getattr(campaign_data, "customer_info", None):
        try:
            from app.models import Event
            evt = Event(
                entity_type="campaign",
                entity_id=campaign.id,
                action="CAMPAIGN_CUSTOMER_INFO",
                details=campaign_data.customer_info,
                explanation="Per-campaign customer info provided at creation",
            )
            db.add(evt)
            db.commit()
        except Exception:
            # Non-fatal: if Event insert fails, continue — primary storage is campaign.customer_info
            db.rollback()
    db.refresh(campaign)
    
    # Add leads to campaign
    leads = db.query(Lead).filter(
        Lead.id.in_(campaign_data.lead_ids),
        Lead.workspace_id == workspace_id
    ).all()
    
    for lead in leads:
        campaign_lead = CampaignLead(
            campaign_id=campaign.id,
            lead_id=lead.id,
            status=CampaignLeadStatus.PENDING
        )
        db.add(campaign_lead)
    
    db.commit()
    
    return campaign


@router.put("/{campaign_id}/emails", response_model=CampaignResponse)
async def set_email_content(
    campaign_id: int,
    content: CampaignEmailContent,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Set email content for a campaign.
    """
    campaign = db.query(Campaign).join(Workspace).filter(
        Campaign.id == campaign_id,
        Workspace.user_id == current_user.id
    ).first()
    
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found"
        )
    
    if campaign.status not in [CampaignStatus.DRAFT, CampaignStatus.PAUSED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot modify email content for running campaign"
        )
    
    campaign.subject = content.subject
    campaign.body = content.body
    campaign.followup_enabled = content.followup_enabled
    campaign.followup_delay_days = content.followup_delay_days
    campaign.followup_subject = content.followup_subject
    campaign.followup_body = content.followup_body
    campaign.max_followups = content.max_followups
    
    db.commit()
    db.refresh(campaign)
    
    return campaign


@router.get("/{campaign_id}/preview", response_model=CampaignPreview)
async def preview_campaign(
    campaign_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get preview of campaign before launch.
    Shows estimated timeline and safety explanation.
    """
    campaign = db.query(Campaign).join(Workspace).filter(
        Campaign.id == campaign_id,
        Workspace.user_id == current_user.id
    ).first()
    
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found"
        )
    
    # Count leads
    lead_count = db.query(CampaignLead).filter(
        CampaignLead.campaign_id == campaign_id
    ).count()
    
    # Get safety explanation
    safety_info = SafetyService.get_safety_explanation_for_campaign(db, campaign)
    daily_limit = safety_info['daily_limit']
    
    # Calculate estimated days
    estimated_days = (lead_count + daily_limit - 1) // daily_limit
    
    # Generate sample emails (first 3)
    sample_leads = db.query(CampaignLead).join(Lead).filter(
        CampaignLead.campaign_id == campaign_id
    ).limit(3).all()
    
    sample_emails = []
    for cl in sample_leads:
        sample_emails.append({
            "to": cl.lead.email,
            "subject": campaign.subject,
            "body": campaign.body,
            "first_name": cl.lead.first_name,
            "company": cl.lead.company
        })
    
    return CampaignPreview(
        total_leads=lead_count,
        estimated_days_to_complete=estimated_days,
        daily_send_limit=daily_limit,
        safety_explanation=safety_info['explanation'],
        sample_emails=sample_emails
    )


@router.post("/{campaign_id}/launch", response_model=CampaignResponse)
async def launch_campaign(
    campaign_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Launch a campaign. Schedules first batch of sends.
    """
    campaign = db.query(Campaign).join(Workspace).filter(
        Campaign.id == campaign_id,
        Workspace.user_id == current_user.id
    ).first()
    
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found"
        )
    
    if campaign.status != CampaignStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Campaign cannot be launched from state: {campaign.status.value}"
        )
    
    if not campaign.subject or not campaign.body:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Campaign must have subject and body before launching"
        )
    
    # Verify mailbox is active
    if not campaign.mailbox.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mailbox is not active"
        )
    
    # CRITICAL: Verify domain safety before launching
    # Get domain name from mailbox email
    domain_name = campaign.mailbox.email.split("@")[1] if "@" in campaign.mailbox.email else None
    
    if not domain_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid mailbox email format: {campaign.mailbox.email}"
        )
    
    # Query domain by name and workspace (not by mailbox_id, to support multiple mailboxes with same domain)
    domain = db.query(Domain).filter(
        Domain.workspace_id == campaign.mailbox.workspace_id,
        Domain.domain == domain_name
    ).first()
    
    if not domain:
        db.add(Event(
            entity_type="campaign",
            entity_id=campaign.id,
            action="LAUNCH_BLOCKED_DOMAIN_UNSAFE",
            details={"domain": domain_name, "reason": "domain_missing"},
            explanation=f"Launch blocked: domain {domain_name} not configured."
        ))
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Domain not configured for {domain_name}. Please connect the mailbox again."
        )

    if not domain.spf_valid or not domain.dmarc_valid:
        reasons = []
        if not domain.spf_valid:
            reasons.append("SPF invalid")
        if not domain.dmarc_valid:
            reasons.append("DMARC invalid")
        db.add(Event(
            entity_type="campaign",
            entity_id=campaign.id,
            action="LAUNCH_BLOCKED_DOMAIN_UNSAFE",
            details={
                "domain": domain.domain,
                "spf_valid": domain.spf_valid,
                "dmarc_valid": domain.dmarc_valid
            },
            explanation=f"Launch blocked: {', '.join(reasons)} for {domain.domain}."
        ))
        db.commit()
        if not domain.spf_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"SPF record invalid for domain {domain.domain}. Please fix your DNS settings before launching. Current SPF: {domain.spf_record or 'Not found'}"
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"DMARC record invalid for domain {domain.domain}. Please fix your DNS settings before launching. Current DMARC: {domain.dmarc_record or 'Not found'}"
        )
    
    # Schedule initial sends
    now = datetime.utcnow()
    campaign_leads = db.query(CampaignLead).filter(
        CampaignLead.campaign_id == campaign_id,
        CampaignLead.status == CampaignLeadStatus.PENDING
    ).all()
    
    # Schedule sends starting from now, distributed over time
    for i, cl in enumerate(campaign_leads):
        # Stagger sends by 1-2 minutes to appear more natural
        delay_minutes = i * 2
        first_send_at = now + timedelta(minutes=delay_minutes)
        cl.next_scheduled_at = first_send_at
        cl.followup_state = FollowupState.SCHEDULED
        cl.current_step = 0

        # Build schedule_json for UI transparency
        schedule = []
        for step in range(0, campaign.max_followups + 1):
            if step == 0:
                planned_at = first_send_at
                subject = campaign.subject or ""
                body_full = campaign.body or ""
                body_preview = (body_full[:100] + "...") if body_full else ""
            else:
                planned_at = first_send_at + timedelta(days=campaign.followup_delay_days * step)
                subject = campaign.followup_subject or campaign.subject or ""
                body_full = campaign.followup_body or ""
                body_preview = (body_full[:100] + "...") if body_full else "Follow-up email"
            schedule.append({
                "step": step,
                "planned_at": planned_at.isoformat(),
                "subject": subject,
                "body": body_full,
                "body_preview": body_preview,
                "status": "PENDING" if step == 0 else "PLANNED"
            })
        cl.schedule_json = schedule
    
    campaign.status = CampaignStatus.RUNNING
    campaign.launched_at = now
    campaign.pause_reason = None
    
    db.commit()
    db.refresh(campaign)
    
    return campaign


@router.post("/{campaign_id}/pause", response_model=CampaignResponse)
async def pause_campaign(
    campaign_id: int,
    reason: str = "Manually paused by user",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Pause a running campaign.
    """
    campaign = db.query(Campaign).join(Workspace).filter(
        Campaign.id == campaign_id,
        Workspace.user_id == current_user.id
    ).first()
    
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found"
        )
    
    campaign.status = CampaignStatus.PAUSED
    campaign.pause_reason = reason
    
    db.commit()
    db.refresh(campaign)
    
    return campaign


@router.post("/{campaign_id}/resume", response_model=CampaignResponse)
async def resume_campaign(
    campaign_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Resume a paused campaign.
    """
    campaign = db.query(Campaign).join(Workspace).filter(
        Campaign.id == campaign_id,
        Workspace.user_id == current_user.id
    ).first()
    
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found"
        )
    
    if campaign.status != CampaignStatus.PAUSED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Campaign is not paused"
        )
    
    campaign.status = CampaignStatus.RUNNING
    campaign.pause_reason = None
    
    # Re-schedule pending leads
    now = datetime.utcnow()
    pending_leads = db.query(CampaignLead).filter(
        CampaignLead.campaign_id == campaign_id,
        CampaignLead.status == CampaignLeadStatus.PENDING
    ).all()
    
    for i, cl in enumerate(pending_leads):
        cl.next_scheduled_at = now + timedelta(minutes=i * 2)
        cl.followup_state = FollowupState.SCHEDULED
    
    db.commit()
    db.refresh(campaign)
    
    return campaign


@router.get("/", response_model=List[CampaignResponse])
async def list_campaigns(
    workspace_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all campaigns for a workspace.
    """
    workspace = db.query(Workspace).filter(
        Workspace.id == workspace_id,
        Workspace.user_id == current_user.id
    ).first()
    
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )
    
    campaigns = db.query(Campaign).filter(
        Campaign.workspace_id == workspace_id
    ).order_by(Campaign.created_at.desc()).all()
    
    print(f"DEBUG: Returning {len(campaigns)} campaigns for workspace {workspace_id}")
    if campaigns:
        from app.schemas import CampaignResponse
        try:
            sample = CampaignResponse.from_orm(campaigns[0]).json()
            print(f"DEBUG: Sample Campaign JSON: {sample}")
        except:
            print(f"DEBUG: Could not serialize sample campaign to JSON")
    return campaigns


@router.get("/{campaign_id}/dashboard", response_model=CampaignDashboard)
async def get_campaign_dashboard(
    campaign_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get campaign dashboard with stats.
    """
    campaign = db.query(Campaign).join(Workspace).filter(
        Campaign.id == campaign_id,
        Workspace.user_id == current_user.id
    ).first()
    
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found"
        )
    
    # Get stats
    today = datetime.utcnow().date()
    start_of_today = datetime.combine(today, datetime.min.time())
    
    emails_sent_today = db.query(Message).join(CampaignLead).filter(
        CampaignLead.campaign_id == campaign_id,
        Message.direction == MessageDirection.OUTBOUND,
        Message.sent_at >= start_of_today
    ).count()
    
    total_sent = db.query(Message).join(CampaignLead).filter(
        CampaignLead.campaign_id == campaign_id,
        Message.direction == MessageDirection.OUTBOUND
    ).count()
    
    replies = db.query(Message).join(CampaignLead).filter(
        CampaignLead.campaign_id == campaign_id,
        Message.direction == MessageDirection.INBOUND
    ).count()
    
    # Count bookings from Calendly events tied to campaign leads
    lead_emails = [row[0] for row in db.query(Lead.email).join(CampaignLead).filter(
        CampaignLead.campaign_id == campaign_id
    ).all()]

    meetings = 0
    meetings_today = 0
    meetings_7d = 0
    if lead_emails:
        meetings = db.query(BookingEvent).filter(
            BookingEvent.invitee_email.in_(lead_emails),
            BookingEvent.event_type == "invitee.created"
        ).count()
        meetings_today = db.query(BookingEvent).filter(
            BookingEvent.invitee_email.in_(lead_emails),
            BookingEvent.event_type == "invitee.created",
            BookingEvent.received_at >= start_of_today
        ).count()
        meetings_7d = db.query(BookingEvent).filter(
            BookingEvent.invitee_email.in_(lead_emails),
            BookingEvent.event_type == "invitee.created",
            BookingEvent.received_at >= datetime.utcnow() - timedelta(days=7)
        ).count()
    
    # Get safety info
    safety_info = SafetyService.get_safety_explanation_for_campaign(db, campaign)
    
    result = CampaignDashboard(
        campaign_id=campaign.id,
        name=campaign.name,
        status=campaign.status,
        pause_reason=campaign.pause_reason,
        emails_sent_today=emails_sent_today,
        total_emails_sent=total_sent,
        replies_count=replies,
        meetings_booked=meetings,
        meetings_booked_today=meetings_today,
        meetings_booked_7d=meetings_7d,
        daily_limit=safety_info['daily_limit'],
        remaining_today=safety_info['remaining_today']
    )
    print(f"DEBUG: Dashboard for {campaign_id}: sent_today={emails_sent_today}, status={campaign.status}")
    return result


@router.get("/{campaign_id}/schedule")
async def get_campaign_schedule(
    campaign_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get campaign follow-up schedule per lead.
    """
    campaign = db.query(Campaign).join(Workspace).filter(
        Campaign.id == campaign_id,
        Workspace.user_id == current_user.id
    ).first()

    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found"
        )

    leads = db.query(CampaignLead).join(Lead).filter(
        CampaignLead.campaign_id == campaign_id
    ).all()

    items = []
    for cl in leads:
        lead = cl.lead
        schedule = cl.schedule_json or []
        if schedule:
            updated = []
            for item in schedule:
                step = item.get("step")
                body = item.get("body")
                if not body and step and step > 0:
                    body = campaign.followup_body or ""
                if not body and step == 0:
                    body = campaign.body or ""
                if body:
                    item = {**item, "body": body}
                updated.append(item)
            schedule = updated
        items.append({
            "campaign_lead_id": cl.id,
            "lead_email": lead.email,
            "lead_name": f"{lead.first_name or ''} {lead.last_name or ''}".strip() or None,
            "followup_state": cl.followup_state.value if cl.followup_state else None,
            "next_scheduled_at": cl.next_scheduled_at,
            "current_step": cl.current_step,
            "max_followups": campaign.max_followups,
            "cancel_reason": cl.cancel_reason.value if cl.cancel_reason else None,
            "cancel_detail": cl.cancel_detail,
            "cancelled_at": cl.cancelled_at,
            "schedule_json": schedule
        })

    return {
        "campaign_id": campaign.id,
        "campaign_name": campaign.name,
        "items": items
    }


@router.post("/{campaign_id}/resume", response_model=CampaignResponse)
async def resume_campaign_if_auth_fixed(
    campaign_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Fix B2: Resume a campaign that was paused due to mailbox re-authentication.
    
    Verifies that:
    1. Campaign exists and belongs to user
    2. Campaign is paused due to auth issue
    3. Mailbox is now active (user re-authenticated)
    
    If all checks pass, resumes the campaign with rescheduled sends.
    """
    campaign = db.query(Campaign).join(Workspace).filter(
        Campaign.id == campaign_id,
        Workspace.user_id == current_user.id
    ).first()
    
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found"
        )
    
    if campaign.status != CampaignStatus.PAUSED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Campaign is {campaign.status.value}, not paused"
        )
    
    # Check if pause reason indicates auth issue
    if not campaign.pause_reason or "re-authentication" not in campaign.pause_reason.lower():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Campaign paused for different reason: {campaign.pause_reason}. Use /pause endpoint to manually resume."
        )
    
    # Verify mailbox is now active
    from app.models import Mailbox
    mailbox = db.query(Mailbox).filter(Mailbox.id == campaign.mailbox_id).first()
    
    if not mailbox:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mailbox not found"
        )
    
    if not mailbox.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mailbox is still inactive. Please re-authenticate first."
        )
    
    # Resume campaign
    campaign.status = CampaignStatus.RUNNING
    campaign.pause_reason = None
    
    # Reschedule pending leads
    now = datetime.utcnow()
    pending_leads = db.query(CampaignLead).filter(
        CampaignLead.campaign_id == campaign_id,
        CampaignLead.status == CampaignLeadStatus.PENDING
    ).all()
    
    for i, cl in enumerate(pending_leads):
        cl.next_scheduled_at = now + timedelta(minutes=i * 2)
        cl.followup_state = FollowupState.SCHEDULED
    
    db.commit()
    db.refresh(campaign)
    
    return campaign


@router.delete("/{campaign_id}", response_model=CampaignResponse)
async def terminate_campaign(
    campaign_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Terminate a campaign. Sets status to COMPLETED and clears all pending schedules.
    """
    campaign = db.query(Campaign).join(Workspace).filter(
        Campaign.id == campaign_id,
        Workspace.user_id == current_user.id
    ).first()
    
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found"
        )
    
    # Soft terminate
    campaign.status = CampaignStatus.COMPLETED
    campaign.pause_reason = "Terminated by user"
    
    # Clear all pending schedules for this campaign
    db.query(CampaignLead).filter(
        CampaignLead.campaign_id == campaign_id
    ).update({
        "next_scheduled_at": None,
        "followup_state": FollowupState.COMPLETED.value,
        "status": CampaignLeadStatus.COMPLETED
    }, synchronize_session=False)
    
    db.commit()
    db.refresh(campaign)
    
    return campaign
