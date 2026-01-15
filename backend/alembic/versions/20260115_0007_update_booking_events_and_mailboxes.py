"""update booking events and mailboxes

Revision ID: 007_update_booking_events
Revises: 006_add_followup_and_drafts
Create Date: 2026-01-15 00:07:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '007_update_booking_events'
down_revision = '006_add_followup_and_drafts'
branch_labels = None
depends_on = None


def _column_names(conn, table_name: str) -> set:
    res = conn.execute(sa.text(
        "SELECT column_name FROM information_schema.columns WHERE table_name=:table"
    ), {"table": table_name}).fetchall()
    return {r[0] for r in res}


def _table_exists(conn, table_name: str) -> bool:
    res = conn.execute(sa.text(
        "SELECT table_name FROM information_schema.tables WHERE table_name=:table"
    ), {"table": table_name}).fetchall()
    return len(res) > 0


def upgrade():
    conn = op.get_bind()

    # Mailboxes: error_reason
    mailbox_cols = _column_names(conn, "mailboxes")
    if "error_reason" not in mailbox_cols:
        op.add_column("mailboxes", sa.Column("error_reason", sa.Text(), nullable=True))

    # Booking events: align schema
    if not _table_exists(conn, "booking_events"):
        op.create_table(
            "booking_events",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("workspace_id", sa.Integer(), sa.ForeignKey("workspaces.id"), nullable=True),
            sa.Column("mailbox_id", sa.Integer(), sa.ForeignKey("mailboxes.id"), nullable=True),
            sa.Column("calendly_event_uuid", sa.Text(), nullable=False, unique=True),
            sa.Column("invitee_email", sa.String(length=255), nullable=True),
            sa.Column("event_type", sa.String(length=100), nullable=True),
            sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("received_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        )
        op.create_index(op.f("ix_booking_events_calendly_event_uuid"), "booking_events", ["calendly_event_uuid"], unique=True)
        booking_cols = _column_names(conn, "booking_events")
    else:
        booking_cols = _column_names(conn, "booking_events")

    if "workspace_id" in booking_cols:
        try:
            op.alter_column("booking_events", "workspace_id", nullable=True)
        except Exception:
            pass

    if "mailbox_id" not in booking_cols:
        op.add_column("booking_events", sa.Column("mailbox_id", sa.Integer(), nullable=True))
        op.create_foreign_key(
            "fk_booking_events_mailbox_id",
            "booking_events",
            "mailboxes",
            ["mailbox_id"],
            ["id"]
        )

    if "payload" not in booking_cols:
        op.add_column("booking_events", sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True))

    if "received_at" not in booking_cols:
        op.add_column("booking_events", sa.Column("received_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False))

    # Remove deprecated columns if present
    for col in ["event_start_time", "payload_hash", "processed_at", "created_at"]:
        if col in booking_cols:
            try:
                op.drop_column("booking_events", col)
            except Exception:
                pass


def downgrade():
    conn = op.get_bind()
    booking_cols = _column_names(conn, "booking_events")

    if "received_at" in booking_cols:
        op.drop_column("booking_events", "received_at")
    if "payload" in booking_cols:
        op.drop_column("booking_events", "payload")
    if "mailbox_id" in booking_cols:
        op.drop_constraint("fk_booking_events_mailbox_id", "booking_events", type_="foreignkey")
        op.drop_column("booking_events", "mailbox_id")

    mailbox_cols = _column_names(conn, "mailboxes")
    if "error_reason" in mailbox_cols:
        op.drop_column("mailboxes", "error_reason")
