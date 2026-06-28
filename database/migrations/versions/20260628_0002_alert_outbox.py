"""Add alert outbox.

Revision ID: 20260628_0002
Revises: 20260628_0001
Create Date: 2026-06-28
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260628_0002"
down_revision = "20260628_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "alert_outbox",
        sa.Column("outbox_id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("event_id", sa.BigInteger(), nullable=False),
        sa.Column("channel", sa.Text(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="pending"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["events.event_id"]),
    )
    op.create_index("idx_alert_outbox_due", "alert_outbox", ["status", "next_attempt_at"])
    op.create_index("idx_alert_outbox_event", "alert_outbox", ["event_id"])
    op.create_index(
        "uq_alert_outbox_event_channel",
        "alert_outbox",
        ["event_id", "channel"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_alert_outbox_event_channel", table_name="alert_outbox")
    op.drop_index("idx_alert_outbox_event", table_name="alert_outbox")
    op.drop_index("idx_alert_outbox_due", table_name="alert_outbox")
    op.drop_table("alert_outbox")
