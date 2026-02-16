"""
Leads router - CSV upload, column mapping, web sourcing.
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.models import User, Workspace, Lead, SuppressionEntry
from app.schemas import (
    LeadResponse, CSVColumnMapping, CSVUploadResponse,
    WebSourceRequest, WebSourceResponse,
    LeadGenRequest, LeadGenSearchResponse, LeadGenImportRequest,
    LeadManualImportRequest, LeadGenEnrichRequest, LeadGenCandidate
)
from app.utils.dependencies import get_current_user
from app.services.lead_service import LeadService
from app.services.lead_gen_service import LeadGenService

router = APIRouter()


@router.post("/upload-csv", response_model=CSVUploadResponse)
async def upload_csv(
    workspace_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload a CSV file and get column headers for mapping.
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
    
    # Read and parse CSV
    content = await file.read()
    columns, rows = LeadService.parse_csv(content)
    
    if not columns:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not parse CSV file or file is empty"
        )
    
    return CSVUploadResponse(
        total_rows=len(rows),
        valid_leads=0,  # Will be calculated after mapping
        invalid_emails=0,
        role_emails=0,
        columns=columns
    )


@router.post("/map-columns", response_model=List[LeadResponse])
async def map_columns_and_import(
    workspace_id: int,
    file: UploadFile = File(...),
    email: str = Form(...),
    first_name: Optional[str] = Form(None),
    last_name: Optional[str] = Form(None),
    company: Optional[str] = Form(None),
    title: Optional[str] = Form(None),
    exclude_role_emails: bool = Form(False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Map CSV columns and import leads.
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
    
    # Parse CSV
    content = await file.read()
    columns, rows = LeadService.parse_csv(content)
    
    # Process leads
    # Process leads
    column_mapping = {
        'email': email,
        'first_name': first_name,
        'last_name': last_name,
        'company': company,
        'title': title,
    }
    
    leads_data, invalid_count, role_count = LeadService.process_csv_leads(
        rows, column_mapping
    )
    
    # Get suppression list for this workspace
    suppressed_emails = set(
        entry.email for entry in 
        db.query(SuppressionEntry).filter(
            SuppressionEntry.workspace_id == workspace_id
        ).all()
    )
    
    # Create lead records
    created_leads = []
    for lead_data in leads_data:
        # Skip role emails if requested
        if exclude_role_emails and lead_data['is_role_email']:
            continue
        
        # Skip suppressed emails
        if lead_data['email'] in suppressed_emails:
            continue
        
        # Check if lead already exists
        existing = db.query(Lead).filter(
            Lead.workspace_id == workspace_id,
            Lead.email == lead_data['email']
        ).first()
        
        if existing:
            continue
        
        lead = Lead(
            workspace_id=workspace_id,
            email=lead_data['email'],
            first_name=lead_data['first_name'],
            last_name=lead_data['last_name'],
            company=lead_data['company'],
            title=lead_data['title'],
            is_valid_email=lead_data['is_valid_email'],
            is_role_email=lead_data['is_role_email'],
            source=lead_data['source'],
            source_url=lead_data['source_url'],
        )
        db.add(lead)
        created_leads.append(lead)
    
    db.commit()
    
    # Refresh to get IDs
    for lead in created_leads:
        db.refresh(lead)
    
    return created_leads


@router.post("/source", response_model=WebSourceResponse)
async def source_leads(
    workspace_id: int,
    request: WebSourceRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Source leads from a list of company domains.
    Crawls homepage, /about, /contact, /team pages.
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
    
    # Source leads
    leads_data, domains_searched = LeadService.source_leads_from_domains(request.domains)
    
    # Get suppression list
    suppressed_emails = set(
        entry.email for entry in 
        db.query(SuppressionEntry).filter(
            SuppressionEntry.workspace_id == workspace_id
        ).all()
    )
    
    # Create lead records
    created_leads = []
    for lead_data in leads_data:
        # Skip suppressed emails
        if lead_data['email'] in suppressed_emails:
            continue
        
        # Check if lead already exists
        existing = db.query(Lead).filter(
            Lead.workspace_id == workspace_id,
            Lead.email == lead_data['email']
        ).first()
        
        if existing:
            continue
        
        lead = Lead(
            workspace_id=workspace_id,
            email=lead_data['email'],
            first_name=lead_data['first_name'],
            last_name=lead_data['last_name'],
            company=lead_data['company'],
            title=lead_data['title'],
            is_valid_email=lead_data['is_valid_email'],
            is_role_email=lead_data['is_role_email'],
            source=lead_data['source'],
            source_url=lead_data['source_url'],
        )
        db.add(lead)
        created_leads.append(lead)
    
    db.commit()
    
    for lead in created_leads:
        db.refresh(lead)
    
    return WebSourceResponse(
        leads_found=len(created_leads),
        domains_searched=domains_searched,
        leads=created_leads
    )


@router.get("/", response_model=List[LeadResponse])
async def list_leads(
    workspace_id: int,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List leads for a workspace.
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
    
    leads = db.query(Lead).filter(
        Lead.workspace_id == workspace_id
    ).offset(skip).limit(limit).all()
    
    return leads


@router.post("/leadgen/search", response_model=LeadGenSearchResponse)
async def leadgen_search(
    workspace_id: int,
    request: LeadGenRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Search the web for businesses and extract contacts with full data fields.
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

    suppressed_emails = set(
        entry.email.lower() for entry in
        db.query(SuppressionEntry).filter(
            SuppressionEntry.workspace_id == workspace_id
        ).all()
    )
    existing_emails = set(
        email.lower() for (email,) in
        db.query(Lead.email).filter(
            Lead.workspace_id == workspace_id
        ).all()
    )

    desired = request.desired_count or 20
    desired = max(10, min(desired, 20))

    leads, companies = await run_in_threadpool(
        LeadGenService.search_with_companies,
        request.query,
        request.location,
        suppressed_emails | existing_emails,
        None,
        desired,
        None,
    )

    return LeadGenSearchResponse(
        query=request.query,
        location=request.location,
        leads=leads,
        companies=companies,
    )


@router.post("/leadgen/import", response_model=List[LeadResponse])
async def leadgen_import(
    workspace_id: int,
    request: LeadGenImportRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Import lead-gen candidates into the workspace.
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

    suppressed_emails = set(
        entry.email.lower() for entry in
        db.query(SuppressionEntry).filter(
            SuppressionEntry.workspace_id == workspace_id
        ).all()
    )

    created_leads = []
    for lead_data in request.leads:
        email_lower = lead_data.email.lower()
        if email_lower in suppressed_emails:
            continue

        existing = db.query(Lead).filter(
            Lead.workspace_id == workspace_id,
            Lead.email == lead_data.email
        ).first()
        if existing:
            continue

        lead = Lead(
            workspace_id=workspace_id,
            email=lead_data.email,
            first_name=lead_data.first_name,
            last_name=lead_data.last_name,
            company=lead_data.company,
            title=lead_data.title,
            is_valid_email=True,
            is_role_email=False,
            source="lead_gen",
            source_url=lead_data.source_url or lead_data.website,
        )
        db.add(lead)
        created_leads.append(lead)

    db.commit()

    for lead in created_leads:
        db.refresh(lead)

    return created_leads


@router.post("/leadgen/enrich", response_model=List[LeadGenCandidate])
async def leadgen_enrich(
    workspace_id: int,
    request: LeadGenEnrichRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Enrich a single company by crawling its site for contacts.
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

    leads = await run_in_threadpool(
        LeadGenService.enrich_company,
        request.website,
        request.company,
        10,
    )

    return leads


@router.post("/manual", response_model=List[LeadResponse])
async def manual_import(
    workspace_id: int,
    request: LeadManualImportRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Manually import leads into the workspace.
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

    suppressed_emails = set(
        entry.email.lower() for entry in
        db.query(SuppressionEntry).filter(
            SuppressionEntry.workspace_id == workspace_id
        ).all()
    )

    created_leads = []
    for lead_data in request.leads:
        email_lower = lead_data.email.lower()
        if email_lower in suppressed_emails:
            continue

        existing = db.query(Lead).filter(
            Lead.workspace_id == workspace_id,
            Lead.email == lead_data.email
        ).first()
        if existing:
            continue

        # Basic email validation check again just in case
        is_valid, normalized_email = LeadService.validate_email_address(lead_data.email)
        if not is_valid:
            continue

        is_role = LeadService.is_role_email(normalized_email)

        lead = Lead(
            workspace_id=workspace_id,
            email=normalized_email,
            first_name=lead_data.first_name,
            last_name=lead_data.last_name,
            company=lead_data.company,
            title=lead_data.title,
            is_valid_email=True,
            is_role_email=is_role,
            source="manual",
            source_url=None,
        )
        db.add(lead)
        created_leads.append(lead)

    db.commit()

    for lead in created_leads:
        db.refresh(lead)

    return created_leads


@router.delete("/{lead_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_lead(
    lead_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a lead.
    """
    lead = db.query(Lead).join(Workspace).filter(
        Lead.id == lead_id,
        Workspace.user_id == current_user.id
    ).first()
    
    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lead not found"
        )
    
    db.delete(lead)
    db.commit()
