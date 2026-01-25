"""add followup and drafts

Revision ID: 006_add_followup_and_drafts
Revises: 005_add_warmup_fields
Create Date: 2026-01-14 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '006_add_followup_and_drafts'
down_revision = '005_add_warmup_fields'
branch_labels = None
depends_on = None

def upgrade():
    conn = op.get_bind()
    
    # 1. Add columns to campaign_leads
    res_cl = conn.execute(sa.text("SELECT column_name FROM information_schema.columns WHERE table_name='campaign_leads'")).fetchall()
    cols_cl = [r[0] for r in res_cl]
    
    # Enums
    # We define them but use them carefully.
    followup_state_enum = postgresql.ENUM(
        'SCHEDULED',
        'CANCELLED',
        'COMPLETED',
        name='followupstate',
        create_type=False,
    )
    cancel_reason_enum = postgresql.ENUM(
        'REPLIED',
        'NEGATIVE_REPLY',
        'UNSUBSCRIBE',
        'BOOKED',
        'BOUNCE',
        'SUPPRESSED',
        'MANUAL',
        'SAFETY',
        name='cancelreason',
        create_type=False,
    )
    
    if 'followup_state' not in cols_cl:
        followup_state_enum.create(op.get_bind(), checkfirst=True)
        op.add_column('campaign_leads', sa.Column('followup_state', followup_state_enum, server_default='SCHEDULED', nullable=False))
        
    if 'cancelled_at' not in cols_cl:
        op.add_column('campaign_leads', sa.Column('cancelled_at', sa.DateTime(), nullable=True))
        
    if 'cancel_reason' not in cols_cl:
        cancel_reason_enum.create(op.get_bind(), checkfirst=True)
        op.add_column('campaign_leads', sa.Column('cancel_reason', cancel_reason_enum, nullable=True))
        
    if 'cancel_detail' not in cols_cl:
        op.add_column('campaign_leads', sa.Column('cancel_detail', sa.Text(), nullable=True))
        
    if 'current_step' not in cols_cl:
        op.add_column('campaign_leads', sa.Column('current_step', sa.Integer(), server_default='0', nullable=False))
        
    if 'next_scheduled_at' not in cols_cl:
        op.add_column('campaign_leads', sa.Column('next_scheduled_at', sa.DateTime(), nullable=True))
        op.create_index(op.f('ix_campaign_leads_next_scheduled_at'), 'campaign_leads', ['next_scheduled_at'], unique=False)

    if 'schedule_json' not in cols_cl:
        op.add_column('campaign_leads', sa.Column('schedule_json', sa.JSON(), nullable=True))

    # 2. Add columns to messages
    res_m = conn.execute(sa.text("SELECT column_name FROM information_schema.columns WHERE table_name='messages'")).fetchall()
    cols_m = [r[0] for r in res_m]
    
    draft_status_enum = postgresql.ENUM(
        'GENERATED',
        'EDITED',
        'SENT',
        'DISCARDED',
        'SAVED_TO_GMAIL_DRAFT',
        name='draftstatus',
        create_type=False,
    )
    
    if 'planned_send_at' not in cols_m:
        op.add_column('messages', sa.Column('planned_send_at', sa.DateTime(), nullable=True))
        
    if 'cancelled' not in cols_m:
        op.add_column('messages', sa.Column('cancelled', sa.Boolean(), server_default='false', nullable=False))
        
    if 'cancel_reason' not in cols_m:
        op.add_column('messages', sa.Column('cancel_reason', sa.String(length=255), nullable=True))
        
    if 'is_draft' not in cols_m:
        op.add_column('messages', sa.Column('is_draft', sa.Boolean(), server_default='false', nullable=False))
        
    if 'draft_status' not in cols_m:
        draft_status_enum.create(op.get_bind(), checkfirst=True)
        op.add_column('messages', sa.Column('draft_status', draft_status_enum, nullable=True))

    # Fix Unique Constraint to include is_draft
    # Note: check if constraint exists first? Standard code assumes it does if it matches model history.
    try:
        op.drop_constraint('uq_message_idempotency', 'messages', type_='unique')
        op.create_unique_constraint('uq_message_idempotency', 'messages', ['campaign_lead_id', 'step_number', 'direction', 'is_draft'])
    except Exception as e:
        print(f"Constraint update warning: {e}")

    # 3. Create reply_drafts table
    tables = conn.execute(sa.text("SELECT table_name FROM information_schema.tables WHERE table_name='reply_drafts'")).fetchall()
    if not tables:
        draft_status_enum.create(op.get_bind(), checkfirst=True)
        op.create_table('reply_drafts',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('workspace_id', sa.Integer(), nullable=False),
            sa.Column('mailbox_id', sa.Integer(), nullable=False),
            sa.Column('gmail_thread_id', sa.String(length=255), nullable=False),
            sa.Column('gmail_message_id', sa.String(length=255), nullable=True),
            sa.Column('subject', sa.Text(), nullable=True),
            sa.Column('body', sa.Text(), nullable=True),
            sa.Column('model', sa.String(length=100), nullable=False),
            sa.Column('prompt_version', sa.String(length=100), nullable=False),
            sa.Column('status', draft_status_enum, server_default='GENERATED', nullable=False),
            sa.Column('risk_flags', sa.JSON(), nullable=True),
            sa.Column('classification', sa.String(length=100), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['mailbox_id'], ['mailboxes.id'], ),
            sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_reply_drafts_gmail_thread_id'), 'reply_drafts', ['gmail_thread_id'], unique=False)
        op.create_index(op.f('ix_reply_drafts_id'), 'reply_drafts', ['id'], unique=False)

def downgrade():
    op.drop_table('reply_drafts')
    
    op.drop_column('messages', 'draft_status')
    op.drop_column('messages', 'is_draft')
    op.drop_column('messages', 'cancel_reason')
    op.drop_column('messages', 'cancelled')
    op.drop_column('messages', 'planned_send_at')
    
    op.drop_column('campaign_leads', 'schedule_json')
    op.drop_column('campaign_leads', 'next_scheduled_at')
    op.drop_column('campaign_leads', 'current_step')
    op.drop_column('campaign_leads', 'cancel_detail')
    op.drop_column('campaign_leads', 'cancel_reason')
    op.drop_column('campaign_leads', 'cancelled_at')
    op.drop_column('campaign_leads', 'followup_state')
    
    # Revert constraint
    op.drop_constraint('uq_message_idempotency', 'messages', type_='unique')
    op.create_unique_constraint('uq_message_idempotency', 'messages', ['campaign_lead_id', 'step_number', 'direction'])
