from app.database import engine
from sqlalchemy import inspect

def check_db():
    insp = inspect(engine)
    tables = ['users', 'workspaces', 'mailboxes', 'domains', 'leads', 'campaigns', 'campaign_leads', 'messages', 'booking_events']
    
    for table in tables:
        if not insp.has_table(table):
            print(f"TABLE {table} MISSING")
            continue
        cols = [c['name'] for c in insp.get_columns(table)]
        print(f"TABLE {table}: {cols}")

if __name__ == "__main__":
    check_db()
