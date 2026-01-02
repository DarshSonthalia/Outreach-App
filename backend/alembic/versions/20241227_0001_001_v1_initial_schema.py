"""V1 schema with all fixes

Revision ID: 001_v1_initial_schema
Revises: 
Create Date: 2024-12-27

Includes all model changes from Fix Sets A-H:
- A1: Mailbox fields (gmail_watch_expiration, last_polled_at, status)
- C2: BookingEvent table for Calendly webhook idempotency
- D2: Message step_number + unique constraint
- D3: CampaignLead retry_count, next_retry_at
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '001_v1_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Users table
    op.create_table('users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    # Workspaces table
    op.create_table('workspaces',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('what_you_sell', sa.Text(), nullable=True),
        sa.Column('target_industry', sa.String(length=255), nullable=True),
        sa.Column('target_role', sa.String(length=255), nullable=True),
        sa.Column('target_region', sa.String(length=255), nullable=True),
        sa.Column('offer_type', sa.String(length=100), nullable=True),
        sa.Column('safety_preference', sa.Enum('LOW', 'MEDIUM', 'HIGH', name='safetylevel'), nullable=True),
        sa.Column('meeting_days', sa.JSON(), nullable=True),
        sa.Column('meeting_time_start', sa.String(length=10), nullable=True),
        sa.Column('meeting_time_end', sa.String(length=10), nullable=True),
        sa.Column('has_leads', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_workspaces_id'), 'workspaces', ['id'], unique=False)

    # Mailboxes table - Fix A1 fields included
    op.create_table('mailboxes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('workspace_id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('access_token_encrypted', sa.LargeBinary(), nullable=True),
        sa.Column('refresh_token_encrypted', sa.LargeBinary(), nullable=True),
        sa.Column('token_expiry', sa.DateTime(), nullable=True),
        sa.Column('last_history_id', sa.String(length=100), nullable=True),
        sa.Column('gmail_watch_expiration', sa.DateTime(), nullable=True),  # Fix A1
        sa.Column('last_polled_at', sa.DateTime(), nullable=True),  # Fix A1
        sa.Column('status', sa.Enum('ACTIVE', 'REAUTH_REQUIRED', 'DISCONNECTED', name='mailboxstatus'), nullable=True),  # Fix B2
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('connected_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_mailboxes_id'), 'mailboxes', ['id'], unique=False)
    op.create_index(op.f('ix_mailboxes_email'), 'mailboxes', ['email'], unique=False)

    # Domains table
    op.create_table('domains',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('workspace_id', sa.Integer(), nullable=False),
        sa.Column('mailbox_id', sa.Integer(), nullable=True),
        sa.Column('domain', sa.String(length=255), nullable=False),
        sa.Column('spf_valid', sa.Boolean(), nullable=True),
        sa.Column('spf_record', sa.Text(), nullable=True),
        sa.Column('dmarc_valid', sa.Boolean(), nullable=True),
        sa.Column('dmarc_record', sa.Text(), nullable=True),
        sa.Column('last_checked_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
        sa.ForeignKeyConstraint(['mailbox_id'], ['mailboxes.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_domains_id'), 'domains', ['id'], unique=False)
    op.create_index(op.f('ix_domains_domain'), 'domains', ['domain'], unique=False)

    # Leads table
    op.create_table('leads',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('workspace_id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('first_name', sa.String(length=100), nullable=True),
        sa.Column('last_name', sa.String(length=100), nullable=True),
        sa.Column('company', sa.String(length=255), nullable=True),
        sa.Column('title', sa.String(length=255), nullable=True),
        sa.Column('source', sa.String(length=50), nullable=True),
        sa.Column('source_url', sa.Text(), nullable=True),  # Fix G2 auditability
        sa.Column('is_valid', sa.Boolean(), nullable=True),
        sa.Column('validation_reason', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_leads_id'), 'leads', ['id'], unique=False)
    op.create_index(op.f('ix_leads_email'), 'leads', ['email'], unique=False)

    # Campaigns table
    op.create_table('campaigns',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('workspace_id', sa.Integer(), nullable=False),
        sa.Column('mailbox_id', sa.Integer(), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('subject', sa.String(length=500), nullable=True),
        sa.Column('body', sa.Text(), nullable=True),
        sa.Column('followup_enabled', sa.Boolean(), nullable=True),
        sa.Column('followup_delay_days', sa.Integer(), nullable=True),
        sa.Column('max_followups', sa.Integer(), nullable=True),
        sa.Column('followup_subject', sa.String(length=500), nullable=True),
        sa.Column('followup_body', sa.Text(), nullable=True),
        sa.Column('status', sa.Enum('DRAFT', 'RUNNING', 'PAUSED', 'THROTTLED', 'COMPLETED', name='campaignstatus'), nullable=True),
        sa.Column('pause_reason', sa.Text(), nullable=True),
        sa.Column('scheduled_start', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
        sa.ForeignKeyConstraint(['mailbox_id'], ['mailboxes.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_campaigns_id'), 'campaigns', ['id'], unique=False)
    op.create_index(op.f('ix_campaigns_status'), 'campaigns', ['status'], unique=False)

    # CampaignLeads table - Fix D3 retry fields included
    op.create_table('campaign_leads',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('campaign_id', sa.Integer(), nullable=False),
        sa.Column('lead_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.Enum('PENDING', 'IN_PROGRESS', 'SENT', 'REPLIED', 'BOUNCED', 'UNSUBSCRIBED', 'COMPLETED', name='campaignleadstatus'), nullable=True),
        sa.Column('next_action_at', sa.DateTime(), nullable=True),
        sa.Column('followup_count', sa.Integer(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=True),  # Fix D3
        sa.Column('next_retry_at', sa.DateTime(), nullable=True),  # Fix D3
        sa.Column('last_sent_at', sa.DateTime(), nullable=True),
        sa.Column('replied_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['campaign_id'], ['campaigns.id'], ),
        sa.ForeignKeyConstraint(['lead_id'], ['leads.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_campaign_leads_id'), 'campaign_leads', ['id'], unique=False)
    op.create_index(op.f('ix_campaign_leads_next_action_at'), 'campaign_leads', ['next_action_at'], unique=False)

    # Messages table - Fix D2 step_number + unique constraint
    op.create_table('messages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('campaign_lead_id', sa.Integer(), nullable=False),
        sa.Column('direction', sa.Enum('OUTBOUND', 'INBOUND', name='messagedirection'), nullable=False),
        sa.Column('step_number', sa.Integer(), nullable=False, server_default='0'),  # Fix D2
        sa.Column('gmail_message_id', sa.String(length=255), nullable=True),
        sa.Column('gmail_thread_id', sa.String(length=255), nullable=True),
        sa.Column('subject', sa.String(length=500), nullable=True),
        sa.Column('body', sa.Text(), nullable=True),
        sa.Column('classification', sa.Enum('UNSUBSCRIBE', 'NEGATIVE', 'NEUTRAL', 'BOOKING_INTENT', 'UNKNOWN', name='replyclassification'), nullable=True),
        sa.Column('sent_at', sa.DateTime(), nullable=True),
        sa.Column('received_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['campaign_lead_id'], ['campaign_leads.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('campaign_lead_id', 'step_number', 'direction', name='uq_message_idempotency')  # Fix D2
    )
    op.create_index(op.f('ix_messages_id'), 'messages', ['id'], unique=False)
    op.create_index(op.f('ix_messages_gmail_message_id'), 'messages', ['gmail_message_id'], unique=False)
    op.create_index(op.f('ix_messages_gmail_thread_id'), 'messages', ['gmail_thread_id'], unique=False)

    # Events table
    op.create_table('events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('entity_type', sa.String(length=50), nullable=False),
        sa.Column('entity_id', sa.Integer(), nullable=False),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('explanation', sa.Text(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_events_id'), 'events', ['id'], unique=False)
    op.create_index(op.f('ix_events_timestamp'), 'events', ['timestamp'], unique=False)

    # Suppression list table
    op.create_table('suppression_list',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('workspace_id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('reason', sa.Enum('UNSUBSCRIBE', 'BOUNCE', 'MANUAL', 'ROLE_EMAIL', name='suppressionreason'), nullable=False),
        sa.Column('source_details', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_suppression_list_id'), 'suppression_list', ['id'], unique=False)
    op.create_index(op.f('ix_suppression_list_email'), 'suppression_list', ['email'], unique=False)

    # Risk snapshots table
    op.create_table('risk_snapshots',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('domain_id', sa.Integer(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('sent_count', sa.Integer(), nullable=True),
        sa.Column('bounce_count', sa.Integer(), nullable=True),
        sa.Column('reply_count', sa.Integer(), nullable=True),
        sa.Column('unsubscribe_count', sa.Integer(), nullable=True),
        sa.Column('is_throttled', sa.Boolean(), nullable=True),
        sa.Column('is_paused', sa.Boolean(), nullable=True),
        sa.Column('pause_reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['domain_id'], ['domains.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_risk_snapshots_id'), 'risk_snapshots', ['id'], unique=False)
    op.create_index(op.f('ix_risk_snapshots_date'), 'risk_snapshots', ['date'], unique=False)

    # Booking events table - Fix C2
    op.create_table('booking_events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('workspace_id', sa.Integer(), nullable=False),
        sa.Column('calendly_event_uuid', sa.String(length=255), nullable=False),
        sa.Column('event_type', sa.String(length=100), nullable=False),
        sa.Column('invitee_email', sa.String(length=255), nullable=True),
        sa.Column('event_start_time', sa.DateTime(), nullable=True),
        sa.Column('payload_hash', sa.String(length=64), nullable=True),
        sa.Column('processed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_booking_events_id'), 'booking_events', ['id'], unique=False)
    op.create_index(op.f('ix_booking_events_calendly_event_uuid'), 'booking_events', ['calendly_event_uuid'], unique=True)


def downgrade() -> None:
    op.drop_table('booking_events')
    op.drop_table('risk_snapshots')
    op.drop_table('suppression_list')
    op.drop_table('events')
    op.drop_table('messages')
    op.drop_table('campaign_leads')
    op.drop_table('campaigns')
    op.drop_table('leads')
    op.drop_table('domains')
    op.drop_table('mailboxes')
    op.drop_table('workspaces')
    op.drop_table('users')
