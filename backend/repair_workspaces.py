from app.database import engine
from sqlalchemy import text

statements = [
    # workspaces table repair
    "ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS what_you_sell TEXT",
    "ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS target_industry VARCHAR(255)",
    "ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS target_role VARCHAR(255)",
    "ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS target_region VARCHAR(255)",
    "ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS offer_type VARCHAR(100)",
    "ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS safety_preference VARCHAR(50) DEFAULT 'MEDIUM'",
    "ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS has_leads BOOLEAN DEFAULT FALSE",
    "ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS meeting_days JSON",
    "ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS meeting_time_start VARCHAR(10)",
    "ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS meeting_time_end VARCHAR(10)",
]

with engine.connect() as conn:
    print("Executing Workspace SQL repairs...")
    for stmt in statements:
        try:
            conn.execute(text(stmt))
            conn.commit()
            print(f"Executed: {stmt}")
        except Exception as e:
            print(f"FAILED: {stmt} -> {str(e)}")
    print("SQL Repairs Finished.")
