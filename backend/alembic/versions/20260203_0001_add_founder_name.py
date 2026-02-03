"""add founder name

Revision ID: 20260203_0001
Revises: 20260110_0004
Create Date: 2026-02-03 12:50:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260203_0001'
down_revision = '007_update_booking_events'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('workspaces', sa.Column('founder_name', sa.String(length=255), nullable=True))


def downgrade():
    op.drop_column('workspaces', 'founder_name')
