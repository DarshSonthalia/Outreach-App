from app.database import engine
from sqlalchemy import inspect

def check_db():
    insp = inspect(engine)
    
    # Table: campaigns
    if insp.has_table('campaigns'):
        cols = [c['name'] for c in insp.get_columns('campaigns')]
        print(f"campaigns columns: {cols}")
        for col in ['id', 'workspace_id', 'mailbox_id', 'name', 'status', 'subject', 'body', 'safety_level']:
            print(f"- campaigns.{col}: {'OK' if col in cols else 'MISSING'}")
            
    # Table: campaign_leads
    if insp.has_table('campaign_leads'):
        cols = [c['name'] for c in insp.get_columns('campaign_leads')]
        print(f"campaign_leads columns: {cols}")
        for col in ['campaign_id', 'lead_id', 'status', 'retry_count', 'next_retry_at']:
            print(f"- campaign_leads.{col}: {'OK' if col in cols else 'MISSING'}")

if __name__ == "__main__":
    check_db()
