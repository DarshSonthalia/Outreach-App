from app.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    res = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='campaigns' ORDER BY ordinal_position"))
    cols = [r[0] for r in res.fetchall()]
    print('campaigns columns:')
    for c in cols:
        print(' -', c)
