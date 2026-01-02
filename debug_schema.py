from app.database import engine
from sqlalchemy import inspect

def check_schema():
    insp = inspect(engine)
    cols = insp.get_columns('campaign_leads')
    names = [c['name'] for c in cols]
    print(f"Columns in campaign_leads: {names}")
    
    if 'retry_count' in names:
        print("campaign_leads.retry_count EXISTS")
    else:
        print("campaign_leads.retry_count MISSING")
        
    if 'next_retry_at' in names:
        print("campaign_leads.next_retry_at EXISTS")
    else:
        print("campaign_leads.next_retry_at MISSING")

    cols_c = insp.get_columns('campaigns')
    names_c = [c['name'] for c in cols_c]
    if 'safety_level' in names_c:
        print("campaigns.safety_level EXISTS")
    else:
        print("campaigns.safety_level MISSING")

if __name__ == "__main__":
    check_schema()
