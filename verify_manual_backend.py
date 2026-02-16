import sys
import os
import pytest
from unittest.mock import MagicMock, patch

# Add backend to sys.path
backend_path = os.path.join(os.getcwd(), "backend")
if backend_path not in sys.path:
    sys.path.append(backend_path)

from app.routers.leads import manual_import
from app.schemas.schemas import LeadManualImportRequest, LeadCreate
from app.models import Workspace, Lead, SuppressionEntry

@pytest.mark.asyncio
async def test_manual_import_success():
    # Setup mocks
    mock_db = MagicMock()
    mock_user = MagicMock(id=1)
    workspace_id = 1
    
    # Mock workspace check
    mock_workspace = Workspace(id=workspace_id, user_id=1)
    mock_db.query.return_value.filter.return_value.first.return_value = mock_workspace
    
    # Mock suppression list (empty)
    mock_db.query.return_value.filter.return_value.all.return_value = []
    
    # Mock existing leads check (none exist)
    # We need to handle the chain: db.query(Lead).filter(...).first()
    # Let's use a side effect to distinguish between Workspace query and Lead query
    def query_side_effect(model):
        q = MagicMock()
        if model == Workspace:
            q.filter.return_value.first.return_value = mock_workspace
        elif model == SuppressionEntry:
            q.filter.return_value.all.return_value = []
        elif model == Lead:
            # First Lead query is usually to check if it exists
            q.filter.return_value.first.return_value = None
        return q
        
    mock_db.query.side_effect = query_side_effect
    
    # Request data
    request = LeadManualImportRequest(leads=[
        LeadCreate(email="test@example.com", first_name="Test", last_name="User")
    ])
    
    # Call the function
    # Note: manual_import is async
    with patch("app.routers.leads.LeadService") as mock_lead_service:
        mock_lead_service.validate_email_address.return_value = (True, "test@example.com")
        mock_lead_service.is_role_email.return_value = False
        
        result = await manual_import(workspace_id, request, mock_user, mock_db)
        
        # Assertions
        assert len(result) == 1
        assert result[0].email == "test@example.com"
        assert mock_db.add.called
        assert mock_db.commit.called

if __name__ == "__main__":
    # Run test manually if executed directly
    import asyncio
    asyncio.run(test_manual_import_success())
    print("Verification script finished successfully!")
