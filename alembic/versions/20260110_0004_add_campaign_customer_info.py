"""add campaign.customer_info JSON column

Revision ID: 20260110_0004
Revises: 20241230_0003_003_final_schema_repair
Create Date: 2026-01-10 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20260110_0004'
down_revision = '20241230_0003_003_final_schema_repair'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('campaigns', sa.Column('customer_info', sa.JSON(), nullable=True))


def downgrade():
    op.drop_column('campaigns', 'customer_info')
