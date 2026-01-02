from app.database import engine
from sqlalchemy import text

def inspect_workspaces():
    with engine.connect() as conn:
        print("Inspecting 'workspaces' columns...")
        res = conn.execute(text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'workspaces'"))
        for row in res:
            print(f"- {row[0]}: {row[1]}")

if __name__ == "__main__":
    inspect_workspaces()
