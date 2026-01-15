"""
Workspace router - create workspace, update setup wizard answers.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_
from celery.app.control import Inspect
from typing import List
from datetime import datetime

from app.database import get_db
from app.models import User, Workspace, Event, Mailbox, Domain, Campaign, CampaignLead
from app.schemas import WorkspaceCreate, WorkspaceSetup, WorkspaceResponse
from app.utils.dependencies import get_current_user
from app.services.safety_service import SafetyService
from app.celery_app import celery_app
from app.enums import CampaignStatus

router = APIRouter()


@router.post("/", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
async def create_workspace(
    workspace_data: WorkspaceCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new workspace for the user.
    """
    today = datetime.utcnow()
    workspace = Workspace(
        user_id=current_user.id,
        name=workspace_data.name,
        warmup_enabled=True,
        warmup_start_date=today
    )
    db.add(workspace)
    db.commit()
    db.refresh(workspace)
    
    # Log warm-up start
    event = Event(
        entity_type="workspace",
        entity_id=workspace.id,
        action="WARMUP_STARTED",
        explanation="Domain warm-up started automatically for new workspace."
    )
    db.add(event)
    db.commit()
    
    return workspace


@router.get("/", response_model=List[WorkspaceResponse])
async def list_workspaces(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all workspaces for the current user.
    """
    workspaces = db.query(Workspace).filter(
        Workspace.user_id == current_user.id
    ).all()
    return workspaces


@router.get("/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace(
    workspace_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific workspace by ID.
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
    
    return workspace


@router.put("/{workspace_id}/setup", response_model=WorkspaceResponse)
async def update_workspace_setup(
    workspace_id: int,
    setup_data: WorkspaceSetup,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update workspace with wizard setup answers.
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
    
    # Update fields from setup data
    workspace.what_you_sell = setup_data.what_you_sell
    workspace.target_industry = setup_data.target_industry
    workspace.target_role = setup_data.target_role
    workspace.target_region = setup_data.target_region
    workspace.offer_type = setup_data.offer_type
    workspace.safety_preference = setup_data.safety_preference
    workspace.meeting_days = setup_data.meeting_days
    workspace.meeting_time_start = setup_data.meeting_time_start
    workspace.meeting_time_end = setup_data.meeting_time_end
    workspace.has_leads = setup_data.has_leads
    
    db.commit()
    db.refresh(workspace)
    
    return workspace


@router.get("/{workspace_id}/safety-status")
async def get_safety_status(
    workspace_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get safety and deliverability status for a workspace.
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

    inspect = Inspect(app=celery_app)
    active_workers = inspect.active()
    workers_online = bool(active_workers) and len(active_workers) > 0

    mailboxes = db.query(Mailbox).filter(
        Mailbox.workspace_id == workspace_id
    ).all()

    mailbox_items = []
    for mailbox in mailboxes:
        daily_limit = SafetyService.get_daily_limit(mailbox)
        sent_today = SafetyService.get_daily_send_count(db, mailbox.id)
        mailbox_campaigns = db.query(Campaign).filter(Campaign.mailbox_id == mailbox.id).all()
        paused_campaign = next((c for c in mailbox_campaigns if c.status == CampaignStatus.PAUSED), None)
        throttled_campaign = next((c for c in mailbox_campaigns if c.status == CampaignStatus.THROTTLED), None)

        mailbox_items.append({
            "mailbox_id": mailbox.id,
            "email": mailbox.email,
            "daily_limit": daily_limit,
            "sent_today": sent_today,
            "throttled": throttled_campaign is not None,
            "paused": paused_campaign is not None,
            "pause_reason": paused_campaign.pause_reason if paused_campaign else None
        })

    domains = db.query(Domain).filter(Domain.workspace_id == workspace_id).all()
    domain_items = [{
        "domain": d.domain,
        "spf_valid": d.spf_valid,
        "dmarc_valid": d.dmarc_valid,
        "warmup_day": d.warmup_day,
        "warmup_completed": d.warmup_completed
    } for d in domains]

    campaign_ids = [c.id for c in db.query(Campaign).filter(Campaign.workspace_id == workspace_id).all()]
    campaign_lead_ids = [cl.id for cl in db.query(CampaignLead).join(Campaign).filter(
        Campaign.workspace_id == workspace_id
    ).all()]
    mailbox_ids = [m.id for m in mailboxes]
    domain_ids = [d.id for d in domains]

    events = db.query(Event).filter(
        or_(
            (Event.entity_type == "campaign") & (Event.entity_id.in_(campaign_ids)),
            (Event.entity_type == "campaign_lead") & (Event.entity_id.in_(campaign_lead_ids)),
            (Event.entity_type == "mailbox") & (Event.entity_id.in_(mailbox_ids)),
            (Event.entity_type == "domain") & (Event.entity_id.in_(domain_ids)),
        )
    ).order_by(Event.timestamp.desc()).limit(20).all()

    recent_events = [{
        "entity_type": e.entity_type,
        "entity_id": e.entity_id,
        "action": e.action,
        "details": e.details,
        "explanation": e.explanation,
        "timestamp": e.timestamp
    } for e in events]

    return {
        "workers_online": workers_online,
        "mailboxes": mailbox_items,
        "domains": domain_items,
        "recent_safety_events": recent_events
    }
