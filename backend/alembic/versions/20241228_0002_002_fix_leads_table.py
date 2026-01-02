"""Fix leads table schema

Revision ID: 002_fix_leads_table
Revises: 001_v1_initial_schema
Create Date: 2024-12-28 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '002_fix_leads_table'
down_revision: Union[str, None] = '001_v1_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Rename is_valid to is_valid_email matches model
    op.alter_column('leads', 'is_valid', new_column_name='is_valid_email')
    
    # Add is_role_email
    op.add_column('leads', sa.Column('is_role_email', sa.Boolean(), server_default='false', nullable=False))


def downgrade() -> None:
    op.drop_column('leads', 'is_role_email')
    op.alter_column('leads', 'is_valid_email', new_column_name='is_valid')
