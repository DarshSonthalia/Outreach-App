"""
Campaign leads router - follow-up controls.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import CampaignLead, Campaign, Workspace, User
from app.schemas import CancelFollowupsRequest
from app.utils.dependencies import get_current_user
from app.services.followup_service import FollowupService
from app.enums import CancelReason

router = APIRouter()


@router.post("/{campaign_lead_id}/cancel-followups")
async def cancel_followups(
    campaign_lead_id: int,
    request: CancelFollowupsRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Manually cancel follow-ups for a campaign lead.
    """
    campaign_lead = db.query(CampaignLead).join(Campaign).join(Workspace).filter(
        CampaignLead.id == campaign_lead_id,
        Workspace.user_id == current_user.id
    ).first()

    if not campaign_lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign lead not found"
        )

    reason = CancelReason.MANUAL if request.reason.upper() == "MANUAL" else CancelReason.MANUAL
    FollowupService.cancel_followups(
        db,
        campaign_lead_id,
        reason,
        request.detail or "User cancelled from UI"
    )

    return {"status": "ok"}
