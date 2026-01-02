from app.database import engine
from sqlalchemy import inspect

def check_db():
    insp = inspect(engine)
    
    # Table: campaigns
    c_cols = [c['name'] for c in insp.get_columns('campaigns')]
    print(f"campaigns.safety_level: {'PRESENT' if 'safety_level' in c_cols else 'MISSING'}")
    
    # Table: campaign_leads
    cl_cols = [c['name'] for c in insp.get_columns('campaign_leads')]
    print(f"campaign_leads.retry_count: {'PRESENT' if 'retry_count' in cl_cols else 'MISSING'}")
    print(f"campaign_leads.next_retry_at: {'PRESENT' if 'next_retry_at' in cl_cols else 'MISSING'}")

if __name__ == "__main__":
    check_db()
