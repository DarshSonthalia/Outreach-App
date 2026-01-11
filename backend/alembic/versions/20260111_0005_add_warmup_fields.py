"""add warmup fields

Revision ID: 005_add_warmup_fields
Revises: 004_add_campaign_customer_info
Create Date: 2026-01-11 11:40:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '005_add_warmup_fields'
down_revision = '004_add_campaign_customer_info'
branch_labels = None
depends_on = None

def upgrade():
    # Helper to check if column exists
    conn = op.get_bind()
    
    # Workspaces
    res_w = conn.execute(sa.text("SELECT column_name FROM information_schema.columns WHERE table_name='workspaces'")).fetchall()
    cols_w = [r[0] for r in res_w]
    
    if 'warmup_enabled' not in cols_w:
        op.add_column('workspaces', sa.Column('warmup_enabled', sa.Boolean(), server_default='false', nullable=False))
    if 'warmup_start_date' not in cols_w:
        op.add_column('workspaces', sa.Column('warmup_start_date', sa.DateTime(), nullable=True))

    # Domains
    res_d = conn.execute(sa.text("SELECT column_name FROM information_schema.columns WHERE table_name='domains'")).fetchall()
    cols_d = [r[0] for r in res_d]
    
    if 'warmup_day' not in cols_d:
        op.add_column('domains', sa.Column('warmup_day', sa.Integer(), server_default='0', nullable=False))
    if 'warmup_completed' not in cols_d:
        op.add_column('domains', sa.Column('warmup_completed', sa.Boolean(), server_default='false', nullable=False))


def downgrade():
    conn = op.get_bind()
    
    # Domains
    res_d = conn.execute(sa.text("SELECT column_name FROM information_schema.columns WHERE table_name='domains'")).fetchall()
    cols_d = [r[0] for r in res_d]
    if 'warmup_completed' in cols_d:
        op.drop_column('domains', 'warmup_completed')
    if 'warmup_day' in cols_d:
        op.drop_column('domains', 'warmup_day')
        
    # Workspaces
    res_w = conn.execute(sa.text("SELECT column_name FROM information_schema.columns WHERE table_name='workspaces'")).fetchall()
    cols_w = [r[0] for r in res_w]
    if 'warmup_start_date' in cols_w:
        op.drop_column('workspaces', 'warmup_start_date')
    if 'warmup_enabled' in cols_w:
        op.drop_column('workspaces', 'warmup_enabled')
