"""add campaign.customer_info JSON column

Revision ID: 004_add_campaign_customer_info
Revises: 003_final_schema_repair
Create Date: 2026-01-10 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '004_add_campaign_customer_info'
down_revision = '003_final_schema_repair'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    # Only add column if it doesn't already exist
    res = conn.execute(sa.text("SELECT column_name FROM information_schema.columns WHERE table_name='campaigns'")).fetchall()
    existing_cols = [r[0] for r in res]
    if 'customer_info' not in existing_cols:
        op.add_column('campaigns', sa.Column('customer_info', sa.JSON(), nullable=True))


def downgrade():
    conn = op.get_bind()
    res = conn.execute(sa.text("SELECT column_name FROM information_schema.columns WHERE table_name='campaigns'")).fetchall()
    existing_cols = [r[0] for r in res]
    if 'customer_info' in existing_cols:
        op.drop_column('campaigns', 'customer_info')
