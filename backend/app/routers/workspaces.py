"""
Workspace router - create workspace, update setup wizard answers.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models import User, Workspace
from app.schemas import WorkspaceCreate, WorkspaceSetup, WorkspaceResponse
from app.utils.dependencies import get_current_user

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
    workspace = Workspace(
        user_id=current_user.id,
        name=workspace_data.name
    )
    db.add(workspace)
    db.commit()
    db.refresh(workspace)
    
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
