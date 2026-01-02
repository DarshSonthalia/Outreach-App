"""Final schema repair

Revision ID: 003_final_schema_repair
Revises: 002_fix_leads_table
Create Date: 2024-12-30 20:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '003_final_schema_repair'
down_revision: Union[str, None] = '002_fix_leads_table'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Check if columns exist before adding to avoid 'already exists' errors
    # campaign_leads columns
    conn = op.get_bind()
    res = conn.execute(sa.text("SELECT column_name FROM information_schema.columns WHERE table_name='campaign_leads'")).fetchall()
    existing_cols = [r[0] for r in res]
    
    if 'retry_count' not in existing_cols:
        op.add_column('campaign_leads', sa.Column('retry_count', sa.Integer(), server_default='0'))
    
    if 'next_retry_at' not in existing_cols:
        op.add_column('campaign_leads', sa.Column('next_retry_at', sa.DateTime(), nullable=True))
        
    # campaigns columns
    res_c = conn.execute(sa.text("SELECT column_name FROM information_schema.columns WHERE table_name='campaigns'")).fetchall()
    existing_cols_c = [r[0] for r in res_c]
    
    if 'safety_level' not in existing_cols_c:
        # safety_level enum already exists for workspaces.safety_preference
        op.add_column('campaigns', sa.Column('safety_level', sa.Enum('LOW', 'MEDIUM', 'HIGH', name='safetylevel'), server_default='MEDIUM', nullable=True))

    if 'launched_at' not in existing_cols_c:
        op.add_column('campaigns', sa.Column('launched_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column('campaigns', 'safety_level')
    op.drop_column('campaign_leads', 'next_retry_at')
    op.drop_column('campaign_leads', 'retry_count')
