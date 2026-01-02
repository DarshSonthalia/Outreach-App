from app.database import engine
from sqlalchemy import text

statements = [
    # campaigns table
    "ALTER TABLE campaigns ADD COLUMN IF NOT EXISTS safety_level VARCHAR(50) DEFAULT 'MEDIUM'",
    "ALTER TABLE campaigns ADD COLUMN IF NOT EXISTS launched_at TIMESTAMP WITHOUT TIME ZONE",
    
    # campaign_leads table
    "ALTER TABLE campaign_leads ADD COLUMN IF NOT EXISTS retry_count INTEGER DEFAULT 0",
    "ALTER TABLE campaign_leads ADD COLUMN IF NOT EXISTS next_retry_at TIMESTAMP WITHOUT TIME ZONE",
]

with engine.connect() as conn:
    print("Executing manual SQL repairs...")
    for stmt in statements:
        try:
            conn.execute(text(stmt))
            conn.commit()
            print(f"Executed: {stmt}")
        except Exception as e:
            print(f"FAILED: {stmt} -> {str(e)}")
    print("SQL Repairs Finished.")
