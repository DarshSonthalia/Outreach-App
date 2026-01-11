from app.database import engine
from sqlalchemy import text
import json
from datetime import datetime

with engine.connect() as conn:
    now = datetime.utcnow()
    customer_info = {'company': 'ACME', 'industry': 'testing', 'notes': 'inserted-by-sql'}
    insert_sql = text(
        """
        INSERT INTO campaigns (workspace_id, mailbox_id, name, subject, body, customer_info, created_at, updated_at)
        VALUES (:workspace_id, :mailbox_id, :name, :subject, :body, CAST(:customer_info AS JSON), :created_at, :updated_at)
        RETURNING id
        """
    )
    # Use PostgreSQL cast for JSON; if using sqlite, remove cast
    params = {
        'workspace_id': 1,
        'mailbox_id': 1,
        'name': 'smoke-sql-campaign',
        'subject': 'SQL smoke',
        'body': 'Inserted via raw SQL',
        'customer_info': json.dumps(customer_info),
        'created_at': now,
        'updated_at': now,
    }
    try:
        res = conn.execute(insert_sql, params)
        row = res.fetchone()
        cid = row[0]
        print('Inserted campaign id=', cid)
    except Exception as e:
        print('Insert failed:', e)
        # Try fallback for sqlite (no ::json)
        try:
            insert_sql2 = text(
                """
                INSERT INTO campaigns (workspace_id, mailbox_id, name, subject, body, customer_info, created_at, updated_at)
                  VALUES (:workspace_id, :mailbox_id, :name, :subject, :body, CAST(:customer_info AS JSON), :created_at, :updated_at)
                RETURNING id
                """
            )
            res = conn.execute(insert_sql2, params)
            row = res.fetchone()
            cid = row[0]
            print('Inserted campaign id (fallback)=', cid)
        except Exception as e2:
            print('Fallback insert failed:', e2)
            raise

    # fetch it back
    sel = conn.execute(text('SELECT id, customer_info FROM campaigns WHERE id = :id'), {'id': cid})
    r = sel.fetchone()
    print('Fetched:', r)
