"""
Domain router - SPF/DMARC checks.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime

from app.database import get_db
from app.models import User, Workspace, Domain
from app.schemas import DomainCheckRequest, DomainResponse
from app.utils.dependencies import get_current_user
from app.services.domain_service import DomainService

router = APIRouter()


@router.post("/check")
async def check_domain(
    request: DomainCheckRequest,
    workspace_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Run SPF and DMARC checks on a domain.
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
    
    # Run checks
    spf_valid, spf_record = DomainService.check_spf(request.domain)
    dmarc_valid, dmarc_record = DomainService.check_dmarc(request.domain)
    
    # Get or create domain record
    domain = db.query(Domain).filter(
        Domain.workspace_id == workspace_id,
        Domain.domain == request.domain
    ).first()
    
    if domain:
        domain.spf_valid = spf_valid
        domain.spf_record = spf_record
        domain.dmarc_valid = dmarc_valid
        domain.dmarc_record = dmarc_record
        domain.last_checked_at = datetime.utcnow()
    else:
        domain = Domain(
            workspace_id=workspace_id,
            domain=request.domain,
            spf_valid=spf_valid,
            spf_record=spf_record,
            dmarc_valid=dmarc_valid,
            dmarc_record=dmarc_record,
            last_checked_at=datetime.utcnow()
        )
        db.add(domain)
    
    db.commit()
    db.refresh(domain)
    
    # Return with health status
    health = DomainService.get_domain_health_status(spf_valid, dmarc_valid)
    
    return {
        "domain": domain,
        "health": health
    }


@router.get("/{domain_id}", response_model=DomainResponse)
async def get_domain(
    domain_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get domain details by ID.
    """
    domain = db.query(Domain).join(Workspace).filter(
        Domain.id == domain_id,
        Workspace.user_id == current_user.id
    ).first()
    
    if not domain:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Domain not found"
        )
    
    return domain
